import csv
import sys
import unittest
import uuid
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from data_logger import DataLogger
from data_model import CSV_HEADER
from mock_data import MockDataGenerator


class DataLoggerTests(unittest.TestCase):
    def setUp(self):
        self.directory = Path(__file__).resolve().parent / "_runtime" / uuid.uuid4().hex
        self.directory.mkdir(parents=True)

    def tearDown(self):
        for path in self.directory.iterdir():
            path.unlink()
        self.directory.rmdir()
        parent = self.directory.parent
        if parent.exists() and not any(parent.iterdir()):
            parent.rmdir()

    def test_logger_writes_header_and_row(self):
        generator = MockDataGenerator(seed=1)
        measurement = generator.next_measurement()
        logger = DataLogger(self.directory, today=date(2026, 9, 15))
        path = logger.path
        logger.write(measurement)
        logger.close()

        with path.open(encoding="utf-8", newline="") as file:
            rows = list(csv.reader(file))
        self.assertEqual(tuple(rows[0]), CSV_HEADER)
        self.assertEqual(rows[1][0], "1")
        self.assertEqual(len(rows[1]), len(CSV_HEADER))

    def test_logger_never_overwrites(self):
        first = DataLogger(self.directory, today=date(2026, 9, 15))
        first.close()
        second = DataLogger(self.directory, today=date(2026, 9, 15))
        second.close()
        self.assertNotEqual(first.path, second.path)


class MockGeneratorTests(unittest.TestCase):
    def test_mock_rows_parse_and_change(self):
        generator = MockDataGenerator(seed=3)
        first = generator.next_measurement()
        second = generator.next_measurement()
        self.assertEqual((first.seq, second.seq), (1, 2))
        self.assertNotEqual(first.temperature_C, second.temperature_C)
        self.assertTrue(second.gps_ok)


if __name__ == "__main__":
    unittest.main()
