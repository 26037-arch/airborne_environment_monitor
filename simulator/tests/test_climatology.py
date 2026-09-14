import json
import shutil
import unittest
import uuid
from pathlib import Path

import numpy as np

from simulator.environment.cams_climatology import CamsClimatology, kgm3_to_ugm3
from simulator.environment.era5_climatology import Era5Climatology


class ClimatologyTests(unittest.TestCase):
    def setUp(self):
        self.directory = Path(__file__).parent / "_runtime" / uuid.uuid4().hex
        self.directory.mkdir(parents=True)

    def tearDown(self):
        shutil.rmtree(self.directory)

    def _metadata(self, directory, name="profile", month=9):
        directory.mkdir(parents=True)
        (directory / f"{name}.json").write_text(json.dumps({
            "latitude": 37.5, "longitude": 127.0, "month": month,
            "fixture": "synthetic structure test; not Earth data",
        }), encoding="utf-8")

    def test_era5_interpolation_and_ranges(self):
        target = self.directory / "era5"
        self._metadata(target)
        np.savez(target / "profile.npz", altitude_m=[0.0, 1000.0, 2000.0],
                 temperature_K=[290.0, 280.0, 270.0], pressure_Pa=[101000.0, 90000.0, 79000.0],
                 density_kgm3=[1.21, 1.10, 1.00], relative_humidity_pct=[60.0, 50.0, 40.0],
                 wind_east_mps=[1.0, 2.0, 3.0], wind_north_mps=[2.0, 3.0, 4.0],
                 wind_vertical_mps=[0.0, 0.0, 0.0])
        loader = Era5Climatology(target)
        sample = loader.sample(37.5, 127.0, 9, 500.0)
        self.assertAlmostEqual(sample.temperature_K, 285.0)
        self.assertAlmostEqual(sample.pressure_Pa, 95500.0)
        self.assertTrue(0.0 <= sample.relative_humidity_pct <= 100.0)
        self.assertIsNone(loader.sample(37.5, 127.0, 9, 3000.0))
        self.assertIsNone(loader.sample(1.3, 103.8, 9, 500.0))

    def test_era5_rejects_non_monotonic_altitude(self):
        target = self.directory / "era5"
        self._metadata(target)
        values = dict(altitude_m=[0.0, 1000.0, 900.0], temperature_K=[290.0] * 3,
                      pressure_Pa=[101000.0, 90000.0, 89000.0], density_kgm3=[1.0] * 3,
                      relative_humidity_pct=[50.0] * 3, wind_east_mps=[0.0] * 3,
                      wind_north_mps=[0.0] * 3, wind_vertical_mps=[0.0] * 3)
        np.savez(target / "profile.npz", **values)
        with self.assertRaises(ValueError):
            Era5Climatology(target).sample(37.5, 127.0, 9, 500.0)

    def test_era5_rejects_pressure_that_increases_with_altitude(self):
        target = self.directory / "era5"
        self._metadata(target)
        values = dict(altitude_m=[0.0, 1000.0], temperature_K=[290.0, 280.0],
                      pressure_Pa=[90000.0, 101000.0], density_kgm3=[1.1, 1.0],
                      relative_humidity_pct=[50.0, 40.0], wind_east_mps=[0.0, 0.0],
                      wind_north_mps=[0.0, 0.0], wind_vertical_mps=[0.0, 0.0])
        np.savez(target / "profile.npz", **values)
        with self.assertRaises(ValueError):
            Era5Climatology(target).sample(37.5, 127.0, 9, 500.0)

    def test_cams_unit_conversion_surface_policy_and_nan(self):
        self.assertEqual(kgm3_to_ugm3(1e-9), 1.0)
        with self.assertRaises(ValueError):
            kgm3_to_ugm3(-1e-9)
        target = self.directory / "cams"
        self._metadata(target)
        np.savez(target / "profile.npz", altitude_m=[0.0], pm25_kgm3=[12e-9], pm10_kgm3=[20e-9])
        loader = CamsClimatology(target)
        sample = loader.sample(37.5, 127.0, 9, 0.5)
        self.assertAlmostEqual(sample.pm25_ugm3, 12.0)
        self.assertAlmostEqual(sample.pm10_ugm3, 20.0)
        self.assertIsNone(loader.sample(37.5, 127.0, 9, 2.0))
        self.assertIsNone(loader.sample(1.3, 103.8, 9, 0.0))
        np.savez(target / "profile.npz", altitude_m=[0.0], pm25_kgm3=[np.nan], pm10_kgm3=[20e-9])
        self.assertIsNone(loader.sample(37.5, 127.0, 9, 0.0))


if __name__ == "__main__":
    unittest.main()
