"""Short serialized sessions, with explicit state confirmation of each change."""

from __future__ import annotations

import asyncio
import logging
import re
from collections.abc import Awaitable, Callable
from contextlib import asynccontextmanager

from bleak.exc import BleakGATTProtocolError

from .hci import HciParser, HciReceiver
from .protocol import (
    NOTIFY_UUID,
    QUERY,
    SERVICE_UUID,
    WRITE_UUID,
    FireState,
    brightness_command,
    decode_state,
    heating_command,
    power_command,
)

_LOGGER = logging.getLogger(__name__)


class EvonicError(RuntimeError):
    """A command or state query could not be confirmed."""


class CommandRejected(EvonicError):
    """No control write was attempted; optional state is freshly confirmed."""

    def __init__(self, message: str, state: FireState | None = None):
        super().__init__(message)
        self.state = state


def validate_request(*, power=None, brightness=None, target=None, level=None):
    """Reject invalid input before it can replace valid queued work."""
    groups = sum(
        (power is not None, brightness is not None, target is not None or level is not None)
    )
    try:
        if groups > 1:
            raise ValueError("Change one control per operation")
        if power is not None:
            power_command(power)
        if brightness is not None:
            brightness_command(brightness)
        if target is not None:
            heating_command(target, 1)
        if level is not None:
            heating_command(22, level)
    except ValueError as error:
        raise CommandRejected(str(error)) from error


def notification_value_handle(characteristic) -> int:
    """Resolve the two observed backend layouts, refusing ambiguous layouts.

    On this controller BlueZ's char0020 path identifies declaration 0x20,
    FFF2 value is 0x21, CCCD is 0x22. Other backends may expose value directly.
    Use the discovered CCCD to distinguish them rather than hardcoding 0x21.
    """
    descriptors = [
        descriptor
        for descriptor in characteristic.descriptors
        if descriptor.uuid.lower() == "00002902-0000-1000-8000-00805f9b34fb"
    ]
    if len(descriptors) != 1:
        raise EvonicError("Expected exactly one FFF2 notification descriptor")
    descriptor_handle = descriptors[0].handle
    if descriptor_handle - characteristic.handle not in (1, 2):
        raise EvonicError("Unrecognised FFF2 value/descriptor layout")
    return descriptor_handle - 1


class EvonicTransport:
    """No background tasks, connections or power writes at construction."""

    def __init__(
        self,
        address: str,
        get_device: Callable,
        connect: Callable[..., Awaitable],
        receiver_factory=HciReceiver,
    ):
        self.address = address
        self.get_device = get_device
        self.connect = connect
        self.receiver_factory = receiver_factory
        self.lock = asyncio.Lock()
        self.reply_timeout = 6

    @asynccontextmanager
    async def _session(self):
        device = self.get_device()
        path = device.details.get("path", "") if device is not None else ""
        match = re.match(r"^/org/bluez/hci(\d+)/dev_", path)
        if match is None:
            raise EvonicError("Fire not visible on a local Linux Bluetooth adapter")
        queue: asyncio.Queue[bytes | Exception] = asyncio.Queue(maxsize=32)

        def received(payload):
            if not queue.full():
                queue.put_nowait(payload)

        def failed(error):
            while not queue.empty():
                queue.get_nowait()
            queue.put_nowait(EvonicError(f"Bluetooth receiver failed: {type(error).__name__}"))

        parser = HciParser(self.address, int(match[1]), received)
        receiver = self.receiver_factory(parser, failed)
        client = None
        try:
            receiver.start()
            client = await self.connect(device)
            # Route selection must agree with an observed target connection on
            # our selected controller before sending even a status query.
            try:
                async with asyncio.timeout(1):
                    while not parser.connections:  # noqa: ASYNC110 - bounded to one second; observes parser-owned state
                        await asyncio.sleep(0.01)
            except TimeoutError as error:
                raise EvonicError(
                    "No target connection observed on the selected local adapter"
                ) from error
            service = client.services.get_service(SERVICE_UUID)
            write = service.get_characteristic(WRITE_UUID) if service else None
            notify = service.get_characteristic(NOTIFY_UUID) if service else None
            if write is None or notify is None:
                raise EvonicError("Fire does not expose the expected FFF0/FFF1/FFF2 service")
            parser.value_handle = notification_value_handle(notify)
            try:
                await client.start_notify(notify, lambda _, data: None)
            except BleakGATTProtocolError as error:
                if int(error.code) != 0x11:
                    raise
            yield client, write, queue
        finally:
            # Close raw receiver even if disconnect times out or this task cancels.
            try:
                receiver.close()
            except Exception:
                _LOGGER.warning(
                    "Unable to fully close the fire's Bluetooth receiver", exc_info=True
                )
            if client is not None:
                try:
                    async with asyncio.timeout(5):
                        await client.disconnect()
                except asyncio.CancelledError:
                    raise
                except Exception:
                    # Preserve the body exception, especially cancellation. A
                    # failed disconnect is observable rather than silently lost.
                    _LOGGER.warning(
                        "Fire Bluetooth disconnect did not complete cleanly", exc_info=True
                    )

    async def _write(self, client, characteristic, payload):
        try:
            await client.write_gatt_char(characteristic, payload, response=True)
        except BleakGATTProtocolError as error:
            # This error is NOT success. The subsequent matching reply is required.
            if int(error.code) != 0x0A:
                raise
        await asyncio.sleep(0.15)

    async def _query(self, client, characteristic, queue) -> FireState:
        while not queue.empty():
            item = queue.get_nowait()
            if isinstance(item, Exception):
                raise item
        await self._write(client, characteristic, QUERY)
        rejected = None
        try:
            async with asyncio.timeout(self.reply_timeout):
                while True:
                    payload = await queue.get()
                    if isinstance(payload, Exception):
                        raise payload
                    try:
                        return decode_state(payload)
                    except ValueError:
                        if len(payload) == 20 and payload[0] in (0x29, 0x30):
                            rejected = payload
                            _LOGGER.debug(
                                "Rejected fire status fields: power=%d mode=%d target_raw=%d level=%d brightness=%d",
                                payload[1],
                                payload[2],
                                int.from_bytes(payload[3:5], "big"),
                                payload[7],
                                payload[8],
                            )
        except TimeoutError as error:
            if rejected is not None:
                raise EvonicError(
                    "Fire replied with unsupported status fields; see debug log"
                ) from error
            raise

    async def execute(self, *, power=None, brightness=None, target=None, level=None) -> FireState:
        """Query or change ONE control; never retry or replay a control write."""
        validate_request(power=power, brightness=brightness, target=target, level=level)
        async with asyncio.timeout(35):
            async with self.lock:
                async with self._session() as (client, write, queue):
                    initial = await self._query(client, write, queue)
                    expected = dict(vars(initial))
                    command = None
                    if power is not None:
                        expected["power"] = power
                        command = power_command(power)
                    elif brightness is not None:
                        if not initial.power:
                            raise CommandRejected(
                                "Turn the fire on before changing brightness", initial
                            )
                        expected["brightness"] = brightness
                        command = brightness_command(brightness)
                    elif target is not None or level is not None:
                        # The native app gates these controls on deviceState.
                        # Live off-state temperature writes were not applied.
                        if not initial.power:
                            raise CommandRejected(
                                "Turn the fire on before changing temperature or heat level",
                                initial,
                            )
                        if initial.schedule_mode not in (0, 1, 2):
                            raise CommandRejected(
                                "Temperature and heat level cannot be changed in an unrecognised controller mode",
                                initial,
                            )
                        new_target = initial.target_temperature if target is None else target
                        new_level = initial.heat_level if level is None else level
                        new_mode = initial.schedule_mode if target is None else 0
                        command = heating_command(new_target, new_level, mode=new_mode)
                        expected.update(
                            target_temperature=new_target,
                            heat_level=new_level,
                            schedule_mode=new_mode,
                        )
                    wanted = FireState(**expected)
                    if command is None or wanted.control_settings == initial.control_settings:
                        return initial
                    await self._write(client, write, command)
                    # Only status queries may be repeated. Never replay a mutation.
                    for _ in range(2):
                        state = await self._query(client, write, queue)
                        if state.control_settings == wanted.control_settings:
                            return state
                    raise EvonicError(
                        "Fire did not confirm the requested state; refresh before retrying"
                    )
