import csv
import unittest
from pathlib import Path

from simulator.environment.standard_atmosphere import standard_atmosphere


class StandardAtmosphereTests(unittest.TestCase):
    # U.S. Standard Atmosphere 1976 reference values at geometric altitude.
    # T: 0.05 K, pressure/density: 0.2% relative tolerance.
    def test_reference_table(self):
        reference = Path(__file__).parents[1] / "data" / "standard_atmosphere" / "reference_1976.csv"
        with reference.open(encoding="utf-8", newline="") as source:
            rows = list(csv.DictReader(source))
        for row in rows:
            altitude = float(row["geometric_altitude_m"])
            temperature = float(row["temperature_K"])
            pressure = float(row["pressure_Pa"])
            density = float(row["density_kgm3"])
            with self.subTest(altitude=altitude):
                sample = standard_atmosphere(altitude)
                self.assertAlmostEqual(sample.temperature_K, temperature, delta=0.05)
                self.assertAlmostEqual(sample.pressure_Pa, pressure, delta=pressure * 0.002)
                self.assertAlmostEqual(sample.density_kgm3, density, delta=density * 0.002)

    def test_supported_range_is_enforced(self):
        with self.assertRaises(ValueError):
            standard_atmosphere(-1.0)
        with self.assertRaises(ValueError):
            standard_atmosphere(90_000.0)


if __name__ == "__main__":
    unittest.main()
