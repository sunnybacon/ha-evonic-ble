"""Verify confirmation, failure, cancellation and non-replay without a fire."""

import asyncio
import importlib
import sys
import types
import unittest
from dataclasses import replace
from pathlib import Path

from bleak.exc import BleakGATTProtocolError

package = types.ModuleType("evonic_test")
package.__path__ = [str(Path(__file__).parents[1] / "custom_components/evonic_ble")]
sys.modules["evonic_test"] = package
protocol = importlib.import_module("evonic_test.protocol")
transport = importlib.import_module("evonic_test.transport")


def packet(state):
    room = 65535 if state.room_temperature is None else round(state.room_temperature * 10)
    return (
        bytes((0x29, state.power, state.schedule_mode))
        + int(state.target_temperature * 10).to_bytes(2, "big")
        + room.to_bytes(2, "big")
        + bytes((state.heat_level, state.brightness))
        + bytes(11)
    )


class Characteristic:
    # Real captured BlueZ layout; this differs from the ATT notification handle.
    handle = 0x20
    descriptors = [types.SimpleNamespace(uuid="00002902-0000-1000-8000-00805f9b34fb", handle=0x22)]


class FakeClient:
    def __init__(self, fixture):
        self.fixture = fixture
        self.services = self
        self.disconnected = False

    def get_service(self, uuid):
        return self

    def get_characteristic(self, uuid):
        return Characteristic()

    async def start_notify(self, characteristic, callback):
        raise BleakGATTProtocolError(self.fixture.subscribe_error)

    async def write_gatt_char(self, characteristic, payload, response):
        self.fixture.writes.append(bytes(payload))
        self.fixture.write_started.set()
        self.fixture.assertTrue(response)
        if payload == protocol.QUERY:
            if self.fixture.replies:
                self.fixture.receiver.parser.callback(packet(self.fixture.state))
        elif self.fixture.apply:
            if getattr(self.fixture, "room_after_write", None) is not None:
                self.fixture.state = replace(
                    self.fixture.state, room_temperature=self.fixture.room_after_write
                )
            if payload[0] == 0x39:
                self.fixture.state = replace(self.fixture.state, power=bool(payload[1]))
            elif payload[0] == 0x32:
                self.fixture.state = replace(self.fixture.state, brightness=payload[1])
            elif payload[0] == 0x31:
                self.fixture.state = replace(
                    self.fixture.state,
                    schedule_mode=payload[1],
                    target_temperature=int.from_bytes(payload[2:4], "big") / 10,
                    heat_level=payload[4],
                )
        raise BleakGATTProtocolError(self.fixture.write_error)

    async def disconnect(self):
        self.disconnected = True


class TransportTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.state = protocol.FireState(False, 0, 22, 2, 100)
        self.writes = []
        self.write_started = asyncio.Event()
        self.clients = []
        self.receivers = []
        self.replies = True
        self.apply = True
        self.subscribe_error = 0x11
        self.write_error = 0x0A
        fixture = self

        class Receiver:
            def __init__(self, parser, failed):
                self.parser = parser
                self.closed = False
                fixture.receiver = self
                fixture.receivers.append(self)

            def start(self):
                pass

            def close(self):
                self.closed = True

        async def connect(device):
            client = FakeClient(self)
            self.clients.append(client)
            self.receiver.parser.connections.add(1)
            return client

        device = types.SimpleNamespace(details={"path": "/org/bluez/hci0/dev_AA_BB_CC_DD_EE_01"})
        self.transport = transport.EvonicTransport(
            "AA:BB:CC:DD:EE:01", lambda: device, connect, Receiver
        )
        self.transport.reply_timeout = 0.02

    async def test_status_only_never_changes_power(self):
        state = await self.transport.execute()
        self.assertFalse(state.power)
        self.assertEqual(self.writes, [b"\x29"])
        self.assertTrue(self.receiver.closed)
        self.assertTrue(self.clients[0].disconnected)
        self.assertEqual(self.receiver.parser.value_handle, 0x21)

    async def test_measurement_changes_do_not_reject_confirmed_commands(self):
        for values in ({"power": True}, {"brightness": 60}, {"target": 23}, {"level": 1}):
            with self.subTest(values=values):
                self.state = protocol.FireState("power" not in values, 0, 22, 2, 100, 20.4)
                self.room_after_write = 20.6
                self.writes.clear()
                result = await self.transport.execute(**values)
                self.assertEqual(result.room_temperature, 20.6)
                self.assertEqual(len([p for p in self.writes if p != protocol.QUERY]), 1)

    async def test_status_reports_measurement_while_off(self):
        self.state = replace(self.state, room_temperature=20.4)
        result = await self.transport.execute()
        self.assertEqual(result.room_temperature, 20.4)
        self.assertFalse(result.power)
        self.assertEqual(self.writes, [protocol.QUERY])

    async def test_missing_services_fail_before_any_gatt_write_and_clean_up(self):
        original = self.transport.connect

        async def missing(device):
            client = await original(device)
            client.get_service = lambda uuid: None
            return client

        self.transport.connect = missing
        with self.assertRaisesRegex(transport.EvonicError, "expected FFF0/FFF1/FFF2"):
            await self.transport.execute(power=True)
        self.assertEqual(self.writes, [])
        self.assertTrue(self.receiver.closed)
        self.assertTrue(self.clients[-1].disconnected)

    async def test_known_errors_require_actual_matching_confirmation(self):
        state = await self.transport.execute(power=True)
        self.assertTrue(state.power)
        self.assertEqual(self.writes, [b"\x29", b"\x39\x01", b"\x29"])

    async def test_unconfirmed_write_is_never_replayed(self):
        self.apply = False
        with self.assertRaises(transport.EvonicError):
            await self.transport.execute(power=True)
        self.assertEqual(self.writes.count(b"\x39\x01"), 1)
        self.assertTrue(self.receiver.closed)
        self.assertTrue(self.clients[0].disconnected)

    async def test_error_code_without_reply_is_failure(self):
        self.replies = False
        with self.assertRaises(TimeoutError):
            await self.transport.execute(power=True)
        self.assertEqual(self.writes, [b"\x29"])
        self.assertTrue(self.receiver.closed)

    async def test_unsupported_full_status_is_distinct_from_no_reply(self):
        self.state = replace(self.state, power=2)
        with self.assertLogs("evonic_test.transport", level="DEBUG") as logs:
            with self.assertRaisesRegex(transport.EvonicError, "unsupported status fields"):
                await self.transport.execute(power=True)
        self.assertIn("power=2", logs.output[0])
        self.assertEqual(self.writes, [b"\x29"])
        self.assertTrue(self.receiver.closed)
        self.assertTrue(self.clients[0].disconnected)

    async def test_unknown_controller_mode_preserves_status_and_power_control(self):
        self.state = replace(self.state, schedule_mode=182)
        self.assertEqual(await self.transport.execute(), self.state)
        result = await self.transport.execute(power=True)
        self.assertTrue(result.power)
        self.assertEqual(result.schedule_mode, 182)
        result = await self.transport.execute(brightness=60)
        self.assertEqual(result.brightness, 60)
        self.assertEqual(result.schedule_mode, 182)

    async def test_unknown_controller_mode_blocks_heating_changes(self):
        self.state = replace(self.state, power=True, schedule_mode=182)
        for kwargs in ({"target": 23}, {"level": 1}):
            self.writes.clear()
            with self.assertRaisesRegex(
                transport.CommandRejected, "unrecognised controller mode"
            ) as caught:
                await self.transport.execute(**kwargs)
            self.assertEqual(caught.exception.state, self.state)
            self.assertEqual(self.writes, [b"\x29"])

    async def test_unexpected_protocol_errors_are_not_swallowed(self):
        self.subscribe_error = 0x05
        with self.assertRaises(BleakGATTProtocolError):
            await self.transport.execute()
        self.assertEqual(self.writes, [])
        self.assertTrue(self.receiver.closed)
        self.subscribe_error = 0x11
        self.write_error = 0x03
        with self.assertRaises(BleakGATTProtocolError):
            await self.transport.execute()

    async def test_brightness_cannot_turn_on_an_off_fire(self):
        with self.assertRaises(transport.CommandRejected) as caught:
            await self.transport.execute(brightness=60)
        self.assertEqual(self.writes, [b"\x29"])
        self.assertEqual(caught.exception.state, self.state)
        self.assertTrue(self.receiver.closed)
        self.assertTrue(self.clients[0].disconnected)

    async def test_temperature_and_level_preserve_power_and_brightness(self):
        self.state = replace(self.state, power=True)
        state = await self.transport.execute(target=21)
        self.assertEqual(state, replace(self.state, target_temperature=21))
        self.assertTrue(state.power)
        self.assertIn(bytes.fromhex("31 00 00 d2 02"), self.writes)
        state = await self.transport.execute(level=1)
        self.assertTrue(state.power)
        self.assertEqual(state.heat_level, 1)
        self.assertEqual(state.brightness, 100)

    async def test_heating_changes_while_off_only_query_and_reject(self):
        for request in ({"target": 23}, {"level": 1}, {"target": 22}, {"level": 2}):
            with self.subTest(request=request):
                self.writes.clear()
                with self.assertRaises(transport.CommandRejected) as caught:
                    await self.transport.execute(**request)
                self.assertEqual(caught.exception.state, self.state)
                self.assertEqual(self.writes, [b"\x29"])
                self.assertTrue(self.receiver.closed)
                self.assertTrue(self.clients[-1].disconnected)

    async def test_gear_only_preserves_week_and_holiday_modes(self):
        for mode in (1, 2):
            self.state = protocol.FireState(True, mode, 22, 2, 56)
            self.writes.clear()
            expected = replace(self.state, heat_level=1)
            result = await self.transport.execute(level=1)
            self.assertEqual(result, expected)
            self.assertEqual(self.writes, [b"\x29", bytes((0x31, mode, 0, 220, 1)), b"\x29"])

    async def test_temperature_explicitly_selects_manual_mode(self):
        for mode in (1, 2):
            self.state = protocol.FireState(True, mode, 22, 2, 56)
            self.writes.clear()
            expected = replace(self.state, target_temperature=23, schedule_mode=0)
            result = await self.transport.execute(target=23)
            self.assertEqual(result, expected)
            self.assertEqual(self.writes, [b"\x29", bytes.fromhex("31 00 00 e6 02"), b"\x29"])

    async def test_gear_confirmation_must_preserve_mode(self):
        self.state = protocol.FireState(True, 1, 22, 2, 56)
        original_write = self.transport._write

        async def incorrect_mode(client, characteristic, payload):
            await original_write(client, characteristic, payload)
            if payload[0] == 0x31:
                self.state = replace(self.state, schedule_mode=0)

        self.transport._write = incorrect_mode
        with self.assertRaisesRegex(transport.EvonicError, "did not confirm"):
            await self.transport.execute(level=1)
        self.assertEqual(sum(payload[0] == 0x31 for payload in self.writes), 1)
        self.assertTrue(self.receiver.closed)
        self.assertTrue(self.clients[-1].disconnected)

    async def test_invalid_input_never_opens_receiver(self):
        for kwargs in (
            {"power": 1},
            {"brightness": 101},
            {"target": 4},
            {"target": 22.5},
            {"level": 0},
            {"power": True, "brightness": 60},
        ):
            with self.assertRaises(transport.CommandRejected) as caught:
                await self.transport.execute(**kwargs)
            self.assertIsNone(caught.exception.state)
        self.assertEqual(self.receivers, [])
        self.assertEqual(self.writes, [])

    async def test_new_session_after_disconnect(self):
        await self.transport.execute()
        await self.transport.execute()
        self.assertEqual(len(self.clients), 2)
        self.assertTrue(all(c.disconnected for c in self.clients))
        self.assertTrue(all(r.closed for r in self.receivers))

    async def test_cancel_closes_receiver_and_disconnects(self):
        self.replies = False
        self.transport.reply_timeout = 10
        task = asyncio.create_task(self.transport.execute())
        await asyncio.sleep(0.01)
        task.cancel()
        with self.assertRaises(asyncio.CancelledError):
            await task
        self.assertTrue(self.receiver.closed)
        self.assertTrue(self.clients[0].disconnected)

    async def test_lost_readback_after_applied_change_is_not_replayed_on_reconnect(self):
        self.state = replace(self.state, power=True)
        original = self.transport._write

        async def lose_readback(client, characteristic, payload):
            await original(client, characteristic, payload)
            if payload[0] == 0x32:
                self.replies = False  # Write applied; its confirmation is lost.

        self.transport._write = lose_readback
        with self.assertRaises(TimeoutError):
            await self.transport.execute(brightness=40)
        self.assertEqual(self.state.brightness, 40)
        self.assertEqual(self.writes.count(b"\x32\x28"), 1)
        self.assertTrue(self.receiver.closed)
        self.assertTrue(self.clients[-1].disconnected)
        self.replies = True
        recovered = await self.transport.execute()
        self.assertEqual(recovered.brightness, 40)
        self.assertEqual(self.writes.count(b"\x32\x28"), 1)
        self.assertEqual(len(self.clients), 2)

    async def test_disconnect_before_control_write_does_not_apply_change(self):
        self.state = replace(self.state, power=True)
        initial = self.state
        original = self.transport._write

        async def disconnect_before_write(client, characteristic, payload):
            if payload[0] == 0x32:
                raise ConnectionError("Link lost before control write")
            await original(client, characteristic, payload)

        self.transport._write = disconnect_before_write
        with self.assertRaises(ConnectionError):
            await self.transport.execute(brightness=40)
        self.assertEqual(self.state, initial)
        self.assertEqual(self.writes, [b"\x29"])
        self.assertTrue(self.receiver.closed)
        self.assertTrue(self.clients[-1].disconnected)

    async def test_cancel_is_preserved_if_disconnect_cleanup_fails(self):
        original = self.transport.connect
        self.replies = False
        self.transport.reply_timeout = 10

        async def connect(device):
            client = await original(device)

            async def fail_disconnect():
                raise OSError("Disconnect failed")

            client.disconnect = fail_disconnect
            return client

        self.transport.connect = connect
        task = asyncio.create_task(self.transport.execute())
        async with asyncio.timeout(1):
            await self.write_started.wait()
        with self.assertLogs("evonic_test.transport", level="WARNING"):
            task.cancel()
            with self.assertRaises(asyncio.CancelledError):
                await task
        self.assertTrue(self.receiver.closed)

    async def test_receiver_close_failure_still_attempts_disconnect(self):
        original = self.transport.connect

        async def connect(device):
            client = await original(device)

            def fail_close():
                raise OSError("Reader cleanup failed")

            self.receiver.close = fail_close
            return client

        self.transport.connect = connect
        with self.assertLogs("evonic_test.transport", level="WARNING"):
            result = await self.transport.execute()
        self.assertEqual(result, self.state)
        self.assertTrue(self.clients[-1].disconnected)

    async def test_proxy_only_device_is_rejected(self):
        self.transport.get_device = lambda: types.SimpleNamespace(details={"source": "proxy"})
        with self.assertRaises(transport.EvonicError):
            await self.transport.execute()
        self.assertEqual(self.receivers, [])

    async def test_no_local_connection_event_blocks_all_gatt_writes(self):
        async def connect_without_local_event(device):
            client = FakeClient(self)
            self.clients.append(client)
            return client

        self.transport.connect = connect_without_local_event
        with self.assertRaisesRegex(transport.EvonicError, "No target connection"):
            await self.transport.execute(power=True)
        self.assertEqual(self.writes, [])
        self.assertTrue(self.clients[0].disconnected)
        self.assertTrue(self.receiver.closed)

    async def test_operations_are_serialized(self):
        await asyncio.gather(self.transport.execute(), self.transport.execute())
        self.assertEqual(len(self.clients), 2)
        self.assertEqual(self.writes, [b"\x29", b"\x29"])


class PacketTests(unittest.TestCase):
    def test_value_handle_backend_layouts(self):
        for handle in (0x20, 0x21):
            characteristic = types.SimpleNamespace(
                handle=handle, descriptors=Characteristic.descriptors
            )
            self.assertEqual(transport.notification_value_handle(characteristic), 0x21)
        for descriptors in ([], [types.SimpleNamespace(uuid="other", handle=0x22)]):
            with self.assertRaises(transport.EvonicError):
                transport.notification_value_handle(
                    types.SimpleNamespace(handle=0x20, descriptors=descriptors)
                )
        with self.assertRaises(transport.EvonicError):
            transport.notification_value_handle(
                types.SimpleNamespace(handle=0x10, descriptors=Characteristic.descriptors)
            )

    def test_captured_full_state(self):
        state = protocol.decode_state(
            bytes.fromhex("29 00 00 00 dc 00 cb 02 64 00 00 00 00 00 00 00 00 00 00 00")
        )
        self.assertEqual(state, protocol.FireState(False, 0, 22, 2, 100, 20.3))

    def test_optional_measurement_boundaries_preserve_other_state(self):
        for raw, expected in ((0, 0.0), (204, 20.4), (600, 60.0), (601, None), (65535, None)):
            with self.subTest(raw=raw):
                payload = bytearray(packet(protocol.FireState(False, 0, 23, 2, 100)))
                payload[5:7] = raw.to_bytes(2, "big")
                result = protocol.decode_state(bytes(payload))
                self.assertEqual(result.room_temperature, expected)
                self.assertEqual(result.control_settings, (False, 0, 23, 2, 100))

    def test_measurement_changes_remain_visible_to_coordinator_equality(self):
        before = protocol.FireState(False, 0, 23, 2, 100, 20.4)
        after = replace(before, room_temperature=20.5)
        self.assertNotEqual(before, after)
        self.assertEqual(before.control_settings, after.control_settings)
        self.assertNotEqual(before.control_settings, replace(after, brightness=60).control_settings)

    def test_invalid_packets(self):
        good = packet(protocol.FireState(False, 0, 22, 2, 100))
        for invalid in (
            good[:-1],
            good + b"x",
            b"\x39" + good[1:],
            packet(protocol.FireState(False, 0, 99, 2, 100)),
            packet(protocol.FireState(False, 0, 22, 3, 100)),
        ):
            with self.assertRaises(ValueError):
                protocol.decode_state(invalid)

    def test_heating_command_matches_app_builder(self):
        self.assertEqual(protocol.heating_command(22, 2), bytes.fromhex("31 00 00 dc 02"))
        self.assertEqual(protocol.heating_command(5, 1), bytes.fromhex("31 00 00 32 01"))
        self.assertEqual(protocol.heating_command(32, 2), bytes.fromhex("31 00 01 40 02"))


if __name__ == "__main__":
    unittest.main()
