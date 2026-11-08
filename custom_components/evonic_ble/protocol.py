"""Commands recovered from Evonic BLE 2.8; no schedules or clock writes."""

import math
from dataclasses import dataclass

SERVICE_UUID = "0000fff0-0000-1000-8000-00805f9b34fb"
WRITE_UUID = "0000fff1-0000-1000-8000-00805f9b34fb"
NOTIFY_UUID = "0000fff2-0000-1000-8000-00805f9b34fb"
QUERY = b"\x29"


@dataclass(frozen=True)
class FireState:
    power: bool
    schedule_mode: int
    target_temperature: float
    heat_level: int
    brightness: int
    room_temperature: float | None = None

    @property
    def control_settings(self):
        """Fields a command must preserve/confirm; measured temperature can drift."""
        return (
            self.power,
            self.schedule_mode,
            self.target_temperature,
            self.heat_level,
            self.brightness,
        )


def decode_state(payload: bytes) -> FireState:
    if len(payload) != 20 or payload[0] not in (0x29, 0x30):
        raise ValueError("Not a complete Evonic state packet")
    target = int.from_bytes(payload[3:5], "big") / 10
    # Preserve unrecognised controller modes (182 observed after touchscreen
    # use). One unknown optional field must not hide otherwise valid status.
    if (
        payload[1] not in (0, 1)
        or not 5 <= target <= 32
        or payload[7] not in (0, 1, 2)
        or payload[8] > 100
    ):
        raise ValueError("Invalid Evonic state fields")
    room = int.from_bytes(payload[5:7], "big") / 10
    # Conservative unsigned indoor range, not a documented firmware limit.
    # Missing/sentinel/implausible readings must not invalidate other controls.
    room = room if 0 <= room <= 60 else None
    return FireState(bool(payload[1]), payload[2], target, payload[7], payload[8], room)


def power_command(power: bool) -> bytes:
    if type(power) is not bool:
        raise ValueError("Power must be a boolean")
    return bytes((0x39, int(power)))


def brightness_command(percent: int) -> bytes:
    if type(percent) is not int or not 0 <= percent <= 100:
        raise ValueError("Brightness must be a whole percentage, 0 to 100")
    return bytes((0x32, percent))


def heating_command(target: float, level: int, *, mode: int = 0) -> bytes:
    if (
        type(target) not in (int, float)
        or not math.isfinite(target)
        or not 5 <= target <= 32
        or int(target) != target
    ):
        raise ValueError("Temperature must be a whole degree, 5 to 32 C")
    if type(level) is not int or level not in (1, 2):
        raise ValueError("Heating level must be 1 (low) or 2 (high)")
    if type(mode) is not int or not 0 <= mode <= 255:
        raise ValueError("Controller mode must be a raw byte, 0 to 255")
    # App temperature changes use 0; gear-only changes preserve the mode byte.
    return bytes((0x31, mode)) + int(target * 10).to_bytes(2, "big") + bytes((level,))
