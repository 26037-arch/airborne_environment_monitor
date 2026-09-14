from __future__ import annotations

from shared.data_types import SensorReadings
from shared.telemetry_schema import encode_csv_row


class TelemetryEncoder:
    def encode(self, seq: int, time_ms: int, sensor: SensorReadings) -> str:
        return encode_csv_row({
            "seq": seq, "time_ms": time_ms,
            "temperature_C": sensor.temperature_C,
            "humidity_pct": sensor.humidity_pct,
            "pressure_hPa": sensor.pressure_hPa,
            "pm1_ugm3": sensor.pm1_ugm3,
            "pm25_ugm3": sensor.pm25_ugm3,
            "pm4_ugm3": sensor.pm4_ugm3,
            "pm10_ugm3": sensor.pm10_ugm3,
            "latitude": sensor.latitude, "longitude": sensor.longitude,
            "gps_altitude_m": sensor.gps_altitude_m,
            "gps_speed_mps": sensor.gps_speed_mps,
            "gps_course_deg": sensor.gps_course_deg,
            "bme_ok": sensor.bme_ok, "sps_ok": sensor.sps_ok,
            "gps_ok": sensor.gps_ok, "sd_ok": sensor.sd_ok,
        })

