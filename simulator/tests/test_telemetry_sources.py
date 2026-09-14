import shutil
import unittest
import uuid
from pathlib import Path

from shared.telemetry_schema import CSV_HEADER
from shared.telemetry_sources import CSVReplaySource, TelemetrySource


class TelemetrySourceTests(unittest.TestCase):
    def setUp(self):
        self.directory = Path(__file__).parent / "_runtime" / uuid.uuid4().hex
        self.directory.mkdir(parents=True)

    def tearDown(self):
        shutil.rmtree(self.directory)

    def test_csv_replay_uses_canonical_parser(self):
        path = self.directory / "flight.csv"
        path.write_text(
            ",".join(CSV_HEADER) + "\n" +
            "1,0,20.00,50.00,1013.25,1.00,2.00,3.00,4.00,37.500000,127.000000,"
            "100.00,0.00,0.00,1,1,1,1\n",
            encoding="utf-8",
        )
        source: TelemetrySource = CSVReplaySource(path, realtime=False)
        try:
            self.assertEqual(source.read().seq, 1)
            self.assertIsNone(source.read())
        finally:
            source.close()

    def test_wrong_header_is_rejected(self):
        path = self.directory / "bad.csv"
        path.write_text("seq,time_ms\n1,0\n", encoding="utf-8")
        with self.assertRaises(ValueError):
            CSVReplaySource(path, realtime=False)


if __name__ == "__main__":
    unittest.main()
