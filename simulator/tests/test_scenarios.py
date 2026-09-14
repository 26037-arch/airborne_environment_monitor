import csv
import json
import shutil
import unittest
import uuid
from pathlib import Path

import numpy as np

from shared.data_types import PayloadState
from shared.telemetry_schema import CSV_HEADER, parse_csv_line
from simulator.configuration import SimulationConfig
from simulator.environment.earth_environment import AtmosphereMode, EarthEnvironment
from simulator.environment.wind_model import WindConfig, WindMode, WindModel
from simulator.runtime import SimulationRuntime
from simulator.sensors.noise import NoiseConfig, NoiseMode
from simulator.sensors.sensor_suite import FailureState
from simulator.telemetry.virtual_radio import VirtualRadioConfig


class ScenarioTests(unittest.TestCase):
    def setUp(self):
        self.root = Path(__file__).parent / "_runtime" / uuid.uuid4().hex
        self.data = self.root / "data"
        self.root.mkdir(parents=True)

    def tearDown(self):
        shutil.rmtree(self.root)

    @staticmethod
    def state(time_s=0.0, altitude=1000.0):
        return PayloadState(time_s, 37.5, 127.0, altitude, (0.0, 0.0, altitude),
                            (1.0, 0.0, -5.0), (0.0, 0.0, 1.0, 0.0))

    def _install_structural_fixtures(self):
        # Loader/integration fixture only: deliberately labelled synthetic and never shipped as Earth data.
        era = self.data / "climatology" / "era5"
        cams = self.data / "climatology" / "cams"
        era.mkdir(parents=True); cams.mkdir(parents=True)
        meta = {"latitude": 37.5, "longitude": 127.0, "month": 9,
                "fixture": "SYNTHETIC STRUCTURE TEST - NOT EARTH DATA"}
        (era / "fixture.json").write_text(json.dumps(meta), encoding="utf-8")
        (cams / "fixture.json").write_text(json.dumps(meta), encoding="utf-8")
        np.savez(era / "fixture.npz", altitude_m=[0.0, 2000.0],
                 temperature_K=[290.0, 270.0], pressure_Pa=[101000.0, 79000.0],
                 density_kgm3=[1.21, 1.00], relative_humidity_pct=[60.0, 40.0],
                 wind_east_mps=[1.0, 3.0], wind_north_mps=[2.0, 4.0],
                 wind_vertical_mps=[0.0, 0.0])
        np.savez(cams / "fixture.npz", altitude_m=[0.0, 2000.0],
                 pm25_kgm3=[10e-9, 5e-9], pm10_kgm3=[20e-9, 10e-9])

    def test_scenario_a_standard_calm_ideal_and_logs(self):
        config = SimulationConfig(atmosphere_mode=AtmosphereMode.STANDARD_ATMOSPHERE,
                                  noise=NoiseConfig(mode=NoiseMode.IDEAL, enabled=False),
                                  wind=WindConfig(mode=WindMode.CALM))
        run = self.root / "scenario_a"
        runtime = SimulationRuntime(config, self.data, run)
        drag, rows, env = runtime.step(self.state())
        runtime.close()
        self.assertEqual(env.wind_vector, (0.0, 0.0, 0.0))
        self.assertEqual(env.provenance["cams_status"], "NOT USED IN STANDARD ATMOSPHERE MODE")
        self.assertTrue(all(np.isfinite(drag)))
        self.assertEqual(len(rows), 1)
        with (run / "telemetry.csv").open(encoding="utf-8") as source:
            self.assertEqual(tuple(next(csv.reader(source))), CSV_HEADER)
        self.assertTrue((run / "truth.csv").exists() and (run / "error_report.json").exists())

    def test_scenario_b_climatology_fixture_constant_wind_datasheet(self):
        self._install_structural_fixtures()
        config = SimulationConfig(
            atmosphere_mode=AtmosphereMode.EARTH_CLIMATOLOGY,
            noise=NoiseConfig(mode=NoiseMode.DATASHEET, enabled=True, random_seed=12),
            wind=WindConfig(mode=WindMode.CONSTANT, speed_mps=10.0, direction_to_deg=90.0),
        )
        runtime = SimulationRuntime(config, self.data, self.root / "scenario_b")
        _drag, rows, env = runtime.step(self.state())
        runtime.close()
        self.assertEqual(env.mode, AtmosphereMode.EARTH_CLIMATOLOGY.value)
        self.assertAlmostEqual(env.wind_east_mps, 10.0)
        self.assertAlmostEqual(env.pm25_ugm3, 7.5)
        self.assertEqual(len(rows), 1)
        self.assertEqual(parse_csv_line(rows[0]).gps_ok, True)

    def test_scenario_c_same_gust_seed_repeats(self):
        config = WindConfig(mode=WindMode.GUST, mean_speed_mps=5.0,
                            gust_amplitude_mps=3.0, turbulence_std_mps=0.5,
                            random_seed=12345)
        first = [WindModel(config).vector(1000.0, i / 50.0) for i in range(50)]
        second = [WindModel(config).vector(1000.0, i / 50.0) for i in range(50)]
        self.assertEqual(first, second)

    def test_scenario_d_packet_loss_and_gps_dropout_remain_parseable(self):
        config = SimulationConfig(
            atmosphere_mode=AtmosphereMode.STANDARD_ATMOSPHERE,
            failures=FailureState(gps_dropout=True),
            radio=VirtualRadioConfig(failure_test_enabled=True, packet_loss_probability=0.1,
                                     random_seed=12345),
        )
        runtime = SimulationRuntime(config, self.data, self.root / "scenario_d")
        for index in range(100):
            runtime.step(self.state(float(index), 1000.0 - index))
        runtime.close()
        with (self.root / "scenario_d" / "telemetry.csv").open(encoding="utf-8") as source:
            measurements = [parse_csv_line(line) for line in list(source)[1:]]
        self.assertEqual(len(measurements), 100)
        self.assertTrue(all(not row.gps_ok and row.latitude is None for row in measurements))

    def test_scenario_e_no_cams_is_na_and_other_environment_continues(self):
        environment = EarthEnvironment(self.data, WindModel(WindConfig()))
        sample = environment.sample(37.5, 127.0, 9, 1000.0, 0.0,
                                    AtmosphereMode.EARTH_CLIMATOLOGY)
        self.assertIsNone(sample.pm25_ugm3)
        self.assertIsNone(sample.pm10_ugm3)
        self.assertGreater(sample.pressure_Pa, 0.0)
        self.assertEqual(sample.mode, AtmosphereMode.STANDARD_ATMOSPHERE.value)


if __name__ == "__main__":
    unittest.main()
