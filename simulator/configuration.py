from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from .environment.earth_environment import AtmosphereMode
from .environment.wind_model import WindConfig, WindLayer, WindMode
from .flight.telemetry_source import FlightControllerMode, FlightTelemetryConfig
from .sensors.noise import NoiseConfig, NoiseMode
from .sensors.sensor_suite import FailureState
from .telemetry.virtual_radio import VirtualRadioConfig


@dataclass
class FlightPhysicsConfig:
    mode: str = "OFF"
    host: str = "127.0.0.1"
    port: int = 9002
    lockstep: bool = True
    timeout_ms: int = 1000
    pwm_min: int = 1000
    pwm_max: int = 2000
    lifecycle: str = "EXTERNAL"
    binary: str | None = None
    working_directory: str | None = None
    arguments: list[str] = field(default_factory=list)


@dataclass
class VehicleConfig:
    type: str = "DISABLED"
    mass_kg: float | None = None
    inertia: list[float] | None = None
    motor_count: int | None = None
    motor_positions_m: list[list[float]] | None = None
    motor_directions: list[int] | None = None
    max_thrust_per_motor_n: float | None = None
    torque_coefficient: float | None = None
    profile_label: str = "NOT CONFIGURED"


@dataclass
class FlightControllerConfig:
    telemetry: FlightTelemetryConfig = field(default_factory=FlightTelemetryConfig)
    physics_engine: FlightPhysicsConfig = field(default_factory=FlightPhysicsConfig)


@dataclass
class SimulationConfig:
    latitude: float = 37.5
    longitude: float = 127.0
    month: int = 9
    atmosphere_mode: AtmosphereMode = AtmosphereMode.EARTH_CLIMATOLOGY
    initial_altitude_m: float = 1000.0
    initial_velocity_east_mps: float = 0.0
    initial_velocity_north_mps: float = 0.0
    initial_velocity_vertical_mps: float = -5.0
    payload_mass_kg: float = 1.0
    drag_coefficient: float = 0.8
    reference_area_m2: float = 0.03
    telemetry_interval_s: float = 1.0
    telemetry_schema_version: int = 3
    sea_level_pressure_hpa: float = 1013.25
    simulation_epoch_unix: int = 1767225600
    random_seed: int = 12345
    noise: NoiseConfig = field(default_factory=NoiseConfig)
    wind: WindConfig = field(default_factory=WindConfig)
    failures: FailureState = field(default_factory=FailureState)
    radio: VirtualRadioConfig = field(default_factory=VirtualRadioConfig)
    flight_controller: FlightControllerConfig = field(default_factory=FlightControllerConfig)
    vehicle: VehicleConfig = field(default_factory=VehicleConfig)
    custom_environment: dict[str, float] = field(default_factory=dict)


def load_config(path: Path) -> SimulationConfig:
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    wind_raw = dict(raw.pop("wind", {}))
    wind_raw["mode"] = WindMode(wind_raw.get("mode", WindMode.CALM.value))
    wind_raw["layers"] = [WindLayer(**layer) for layer in wind_raw.get("layers", [])]
    noise_raw = dict(raw.pop("noise", {}))
    noise_raw["mode"] = NoiseMode(noise_raw.get("mode", NoiseMode.IDEAL.value))
    failure_raw = raw.pop("failures", {})
    radio_raw = raw.pop("radio", {})
    flight_raw = dict(raw.pop("flight_controller", {}))
    if "telemetry" not in flight_raw and "physics_engine" not in flight_raw:
        telemetry_raw = {key: flight_raw[key] for key in
                         ("mode", "endpoint", "baud_rate", "timeout_ms") if key in flight_raw}
        physics_raw = {}
    else:
        telemetry_raw = dict(flight_raw.get("telemetry", {}))
        physics_raw = dict(flight_raw.get("physics_engine", {}))
    telemetry_raw["mode"] = FlightControllerMode(
        telemetry_raw.get("mode", FlightControllerMode.OFF.value))
    vehicle_raw = dict(raw.pop("vehicle", {}))
    raw["atmosphere_mode"] = AtmosphereMode(
        raw.get("atmosphere_mode", AtmosphereMode.EARTH_CLIMATOLOGY.value))
    config = SimulationConfig(
        **raw, wind=WindConfig(**wind_raw), noise=NoiseConfig(**noise_raw),
        failures=FailureState(**failure_raw), radio=VirtualRadioConfig(**radio_raw),
        flight_controller=FlightControllerConfig(
            FlightTelemetryConfig(**telemetry_raw), FlightPhysicsConfig(**physics_raw)),
        vehicle=VehicleConfig(**vehicle_raw),
    )
    if config.payload_mass_kg <= 0 or config.reference_area_m2 < 0:
        raise ValueError("payload mass must be positive and reference area non-negative")
    if config.telemetry_interval_s <= 0:
        raise ValueError("telemetry interval must be positive")
    if config.telemetry_schema_version not in {1, 2, 3}:
        raise ValueError("telemetry_schema_version must be 1, 2, or 3")
    if config.sea_level_pressure_hpa <= 0 or not 0 <= config.simulation_epoch_unix <= 0xFFFFFFFF:
        raise ValueError("invalid pressure or simulation epoch")
    if config.flight_controller.telemetry.timeout_ms <= 0:
        raise ValueError("flight telemetry timeout must be positive")
    physics = config.flight_controller.physics_engine
    if physics.mode not in {"OFF", "ARDUPILOT_SITL_JSON"}:
        raise ValueError("physics_engine.mode must be OFF or ARDUPILOT_SITL_JSON")
    if not 1 <= physics.port <= 65535 or physics.timeout_ms <= 0 or physics.pwm_max <= physics.pwm_min:
        raise ValueError("invalid ArduPilot JSON transport configuration")
    if physics.lifecycle not in {"EXTERNAL", "MANAGED"}:
        raise ValueError("physics_engine.lifecycle must be EXTERNAL or MANAGED")
    return config
