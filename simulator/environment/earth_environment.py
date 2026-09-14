from __future__ import annotations

from enum import Enum
from pathlib import Path
from typing import Optional

from shared.data_types import EnvironmentSample

from .cams_climatology import CamsClimatology
from .era5_climatology import Era5Climatology
from .standard_atmosphere import R_AIR, standard_atmosphere
from .wind_model import WindMode, WindModel


class AtmosphereMode(str, Enum):
    EARTH_CLIMATOLOGY = "EARTH CLIMATOLOGY"
    STANDARD_ATMOSPHERE = "STANDARD ATMOSPHERE"
    CUSTOM_TEST = "CUSTOM SYNTHETIC TEST"


class EarthEnvironment:
    """환경 자료 접근을 Webots, sensor, GUI에서 분리하는 유일한 facade."""

    def __init__(self, data_root: Path, wind_model: WindModel,
                 custom_values: Optional[dict[str, float]] = None) -> None:
        root = Path(data_root)
        self.era5 = Era5Climatology(root / "climatology" / "era5")
        self.cams = CamsClimatology(root / "climatology" / "cams")
        self.wind_model = wind_model
        self.custom_values = custom_values or {}

    def sample(self, latitude: float, longitude: float, month: int,
               altitude_m: float, time_s: float,
               mode: AtmosphereMode) -> EnvironmentSample:
        if not -90.0 <= latitude <= 90.0 or not -180.0 <= longitude <= 180.0:
            raise ValueError("latitude/longitude 범위가 잘못되었습니다")
        if not 1 <= month <= 12:
            raise ValueError("month는 1–12여야 합니다")

        if mode == AtmosphereMode.CUSTOM_TEST:
            required = ("temperature_K", "pressure_Pa", "relative_humidity_pct")
            missing = [key for key in required if key not in self.custom_values]
            if missing:
                raise ValueError(f"CUSTOM TEST 값 누락: {missing}")
            temperature = float(self.custom_values["temperature_K"])
            pressure = float(self.custom_values["pressure_Pa"])
            density = float(self.custom_values.get("air_density_kgm3", pressure / (R_AIR * temperature)))
            rh = float(self.custom_values["relative_humidity_pct"])
            baseline_wind = None
            pm1 = self.custom_values.get("pm1_ugm3")
            pm25 = self.custom_values.get("pm25_ugm3")
            pm10 = self.custom_values.get("pm10_ugm3")
            provenance: dict[str, object] = {
                "mode": mode.value, "source": "USER_OVERRIDE",
                "warning": "SYNTHETIC TEST DATA",
            }
        else:
            era = None
            if mode == AtmosphereMode.EARTH_CLIMATOLOGY:
                era = self.era5.sample(latitude, longitude, month, altitude_m)
            if era is None:
                standard = standard_atmosphere(max(0.0, altitude_m))
                temperature, pressure, density = (
                    standard.temperature_K, standard.pressure_Pa, standard.density_kgm3
                )
                rh = None
                baseline_wind = None
                actual_mode = AtmosphereMode.STANDARD_ATMOSPHERE.value
                provenance = {
                    "mode": actual_mode,
                    "temperature_source": "U.S. Standard Atmosphere 1976",
                    "pressure_source": "U.S. Standard Atmosphere 1976",
                    "density_source": "U.S. Standard Atmosphere 1976",
                    "humidity_source": "UNAVAILABLE",
                    "era5_status": "NOT INSTALLED OR OUT OF PROFILE RANGE",
                }
            else:
                temperature, pressure, density = (
                    era.temperature_K, era.pressure_Pa, era.density_kgm3
                )
                rh = era.relative_humidity_pct
                baseline_wind = (
                    era.wind_east_mps, era.wind_north_mps, era.wind_vertical_mps
                )
                actual_mode = AtmosphereMode.EARTH_CLIMATOLOGY.value
                provenance = dict(era.metadata)
                provenance.update({"mode": actual_mode, "era5_status": "INSTALLED"})

            cams = (
                self.cams.sample(latitude, longitude, month, altitude_m)
                if mode == AtmosphereMode.EARTH_CLIMATOLOGY else None
            )
            if mode != AtmosphereMode.EARTH_CLIMATOLOGY:
                pm1 = pm25 = pm10 = None
                provenance.update({
                    "cams_status": "NOT USED IN STANDARD ATMOSPHERE MODE",
                    "pm1_source": "UNAVAILABLE", "pm25_source": "UNAVAILABLE",
                    "pm10_source": "UNAVAILABLE", "pm4_source": "UNAVAILABLE",
                })
            elif cams is None:
                pm1 = pm25 = pm10 = None
                provenance.update({
                    "cams_status": "NOT INSTALLED OR OUT OF PROFILE RANGE",
                    "pm1_source": "UNAVAILABLE", "pm25_source": "UNAVAILABLE",
                    "pm10_source": "UNAVAILABLE", "pm4_source": "UNAVAILABLE",
                })
            else:
                pm1 = None
                pm25, pm10 = cams.pm25_ugm3, cams.pm10_ugm3
                provenance.update(cams.metadata)
                provenance.update({
                    "cams_status": "INSTALLED", "pm1_source": "UNAVAILABLE",
                    "pm4_source": "UNAVAILABLE",
                })

        wind = self.wind_model.vector(altitude_m, time_s, baseline_wind)
        wind_source = self.wind_model.config.mode.value
        if self.wind_model.config.mode == WindMode.ERA5 and baseline_wind is None:
            wind_source += " UNAVAILABLE -> CALM"
        provenance.update({
            "wind_source": wind_source,
            "location_lat": latitude, "location_lon": longitude, "month": month,
        })
        return EnvironmentSample(
            altitude_m, temperature, pressure, density, rh,
            None if pm1 is None else float(pm1),
            None if pm25 is None else float(pm25),
            None if pm10 is None else float(pm10),
            wind[0], wind[1], wind[2], str(provenance["mode"]), provenance,
        )
