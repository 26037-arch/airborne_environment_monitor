from __future__ import annotations

import math
from dataclasses import dataclass, field
from enum import Enum

import numpy as np


class WindMode(str, Enum):
    CALM = "CALM"
    CONSTANT = "CONSTANT"
    LAYERED = "LAYERED"
    GUST = "GUST_RANDOM"
    ERA5 = "ERA5_CLIMATOLOGY"


@dataclass(frozen=True)
class WindLayer:
    minimum_altitude_m: float
    maximum_altitude_m: float
    speed_mps: float
    direction_to_deg: float
    vertical_mps: float = 0.0


@dataclass
class WindConfig:
    mode: WindMode = WindMode.CALM
    speed_mps: float = 0.0
    direction_to_deg: float = 0.0
    vertical_mps: float = 0.0
    layers: list[WindLayer] = field(default_factory=list)
    mean_speed_mps: float = 0.0
    mean_direction_to_deg: float = 0.0
    gust_amplitude_mps: float = 0.0
    gust_frequency_hz: float = 0.1
    turbulence_std_mps: float = 0.0
    random_seed: int = 12345
    physics_rate_hz: float = 50.0


def _horizontal(speed: float, direction_to_deg: float) -> tuple[float, float]:
    """북쪽=0°, 시계방향인 '불어가는 방향'을 east/north로 변환합니다."""
    angle = math.radians(direction_to_deg)
    return speed * math.sin(angle), speed * math.cos(angle)


class WindModel:
    def __init__(self, config: WindConfig) -> None:
        self.config = config

    def vector(self, altitude_m: float, time_s: float,
               era5_vector: tuple[float, float, float] | None = None
               ) -> tuple[float, float, float]:
        mode = self.config.mode
        if mode == WindMode.CALM:
            return (0.0, 0.0, 0.0)
        if mode == WindMode.ERA5:
            return era5_vector if era5_vector is not None else (0.0, 0.0, 0.0)
        if mode == WindMode.LAYERED:
            for layer in self.config.layers:
                if layer.minimum_altitude_m <= altitude_m < layer.maximum_altitude_m:
                    east, north = _horizontal(layer.speed_mps, layer.direction_to_deg)
                    return east, north, layer.vertical_mps
            return (0.0, 0.0, 0.0)
        if mode == WindMode.CONSTANT:
            east, north = _horizontal(self.config.speed_mps, self.config.direction_to_deg)
            return east, north, self.config.vertical_mps

        step = int(round(time_s * self.config.physics_rate_hz))
        rng = np.random.default_rng(np.random.SeedSequence([self.config.random_seed, step]))
        gust = self.config.gust_amplitude_mps * math.sin(
            2.0 * math.pi * self.config.gust_frequency_hz * time_s
        )
        speed = max(
            0.0,
            self.config.mean_speed_mps + gust
            + float(rng.normal(0.0, self.config.turbulence_std_mps)),
        )
        direction = self.config.mean_direction_to_deg + float(
            rng.normal(0.0, self.config.turbulence_std_mps)
        )
        east, north = _horizontal(speed, direction)
        vertical = self.config.vertical_mps + float(
            rng.normal(0.0, self.config.turbulence_std_mps * 0.25)
        )
        return east, north, vertical

