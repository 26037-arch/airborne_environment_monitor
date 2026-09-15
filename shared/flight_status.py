from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Optional


@dataclass(frozen=True)
class FlightStatus:
    """Read-only state received from a flight controller.

    This type deliberately contains no arming or actuator command API.  It is
    shared by the simulator adapter, telemetry encoder and ground station.
    """

    connected: bool = False
    armed: bool = False
    roll_deg: Optional[float] = None
    pitch_deg: Optional[float] = None
    yaw_deg: Optional[float] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    gnss_altitude_m: Optional[float] = None
    estimated_altitude_m: Optional[float] = None
    ground_speed_mps: Optional[float] = None
    vertical_speed_mps: Optional[float] = None
    battery_voltage_v: Optional[float] = None
    battery_current_a: Optional[float] = None
    flight_mode: Optional[int] = None
    system_health: Optional[int] = None
    last_update_ms: int = 0

    def with_timeout(self, now_ms: int, timeout_ms: int) -> "FlightStatus":
        if not self.connected or now_ms - self.last_update_ms <= timeout_ms:
            return self
        return replace(self, connected=False, armed=False)

