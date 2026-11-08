"""Linux HCI monitor receiver for the Evonic firmware notification quirk.

This is a receive-only socket. Commands continue through BlueZ. No traffic is
logged; only ATT notifications on the selected fire's live connection escape
the parser. Imports are deliberately independent of Home Assistant for testing.
"""

from __future__ import annotations

import asyncio
import logging
import re
import socket
import struct
from collections.abc import Callable

_LOGGER = logging.getLogger(__name__)


class MonitorUnavailable(RuntimeError):
    """The runtime cannot open the required Linux monitor socket."""


class HciParser:
    """Filter monitor frames by controller, peer, connection and value handle."""

    def __init__(self, address: str, controller: int, callback: Callable[[bytes], None]):
        if not re.fullmatch(r"(?:[0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}", address):
            raise ValueError("Invalid Bluetooth address")
        self.address = bytes.fromhex(address.replace(":", ""))[::-1]
        self.controller = controller
        self.callback = callback
        self.value_handle: int | None = None
        self.connections: set[int] = set()
        self.fragments: dict[int, bytearray] = {}

    def feed(self, frame: bytes) -> None:
        if len(frame) < 6:
            return
        operation, controller, length = struct.unpack_from("<HHH", frame)
        if controller != self.controller or len(frame) != 6 + length:
            return
        packet = frame[6:]
        if operation == 3:  # HCI event
            self._event(packet)
        elif operation == 5:  # Received ACL data; never accept transmitted data.
            self._acl(packet)

    def _event(self, packet: bytes) -> None:
        if len(packet) < 2 or len(packet) != packet[1] + 2:
            return
        if packet[0] == 0x05 and len(packet) == 6:  # Disconnection Complete
            if packet[2] == 0:
                handle = int.from_bytes(packet[3:5], "little") & 0xFFF
                self.connections.discard(handle)
                self.fragments.pop(handle, None)
        elif packet[0] == 0x3E and len(packet) >= 21 and packet[2] in (0x01, 0x0A, 0x29):
            # LE Connection Complete / Enhanced Complete (v1/v2). Common prefix.
            handle = int.from_bytes(packet[4:6], "little") & 0xFFF
            # Invalidate any previous owner of a reused controller handle.
            self.connections.discard(handle)
            self.fragments.pop(handle, None)
            if packet[3] == 0 and packet[8:14] == self.address:
                self.connections.add(handle)

    def _acl(self, packet: bytes) -> None:
        if len(packet) < 4:
            return
        flags, length = struct.unpack_from("<HH", packet)
        handle = flags & 0xFFF
        if handle not in self.connections or len(packet) != length + 4:
            return
        boundary = (flags >> 12) & 3
        if boundary in (0, 2):
            self.fragments.pop(handle, None)
            if length < 4:
                return
            l2length, cid = struct.unpack_from("<HH", packet, 4)
            if cid != 4 or not 1 <= l2length <= 517:
                return
            self.fragments[handle] = bytearray(packet[4:])
        elif boundary == 1 and handle in self.fragments:
            self.fragments[handle].extend(packet[4:])
        else:
            return
        data = self.fragments.get(handle)
        if data is None:
            return
        expected = int.from_bytes(data[:2], "little") + 4
        if len(data) < expected:
            return
        self.fragments.pop(handle, None)
        if len(data) != expected:
            return
        att = data[4:]
        if (
            len(att) >= 3
            and att[0] == 0x1B
            and self.value_handle is not None
            and int.from_bytes(att[1:3], "little") == self.value_handle
        ):
            self.callback(bytes(att[3:]))


class HciReceiver:
    """Own one bounded monitor socket and its event-loop reader."""

    def __init__(self, parser: HciParser, failed: Callable[[Exception], None]):
        self.parser = parser
        self.failed = failed
        self._socket: socket.socket | None = None
        self._loop: asyncio.AbstractEventLoop | None = None

    def start(self) -> None:
        """Open before connecting so the connection-complete event is observed."""
        sock = None
        try:
            sock = socket.socket(socket.AF_BLUETOOTH, socket.SOCK_RAW, socket.BTPROTO_HCI)
            sock.bind((0xFFFF, 2))  # HCI_CHANNEL_MONITOR, receive-only, all adapters.
            sock.setblocking(False)
            self._loop = asyncio.get_running_loop()
            self._loop.add_reader(sock.fileno(), self._readable)
            self._socket = sock
        except (OSError, AttributeError, NotImplementedError) as error:
            if sock is not None:
                sock.close()
            raise MonitorUnavailable(
                "Linux HCI monitor access is unavailable in this runtime; "
                "the Pi workaround cannot receive state"
            ) from error

    def _readable(self) -> None:
        if self._socket is None:
            return
        try:
            # Yield after 64 frames even on a busy radio.
            for _ in range(64):
                self.parser.feed(self._socket.recv(65535))
        except BlockingIOError:
            pass
        except Exception as error:
            try:
                self.close()
            except Exception:
                _LOGGER.warning(
                    "Bluetooth receiver cleanup failed after a read error", exc_info=True
                )
            self.failed(error)

    def close(self) -> None:
        sock, self._socket = self._socket, None
        try:
            if sock is not None:
                try:
                    if self._loop is not None:
                        self._loop.remove_reader(sock.fileno())
                finally:
                    sock.close()
        finally:
            self.parser.connections.clear()
            self.parser.fragments.clear()


def check_monitor_access() -> None:
    """Open and close a monitor socket, without scanning, connecting or writing."""
    try:
        with socket.socket(socket.AF_BLUETOOTH, socket.SOCK_RAW, socket.BTPROTO_HCI) as sock:
            sock.bind((0xFFFF, 2))
    except (OSError, AttributeError, NotImplementedError) as error:
        raise MonitorUnavailable("HA Core cannot open the Linux HCI monitor") from error
