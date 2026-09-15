"""Optional test against an already-running official ArduPilot JSON SITL.

Start `sim_vehicle.py ... --model JSON:127.0.0.1`, then set
AEM_RUN_ARDUPILOT_SITL=1. This test never reports a synthetic success.
"""
import os
import unittest

from simulator.flight.ardupilot_json import ArduPilotSitlEngine, PhysicsInput


@unittest.skipUnless(os.environ.get("AEM_RUN_ARDUPILOT_SITL") == "1",
                     "ArduPilot SITL not installed/enabled (set AEM_RUN_ARDUPILOT_SITL=1)")
class ArduPilotSitlIntegrationTests(unittest.TestCase):
    def test_actual_json_link_returns_actuators_for_closed_loop_steps(self):
        port = int(os.environ.get("AEM_ARDUPILOT_JSON_PORT", "9002"))
        engine = ArduPilotSitlEngine(port=port, timeout_ms=12000, lockstep=True)
        try:
            commands = []
            for index in range(5):
                state = PhysicsInput(
                    index * 0.02, (0.0, 0.0, -10.0), (0.0, 0.0, 0.0),
                    (1.0, 0.0, 0.0, 0.0), (0.0, 0.0, 0.0),
                    (0.0, 0.0, -9.80665), (0.0, 0.0, 0.0))
                commands.append(engine.step(state))
            self.assertTrue(all(command.valid for command in commands))
            self.assertEqual(engine.status.physics_packet_count, 5)
            self.assertEqual(engine.status.actuator_packet_count, 5)
        finally:
            engine.close()

    def test_actual_mavlink_heartbeat(self):
        try:
            from pymavlink import mavutil
        except ModuleNotFoundError as exc:
            self.skipTest(str(exc))
        endpoint = os.environ.get("AEM_ARDUPILOT_MAVLINK", "udp:127.0.0.1:14550")
        connection = mavutil.mavlink_connection(endpoint)
        try:
            self.assertIsNotNone(connection.wait_heartbeat(timeout=10))
        finally:
            connection.close()


if __name__ == "__main__":
    unittest.main()
