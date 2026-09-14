from __future__ import annotations

import math
import random

from data_model import parse_csv_line, Measurement


class MockDataGenerator:
    """하드웨어 없이도 자연스럽게 변하는 1 Hz 측정값을 만듭니다."""

    def __init__(self, seed: int = 20260915, interval_ms: int = 1000) -> None:
        self._random = random.Random(seed)
        self._interval_ms = interval_ms
        self._seq = 0

    def next_line(self) -> str:
        self._seq += 1
        time_ms = self._seq * self._interval_ms
        t = time_ms / 1000.0

        temperature = 19.5 + 2.2 * math.sin(t / 24.0) + self._random.uniform(-0.08, 0.08)
        humidity = 54.0 + 4.0 * math.sin(t / 31.0)
        altitude = 120.0 + 0.55 * t + 4.0 * math.sin(t / 15.0)
        pressure = 1013.25 * (1.0 - 2.25577e-5 * altitude) ** 5.25588
        pm25 = max(0.0, 6.0 + 1.4 * math.sin(t / 8.0) + self._random.uniform(-0.2, 0.2))
        pm1 = max(0.0, pm25 * 0.63)
        pm4 = pm25 * 1.18
        pm10 = pm25 * 1.43
        latitude = 37.123456 + 0.000015 * math.sin(t / 40.0)
        longitude = 127.123456 + 0.000015 * math.cos(t / 40.0)
        speed = 3.2 + 0.7 * math.sin(t / 10.0)
        course = (118.0 + t * 1.8) % 360.0

        return (
            f"{self._seq},{time_ms},{temperature:.2f},{humidity:.2f},"
            f"{pressure:.2f},{pm1:.2f},{pm25:.2f},{pm4:.2f},{pm10:.2f},"
            f"{latitude:.6f},{longitude:.6f},{altitude:.2f},{speed:.2f},"
            f"{course:.2f},1,1,1,1"
        )

    def next_measurement(self) -> Measurement:
        return parse_csv_line(self.next_line())

