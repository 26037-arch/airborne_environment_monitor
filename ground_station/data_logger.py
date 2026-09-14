from __future__ import annotations

import csv
from datetime import date
from pathlib import Path
from typing import TextIO

from data_model import CSV_HEADER, Measurement


class DataLogger:
    """검증된 telemetry를 PC의 새 CSV 파일에 즉시 flush합니다."""

    def __init__(self, directory: Path, today: date | None = None) -> None:
        self.directory = Path(directory)
        self.directory.mkdir(parents=True, exist_ok=True)
        self.path = self._next_path(today or date.today())
        self._file: TextIO = self.path.open("x", encoding="utf-8", newline="")
        self._writer = csv.writer(self._file, lineterminator="\n")
        self._writer.writerow(CSV_HEADER)
        self._file.flush()

    def _next_path(self, day: date) -> Path:
        stamp = day.isoformat()
        for index in range(1, 1000):
            candidate = self.directory / f"flight_{stamp}_{index:03d}.csv"
            if not candidate.exists():
                return candidate
        raise RuntimeError("하루에 만들 수 있는 로그 파일 999개를 초과했습니다")

    def write(self, measurement: Measurement) -> None:
        # raw_line을 사용해 Arduino가 보낸 숫자 문자열을 그대로 보존합니다.
        self._file.write(measurement.raw_line + "\n")
        self._file.flush()

    def close(self) -> None:
        if not self._file.closed:
            self._file.flush()
            self._file.close()

    def __enter__(self) -> "DataLogger":
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        self.close()

