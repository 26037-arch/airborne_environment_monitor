"""Official ArduPilot SITL JSON physics transport (UDP port 9002)."""
from __future__ import annotations

import json
import math
import socket
import struct
import subprocess
from dataclasses import asdict, dataclass
from typing import Any, Optional

from shared.data_types import EnvironmentSample, PayloadState, Vector3
from .actuators import ActuatorCommand, normalize_pwm
from .frames import (webots_acceleration_to_body_frd,
                     webots_angular_velocity_to_body_frd,
                     webots_enu_to_ned_position, webots_enu_to_ned_vector,
                     webots_orientation_to_ned_quaternion)

MAGIC_16 = 18458
MAGIC_32 = 29569
PACKET_16 = struct.Struct("<HHI16H")
PACKET_32 = struct.Struct("<HHI32H")


@dataclass(frozen=True)
class PhysicsInput:
    timestamp_s: float
    position_ned_m: Vector3
    velocity_ned_mps: Vector3
    quaternion_wxyz: tuple[float, float, float, float]
    gyro_frd_rps: Vector3
    accel_frd_mps2: Vector3
    wind_ned_mps: Vector3

    @classmethod
    def from_webots(cls, state: PayloadState, environment: EnvironmentSample) -> "PhysicsInput":
        if state.linear_acceleration_world_mps2 is None or state.angular_velocity_world_rps is None:
            raise ValueError("ArduPilot physics requires Webots acceleration and angular velocity")
        result = cls(
            float(state.time_s), webots_enu_to_ned_position(state.position_m),
            webots_enu_to_ned_vector(state.velocity_ground_mps),
            webots_orientation_to_ned_quaternion(state.orientation_axis_angle),
            webots_angular_velocity_to_body_frd(state.angular_velocity_world_rps, state.orientation_axis_angle),
            webots_acceleration_to_body_frd(state.linear_acceleration_world_mps2, state.orientation_axis_angle),
            webots_enu_to_ned_vector(environment.wind_vector),
        )
        if not all(math.isfinite(v) for v in result.scalars()):
            raise ValueError("physics state contains NaN or infinity")
        return result

    def scalars(self) -> tuple[float, ...]:
        return (self.timestamp_s, *self.position_ned_m, *self.velocity_ned_mps,
                *self.quaternion_wxyz, *self.gyro_frd_rps, *self.accel_frd_mps2,
                *self.wind_ned_mps)

    def to_packet(self, *, no_time_sync: bool = False,
                  no_lockstep: bool = False, optional: Optional[dict[str, Any]] = None) -> bytes:
        data: dict[str, Any] = {
            "timestamp": self.timestamp_s,
            "imu": {"gyro": self.gyro_frd_rps, "accel_body": self.accel_frd_mps2},
            "position": self.position_ned_m,
            "velocity": self.velocity_ned_mps,
            "quaternion": self.quaternion_wxyz,
            "velocity_wind": self.wind_ned_mps,
            "no_time_sync": no_time_sync,
            "no_lockstep": no_lockstep,
        }
        if optional:
            data.update(optional)
        # ArduPilot accepts a JSON object preceded and terminated by a newline.
        return ("\n" + json.dumps(data, separators=(",", ":"), allow_nan=False) + "\n").encode("ascii")


@dataclass
class ArduPilotLinkStatus:
    sitl_process_running: Optional[bool] = None
    physics_connected: bool = False
    last_physics_timestamp_s: Optional[float] = None
    last_actuator_timestamp_s: Optional[float] = None
    physics_packet_count: int = 0
    actuator_packet_count: int = 0
    timeout_count: int = 0
    invalid_packet_count: int = 0
    frame_rate_hz: Optional[int] = None
    frame_count: Optional[int] = None
    last_error: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class FlightPhysicsEngine:
    def step(self, physics: PhysicsInput) -> ActuatorCommand:
        raise NotImplementedError
    def close(self) -> None:
        pass


class NullFlightPhysicsEngine(FlightPhysicsEngine):
    status = ArduPilotLinkStatus()
    def step(self, physics: PhysicsInput) -> ActuatorCommand:
        return ActuatorCommand((), physics.timestamp_s, False)


class ArduPilotSitlEngine(FlightPhysicsEngine):
    """Bounded UDP exchange. It never exposes or forwards a hardware endpoint."""
    def __init__(self, host: str = "127.0.0.1", port: int = 9002,
                 timeout_ms: int = 1000, lockstep: bool = True,
                 pwm_min: int = 1000, pwm_max: int = 2000,
                 sock: Optional[socket.socket] = None) -> None:
        self.host, self.port = host, port
        self.timeout_s, self.lockstep = timeout_ms / 1000.0, lockstep
        self.pwm_min, self.pwm_max = pwm_min, pwm_max
        self.socket = sock or socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        if sock is None:
            self.socket.bind((host, port))
        self.socket.settimeout(self.timeout_s if lockstep else 0.0)
        self.peer: Optional[tuple[str, int]] = None
        self.status = ArduPilotLinkStatus()
        self._last_timestamp = -math.inf
        self._last_frame_count: Optional[int] = None
        self.process: Optional[subprocess.Popen] = None

    def start_process(self, binary: str, arguments: list[str],
                      working_directory: Optional[str] = None) -> None:
        if not binary:
            raise ValueError("MANAGED lifecycle requires physics_engine.binary")
        self.process = subprocess.Popen(
            [binary, *arguments], cwd=working_directory or None,
            stdin=subprocess.DEVNULL, shell=False,
        )
        self.status.sitl_process_running = True

    def _receive(self, timestamp_s: float) -> ActuatorCommand:
        try:
            packet, peer = self.socket.recvfrom(256)
        except (TimeoutError, socket.timeout, BlockingIOError):
            self.status.timeout_count += 1
            self.status.physics_connected = False
            self.status.last_error = "ArduPilot JSON actuator timeout"
            return ActuatorCommand((), timestamp_s, False)
        try:
            if len(packet) == PACKET_16.size:
                values = PACKET_16.unpack(packet); expected = MAGIC_16
            elif len(packet) == PACKET_32.size:
                values = PACKET_32.unpack(packet); expected = MAGIC_32
            else:
                raise ValueError(f"unexpected actuator packet size {len(packet)}")
            magic, rate, frame_count, *pwm = values
            if magic != expected:
                raise ValueError(f"invalid actuator magic {magic}")
            if self._last_frame_count is not None and frame_count < self._last_frame_count:
                self.status.last_error = "ArduPilot SITL frame counter reset"
            self._last_frame_count = frame_count
            self.peer = peer
            self.status.physics_connected = True
            self.status.last_actuator_timestamp_s = timestamp_s
            self.status.actuator_packet_count += 1
            self.status.frame_rate_hz = rate
            self.status.frame_count = frame_count
            return ActuatorCommand(normalize_pwm(pwm, self.pwm_min, self.pwm_max), timestamp_s, True, tuple(pwm))
        except (ValueError, struct.error) as exc:
            self.status.invalid_packet_count += 1
            self.status.physics_connected = False
            self.status.last_error = str(exc)
            return ActuatorCommand((), timestamp_s, False)

    def step(self, physics: PhysicsInput) -> ActuatorCommand:
        if self.process is not None and self.process.poll() is not None:
            self.status.sitl_process_running = False
            self.status.last_error = f"managed ArduPilot exited with code {self.process.returncode}"
            return ActuatorCommand((), physics.timestamp_s, False)
        if physics.timestamp_s + 1e-12 < self._last_timestamp:
            self.peer = None
            self._last_frame_count = None
            self.status.physics_connected = False
            self.status.last_error = "Webots simulation time reset; stale actuator discarded"
            self._last_timestamp = physics.timestamp_s
            return ActuatorCommand((), physics.timestamp_s, False)
        self._last_timestamp = physics.timestamp_s
        command = self._receive(physics.timestamp_s)
        if command.valid and self.peer is not None:
            try:
                self.socket.sendto(physics.to_packet(no_lockstep=not self.lockstep), self.peer)
                self.status.physics_packet_count += 1
                self.status.last_physics_timestamp_s = physics.timestamp_s
                self.status.last_error = None
            except OSError as exc:
                self.status.physics_connected = False
                self.status.last_error = str(exc)
                return ActuatorCommand((), physics.timestamp_s, False)
        return command

    def close(self) -> None:
        self.socket.close()
        if self.process is not None and self.process.poll() is None:
            self.process.terminate()
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait(timeout=2)
        self.status.sitl_process_running = False
