"""Captured-format and adversarial frames, independent of HA and a radio."""

import importlib.util
import struct
import unittest
from pathlib import Path
from unittest.mock import Mock

spec = importlib.util.spec_from_file_location(
    "evonic_hci", Path(__file__).parents[1] / "custom_components/evonic_ble/hci.py"
)
hci = importlib.util.module_from_spec(spec)
spec.loader.exec_module(hci)

ADDRESS = "AA:BB:CC:DD:EE:01"
STATE = bytes.fromhex("29 00 00 00 dc 00 c9 02 64")


def frame(operation, payload, controller=0):
    return struct.pack("<HHH", operation, controller, len(payload)) + payload


def connected(handle=1, address=ADDRESS, subtype=1, status=0):
    data = bytes((subtype, status)) + struct.pack("<HBB", handle, 0, 0)
    data += bytes.fromhex(address.replace(":", ""))[::-1] + bytes(7)
    return frame(3, bytes((0x3E, len(data))) + data)


def acl(data, handle=1, boundary=2, operation=5, controller=0):
    return frame(
        operation, struct.pack("<HH", handle | boundary << 12, len(data)) + data, controller
    )


def notification(value=0x21):
    att = b"\x1b" + struct.pack("<H", value) + STATE
    return struct.pack("<HH", len(att), 4) + att


class HciFiltering(unittest.TestCase):
    def setUp(self):
        self.received = []
        self.parser = hci.HciParser(ADDRESS, 0, self.received.append)
        self.parser.value_handle = 0x21

    def test_requires_target_connection_and_discovered_value_handle(self):
        self.parser.feed(acl(notification()))
        self.assertEqual(self.received, [])
        self.parser.feed(connected())
        self.parser.feed(acl(notification(0x20)))
        self.assertEqual(self.received, [])
        self.parser.feed(acl(notification()))
        self.assertEqual(self.received, [STATE])

    def test_enhanced_connection_complete(self):
        self.parser.feed(connected(subtype=0x0A))
        self.parser.feed(acl(notification()))
        self.assertEqual(self.received, [STATE])

    def test_other_peer_adapter_transmit_and_handle_are_ignored(self):
        self.parser.feed(connected(address="00:11:22:33:44:55"))
        self.parser.feed(acl(notification()))
        self.parser.feed(connected())
        for kwargs in ({"controller": 1}, {"operation": 4}, {"handle": 2}):
            self.parser.feed(acl(notification(), **kwargs))
        self.assertEqual(self.received, [])

    def test_failed_connection_is_not_accepted(self):
        self.parser.feed(connected(status=1))
        self.parser.feed(acl(notification()))
        self.assertEqual(self.received, [])

    def test_disconnect_and_handle_reuse_cannot_leak_another_peer(self):
        self.parser.feed(connected())
        self.parser.feed(frame(3, b"\x05\x04\x00\x01\x00\x13"))
        self.parser.feed(acl(notification()))
        self.parser.feed(connected(address="00:11:22:33:44:55"))
        self.parser.feed(acl(notification()))
        self.assertEqual(self.received, [])
        self.parser.feed(connected())
        self.parser.feed(acl(notification()))
        self.assertEqual(self.received, [STATE])

    def test_fragmented_packet(self):
        self.parser.feed(connected())
        packet = notification()
        self.parser.feed(acl(packet[:8]))
        self.assertEqual(self.received, [])
        self.parser.feed(acl(packet[8:], boundary=1))
        self.assertEqual(self.received, [STATE])

    def test_disconnect_discards_partial_packet(self):
        self.parser.feed(connected())
        self.parser.feed(acl(notification()[:8]))
        self.parser.feed(frame(3, b"\x05\x04\x00\x01\x00\x13"))
        self.parser.feed(connected())
        self.parser.feed(acl(notification()[8:], boundary=1))
        self.assertEqual(self.received, [])

    def test_malformed_and_oversized_frames_are_ignored(self):
        self.parser.feed(connected())
        for packet in (
            b"",
            b"\x05",
            acl(notification())[:-1],
            acl(struct.pack("<HH", 65535, 4)),
            acl(notification() + b"x"),
            acl(notification()[4:], boundary=1),
        ):
            self.parser.feed(packet)
        self.assertEqual(self.received, [])

    def test_requires_att_channel_and_notification_opcode(self):
        self.parser.feed(connected())
        packet = bytearray(notification())
        packet[2] = 5
        self.parser.feed(acl(bytes(packet)))
        packet = bytearray(notification())
        packet[4] = 0x12
        self.parser.feed(acl(bytes(packet)))
        self.assertEqual(self.received, [])


class ReceiverCleanupTests(unittest.TestCase):
    def setUp(self):
        self.parser = hci.HciParser(ADDRESS, 0, lambda payload: None)
        self.parser.connections.add(1)
        self.parser.fragments[1] = bytearray(b"partial")
        self.failed = Mock()
        self.receiver = hci.HciReceiver(self.parser, self.failed)
        self.sock = Mock()
        self.sock.fileno.return_value = 42
        self.loop = Mock()
        self.receiver._socket = self.sock
        self.receiver._loop = self.loop

    def test_socket_and_peer_state_are_cleared_even_if_reader_removal_fails(self):
        self.loop.remove_reader.side_effect = RuntimeError("Reader removal failed")
        with self.assertRaises(RuntimeError):
            self.receiver.close()
        self.sock.close.assert_called_once_with()
        self.assertIsNone(self.receiver._socket)
        self.assertEqual(self.parser.connections, set())
        self.assertEqual(self.parser.fragments, {})
        self.receiver.close()  # Idempotent after failed cleanup.
        self.sock.close.assert_called_once_with()

    def test_read_failure_notifies_transport_even_if_cleanup_also_fails(self):
        original = OSError("Receive failed")
        self.sock.recv.side_effect = original
        self.loop.remove_reader.side_effect = RuntimeError("Reader removal failed")
        with self.assertLogs("evonic_hci", level="WARNING"):
            self.receiver._readable()
        self.failed.assert_called_once_with(original)
        self.sock.close.assert_called_once_with()
        self.assertIsNone(self.receiver._socket)


if __name__ == "__main__":
    unittest.main()
