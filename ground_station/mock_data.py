from __future__ import annotations

import math
import random

from data_model import Measurement, parse_csv_line
from shared.telemetry_schema import encode_csv_row


class MockDataGenerator:
    """Generate deterministic 1 Hz schema-v3 payload telemetry."""

    def __init__(self, seed: int = 20260915, interval_ms: int = 1000) -> None:
        self._random = random.Random(seed)
        self._interval_ms = interval_ms
        self._seq = 0
        self._epoch = 1767225600

    def next_line(self) -> str:
        self._seq += 1
        time_ms = self._seq * self._interval_ms
        t = time_ms / 1000.0
        temperature = 19.5 + 2.2 * math.sin(t / 24.0) + self._random.uniform(-0.08, 0.08)
        humidity = 54.0 + 4.0 * math.sin(t / 31.0)
        barometric_altitude = 120.0 + 0.55 * t + 4.0 * math.sin(t / 15.0)
        pressure = 1013.25 * (1.0 - 2.25577e-5 * barometric_altitude) ** 5.25588
        latitude = 37.123456 + 0.000015 * math.sin(t / 40.0)
        longitude = 127.123456 + 0.000015 * math.cos(t / 40.0)
        speed = 3.2 + 0.7 * math.sin(t / 10.0)
        course = (118.0 + t * 1.8) % 360.0
        values = {
            "seq": self._seq, "time_ms": time_ms,
            "temperature_C": temperature, "humidity_pct": humidity,
            "pressure_hPa": pressure,
            "barometric_altitude_m": barometric_altitude,
            "latitude": latitude, "longitude": longitude,
            "gps_altitude_m": barometric_altitude + 2.0,
            "gps_speed_mps": speed, "gps_course_deg": course,
            "accel_x_mps2": 0.03 * math.sin(t),
            "accel_y_mps2": 0.03 * math.cos(t),
            "accel_z_mps2": 9.80665,
            "gyro_x_dps": 0.2 * math.sin(t / 2.0),
            "gyro_y_dps": 0.2 * math.cos(t / 2.0),
            "gyro_z_dps": 1.8,
            "rtc_unix_time": self._epoch + round(t),
            "env_ok": True, "imu_ok": True, "gps_ok": True,
            "rtc_ok": True, "sd_ok": True,
        }
        return encode_csv_row(values, schema_version=3)

    def next_measurement(self) -> Measurement:
        return parse_csv_line(self.next_line())
