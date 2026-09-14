from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Optional

from shared.data_types import PayloadState

from .noise import NoiseConfig, NoiseMode, generator


@dataclass(frozen=True)
class GnssReading:
    latitude: Optional[float]
    longitude: Optional[float]
    altitude_m: Optional[float]
    speed_mps: Optional[float]
    course_deg: Optional[float]
    ok: bool


class GnssModel:
    """기본 DATASHEET preset은 문서화된 u-blox NEO-M8 가정입니다."""

    def __init__(self, config: NoiseConfig, horizontal_accuracy_m: float = 2.5,
                 altitude_accuracy_m: float = 4.0, speed_accuracy_mps: float = 0.05) -> None:
        self.config = config
        self.horizontal_accuracy_m = horizontal_accuracy_m
        self.altitude_accuracy_m = altitude_accuracy_m
        self.speed_accuracy_mps = speed_accuracy_mps
        self.rng = generator(config, 8)

    def read(self, state: PayloadState, dropout: bool = False) -> GnssReading:
        if dropout:
            return GnssReading(None, None, None, None, None, False)
        east, north, _vertical = state.velocity_ground_mps
        speed = math.hypot(east, north)
        course = math.degrees(math.atan2(east, north)) % 360.0 if speed > 1e-9 else 0.0
        latitude, longitude, altitude = state.latitude, state.longitude, state.altitude_m
        if self.config.enabled and self.config.mode != NoiseMode.IDEAL:
            scale = self.config.strength
            horizontal = self.horizontal_accuracy_m if self.config.mode == NoiseMode.DATASHEET else 1.0
            altitude_std = self.altitude_accuracy_m if self.config.mode == NoiseMode.DATASHEET else 1.0
            speed_std = self.speed_accuracy_mps if self.config.mode == NoiseMode.DATASHEET else 0.1
            north_error, east_error = self.rng.normal(0.0, horizontal / 3.0 * scale, 2)
            latitude += float(north_error) / 111_320.0
            longitude += float(east_error) / max(1.0, 111_320.0 * math.cos(math.radians(latitude)))
            altitude += float(self.rng.normal(0.0, altitude_std / 3.0 * scale))
            speed = max(0.0, speed + float(self.rng.normal(0.0, speed_std / 3.0 * scale)))
        return GnssReading(latitude, longitude, altitude, speed, course, True)

