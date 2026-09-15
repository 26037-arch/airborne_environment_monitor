import math
import unittest

from simulator.flight.frames import (
    ned_to_webots_enu_vector, webots_acceleration_to_body_frd,
    webots_angular_velocity_to_body_frd, webots_enu_to_ned_vector,
    webots_orientation_to_ned_quaternion,
)


class FrameTests(unittest.TestCase):
    def test_enu_ned_known_vector_and_inverse(self):
        source = (12.0, -4.0, 7.0)
        self.assertEqual(webots_enu_to_ned_vector(source), (-4.0, 12.0, -7.0))
        self.assertEqual(ned_to_webots_enu_vector(webots_enu_to_ned_vector(source)), source)

    def test_identity_webots_body_faces_east_in_ned(self):
        q = webots_orientation_to_ned_quaternion((0.0, 0.0, 1.0, 0.0))
        self.assertAlmostEqual(math.sqrt(sum(v*v for v in q)), 1.0, places=12)
        self.assertAlmostEqual(abs(q[0]), math.sqrt(0.5), places=12)
        self.assertAlmostEqual(abs(q[3]), math.sqrt(0.5), places=12)

    def test_world_angular_velocity_becomes_body_frd(self):
        result = webots_angular_velocity_to_body_frd((1.0, 2.0, 3.0), (0.0, 0.0, 1.0, 0.0))
        self.assertEqual(result, (1.0, -2.0, -3.0))

    def test_stationary_accelerometer_is_minus_g_on_frd_z(self):
        result = webots_acceleration_to_body_frd((0.0, 0.0, 0.0), (0.0, 0.0, 1.0, 0.0))
        self.assertAlmostEqual(result[0], 0.0)
        self.assertAlmostEqual(result[1], 0.0)
        self.assertAlmostEqual(result[2], -9.80665)

    def test_free_fall_specific_force_is_zero(self):
        result = webots_acceleration_to_body_frd((0.0, 0.0, -9.80665), (0.0, 0.0, 1.0, 0.0))
        self.assertTrue(all(abs(v) < 1e-12 for v in result))


if __name__ == "__main__":
    unittest.main()
