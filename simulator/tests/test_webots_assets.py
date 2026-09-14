import unittest
from pathlib import Path


class WebotsAssetTests(unittest.TestCase):
    def setUp(self):
        self.simulator = Path(__file__).parents[1]

    def test_world_declares_enu_50hz_payload_radio_and_visuals(self):
        world = (self.simulator / "webots" / "worlds" / "earth_environment.wbt").read_text(encoding="utf-8")
        for marker in ('coordinateSystem "ENU"', "basicTimeStep 20", "gravity 9.80665",
                       "DEF PAYLOAD Robot", "Emitter {", "Receiver {", "TRAJECTORY_LINE",
                       "WIND_ARROW", "GROUND_VELOCITY_ARROW", "RELATIVE_AIR_ARROW"):
            self.assertIn(marker, world)
        for forbidden in ("Rocket", "Thrust", "ignition", "RotationalMotor"):
            self.assertNotIn(forbidden, world)

    def test_controller_applies_drag_and_generates_trajectory(self):
        controller = (self.simulator / "webots" / "controllers" /
                      "payload_controller" / "payload_controller.py").read_text(encoding="utf-8")
        self.assertIn("payload.addForce", controller)
        self.assertIn("runtime.step", controller)
        self.assertIn("trajectory_coord.insertMFVec3f", controller)


if __name__ == "__main__":
    unittest.main()
