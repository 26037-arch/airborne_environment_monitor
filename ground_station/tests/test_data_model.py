import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from data_model import InvalidRow, SequenceTracker, parse_csv_line


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

