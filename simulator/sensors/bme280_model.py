from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from shared.data_types import EnvironmentSample

from .noise import NoiseConfig, NoiseMode, generator


@dataclass(frozen=True)
class BmeReading:
    temperature_C: Optional[float]
    humidity_pct: Optional[float]
    pressure_hPa: Optional[float]
    ok: bool


class Bme280Model:
    """Bosch accuracy limits를 ±3σ Gaussian으로 해석한 교육용 모델."""

    def __init__(self, config: NoiseConfig, custom_std: tuple[float, float, float] = (0.5, 3.0, 1.0)) -> None:
        self.config = config
        self.custom_std = custom_std
        self.rng = generator(config, 280)

    def read(self, environment: EnvironmentSample, failed: bool = False) -> BmeReading:
        if failed:
            return BmeReading(None, None, None, False)
        values: list[Optional[float]] = [
            environment.temperature_C,
            environment.relative_humidity_pct,
            environment.pressure_hPa,
        ]
        if self.config.enabled and self.config.mode != NoiseMode.IDEAL:
            accuracy = (0.5, 3.0, 1.0) if self.config.mode == NoiseMode.DATASHEET else self.custom_std
            for index, value in enumerate(values):
                if value is not None:
                    sigma = accuracy[index] / 3.0 * self.config.strength
                    values[index] = value + float(self.rng.normal(0.0, sigma))
        if values[1] is not None:
            values[1] = min(100.0, max(0.0, values[1]))
        return BmeReading(values[0], values[1], values[2], all(v is not None for v in values))

