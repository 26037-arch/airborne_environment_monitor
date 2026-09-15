import re
import unittest
from pathlib import Path

from shared.data_types import SensorReadings
from shared.telemetry_schema import CSV_HEADER, CSV_HEADER_V2, CSV_HEADER_V3, parse_csv_line
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
        header_file = Path(__file__).parents[2] / "arduino" / "airborne_monitor" / "telemetry.h"
        text = header_file.read_text(encoding="utf-8")
        macro = text.split("#define CSV_HEADER_V3_TEXT", 1)[1].split("\n\n", 1)[0]
        arduino_header = "".join(re.findall(r'"([^"]*)"', macro))
        self.assertEqual(tuple(arduino_header.split(",")), CSV_HEADER_V3)
        sensor = SensorReadings(20.0, 50.0, 1000.0, 1.0, 2.0, 3.0, 4.0,
                                37.5, 127.0, 100.0, 2.0, 90.0, True, True, True, True,
                                barometric_altitude_m=110.0,
                                accel_x_mps2=0.0, accel_y_mps2=0.0,
                                accel_z_mps2=9.81, gyro_x_dps=0.0,
                                gyro_y_dps=0.0, gyro_z_dps=1.0,
                                rtc_unix_time=1767225601, env_ok=True,
                                imu_ok=True, rtc_ok=True)
        parsed = parse_csv_line(TelemetryEncoder().encode(7, 1000, sensor))
        self.assertEqual(parsed.seq, 7)
        self.assertEqual(parsed.schema_version, 3)
        self.assertTrue(parsed.env_ok and parsed.imu_ok and parsed.gps_ok and parsed.rtc_ok)

        # Legacy encoder paths remain available for old replay/simulation workflows.
        self.assertEqual(parse_csv_line(TelemetryEncoder(1).encode(8, 2000, sensor)).schema_version, 1)
        self.assertEqual(parse_csv_line(TelemetryEncoder(2).encode(9, 3000, sensor)).schema_version, 2)

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

    def test_hc12_baud_matches_and_mega_uses_hardware_uart(self):
        root = Path(__file__).parents[2]
        mega_config = (root / "arduino" / "airborne_monitor" / "config.h").read_text(encoding="utf-8")
        uno_config = (root / "arduino" / "ground_hc12_bridge" / "config.h").read_text(encoding="utf-8")
        pattern = r"#define SERIAL_BAUD_HC12 (\d+)UL"
        self.assertEqual(re.search(pattern, mega_config).group(1),
                         re.search(pattern, uno_config).group(1))
        mega_source = (root / "arduino" / "airborne_monitor" / "airborne_monitor.ino").read_text(encoding="utf-8")
        self.assertIn("Serial3.begin(SERIAL_BAUD_HC12)", mega_source)
        self.assertNotIn("SoftwareSerial", mega_source)


if __name__ == "__main__":
    unittest.main()
