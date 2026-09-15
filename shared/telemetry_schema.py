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


class InvalidRow(ValueError):
    """수신 행이 지정된 telemetry schema와 맞지 않을 때 발생합니다."""


def _optional_float(text: str, column: str) -> Optional[float]:
    if text.strip().upper() in {"NA", ""}:
        return None
    try:
        value = float(text)
    except ValueError as exc:
        raise InvalidRow(f"{column}: 숫자 또는 NA가 필요합니다") from exc
    if not math.isfinite(value):
        raise InvalidRow(f"{column}: 유한한 값이어야 합니다")
    return value


def _flag(text: str, column: str) -> bool:
    if text not in {"0", "1"}:
        raise InvalidRow(f"{column}: 0 또는 1이 필요합니다")
    return text == "1"


@dataclass(frozen=True)
class Measurement:
    seq: int
    time_ms: int
    temperature_C: Optional[float]
    humidity_pct: Optional[float]
    pressure_hPa: Optional[float]
    pm1_ugm3: Optional[float]
    pm25_ugm3: Optional[float]
    pm4_ugm3: Optional[float]
    pm10_ugm3: Optional[float]
    latitude: Optional[float]
    longitude: Optional[float]
    gps_altitude_m: Optional[float]
    gps_speed_mps: Optional[float]
    gps_course_deg: Optional[float]
    bme_ok: bool
    sps_ok: bool
    gps_ok: bool
    sd_ok: bool
    raw_line: str
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

    @property
    def fieldnames(self) -> tuple[str, ...]:
        return CSV_HEADER_V2 if self.schema_version == 2 else CSV_HEADER_V1


def parse_csv_line(line: str) -> Measurement:
    clean = line.strip("\r\n")
    if not clean:
        raise InvalidRow("빈 행입니다")
    try:
        rows = list(csv.reader(StringIO(clean), strict=True))
    except csv.Error as exc:
        raise InvalidRow(f"CSV 문법 오류: {exc}") from exc
    if len(rows) != 1 or len(rows[0]) not in {len(CSV_HEADER_V1), len(CSV_HEADER_V2)}:
        count = len(rows[0]) if rows else 0
        raise InvalidRow(
            f"열 개수 {count}; v1 {len(CSV_HEADER_V1)}개 또는 "
            f"v2 {len(CSV_HEADER_V2)}개가 필요합니다"
        )

    fields = rows[0]
    schema_version = 2 if len(fields) == len(CSV_HEADER_V2) else 1
    try:
        seq, time_ms = int(fields[0]), int(fields[1])
    except ValueError as exc:
        raise InvalidRow("seq와 time_ms는 정수여야 합니다") from exc
    if not (0 <= seq <= 0xFFFFFFFF) or not (0 <= time_ms <= 0xFFFFFFFF):
        raise InvalidRow("seq와 time_ms는 uint32 범위여야 합니다")

    values = [_optional_float(fields[i], CSV_HEADER[i]) for i in range(2, 14)]
    bme_ok, sps_ok, gps_ok, sd_ok = [
        _flag(fields[i], CSV_HEADER[i]) for i in range(14, 18)
    ]
    if bme_ok and any(value is None for value in values[0:3]):
        raise InvalidRow("bme_ok=1인데 BME280 값이 NA입니다")
    if sps_ok and any(value is None for value in values[3:7]):
        raise InvalidRow("sps_ok=1인데 SPS30 값이 NA입니다")
    if gps_ok and any(value is None for value in values[7:12]):
        raise InvalidRow("gps_ok=1인데 GNSS 값이 NA입니다")
    if values[7] is not None and not -90.0 <= values[7] <= 90.0:
        raise InvalidRow("latitude: -90..90 범위여야 합니다")
    if values[8] is not None and not -180.0 <= values[8] <= 180.0:
        raise InvalidRow("longitude: -180..180 범위여야 합니다")

    flight_values: list[Optional[float]] = [None] * 7
    flight_mode: Optional[int] = None
    armed: Optional[bool] = None
    flight_link_ok: Optional[bool] = None
    system_health: Optional[int] = None
    if schema_version == 2:
        flight_values = [
            _optional_float(fields[i], CSV_HEADER_V2[i]) for i in range(18, 25)
        ]
        try:
            flight_mode = None if fields[25].strip().upper() in {"NA", ""} else int(fields[25])
            system_health = None if fields[28].strip().upper() in {"NA", ""} else int(fields[28])
        except ValueError as exc:
            raise InvalidRow("flight_mode/system_health는 정수 또는 NA여야 합니다") from exc
        armed = _flag(fields[26], "armed")
        flight_link_ok = _flag(fields[27], "flight_link_ok")
        if flight_mode is not None and not 0 <= flight_mode <= 0xFFFFFFFF:
            raise InvalidRow("flight_mode은 uint32 범위여야 합니다")
        if system_health is not None and not 0 <= system_health <= 0xFFFFFFFF:
            raise InvalidRow("system_health는 uint32 범위여야 합니다")
        roll, pitch, yaw = flight_values[2:5]
        if roll is not None and not -180.0 <= roll <= 180.0:
            raise InvalidRow("roll_deg: -180..180 범위여야 합니다")
        if pitch is not None and not -90.0 <= pitch <= 90.0:
            raise InvalidRow("pitch_deg: -90..90 범위여야 합니다")
        if yaw is not None and not 0.0 <= yaw <= 360.0:
            raise InvalidRow("yaw_deg: 0..360 범위여야 합니다")
        if flight_values[5] is not None and flight_values[5] < 0.0:
            raise InvalidRow("battery_voltage_V는 음수일 수 없습니다")

    return Measurement(
        seq, time_ms, *values, bme_ok, sps_ok, gps_ok, sd_ok, clean,
        schema_version=schema_version,
        estimated_altitude_m=flight_values[0],
        vertical_speed_mps=flight_values[1], roll_deg=flight_values[2],
        pitch_deg=flight_values[3], yaw_deg=flight_values[4],
        battery_voltage_V=flight_values[5], battery_current_A=flight_values[6],
        flight_mode=flight_mode, armed=armed, flight_link_ok=flight_link_ok,
        system_health=system_health,
    )


def encode_csv_row(values: dict[str, object], schema_version: int = 1) -> str:
    """v1 또는 확장 v2 행을 만들고 동일 parser로 다시 검증합니다."""
    if schema_version not in {1, 2}:
        raise ValueError("schema_version은 1 또는 2여야 합니다")
    header = CSV_HEADER_V2 if schema_version == 2 else CSV_HEADER_V1

    def token(name: str) -> str:
        value = values.get(name)
        if value is None or (isinstance(value, float) and not math.isfinite(value)):
            return "NA"
        if name in {"bme_ok", "sps_ok", "gps_ok", "sd_ok", "armed", "flight_link_ok"}:
            return "1" if bool(value) else "0"
        if name in {"seq", "time_ms", "flight_mode", "system_health"}:
            return str(int(value))
        if name in {"latitude", "longitude"}:
            return f"{float(value):.6f}"
        return f"{float(value):.2f}"

    row = ",".join(token(name) for name in header)
    parse_csv_line(row)
    return row
