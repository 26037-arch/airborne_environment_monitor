from __future__ import annotations

from dataclasses import dataclass

from shared.data_types import EnvironmentSample, PayloadState, SensorReadings

from .aht20_model import Aht20Model
from .bme280_model import Bme280Model
from .bmp280_model import Bmp280Model
from .gnss_model import GnssModel
from .mpu6050_model import Mpu6050Model
from .noise import NoiseConfig
from .rtc_model import RtcModel
from .sps30_model import Sps30Model


@dataclass
class FailureState:
    # Legacy v1/v2 simulation controls remain supported.
    bme280_failure: bool = False
    sps30_failure: bool = False
    gps_dropout: bool = False
    sd_failure: bool = False
    # Physical payload v3 controls.
    aht20_failure: bool = False
    bmp280_failure: bool = False
    mpu6050_failure: bool = False
    rtc_failure: bool = False


class SensorSuite:
    def __init__(self, noise: NoiseConfig, sea_level_pressure_hpa: float = 1013.25,
                 simulation_epoch_unix: int = 1767225600) -> None:
        self.aht = Aht20Model(noise)
        self.bmp = Bmp280Model(noise, sea_level_pressure_hpa)
        self.mpu = Mpu6050Model(noise)
        self.rtc = RtcModel(simulation_epoch_unix)
        self.bme = Bme280Model(noise)
        self.sps = Sps30Model(noise)
        self.gnss = GnssModel(noise)

    def read(self, environment: EnvironmentSample, state: PayloadState,
             failures: FailureState, schema_version: int = 3) -> SensorReadings:
        gps = self.gnss.read(state, failures.gps_dropout)
        if schema_version in {1, 2}:
            bme = self.bme.read(environment, failures.bme280_failure)
            sps = self.sps.read(environment, failures.sps30_failure)
            return SensorReadings(
                bme.temperature_C, bme.humidity_pct, bme.pressure_hPa,
                sps.pm1_ugm3, sps.pm25_ugm3, sps.pm4_ugm3, sps.pm10_ugm3,
                gps.latitude, gps.longitude, gps.altitude_m, gps.speed_mps,
                gps.course_deg, bme.ok, sps.ok, gps.ok, not failures.sd_failure,
            )

        aht = self.aht.read(
            environment, failures.aht20_failure or failures.bme280_failure
        )
        bmp = self.bmp.read(
            environment, failures.bmp280_failure or failures.bme280_failure
        )
        imu = self.mpu.read(state, failures.mpu6050_failure)
        rtc = self.rtc.read(state.time_s, failures.rtc_failure)
        env_ok = aht.ok and bmp.ok
        return SensorReadings(
            temperature_C=aht.temperature_C,
            humidity_pct=aht.humidity_pct,
            pressure_hPa=bmp.pressure_hPa,
            pm1_ugm3=None, pm25_ugm3=None, pm4_ugm3=None, pm10_ugm3=None,
            latitude=gps.latitude, longitude=gps.longitude,
            gps_altitude_m=gps.altitude_m, gps_speed_mps=gps.speed_mps,
            gps_course_deg=gps.course_deg, bme_ok=env_ok, sps_ok=False,
            gps_ok=gps.ok, sd_ok=not failures.sd_failure,
            barometric_altitude_m=bmp.barometric_altitude_m,
            accel_x_mps2=imu.acceleration_mps2[0],
            accel_y_mps2=imu.acceleration_mps2[1],
            accel_z_mps2=imu.acceleration_mps2[2],
            gyro_x_dps=imu.gyro_dps[0], gyro_y_dps=imu.gyro_dps[1],
            gyro_z_dps=imu.gyro_dps[2], rtc_unix_time=rtc.unix_time,
            env_ok=env_ok, imu_ok=imu.ok, rtc_ok=rtc.ok,
        )
