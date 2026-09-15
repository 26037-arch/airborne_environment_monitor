import math
import shutil
import unittest
import uuid
from pathlib import Path
from types import SimpleNamespace

from shared.data_types import PayloadState
from shared.telemetry_schema import parse_csv_line
from simulator.configuration import SimulationConfig
from simulator.environment.earth_environment import AtmosphereMode
from simulator.flight.telemetry_source import (
    FlightTelemetryConfig, MavlinkTelemetrySource, MockFlightTelemetrySource,
)
from simulator.runtime import SimulationRuntime


class FakeConnection:
    def __init__(self, messages):
        self.messages = list(messages)

    def recv_match(self, blocking=False):
        return self.messages.pop(0) if self.messages else None


def message(kind, **values):
    return SimpleNamespace(get_type=lambda: kind, **values)


class FlightAdapterTests(unittest.TestCase):
    def test_bad_data_does_not_mark_link_connected(self):
        source = MavlinkTelemetrySource(
            FlightTelemetryConfig(), FakeConnection([message("BAD_DATA")])
        )
        self.assertFalse(source.poll(1000).connected)

    def test_mavlink_messages_update_status_without_blocking(self):
        connection = FakeConnection([
            message("HEARTBEAT", base_mode=128, custom_mode=4, system_status=3),
            message("ATTITUDE", roll=math.radians(2), pitch=math.radians(-3),
                    yaw=math.radians(-10)),
            message("GLOBAL_POSITION_INT", lat=375000000, lon=1270000000,
                    alt=123400, relative_alt=120000, vx=300, vy=400, vz=150),
            message("SYS_STATUS", voltage_battery=11800, current_battery=140,
                    onboard_control_sensors_health=31),
        ])
        source = MavlinkTelemetrySource(FlightTelemetryConfig(timeout_ms=3000), connection)
        status = source.poll(1000)
        self.assertTrue(status.connected and status.armed)
        self.assertAlmostEqual(status.yaw_deg, 350.0)
        self.assertAlmostEqual(status.ground_speed_mps, 5.0)
        self.assertAlmostEqual(status.vertical_speed_mps, -1.5)
        self.assertAlmostEqual(status.battery_voltage_v, 11.8)

    def test_timeout_marks_link_disconnected(self):
        source = MavlinkTelemetrySource(
            FlightTelemetryConfig(timeout_ms=3000),
            FakeConnection([message("HEARTBEAT", base_mode=128, custom_mode=4,
                                    system_status=3)]),
        )
        self.assertTrue(source.poll(1000).connected)
        status = source.poll(4001)
        self.assertFalse(status.connected)
        self.assertFalse(status.armed)


class MockFlightIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.root = Path(__file__).parent / "_runtime" / uuid.uuid4().hex
        self.root.mkdir(parents=True)

    def tearDown(self):
        shutil.rmtree(self.root)

    def test_mock_fc_to_v2_telemetry_and_ground_parser(self):
        config = SimulationConfig(atmosphere_mode=AtmosphereMode.STANDARD_ATMOSPHERE)
        runtime = SimulationRuntime(
            config, self.root / "data", self.root / "run",
            flight_source=MockFlightTelemetrySource(),
        )
        state = PayloadState(
            0.0, 37.5, 127.0, 100.0, (0.0, 0.0, 100.0),
            (3.0, 4.0, -2.0), (0.0, 0.0, 1.0, 0.0),
        )
        _drag, rows, _environment = runtime.step(state)
        runtime.close()
        measurement = parse_csv_line(rows[0])
        self.assertEqual(measurement.schema_version, 2)
        self.assertTrue(measurement.flight_link_ok)
        self.assertAlmostEqual(measurement.gps_speed_mps, 5.0)
        self.assertAlmostEqual(measurement.vertical_speed_mps, -2.0)


if __name__ == "__main__":
    unittest.main()
