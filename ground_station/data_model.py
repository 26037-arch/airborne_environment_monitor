from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# 기존 import 경로를 유지하는 compatibility facade입니다.
from shared.telemetry_schema import (
    CSV_HEADER, CSV_HEADER_V1, CSV_HEADER_V2, CSV_HEADER_V3, InvalidRow, Measurement,
    parse_csv_line,
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
                self.stats.resets += 1
        self.stats.received += 1
        self.stats.last_seq = seq
        return missing_now
