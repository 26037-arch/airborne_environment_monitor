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
    random_seed: int = 12345
    noise: NoiseConfig = field(default_factory=NoiseConfig)
    wind: WindConfig = field(default_factory=WindConfig)
    failures: FailureState = field(default_factory=FailureState)
    radio: VirtualRadioConfig = field(default_factory=VirtualRadioConfig)
    flight_controller: FlightTelemetryConfig = field(default_factory=FlightTelemetryConfig)
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
    flight_raw["mode"] = FlightControllerMode(
        flight_raw.get("mode", FlightControllerMode.OFF.value)
    )
    raw["atmosphere_mode"] = AtmosphereMode(
        raw.get("atmosphere_mode", AtmosphereMode.EARTH_CLIMATOLOGY.value)
    )
    config = SimulationConfig(
        **raw,
        wind=WindConfig(**wind_raw),
        noise=NoiseConfig(**noise_raw),
        failures=FailureState(**failure_raw),
        radio=VirtualRadioConfig(**radio_raw),
        flight_controller=FlightTelemetryConfig(**flight_raw),
    )
    if config.payload_mass_kg <= 0 or config.reference_area_m2 < 0:
        raise ValueError("payload mass는 양수, reference area는 0 이상이어야 합니다")
    if config.telemetry_interval_s <= 0:
        raise ValueError("telemetry interval은 양수여야 합니다")
    if config.flight_controller.timeout_ms <= 0:
        raise ValueError("flight controller timeout은 양수여야 합니다")
    return config
