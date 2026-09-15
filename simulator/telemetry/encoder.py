from __future__ import annotations

from shared.data_types import SensorReadings
from shared.flight_status import FlightStatus
from shared.telemetry_schema import encode_csv_row


class TelemetryEncoder:
    def __init__(self, schema_version: int = 3) -> None:
        if schema_version not in {1, 2, 3}:
            raise ValueError("schema_version must be 1, 2, or 3")
        self.schema_version = schema_version

    def encode(self, seq: int, time_ms: int, sensor: SensorReadings,
               flight: FlightStatus | None = None) -> str:
        if self.schema_version == 3:
            values = {
                "seq": seq, "time_ms": time_ms,
                "temperature_C": sensor.temperature_C,
                "humidity_pct": sensor.humidity_pct,
                "pressure_hPa": sensor.pressure_hPa,
                "barometric_altitude_m": sensor.barometric_altitude_m,
                "latitude": sensor.latitude, "longitude": sensor.longitude,
                "gps_altitude_m": sensor.gps_altitude_m,
                "gps_speed_mps": sensor.gps_speed_mps,
                "gps_course_deg": sensor.gps_course_deg,
                "accel_x_mps2": sensor.accel_x_mps2,
                "accel_y_mps2": sensor.accel_y_mps2,
                "accel_z_mps2": sensor.accel_z_mps2,
                "gyro_x_dps": sensor.gyro_x_dps,
                "gyro_y_dps": sensor.gyro_y_dps,
                "gyro_z_dps": sensor.gyro_z_dps,
                "rtc_unix_time": sensor.rtc_unix_time,
                "env_ok": sensor.env_ok, "imu_ok": sensor.imu_ok,
                "gps_ok": sensor.gps_ok, "rtc_ok": sensor.rtc_ok,
                "sd_ok": sensor.sd_ok,
            }
            return encode_csv_row(values, schema_version=3)

        values = {
            "seq": seq, "time_ms": time_ms,
            "temperature_C": sensor.temperature_C,
            "humidity_pct": sensor.humidity_pct,
            "pressure_hPa": sensor.pressure_hPa,
            "pm1_ugm3": sensor.pm1_ugm3, "pm25_ugm3": sensor.pm25_ugm3,
            "pm4_ugm3": sensor.pm4_ugm3, "pm10_ugm3": sensor.pm10_ugm3,
            "latitude": sensor.latitude, "longitude": sensor.longitude,
            "gps_altitude_m": sensor.gps_altitude_m,
            "gps_speed_mps": sensor.gps_speed_mps,
            "gps_course_deg": sensor.gps_course_deg,
            "bme_ok": sensor.bme_ok, "sps_ok": sensor.sps_ok,
            "gps_ok": sensor.gps_ok, "sd_ok": sensor.sd_ok,
        }
        if self.schema_version == 1:
            return encode_csv_row(values, schema_version=1)
        if flight is not None and flight.connected:
            if flight.latitude is not None and flight.longitude is not None:
                values.update(
                    latitude=flight.latitude, longitude=flight.longitude,
                    gps_altitude_m=flight.gnss_altitude_m,
                    gps_speed_mps=flight.ground_speed_mps,
                    gps_course_deg=flight.yaw_deg,
                    gps_ok=all(value is not None for value in (
                        flight.latitude, flight.longitude, flight.gnss_altitude_m,
                        flight.ground_speed_mps, flight.yaw_deg,
                    )),
                )
            values.update(
                estimated_altitude_m=flight.estimated_altitude_m,
                vertical_speed_mps=flight.vertical_speed_mps,
                roll_deg=flight.roll_deg, pitch_deg=flight.pitch_deg,
                yaw_deg=flight.yaw_deg, battery_voltage_V=flight.battery_voltage_v,
                battery_current_A=flight.battery_current_a,
                flight_mode=flight.flight_mode, armed=flight.armed,
                flight_link_ok=True, system_health=flight.system_health,
            )
        else:
            values.update(armed=False, flight_link_ok=False)
        return encode_csv_row(values, schema_version=2)
