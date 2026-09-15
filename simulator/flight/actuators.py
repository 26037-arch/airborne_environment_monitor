"""Simulation-only conversion of SITL PWM outputs into Webots forces."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from shared.data_types import Vector3


@dataclass(frozen=True)
class ActuatorCommand:
    channels: tuple[float, ...]
    timestamp_s: float
    valid: bool = True
    raw_pwm: tuple[int, ...] = ()


@dataclass(frozen=True)
class ActuatorWrench:
    force_body_flu_n: Vector3 = (0.0, 0.0, 0.0)
    torque_body_flu_nm: Vector3 = (0.0, 0.0, 0.0)
    motor_forces_n: tuple[float, ...] = ()


def normalize_pwm(values: Sequence[int], pwm_min: int = 1000,
                  pwm_max: int = 2000) -> tuple[float, ...]:
    if pwm_max <= pwm_min:
        raise ValueError("pwm_max must be greater than pwm_min")
    scale = float(pwm_max - pwm_min)
    return tuple(max(0.0, min(1.0, (float(value) - pwm_min) / scale)) for value in values)


class VirtualActuatorModel:
    def calculate(self, command: ActuatorCommand) -> ActuatorWrench:
        raise NotImplementedError


class DisabledActuatorModel(VirtualActuatorModel):
    def calculate(self, command: ActuatorCommand) -> ActuatorWrench:
        return ActuatorWrench()


class ConfigurableMultirotorActuatorModel(VirtualActuatorModel):
    """Simple rotor thrust model; parameters must come from an explicit profile.

    Positions are Webots body FLU coordinates. Positive thrust points along +Z.
    This is a virtual model only and never writes to hardware endpoints.
    """
    def __init__(self, motor_count: int, motor_positions_m: Sequence[Sequence[float]],
                 motor_directions: Sequence[int], max_thrust_per_motor_n: float,
                 torque_coefficient: float) -> None:
        if motor_count <= 0 or len(motor_positions_m) != motor_count or len(motor_directions) != motor_count:
            raise ValueError("motor geometry must contain exactly motor_count entries")
        if max_thrust_per_motor_n <= 0 or torque_coefficient < 0:
            raise ValueError("invalid virtual actuator coefficients")
        self.motor_count = motor_count
        self.positions = tuple(tuple(map(float, p)) for p in motor_positions_m)
        self.directions = tuple(1 if int(d) >= 0 else -1 for d in motor_directions)
        self.max_thrust = float(max_thrust_per_motor_n)
        self.torque_coefficient = float(torque_coefficient)

    def calculate(self, command: ActuatorCommand) -> ActuatorWrench:
        if not command.valid:
            return ActuatorWrench()
        forces = tuple(self.max_thrust * value * value for value in command.channels[:self.motor_count])
        if len(forces) < self.motor_count:
            return ActuatorWrench()
        total = sum(forces)
        # r x (0,0,F) = (r_y F, -r_x F, 0)
        tx = sum(self.positions[i][1] * forces[i] for i in range(self.motor_count))
        ty = sum(-self.positions[i][0] * forces[i] for i in range(self.motor_count))
        tz = sum(self.directions[i] * self.torque_coefficient * forces[i] for i in range(self.motor_count))
        return ActuatorWrench((0.0, 0.0, total), (tx, ty, tz), forces)


def create_actuator_model(vehicle) -> VirtualActuatorModel:
    if getattr(vehicle, "type", "DISABLED") != "MULTIROTOR_SIMULATION":
        return DisabledActuatorModel()
    required = (vehicle.motor_count, vehicle.motor_positions_m, vehicle.motor_directions,
                vehicle.max_thrust_per_motor_n, vehicle.torque_coefficient)
    if any(value is None for value in required):
        raise ValueError("MULTIROTOR_SIMULATION requires an explicit, calibrated vehicle profile")
    return ConfigurableMultirotorActuatorModel(*required)
