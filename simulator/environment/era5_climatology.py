from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import numpy as np


@dataclass(frozen=True)
class Era5Sample:
    temperature_K: float
    pressure_Pa: float
    density_kgm3: float
    relative_humidity_pct: float
    wind_east_mps: float
    wind_north_mps: float
    wind_vertical_mps: float
    metadata: dict[str, object]


class Era5Climatology:
    """전처리된 ERA5 pressure-level profile을 offline에서 읽습니다."""

    REQUIRED = (
        "altitude_m", "temperature_K", "pressure_Pa", "density_kgm3",
        "relative_humidity_pct", "wind_east_mps", "wind_north_mps",
        "wind_vertical_mps",
    )

    def __init__(self, directory: Path, maximum_distance_deg: float = 0.5) -> None:
        self.directory = Path(directory)
        self.maximum_distance_deg = maximum_distance_deg
        self.profiles: list[tuple[Path, dict[str, object]]] = []
        for path in sorted(self.directory.glob("*.npz")):
            metadata_path = path.with_suffix(".json")
            if metadata_path.exists():
                metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
                self.profiles.append((path, metadata))

    @property
    def installed(self) -> bool:
        return bool(self.profiles)

    def _nearest(self, latitude: float, longitude: float, month: int):
        candidates = [item for item in self.profiles if int(item[1].get("month", -1)) == month]
        if not candidates:
            return None
        selected = min(
            candidates,
            key=lambda item: (float(item[1]["latitude"]) - latitude) ** 2
            + (((float(item[1]["longitude"]) - longitude + 180.0) % 360.0) - 180.0) ** 2,
        )
        lon_delta = ((float(selected[1]["longitude"]) - longitude + 180.0) % 360.0) - 180.0
        distance = math.hypot(float(selected[1]["latitude"]) - latitude, lon_delta)
        return selected if distance <= self.maximum_distance_deg else None

    def sample(self, latitude: float, longitude: float, month: int,
               altitude_m: float) -> Optional[Era5Sample]:
        selected = self._nearest(latitude, longitude, month)
        if selected is None:
            return None
        path, metadata = selected
        with np.load(path, allow_pickle=False) as data:
            missing = [name for name in self.REQUIRED if name not in data]
            if missing:
                raise ValueError(f"ERA5 profile 필드 누락: {missing}")
            altitude = np.asarray(data["altitude_m"], dtype=float)
            if altitude.ndim != 1 or len(altitude) < 2 or not np.all(np.diff(altitude) > 0):
                raise ValueError("ERA5 altitude_m은 증가하는 1-D profile이어야 합니다")
            if not altitude[0] <= altitude_m <= altitude[-1]:
                return None

            pressure_profile = np.asarray(data["pressure_Pa"], dtype=float)
            density_profile = np.asarray(data["density_kgm3"], dtype=float)
            if pressure_profile.shape != altitude.shape or np.any(np.diff(pressure_profile) >= 0.0):
                raise ValueError("ERA5 pressure는 고도가 증가할 때 감소해야 합니다")
            if density_profile.shape != altitude.shape or np.any(density_profile <= 0.0):
                raise ValueError("ERA5 density는 양수여야 합니다")

            def interp(name: str) -> float:
                values = np.asarray(data[name], dtype=float)
                if values.shape != altitude.shape or not np.all(np.isfinite(values)):
                    raise ValueError(f"ERA5 {name} profile이 유효하지 않습니다")
                return float(np.interp(altitude_m, altitude, values))

            sample = Era5Sample(
                interp("temperature_K"), interp("pressure_Pa"),
                interp("density_kgm3"), interp("relative_humidity_pct"),
                interp("wind_east_mps"), interp("wind_north_mps"),
                interp("wind_vertical_mps"), metadata,
            )
        if not 0.0 <= sample.relative_humidity_pct <= 100.0:
            raise ValueError("ERA5 relative humidity가 0–100% 범위를 벗어났습니다")
        if sample.pressure_Pa <= 0.0 or sample.temperature_K <= 0.0:
            raise ValueError("ERA5 temperature/pressure가 물리 범위를 벗어났습니다")
        return sample
