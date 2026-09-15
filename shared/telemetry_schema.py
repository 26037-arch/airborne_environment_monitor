from __future__ import annotations

import csv
import math
from dataclasses import dataclass
from io import StringIO
from typing import Optional


CSV_HEADER_V1 = (
    "seq", "time_ms", "temperature_C", "humidity_pct", "pressure_hPa",
    "pm1_ugm3", "pm25_ugm3", "pm4_ugm3", "pm10_ugm3", "latitude",
    "longitude", "gps_altitude_m", "gps_speed_mps", "gps_course_deg",
    "bme_ok", "sps_ok", "gps_ok", "sd_ok",
)

# v1 remains byte-for-byte compatible with the original 18-column format.
CSV_HEADER = CSV_HEADER_V1
CSV_HEADER_V2 = CSV_HEADER_V1 + (
    "estimated_altitude_m", "vertical_speed_mps", "roll_deg", "pitch_deg",
    "yaw_deg", "battery_voltage_V", "battery_current_A", "flight_mode",
    "armed", "flight_link_ok", "system_health",
)
CSV_HEADER_V3 = (
    "seq", "time_ms", "temperature_C", "humidity_pct", "pressure_hPa",
    "barometric_altitude_m", "latitude", "longitude", "gps_altitude_m",
    "gps_speed_mps", "gps_course_deg", "accel_x_mps2", "accel_y_mps2",
    "accel_z_mps2", "gyro_x_dps", "gyro_y_dps", "gyro_z_dps",
    "rtc_unix_time", "env_ok", "imu_ok", "gps_ok", "rtc_ok", "sd_ok",
)

HEADERS_BY_VERSION = {1: CSV_HEADER_V1, 2: CSV_HEADER_V2, 3: CSV_HEADER_V3}


class InvalidRow(ValueError):
    """Raised when one received row does not match a supported schema."""


def _optional_float(text: str, column: str) -> Optional[float]:
    if text.strip().upper() in {"NA", ""}:
        return None
    try:
        value = float(text)
    except ValueError as exc:
        raise InvalidRow(f"{column}: expected a number or NA") from exc
    if not math.isfinite(value):
        raise InvalidRow(f"{column}: expected a finite value")
    return value


def _optional_uint32(text: str, column: str) -> Optional[int]:
    if text.strip().upper() in {"NA", ""}:
        return None
    try:
        value = int(text)
    except ValueError as exc:
        raise InvalidRow(f"{column}: expected an integer or NA") from exc
    if not 0 <= value <= 0xFFFFFFFF:
        raise InvalidRow(f"{column}: expected uint32")
    return value


def _flag(text: str, column: str) -> bool:
    if text not in {"0", "1"}:
        raise InvalidRow(f"{column}: expected 0 or 1")
    return text == "1"


def _validate_position(latitude: Optional[float], longitude: Optional[float],
                       course: Optional[float]) -> None:
    if latitude is not None and not -90.0 <= latitude <= 90.0:
        raise InvalidRow("latitude: expected -90..90")
    if longitude is not None and not -180.0 <= longitude <= 180.0:
        raise InvalidRow("longitude: expected -180..180")
    if course is not None and not 0.0 <= course <= 360.0:
        raise InvalidRow("gps_course_deg: expected 0..360")


@dataclass(frozen=True)
class Measurement:
    seq: int
    time_ms: int
    temperature_C: Optional[float] = None
    humidity_pct: Optional[float] = None
    pressure_hPa: Optional[float] = None
    pm1_ugm3: Optional[float] = None
    pm25_ugm3: Optional[float] = None
    pm4_ugm3: Optional[float] = None
    pm10_ugm3: Optional[float] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    gps_altitude_m: Optional[float] = None
    gps_speed_mps: Optional[float] = None
    gps_course_deg: Optional[float] = None
    bme_ok: bool = False
    sps_ok: bool = False
    gps_ok: bool = False
    sd_ok: bool = False
    raw_line: str = ""
    schema_version: int = 1
    estimated_altitude_m: Optional[float] = None
    vertical_speed_mps: Optional[float] = None
    roll_deg: Optional[float] = None
    pitch_deg: Optional[float] = None
    yaw_deg: Optional[float] = None
    battery_voltage_V: Optional[float] = None
    battery_current_A: Optional[float] = None
    flight_mode: Optional[int] = None
    armed: Optional[bool] = None
    flight_link_ok: Optional[bool] = None
    system_health: Optional[int] = None
    barometric_altitude_m: Optional[float] = None
    accel_x_mps2: Optional[float] = None
    accel_y_mps2: Optional[float] = None
    accel_z_mps2: Optional[float] = None
    gyro_x_dps: Optional[float] = None
    gyro_y_dps: Optional[float] = None
    gyro_z_dps: Optional[float] = None
    rtc_unix_time: Optional[int] = None
    env_ok: Optional[bool] = None
    imu_ok: Optional[bool] = None
    rtc_ok: Optional[bool] = None

    @property
    def fieldnames(self) -> tuple[str, ...]:
        return HEADERS_BY_VERSION[self.schema_version]


def _parse_csv_fields(line: str) -> tuple[str, list[str], int]:
    clean = line.strip("\r\n")
    if not clean:
        raise InvalidRow("empty row")
    try:
        rows = list(csv.reader(StringIO(clean), strict=True))
    except csv.Error as exc:
        raise InvalidRow(f"invalid CSV: {exc}") from exc
    if len(rows) != 1:
        raise InvalidRow("expected exactly one CSV row")
    fields = rows[0]
    matching = [version for version, header in HEADERS_BY_VERSION.items()
                if len(fields) == len(header)]
    if not matching:
        expected = ", ".join(f"v{v}={len(h)}" for v, h in HEADERS_BY_VERSION.items())
        raise InvalidRow(f"column count {len(fields)}; expected {expected}")
    return clean, fields, matching[0]


def _parse_v1_v2(clean: str, fields: list[str], schema_version: int,
                 seq: int, time_ms: int) -> Measurement:
    values = [_optional_float(fields[i], CSV_HEADER_V1[i]) for i in range(2, 14)]
    bme_ok, sps_ok, gps_ok, sd_ok = [
        _flag(fields[i], CSV_HEADER_V1[i]) for i in range(14, 18)
    ]
    if bme_ok and any(value is None for value in values[0:3]):
        raise InvalidRow("bme_ok=1 but a BME280 field is NA")
    if sps_ok and any(value is None for value in values[3:7]):
        raise InvalidRow("sps_ok=1 but an SPS30 field is NA")
    if gps_ok and any(value is None for value in values[7:12]):
        raise InvalidRow("gps_ok=1 but a GNSS field is NA")
    _validate_position(values[7], values[8], values[11])

    extra: dict[str, object] = {}
    if schema_version == 2:
        flight_values = [
            _optional_float(fields[i], CSV_HEADER_V2[i]) for i in range(18, 25)
        ]
        flight_mode = _optional_uint32(fields[25], "flight_mode")
        armed = _flag(fields[26], "armed")
        flight_link_ok = _flag(fields[27], "flight_link_ok")
        system_health = _optional_uint32(fields[28], "system_health")
        roll, pitch, yaw = flight_values[2:5]
        if roll is not None and not -180.0 <= roll <= 180.0:
            raise InvalidRow("roll_deg: expected -180..180")
        if pitch is not None and not -90.0 <= pitch <= 90.0:
            raise InvalidRow("pitch_deg: expected -90..90")
        if yaw is not None and not 0.0 <= yaw <= 360.0:
            raise InvalidRow("yaw_deg: expected 0..360")
        if flight_values[5] is not None and flight_values[5] < 0.0:
            raise InvalidRow("battery_voltage_V must not be negative")
        extra = {
            "estimated_altitude_m": flight_values[0],
            "vertical_speed_mps": flight_values[1],
            "roll_deg": roll, "pitch_deg": pitch, "yaw_deg": yaw,
            "battery_voltage_V": flight_values[5],
            "battery_current_A": flight_values[6], "flight_mode": flight_mode,
            "armed": armed, "flight_link_ok": flight_link_ok,
            "system_health": system_health,
        }

    return Measurement(
        seq=seq, time_ms=time_ms, temperature_C=values[0],
        humidity_pct=values[1], pressure_hPa=values[2], pm1_ugm3=values[3],
        pm25_ugm3=values[4], pm4_ugm3=values[5], pm10_ugm3=values[6],
        latitude=values[7], longitude=values[8], gps_altitude_m=values[9],
        gps_speed_mps=values[10], gps_course_deg=values[11], bme_ok=bme_ok,
        sps_ok=sps_ok, gps_ok=gps_ok, sd_ok=sd_ok, raw_line=clean,
        schema_version=schema_version, **extra,
    )


def _parse_v3(clean: str, fields: list[str], seq: int, time_ms: int) -> Measurement:
    numeric_names = CSV_HEADER_V3[2:17]
    numeric = {
        name: _optional_float(fields[index], name)
        for index, name in enumerate(numeric_names, start=2)
    }
    rtc_unix_time = _optional_uint32(fields[17], "rtc_unix_time")
    env_ok, imu_ok, gps_ok, rtc_ok, sd_ok = [
        _flag(fields[i], CSV_HEADER_V3[i]) for i in range(18, 23)
    ]
    env_names = (
        "temperature_C", "humidity_pct", "pressure_hPa", "barometric_altitude_m"
    )
    imu_names = (
        "accel_x_mps2", "accel_y_mps2", "accel_z_mps2",
        "gyro_x_dps", "gyro_y_dps", "gyro_z_dps",
    )
    gps_names = (
        "latitude", "longitude", "gps_altitude_m", "gps_speed_mps",
        "gps_course_deg",
    )
    if env_ok and any(numeric[name] is None for name in env_names):
        raise InvalidRow("env_ok=1 but an environment field is NA")
    if imu_ok and any(numeric[name] is None for name in imu_names):
        raise InvalidRow("imu_ok=1 but an IMU field is NA")
    if gps_ok and any(numeric[name] is None for name in gps_names):
        raise InvalidRow("gps_ok=1 but a GNSS field is NA")
    if rtc_ok and rtc_unix_time is None:
        raise InvalidRow("rtc_ok=1 but rtc_unix_time is NA")
    _validate_position(numeric["latitude"], numeric["longitude"],
                       numeric["gps_course_deg"])
    humidity = numeric["humidity_pct"]
    if humidity is not None and not 0.0 <= humidity <= 100.5:
        raise InvalidRow("humidity_pct: expected 0..100.5")
    pressure = numeric["pressure_hPa"]
    if pressure is not None and not 0.0 < pressure < 2000.0:
        raise InvalidRow("pressure_hPa: expected 0..2000")
    speed = numeric["gps_speed_mps"]
    if speed is not None and speed < 0.0:
        raise InvalidRow("gps_speed_mps must not be negative")

    return Measurement(
        seq=seq, time_ms=time_ms, temperature_C=numeric["temperature_C"],
        humidity_pct=humidity, pressure_hPa=pressure,
        barometric_altitude_m=numeric["barometric_altitude_m"],
        latitude=numeric["latitude"], longitude=numeric["longitude"],
        gps_altitude_m=numeric["gps_altitude_m"],
        gps_speed_mps=speed, gps_course_deg=numeric["gps_course_deg"],
        accel_x_mps2=numeric["accel_x_mps2"],
        accel_y_mps2=numeric["accel_y_mps2"],
        accel_z_mps2=numeric["accel_z_mps2"],
        gyro_x_dps=numeric["gyro_x_dps"], gyro_y_dps=numeric["gyro_y_dps"],
        gyro_z_dps=numeric["gyro_z_dps"], rtc_unix_time=rtc_unix_time,
        env_ok=env_ok, imu_ok=imu_ok, gps_ok=gps_ok, rtc_ok=rtc_ok,
        sd_ok=sd_ok, bme_ok=env_ok, raw_line=clean, schema_version=3,
    )


def parse_csv_line(line: str) -> Measurement:
    clean, fields, schema_version = _parse_csv_fields(line)
    try:
        seq, time_ms = int(fields[0]), int(fields[1])
    except ValueError as exc:
        raise InvalidRow("seq and time_ms must be integers") from exc
    if not (0 <= seq <= 0xFFFFFFFF) or not (0 <= time_ms <= 0xFFFFFFFF):
        raise InvalidRow("seq and time_ms must fit uint32")
    if schema_version == 3:
        return _parse_v3(clean, fields, seq, time_ms)
    return _parse_v1_v2(clean, fields, schema_version, seq, time_ms)


def encode_csv_row(values: dict[str, object], schema_version: int = 1) -> str:
    """Encode and then validate one v1, v2, or v3 telemetry row."""
    if schema_version not in HEADERS_BY_VERSION:
        raise ValueError("schema_version must be 1, 2, or 3")
    header = HEADERS_BY_VERSION[schema_version]
    flag_names = {
        "bme_ok", "sps_ok", "gps_ok", "sd_ok", "armed", "flight_link_ok",
        "env_ok", "imu_ok", "rtc_ok",
    }
    integer_names = {
        "seq", "time_ms", "flight_mode", "system_health", "rtc_unix_time",
    }

    def token(name: str) -> str:
        value = values.get(name)
        if value is None or (isinstance(value, float) and not math.isfinite(value)):
            return "NA"
        if name in flag_names:
            return "1" if bool(value) else "0"
        if name in integer_names:
            return str(int(value))
        if name in {"latitude", "longitude"}:
            return f"{float(value):.6f}"
        return f"{float(value):.2f}"

    row = ",".join(token(name) for name in header)
    parse_csv_line(row)
    return row
