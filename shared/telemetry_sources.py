from __future__ import annotations

import csv
import socket
import time
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional

from .telemetry_schema import CSV_HEADER, Measurement, parse_csv_line


class TelemetrySource(ABC):
    @abstractmethod
    def read(self) -> Optional[Measurement]:
        """다음 measurement를 반환하며 timeout/EOF이면 None을 반환합니다."""

    def close(self) -> None:
        pass


class SimulationSource(TelemetrySource):
    """Webots ground bridge가 localhost UDP로 보낸 CSV를 받습니다."""

    def __init__(self, host: str = "127.0.0.1", port: int = 19000,
                 timeout: float = 1.2) -> None:
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.bind((host, port))
        self.socket.settimeout(timeout)

    def read(self) -> Optional[Measurement]:
        try:
            payload, _address = self.socket.recvfrom(4096)
        except socket.timeout:
            return None
        return parse_csv_line(payload.decode("ascii", errors="strict"))

    def close(self) -> None:
        self.socket.close()


class SerialSource(TelemetrySource):
    def __init__(self, port: str, baud_rate: int = 115200,
                 timeout: float = 1.2) -> None:
        try:
            import serial
        except ModuleNotFoundError as exc:
            raise RuntimeError("pyserial이 필요합니다") from exc
        self.device = serial.Serial(port, baud_rate, timeout=timeout)

    def read(self) -> Optional[Measurement]:
        raw = self.device.readline()
        return parse_csv_line(raw.decode("ascii")) if raw else None

    def close(self) -> None:
        self.device.close()


class CSVReplaySource(TelemetrySource):
    def __init__(self, path: Path, realtime: bool = True) -> None:
        self.file = Path(path).open(encoding="utf-8", newline="")
        self.reader = csv.DictReader(self.file)
        if tuple(self.reader.fieldnames or ()) != CSV_HEADER:
            self.file.close()
            raise ValueError("CSV replay header가 Arduino schema와 다릅니다")
        self.realtime = realtime
        self.previous_time_ms: Optional[int] = None

    def read(self) -> Optional[Measurement]:
        try:
            row = next(self.reader)
        except StopIteration:
            return None
        line = ",".join(row[name] for name in CSV_HEADER)
        measurement = parse_csv_line(line)
        if self.realtime and self.previous_time_ms is not None:
            delay = max(0.0, min(5.0, (measurement.time_ms - self.previous_time_ms) / 1000.0))
            time.sleep(delay)
        self.previous_time_ms = measurement.time_ms
        return measurement

    def close(self) -> None:
        self.file.close()

