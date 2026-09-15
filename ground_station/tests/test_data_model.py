import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from data_model import InvalidRow, SequenceTracker, parse_csv_line
from shared.telemetry_schema import encode_csv_row


VALID = (
    "152,152000,18.42,55.30,942.83,4.10,7.20,8.30,9.60,"
    "37.123456,127.123456,523.40,3.82,124.30,1,1,1,1"
)


class CsvParsingTests(unittest.TestCase):
    def test_parse_valid_row(self):
        row = parse_csv_line(VALID)
        self.assertEqual(row.seq, 152)
        self.assertAlmostEqual(row.pm25_ugm3, 7.2)
        self.assertTrue(row.sd_ok)

    def test_na_values_when_sensor_failed(self):
        row = parse_csv_line(
            "1,1000,NA,NA,NA,4.1,7.2,8.3,9.6,NA,NA,NA,NA,NA,0,1,0,1"
        )
        self.assertIsNone(row.temperature_C)
        self.assertFalse(row.bme_ok)

    def test_invalid_column_count(self):
        with self.assertRaises(InvalidRow):
            parse_csv_line("1,2,3")

    def test_invalid_flag(self):
        with self.assertRaises(InvalidRow):
            parse_csv_line(VALID[:-1] + "9")

    def test_v2_flight_fields_and_v1_compatibility(self):
        v1 = parse_csv_line(VALID)
        self.assertEqual(v1.schema_version, 1)
        self.assertIsNone(v1.flight_link_ok)
        values = {
            "seq": 153, "time_ms": 153000, "temperature_C": 18.4,
            "humidity_pct": 55.3, "pressure_hPa": 942.8,
            "pm1_ugm3": 4.1, "pm25_ugm3": 7.2, "pm4_ugm3": 8.3,
            "pm10_ugm3": 9.6, "latitude": 37.123456,
            "longitude": 127.123456, "gps_altitude_m": 523.4,
            "gps_speed_mps": 3.82, "gps_course_deg": 124.3,
            "bme_ok": True, "sps_ok": True, "gps_ok": True, "sd_ok": True,
            "estimated_altitude_m": 520.0, "vertical_speed_mps": -1.2,
            "roll_deg": 2.0, "pitch_deg": -3.0, "yaw_deg": 124.3,
            "battery_voltage_V": 11.8, "battery_current_A": 1.4,
            "flight_mode": 4, "armed": True, "flight_link_ok": True,
            "system_health": 31,
        }
        v2 = parse_csv_line(encode_csv_row(values, schema_version=2))
        self.assertEqual(v2.schema_version, 2)
        self.assertAlmostEqual(v2.vertical_speed_mps, -1.2)
        self.assertTrue(v2.armed)
        self.assertTrue(v2.flight_link_ok)

    def test_v2_missing_flight_controller_is_valid(self):
        values = {
            "seq": 1, "time_ms": 1000, "bme_ok": False, "sps_ok": False,
            "gps_ok": False, "sd_ok": True, "armed": False,
            "flight_link_ok": False,
        }
        row = parse_csv_line(encode_csv_row(values, schema_version=2))
        self.assertFalse(row.flight_link_ok)
        self.assertIsNone(row.roll_deg)

    def test_invalid_v2_attitude_is_rejected(self):
        values = {
            "seq": 1, "time_ms": 1000, "bme_ok": False, "sps_ok": False,
            "gps_ok": False, "sd_ok": False, "roll_deg": 999.0,
            "armed": False, "flight_link_ok": True,
        }
        with self.assertRaises(InvalidRow):
            encode_csv_row(values, schema_version=2)


class SequenceTrackerTests(unittest.TestCase):
    def test_packet_loss(self):
        tracker = SequenceTracker()
        self.assertEqual(tracker.update(152), 0)
        self.assertEqual(tracker.update(153), 0)
        self.assertEqual(tracker.update(155), 1)
        self.assertEqual(tracker.stats.lost, 1)

    def test_sequence_reset(self):
        tracker = SequenceTracker()
        tracker.update(98)
        tracker.update(99)
        self.assertEqual(tracker.update(1), 0)
        self.assertEqual(tracker.stats.resets, 1)
        self.assertEqual(tracker.update(2), 0)


if __name__ == "__main__":
    unittest.main()
