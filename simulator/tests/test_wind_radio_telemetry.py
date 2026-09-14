import re
import unittest
from pathlib import Path

from shared.data_types import SensorReadings
from shared.telemetry_schema import CSV_HEADER, parse_csv_line
from simulator.environment.wind_model import WindConfig, WindMode, WindModel
from simulator.telemetry.encoder import TelemetryEncoder
from simulator.telemetry.virtual_radio import VirtualRadio, VirtualRadioConfig


class WindRadioTelemetryTests(unittest.TestCase):
    def test_gust_is_identical_for_same_seed_and_time(self):
        config = WindConfig(mode=WindMode.GUST, mean_speed_mps=8.0,
                            gust_amplitude_mps=2.0, gust_frequency_hz=0.25,
                            turbulence_std_mps=1.0, random_seed=12345)
        first, second = WindModel(config), WindModel(config)
        self.assertEqual([first.vector(300, t / 50) for t in range(200)],
                         [second.vector(300, t / 50) for t in range(200)])

    def test_telemetry_header_and_row_match_arduino(self):
        expected = ("seq", "time_ms", "temperature_C", "humidity_pct", "pressure_hPa",
                    "pm1_ugm3", "pm25_ugm3", "pm4_ugm3", "pm10_ugm3", "latitude",
                    "longitude", "gps_altitude_m", "gps_speed_mps", "gps_course_deg",
                    "bme_ok", "sps_ok", "gps_ok", "sd_ok")
        self.assertEqual(CSV_HEADER, expected)
        header_file = Path(__file__).parents[2] / "arduino" / "airborne_monitor" / "telemetry.h"
        text = header_file.read_text(encoding="utf-8")
        macro = text.split("#define CSV_HEADER_TEXT", 1)[1].split("\n\n", 1)[0]
        arduino_header = "".join(re.findall(r'"([^"]*)"', macro))
        self.assertEqual(tuple(arduino_header.split(",")), CSV_HEADER)
        sensor = SensorReadings(20.0, 50.0, 1000.0, 1.0, 2.0, 3.0, 4.0,
                                37.5, 127.0, 100.0, 2.0, 90.0, True, True, True, True)
        parsed = parse_csv_line(TelemetryEncoder().encode(7, 1000, sensor))
        self.assertEqual(parsed.seq, 7)
        self.assertTrue(parsed.bme_ok and parsed.sps_ok and parsed.gps_ok and parsed.sd_ok)

    def test_failure_radio_loss_delay_and_default_bypass(self):
        bypass = VirtualRadio(VirtualRadioConfig(packet_loss_probability=1.0))
        self.assertTrue(bypass.send("row", 0.0))
        self.assertEqual(bypass.receive_ready(0.0), ["row"])
        failed = VirtualRadio(VirtualRadioConfig(failure_test_enabled=True,
                              packet_loss_probability=1.0, random_seed=1))
        self.assertFalse(failed.send("lost", 0.0))
        delayed = VirtualRadio(VirtualRadioConfig(failure_test_enabled=True,
                               latency_ms=100.0, random_seed=1))
        delayed.send("later", 0.0)
        self.assertEqual(delayed.receive_ready(0.099), [])
        self.assertEqual(delayed.receive_ready(0.100), ["later"])


if __name__ == "__main__":
    unittest.main()
