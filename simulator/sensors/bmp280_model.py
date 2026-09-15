from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Optional

from shared.data_types import EnvironmentSample

from .noise import NoiseConfig, NoiseMode, generator


@dataclass(frozen=True)
class Bmp280Reading:
    pressure_hPa: Optional[float]
    barometric_altitude_m: Optional[float]
    ok: bool


class Bmp280Model:
    def __init__(self, config: NoiseConfig, sea_level_pressure_hpa: float) -> None:
        self.config = config
        self.sea_level_pressure_hpa = sea_level_pressure_hpa
        self.rng = generator(config, 281)

    def read(self, environment: EnvironmentSample, failed: bool = False) -> Bmp280Reading:
        if failed:
            return Bmp280Reading(None, None, False)
        pressure = environment.pressure_hPa
        if self.config.enabled and self.config.mode != NoiseMode.IDEAL:
            pressure += float(self.rng.normal(0.0, 1.0 / 3.0 * self.config.strength))
        if pressure <= 0.0 or self.sea_level_pressure_hpa <= 0.0:
            return Bmp280Reading(None, None, False)
        altitude = 44330.0 * (1.0 - math.pow(pressure / self.sea_level_pressure_hpa, 0.1903))
        return Bmp280Reading(pressure, altitude, math.isfinite(altitude))
