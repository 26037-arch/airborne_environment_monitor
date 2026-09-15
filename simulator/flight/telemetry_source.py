from __future__ import annotations

import math
from abc import ABC, abstractmethod
from dataclasses import dataclass, replace
from enum import Enum
from typing import Any, Optional

from shared.data_types import PayloadState
from shared.flight_status import FlightStatus


class FlightControllerMode(str, Enum):
    OFF = "OFF"
    MOCK = "MOCK"
    MAVLINK = "MAVLINK"


@dataclass
class FlightTelemetryConfig:
    mode: FlightControllerMode = FlightControllerMode.OFF
    endpoint: str = "udp:127.0.0.1:14550"
    baud_rate: int = 115200
    timeout_ms: int = 3000


class FlightTelemetrySource(ABC):
    """Non-blocking, read-only flight-state adapter."""

    @abstractmethod
    def poll(self, now_ms: int, state: Optional[PayloadState] = None) -> Optional[FlightStatus]:
        pass

    def close(self) -> None:
        pass


class NullFlightTelemetrySource(FlightTelemetrySource):
    def poll(self, now_ms: int, state: Optional[PayloadState] = None) -> Optional[FlightStatus]:
        return None


class MockFlightTelemetrySource(FlightTelemetrySource):
    """Deterministic status producer for adapter/integration tests only."""

    def __init__(self, connected: bool = True) -> None:
        self.connected = connected

    def poll(self, now_ms: int, state: Optional[PayloadState] = None) -> FlightStatus:
        if not self.connected or state is None:
            return FlightStatus(last_update_ms=now_ms)
        east, north, vertical = state.velocity_ground_mps
        ground_speed = math.hypot(east, north)
        heading = math.degrees(math.atan2(east, north)) % 360.0 if ground_speed else 0.0
        return FlightStatus(
            connected=True, armed=False, roll_deg=0.0, pitch_deg=0.0,
            yaw_deg=heading, latitude=state.latitude, longitude=state.longitude,
            gnss_altitude_m=state.altitude_m,
            estimated_altitude_m=state.altitude_m,
            ground_speed_mps=ground_speed, vertical_speed_mps=vertical,
            battery_voltage_v=12.0, battery_current_a=0.0,
            flight_mode=0, system_health=0, last_update_ms=now_ms,
        )


class MavlinkTelemetrySource(FlightTelemetrySource):
    """PX4/ArduPilot MAVLink telemetry decoder.

    ``recv_match(blocking=False)`` is drained with a bounded loop, so this may
    be called from a Webots controller without blocking its physics step.  The
    adapter intentionally sends no arm, mode, motor or actuator commands.
    """

    ARMED_FLAG = 128

    def __init__(self, config: FlightTelemetryConfig, connection: Any = None) -> None:
        self.config = config
        if connection is None:
            try:
                from pymavlink import mavutil
            except ModuleNotFoundError as exc:
                raise RuntimeError(
                    "MAVLINK mode에는 pymavlink가 필요합니다: pip install pymavlink"
                ) from exc
            kwargs = {"baud": config.baud_rate} if config.endpoint.upper().startswith("COM") else {}
            connection = mavutil.mavlink_connection(config.endpoint, **kwargs)
        self.connection = connection
        self.status = FlightStatus()

    @staticmethod
    def _finite(value: Any, scale: float = 1.0) -> Optional[float]:
        try:
            converted = float(value) / scale
        except (TypeError, ValueError):
            return None
        return converted if math.isfinite(converted) else None

    def consume_message(self, message: Any, now_ms: int) -> None:
        message_type = message.get_type()
        if message_type == "BAD_DATA":
            return
        updates: dict[str, object] = {"connected": True, "last_update_ms": now_ms}
        if message_type == "HEARTBEAT":
            updates.update(
                armed=bool(int(message.base_mode) & self.ARMED_FLAG),
                flight_mode=int(message.custom_mode),
                system_health=int(message.system_status),
            )
        elif message_type == "ATTITUDE":
            roll = self._finite(message.roll)
            pitch = self._finite(message.pitch)
            yaw = self._finite(message.yaw)
            if roll is not None and pitch is not None and yaw is not None:
                updates.update(
                    roll_deg=math.degrees(roll), pitch_deg=math.degrees(pitch),
                    yaw_deg=math.degrees(yaw) % 360.0,
                )
        elif message_type == "GLOBAL_POSITION_INT":
            lat = self._finite(message.lat, 1e7)
            lon = self._finite(message.lon, 1e7)
            altitude = self._finite(message.alt, 1000.0)
            estimated = self._finite(message.relative_alt, 1000.0)
            vx = self._finite(message.vx, 100.0)
            vy = self._finite(message.vy, 100.0)
            vz_down = self._finite(message.vz, 100.0)
            updates.update(
                latitude=lat, longitude=lon, gnss_altitude_m=altitude,
                estimated_altitude_m=estimated,
                ground_speed_mps=None if vx is None or vy is None else math.hypot(vx, vy),
                vertical_speed_mps=None if vz_down is None else -vz_down,
            )
        elif message_type == "GPS_RAW_INT":
            updates.update(
                latitude=self._finite(message.lat, 1e7),
                longitude=self._finite(message.lon, 1e7),
                gnss_altitude_m=self._finite(message.alt, 1000.0),
                ground_speed_mps=self._finite(message.vel, 100.0),
            )
        elif message_type == "SYS_STATUS":
            voltage = None if int(message.voltage_battery) == 0xFFFF else self._finite(message.voltage_battery, 1000.0)
            current = None if int(message.current_battery) == -1 else self._finite(message.current_battery, 100.0)
            updates.update(
                battery_voltage_v=voltage, battery_current_a=current,
                system_health=int(message.onboard_control_sensors_health),
            )
        self.status = replace(self.status, **updates)

    def poll(self, now_ms: int, state: Optional[PayloadState] = None) -> FlightStatus:
        for _ in range(64):
            message = self.connection.recv_match(blocking=False)
            if message is None:
                break
            self.consume_message(message, now_ms)
        self.status = self.status.with_timeout(now_ms, self.config.timeout_ms)
        return self.status

    def close(self) -> None:
        close = getattr(self.connection, "close", None)
        if close is not None:
            close()


def create_flight_source(config: FlightTelemetryConfig) -> FlightTelemetrySource:
    if config.mode == FlightControllerMode.OFF:
        return NullFlightTelemetrySource()
    if config.mode == FlightControllerMode.MOCK:
        return MockFlightTelemetrySource()
    return MavlinkTelemetrySource(config)

