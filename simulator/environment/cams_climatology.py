from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import numpy as np


KG_M3_TO_UG_M3 = 1.0e9


def kgm3_to_ugm3(value: float) -> float:
    if value < 0.0:
        raise ValueError("PM concentration은 음수일 수 없습니다")
    return value * KG_M3_TO_UG_M3


@dataclass(frozen=True)
class CamsSample:
    pm25_ugm3: float
    pm10_ugm3: float
    metadata: dict[str, object]


class CamsClimatology:
    """CAMS EAC4 PM2.5/PM10 profile. PM1과 PM4는 추정하지 않습니다."""

    def __init__(self, directory: Path, maximum_distance_deg: float = 1.0) -> None:
        self.directory = Path(directory)
        self.maximum_distance_deg = maximum_distance_deg
        self.profiles: list[tuple[Path, dict[str, object]]] = []
        for path in sorted(self.directory.glob("*.npz")):
            metadata_path = path.with_suffix(".json")
            if metadata_path.exists():
                self.profiles.append(
                    (path, json.loads(metadata_path.read_text(encoding="utf-8")))
                )

    @property
    def installed(self) -> bool:
        return bool(self.profiles)

    def sample(self, latitude: float, longitude: float, month: int,
               altitude_m: float) -> Optional[CamsSample]:
        candidates = [item for item in self.profiles if int(item[1].get("month", -1)) == month]
        if not candidates:
            return None
        path, metadata = min(
            candidates,
            key=lambda item: (float(item[1]["latitude"]) - latitude) ** 2
            + (((float(item[1]["longitude"]) - longitude + 180.0) % 360.0) - 180.0) ** 2,
        )
        lon_delta = ((float(metadata["longitude"]) - longitude + 180.0) % 360.0) - 180.0
        if math.hypot(float(metadata["latitude"]) - latitude,
                      lon_delta) > self.maximum_distance_deg:
            return None
        with np.load(path, allow_pickle=False) as data:
            altitude = np.asarray(data["altitude_m"], dtype=float)
            pm25 = np.asarray(data["pm25_kgm3"], dtype=float)
            pm10 = np.asarray(data["pm10_kgm3"], dtype=float)
            if altitude.shape != pm25.shape or altitude.shape != pm10.shape:
                raise ValueError("CAMS profile 배열 shape가 다릅니다")
            if len(altitude) == 1:
                # surface-only 값을 공중 고도로 외삽하지 않습니다.
                if abs(altitude_m - float(altitude[0])) > 1.0:
                    return None
                p25, p10 = float(pm25[0]), float(pm10[0])
            else:
                if not np.all(np.diff(altitude) > 0):
                    raise ValueError("CAMS altitude_m은 증가해야 합니다")
                if not altitude[0] <= altitude_m <= altitude[-1]:
                    return None
                p25 = float(np.interp(altitude_m, altitude, pm25))
                p10 = float(np.interp(altitude_m, altitude, pm10))
        if not np.isfinite(p25) or not np.isfinite(p10):
            return None
        return CamsSample(kgm3_to_ugm3(p25), kgm3_to_ugm3(p10), metadata)
