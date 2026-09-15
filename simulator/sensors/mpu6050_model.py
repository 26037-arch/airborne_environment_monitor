from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Optional

from shared.data_types import PayloadState, Vector3

from .noise import NoiseConfig, NoiseMode, generator


@dataclass(frozen=True)
class Mpu6050Reading:
    acceleration_mps2: tuple[Optional[float], Optional[float], Optional[float]]
    gyro_dps: tuple[Optional[float], Optional[float], Optional[float]]
    ok: bool


def _world_to_body(vector: Vector3,
                   axis_angle: tuple[float, float, float, float]) -> Vector3:
    x, y, z, angle = axis_angle
    norm = math.sqrt(x * x + y * y + z * z)
    if norm < 1e-12 or abs(angle) < 1e-12:
        return vector
    x, y, z = x / norm, y / norm, z / norm
    # Rodrigues rotation by -angle converts a world vector into payload axes.
    cosine, sine = math.cos(angle), -math.sin(angle)
    vx, vy, vz = vector
    cross = (y * vz - z * vy, z * vx - x * vz, x * vy - y * vx)
    dot = x * vx + y * vy + z * vz
    return tuple(
        vector[i] * cosine + cross[i] * sine + (x, y, z)[i] * dot * (1.0 - cosine)
        for i in range(3)
    )


class Mpu6050Model:
    def __init__(self, config: NoiseConfig) -> None:
        self.config = config
        self.rng = generator(config, 6050)

    def read(self, state: PayloadState, failed: bool = False) -> Mpu6050Reading:
        if (failed or state.linear_acceleration_world_mps2 is None or
                state.angular_velocity_world_rps is None):
            missing = (None, None, None)
            return Mpu6050Reading(missing, missing, False)
        # An accelerometer measures specific force. In ENU, gravity points -Z.
        world_specific_force = (
            state.linear_acceleration_world_mps2[0],
            state.linear_acceleration_world_mps2[1],
            state.linear_acceleration_world_mps2[2] + 9.80665,
        )
        acceleration = list(_world_to_body(world_specific_force, state.orientation_axis_angle))
        gyro = [math.degrees(value) for value in _world_to_body(
            state.angular_velocity_world_rps, state.orientation_axis_angle
        )]
        if self.config.enabled and self.config.mode != NoiseMode.IDEAL:
            scale = self.config.strength / 3.0
            for index in range(3):
                acceleration[index] += float(self.rng.normal(0.0, 0.1 * scale))
                gyro[index] += float(self.rng.normal(0.0, 1.0 * scale))
        values = acceleration + gyro
        if not all(math.isfinite(value) for value in values):
            missing = (None, None, None)
            return Mpu6050Reading(missing, missing, False)
        return Mpu6050Reading(tuple(acceleration), tuple(gyro), True)
