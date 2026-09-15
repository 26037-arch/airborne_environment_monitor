import shutil
import unittest
import uuid
from pathlib import Path

from shared.telemetry_schema import CSV_HEADER, CSV_HEADER_V2, CSV_HEADER_V3, encode_csv_row
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

    def test_v2_replay_is_accepted(self):
        path = self.directory / "flight_v2.csv"
        values = {
            "seq": 1, "time_ms": 0, "bme_ok": False, "sps_ok": False,
            "gps_ok": False, "sd_ok": True, "armed": False,
            "flight_link_ok": False,
        }
        path.write_text(
            ",".join(CSV_HEADER_V2) + "\n" +
            encode_csv_row(values, schema_version=2) + "\n", encoding="utf-8"
        )
        source = CSVReplaySource(path, realtime=False)
        try:
            self.assertEqual(source.read().schema_version, 2)
        finally:
            source.close()

    def test_v3_replay_is_accepted(self):
        path = self.directory / "flight_v3.csv"
        values = {
            "seq": 1, "time_ms": 0, "env_ok": False, "imu_ok": False,
            "gps_ok": False, "rtc_ok": False, "sd_ok": True,
        }
        path.write_text(
            ",".join(CSV_HEADER_V3) + "\n" +
            encode_csv_row(values, schema_version=3) + "\n", encoding="utf-8"
        )
        source = CSVReplaySource(path, realtime=False)
        try:
            self.assertEqual(source.read().schema_version, 3)
        finally:
            source.close()


if __name__ == "__main__":
    unittest.main()
