from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class RtcReading:
    unix_time: Optional[int]
    ok: bool


class RtcModel:
    def __init__(self, simulation_epoch_unix: int) -> None:
        self.simulation_epoch_unix = simulation_epoch_unix

    def read(self, simulation_time_s: float, failed: bool = False) -> RtcReading:
        if failed or self.simulation_epoch_unix < 0:
            return RtcReading(None, False)
        value = self.simulation_epoch_unix + int(round(simulation_time_s))
        if not 0 <= value <= 0xFFFFFFFF:
            return RtcReading(None, False)
        return RtcReading(value, True)
