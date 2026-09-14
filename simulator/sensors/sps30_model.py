from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from shared.data_types import EnvironmentSample

from .noise import NoiseConfig, NoiseMode, generator


@dataclass(frozen=True)
class SpsReading:
    pm1_ugm3: Optional[float]
    pm25_ugm3: Optional[float]
    pm4_ugm3: Optional[float]
    pm10_ugm3: Optional[float]
    ok: bool


class Sps30Model:
    """SPS30 mass concentration precision limits를 ±3σ로 해석합니다."""

    def __init__(self, config: NoiseConfig, custom_std_ugm3: float = 1.0) -> None:
        self.config = config
        self.custom_std = custom_std_ugm3
        self.rng = generator(config, 30)

    @staticmethod
    def _datasheet_accuracy(value: float, coarse: bool) -> float:
        if coarse:  # PM4/PM10
            return 25.0 if value <= 100.0 else 0.25 * value
        return 5.0 + 0.05 * value if value <= 100.0 else 0.10 * value

    def _noise(self, value: Optional[float], coarse: bool) -> Optional[float]:
        if value is None or not self.config.enabled or self.config.mode == NoiseMode.IDEAL:
            return value
        accuracy = (
            self._datasheet_accuracy(value, coarse)
            if self.config.mode == NoiseMode.DATASHEET else self.custom_std
        )
        return max(0.0, value + float(self.rng.normal(0.0, accuracy / 3.0 * self.config.strength)))

    def read(self, environment: EnvironmentSample, failed: bool = False) -> SpsReading:
        if failed:
            return SpsReading(None, None, None, None, False)
        # CAMS EAC4가 직접 제공하지 않는 PM1/PM4는 절대 추정하지 않습니다.
        values = (
            self._noise(environment.pm1_ugm3, False),
            self._noise(environment.pm25_ugm3, False),
            None,
            self._noise(environment.pm10_ugm3, True),
        )
        return SpsReading(*values, all(value is not None for value in values))

