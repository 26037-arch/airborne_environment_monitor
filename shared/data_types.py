from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


Vector3 = tuple[float, float, float]


@dataclass(frozen=True)
class EnvironmentSample:
    altitude_m: float
    temperature_K: float
    pressure_Pa: float
    air_density_kgm3: float
    relative_humidity_pct: Optional[float]
    pm1_ugm3: Optional[float]
    pm25_ugm3: Optional[float]
    pm10_ugm3: Optional[float]
    wind_east_mps: float
    wind_north_mps: float
    wind_vertical_mps: float
    mode: str
    provenance: dict[str, object] = field(default_factory=dict)

    @property
    def temperature_C(self) -> float:
        return self.temperature_K - 273.15

    @property
    def pressure_hPa(self) -> float:
        return self.pressure_Pa / 100.0

    @property
    def wind_vector(self) -> Vector3:
        return (self.wind_east_mps, self.wind_north_mps, self.wind_vertical_mps)


@dataclass(frozen=True)
class PayloadState:
    time_s: float
    latitude: float
    longitude: float
    altitude_m: float
    position_m: Vector3
    velocity_ground_mps: Vector3
    orientation_axis_angle: tuple[float, float, float, float]


@dataclass(frozen=True)
class SensorReadings:
    temperature_C: Optional[float]
    humidity_pct: Optional[float]
    pressure_hPa: Optional[float]
    pm1_ugm3: Optional[float]
    pm25_ugm3: Optional[float]
    pm4_ugm3: Optional[float]
    pm10_ugm3: Optional[float]
    latitude: Optional[float]
    longitude: Optional[float]
    gps_altitude_m: Optional[float]
    gps_speed_mps: Optional[float]
    gps_course_deg: Optional[float]
    bme_ok: bool
    sps_ok: bool
    gps_ok: bool
    sd_ok: bool

