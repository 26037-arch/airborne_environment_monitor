from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from shared.data_types import EnvironmentSample

from .noise import NoiseConfig, NoiseMode, generator


@dataclass(frozen=True)
class Aht20Reading:
    temperature_C: Optional[float]
    humidity_pct: Optional[float]
    ok: bool


class Aht20Model:
    def __init__(self, config: NoiseConfig) -> None:
        self.config = config
        self.rng = generator(config, 20)

    def read(self, environment: EnvironmentSample, failed: bool = False) -> Aht20Reading:
        if failed or environment.relative_humidity_pct is None:
            return Aht20Reading(None, None, False)
        temperature = environment.temperature_C
        humidity = environment.relative_humidity_pct
        if self.config.enabled and self.config.mode != NoiseMode.IDEAL:
            scale = self.config.strength / 3.0
            temperature += float(self.rng.normal(0.0, 0.3 * scale))
            humidity += float(self.rng.normal(0.0, 2.0 * scale))
        return Aht20Reading(temperature, min(100.0, max(0.0, humidity)), True)
