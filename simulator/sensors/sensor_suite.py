from __future__ import annotations

from dataclasses import dataclass

from shared.data_types import EnvironmentSample, PayloadState, SensorReadings

from .bme280_model import Bme280Model
from .gnss_model import GnssModel
from .noise import NoiseConfig
from .sps30_model import Sps30Model


@dataclass
class FailureState:
    bme280_failure: bool = False
    sps30_failure: bool = False
    gps_dropout: bool = False
    sd_failure: bool = False


class SensorSuite:
    def __init__(self, noise: NoiseConfig) -> None:
        self.bme = Bme280Model(noise)
        self.sps = Sps30Model(noise)
        self.gnss = GnssModel(noise)

    def read(self, environment: EnvironmentSample, state: PayloadState,
             failures: FailureState) -> SensorReadings:
        bme = self.bme.read(environment, failures.bme280_failure)
        sps = self.sps.read(environment, failures.sps30_failure)
        gps = self.gnss.read(state, failures.gps_dropout)
        return SensorReadings(
            bme.temperature_C, bme.humidity_pct, bme.pressure_hPa,
            sps.pm1_ugm3, sps.pm25_ugm3, sps.pm4_ugm3, sps.pm10_ugm3,
            gps.latitude, gps.longitude, gps.altitude_m, gps.speed_mps,
            gps.course_deg, bme.ok, sps.ok, gps.ok, not failures.sd_failure,
        )

