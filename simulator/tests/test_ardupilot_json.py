import json
import socket
import struct
import shutil
import unittest
import uuid
from pathlib import Path

from shared.data_types import PayloadState
from simulator.configuration import (FlightControllerConfig, FlightPhysicsConfig,
                                     SimulationConfig, VehicleConfig)
from simulator.environment.earth_environment import AtmosphereMode
from simulator.flight.actuators import ActuatorCommand, ConfigurableMultirotorActuatorModel
from simulator.flight.ardupilot_json import (ArduPilotSitlEngine, MAGIC_16,
                                              MAGIC_32, PACKET_16, PACKET_32,
                                              ArduPilotLinkStatus,
                                              FlightPhysicsEngine, PhysicsInput)
from simulator.runtime import SimulationRuntime


class FakeSocket:
    def __init__(self, packets=()):
        self.packets = list(packets); self.sent = []; self.timeout = None; self.closed = False
    def settimeout(self, value): self.timeout = value
    def recvfrom(self, size):
        if not self.packets: raise socket.timeout()
        value = self.packets.pop(0)
        if isinstance(value, Exception): raise value
        return value, ("127.0.0.1", 55000)
    def sendto(self, data, peer): self.sent.append((data, peer)); return len(data)
    def close(self): self.closed = True


def state(timestamp=0.02):
    return PhysicsInput(timestamp, (2.0, 1.0, -3.0), (5.0, 4.0, -6.0),
                        (1.0, 0.0, 0.0, 0.0), (0.1, 0.2, 0.3),
                        (0.0, 0.0, -9.80665), (8.0, 7.0, -9.0))


class ProtocolTests(unittest.TestCase):
    def test_json_contains_current_required_fields_and_19_scalars(self):
        physics = state()
        payload = physics.to_packet()
        self.assertTrue(payload.startswith(b"\n{") and payload.endswith(b"}\n"))
        data = json.loads(payload)
        self.assertEqual(data["position"], [2.0, 1.0, -3.0])
        self.assertEqual(data["velocity_wind"], [8.0, 7.0, -9.0])
        self.assertEqual(len(physics.scalars()), 20)  # timestamp + 19 state scalars
        self.assertIn("gyro", data["imu"]); self.assertIn("accel_body", data["imu"])

    def test_valid_servo_packet_is_normalized_and_replied_to(self):
        pwm = [1000, 1500, 2000] + [0] * 13
        fake = FakeSocket([PACKET_16.pack(MAGIC_16, 400, 7, *pwm)])
        engine = ArduPilotSitlEngine(timeout_ms=10, sock=fake)
        command = engine.step(state())
        self.assertTrue(command.valid)
        self.assertEqual(command.channels[:3], (0.0, 0.5, 1.0))
        self.assertEqual(engine.status.frame_count, 7)
        self.assertEqual(len(fake.sent), 1)
        self.assertEqual(json.loads(fake.sent[0][0])["timestamp"], 0.02)

    def test_current_32_channel_packet(self):
        fake = FakeSocket([PACKET_32.pack(MAGIC_32, 400, 9, *([1500] * 32))])
        command = ArduPilotSitlEngine(timeout_ms=10, sock=fake).step(state())
        self.assertTrue(command.valid)
        self.assertEqual(len(command.channels), 32)

    def test_malformed_timeout_and_reconnect_are_safe(self):
        good = PACKET_16.pack(MAGIC_16, 400, 8, *([1100] * 16))
        fake = FakeSocket([b"bad", socket.timeout(), good])
        engine = ArduPilotSitlEngine(timeout_ms=10, sock=fake)
        self.assertFalse(engine.step(state(0.02)).valid)
        self.assertFalse(engine.step(state(0.04)).valid)
        self.assertTrue(engine.step(state(0.06)).valid)
        self.assertEqual(engine.status.invalid_packet_count, 1)
        self.assertEqual(engine.status.timeout_count, 1)

    def test_time_reset_discards_stale_actuator(self):
        good = PACKET_16.pack(MAGIC_16, 400, 8, *([1100] * 16))
        engine = ArduPilotSitlEngine(timeout_ms=10, sock=FakeSocket([good, good]))
        self.assertTrue(engine.step(state(1.0)).valid)
        self.assertFalse(engine.step(state(0.0)).valid)

    def test_virtual_quad_wrench(self):
        model = ConfigurableMultirotorActuatorModel(
            4, ((1, 1, 0), (1, -1, 0), (-1, -1, 0), (-1, 1, 0)),
            (1, -1, 1, -1), 4.0, 0.1)
        wrench = model.calculate(ActuatorCommand((0.5, 0.5, 0.5, 0.5), 0.0))
        self.assertEqual(wrench.force_body_flu_n, (0.0, 0.0, 4.0))
        self.assertAlmostEqual(sum(abs(v) for v in wrench.torque_body_flu_nm), 0.0)


class FakePhysicsEngine(FlightPhysicsEngine):
    def __init__(self): self.status = ArduPilotLinkStatus(physics_connected=True)
    def step(self, physics):
        self.status.physics_packet_count += 1
        return ActuatorCommand((0.5, 0.5, 0.5, 0.5), physics.timestamp_s, True,
                               (1500, 1500, 1500, 1500))


class RuntimeClosedLoopTests(unittest.TestCase):
    def test_runtime_converts_truth_and_exposes_virtual_wrench(self):
        config = SimulationConfig(
            atmosphere_mode=AtmosphereMode.STANDARD_ATMOSPHERE,
            flight_controller=FlightControllerConfig(
                physics_engine=FlightPhysicsConfig(mode="ARDUPILOT_SITL_JSON")),
            vehicle=VehicleConfig(
                type="MULTIROTOR_SIMULATION", motor_count=4,
                motor_positions_m=[[.2, -.2, 0], [-.2, .2, 0], [.2, .2, 0], [-.2, -.2, 0]],
                motor_directions=[1, 1, -1, -1], max_thrust_per_motor_n=5,
                torque_coefficient=.02, profile_label="TEST"))
        directory = Path(__file__).parent / "_runtime" / uuid.uuid4().hex
        directory.mkdir(parents=True)
        try:
            runtime = SimulationRuntime(config, directory / "data", directory / "run",
                                        physics_engine=FakePhysicsEngine())
            payload = PayloadState(
                .02, 37.5, 127.0, 10.0, (0.0, 0.0, 10.0),
                (0.0, 0.0, 0.0), (0.0, 0.0, 1.0, 0.0),
                (0.0, 0.0, 0.0), (0.0, 0.0, 0.0))
            runtime.step(payload)
            self.assertTrue(runtime.last_actuator.valid)
            self.assertEqual(runtime.last_wrench.force_body_flu_n, (0.0, 0.0, 5.0))
            runtime.close()
            lines = (directory / "run" / "actuator.csv").read_text().splitlines()
            self.assertEqual(len(lines), 2)
        finally:
            shutil.rmtree(directory)


if __name__ == "__main__":
    unittest.main()
