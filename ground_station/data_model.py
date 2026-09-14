from __future__ import annotations

import csv
import math
from dataclasses import dataclass
from io import StringIO
from typing import Optional


CSV_HEADER = (
    "seq",
    "time_ms",
    "temperature_C",
    "humidity_pct",
    "pressure_hPa",
    "pm1_ugm3",
    "pm25_ugm3",
    "pm4_ugm3",
    "pm10_ugm3",
    "latitude",
    "longitude",
    "gps_altitude_m",
    "gps_speed_mps",
    "gps_course_deg",
    "bme_ok",
    "sps_ok",
    "gps_ok",
    "sd_ok",
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


def parse_csv_line(line: str) -> Measurement:
    """18열 CSV 한 행을 엄격하게 검증하고 Measurement로 바꿉니다."""
    clean = line.strip("\r\n")
    if not clean:
        raise InvalidRow("빈 행입니다")
    try:
        rows = list(csv.reader(StringIO(clean), strict=True))
    except csv.Error as exc:
        raise InvalidRow(f"CSV 문법 오류: {exc}") from exc
    if len(rows) != 1 or len(rows[0]) != len(CSV_HEADER):
        count = len(rows[0]) if rows else 0
        raise InvalidRow(f"열 개수 {count}; {len(CSV_HEADER)}개가 필요합니다")

    fields = rows[0]
    try:
        seq = int(fields[0])
        time_ms = int(fields[1])
    except ValueError as exc:
        raise InvalidRow("seq와 time_ms는 정수여야 합니다") from exc
    if not (0 <= seq <= 0xFFFFFFFF) or not (0 <= time_ms <= 0xFFFFFFFF):
        raise InvalidRow("seq와 time_ms는 uint32 범위여야 합니다")

    values = [_optional_float(fields[i], CSV_HEADER[i]) for i in range(2, 14)]
    bme_ok, sps_ok, gps_ok, sd_ok = [
        _flag(fields[i], CSV_HEADER[i]) for i in range(14, 18)
    ]

    # 상태가 정상이라고 쓰인 센서는 해당 값도 모두 있어야 합니다.
    if bme_ok and any(value is None for value in values[0:3]):
        raise InvalidRow("bme_ok=1인데 BME280 값이 NA입니다")
    if sps_ok and any(value is None for value in values[3:7]):
        raise InvalidRow("sps_ok=1인데 SPS30 값이 NA입니다")
    if gps_ok and any(value is None for value in values[7:12]):
        raise InvalidRow("gps_ok=1인데 GNSS 값이 NA입니다")

    return Measurement(
        seq,
        time_ms,
        *values,
        bme_ok,
        sps_ok,
        gps_ok,
        sd_ok,
        clean,
    )


@dataclass
class PacketStats:
    received: int = 0
    lost: int = 0
    resets: int = 0
    duplicates: int = 0
    last_seq: Optional[int] = None

    @property
    def loss_percent(self) -> float:
        expected = self.received + self.lost
        return 100.0 * self.lost / expected if expected else 0.0


class SequenceTracker:
    """증가하는 seq에서 누락을 세고, 감소하면 Arduino 재부팅으로 봅니다."""

    def __init__(self) -> None:
        self.stats = PacketStats()

    def update(self, seq: int) -> int:
        if not (0 <= seq <= 0xFFFFFFFF):
            raise ValueError("seq must fit uint32")

        missing_now = 0
        last = self.stats.last_seq
        if last is not None:
            if seq > last:
                missing_now = seq - last - 1
                self.stats.lost += missing_now
            elif seq == last:
                self.stats.duplicates += 1
            else:
                # Arduino 재부팅 또는 uint32 wrap: 새 기준점에서 다시 시작합니다.
                self.stats.resets += 1

        self.stats.received += 1
        self.stats.last_seq = seq
        return missing_now

