from __future__ import annotations

from shared.data_types import SensorReadings
from shared.flight_status import FlightStatus
from shared.telemetry_schema import encode_csv_row


class TelemetryEncoder:
    def encode(self, seq: int, time_ms: int, sensor: SensorReadings,
               flight: FlightStatus | None = None) -> str:
        values = {
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
        }
        if flight is None:
            return encode_csv_row(values)
        if flight.connected and flight.latitude is not None and flight.longitude is not None:
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
            yaw_deg=flight.yaw_deg,
            battery_voltage_V=flight.battery_voltage_v,
            battery_current_A=flight.battery_current_a,
            flight_mode=flight.flight_mode, armed=flight.armed,
            flight_link_ok=flight.connected, system_health=flight.system_health,
        )
        return encode_csv_row(values, schema_version=2)
