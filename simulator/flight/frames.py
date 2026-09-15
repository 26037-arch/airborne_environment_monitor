"""Coordinate conversions at the Webots/ArduPilot boundary.

Webots world coordinates are ENU and the vehicle's local axes are FLU
(forward, left, up).  ArduPilot uses NED earth axes and FRD body axes.
All quaternions returned here are scalar-first and rotate body FRD into NED.
"""
from __future__ import annotations

import math

from shared.data_types import Vector3

Matrix3 = tuple[tuple[float, float, float], ...]
Quaternion = tuple[float, float, float, float]


def webots_enu_to_ned_vector(value: Vector3) -> Vector3:
    east, north, up = value
    return north, east, -up


def ned_to_webots_enu_vector(value: Vector3) -> Vector3:
    north, east, down = value
    return east, north, -down


webots_enu_to_ned_position = webots_enu_to_ned_vector


def _matmul(a: Matrix3, b: Matrix3) -> Matrix3:
    return tuple(tuple(sum(a[i][k] * b[k][j] for k in range(3)) for j in range(3)) for i in range(3))


def _transpose(a: Matrix3) -> Matrix3:
    return tuple(tuple(a[j][i] for j in range(3)) for i in range(3))


def _matvec(a: Matrix3, v: Vector3) -> Vector3:
    return tuple(sum(a[i][j] * v[j] for j in range(3)) for i in range(3))  # type: ignore[return-value]


def axis_angle_to_matrix(value: tuple[float, float, float, float]) -> Matrix3:
    x, y, z, angle = value
    if not all(math.isfinite(v) for v in value):
        raise ValueError("axis-angle contains NaN or infinity")
    length = math.sqrt(x*x + y*y + z*z)
    if length < 1e-12 or abs(angle) < 1e-12:
        return ((1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0))
    x, y, z = x/length, y/length, z/length
    c, s, t = math.cos(angle), math.sin(angle), 1.0-math.cos(angle)
    return (
        (t*x*x+c, t*x*y-s*z, t*x*z+s*y),
        (t*x*y+s*z, t*y*y+c, t*y*z-s*x),
        (t*x*z-s*y, t*y*z+s*x, t*z*z+c),
    )


def matrix_to_quaternion(matrix: Matrix3) -> Quaternion:
    m = matrix
    trace = m[0][0] + m[1][1] + m[2][2]
    if trace > 0.0:
        s = math.sqrt(trace + 1.0) * 2.0
        q = (0.25*s, (m[2][1]-m[1][2])/s, (m[0][2]-m[2][0])/s, (m[1][0]-m[0][1])/s)
    elif m[0][0] > m[1][1] and m[0][0] > m[2][2]:
        s = math.sqrt(1.0+m[0][0]-m[1][1]-m[2][2])*2.0
        q = ((m[2][1]-m[1][2])/s, 0.25*s, (m[0][1]+m[1][0])/s, (m[0][2]+m[2][0])/s)
    elif m[1][1] > m[2][2]:
        s = math.sqrt(1.0+m[1][1]-m[0][0]-m[2][2])*2.0
        q = ((m[0][2]-m[2][0])/s, (m[0][1]+m[1][0])/s, 0.25*s, (m[1][2]+m[2][1])/s)
    else:
        s = math.sqrt(1.0+m[2][2]-m[0][0]-m[1][1])*2.0
        q = ((m[1][0]-m[0][1])/s, (m[0][2]+m[2][0])/s, (m[1][2]+m[2][1])/s, 0.25*s)
    norm = math.sqrt(sum(v*v for v in q))
    if norm < 1e-12 or not math.isfinite(norm):
        raise ValueError("invalid orientation quaternion")
    return tuple(v/norm for v in q)  # type: ignore[return-value]


_ENU_TO_NED: Matrix3 = ((0.0, 1.0, 0.0), (1.0, 0.0, 0.0), (0.0, 0.0, -1.0))
_FRD_TO_FLU: Matrix3 = ((1.0, 0.0, 0.0), (0.0, -1.0, 0.0), (0.0, 0.0, -1.0))


def webots_orientation_to_ned_matrix(axis_angle: tuple[float, float, float, float]) -> Matrix3:
    # R_ned_frd = R_ned_enu * R_enu_flu * R_flu_frd
    return _matmul(_matmul(_ENU_TO_NED, axis_angle_to_matrix(axis_angle)), _FRD_TO_FLU)


def webots_orientation_to_ned_quaternion(axis_angle: tuple[float, float, float, float]) -> Quaternion:
    return matrix_to_quaternion(webots_orientation_to_ned_matrix(axis_angle))


def webots_angular_velocity_to_body_frd(angular_velocity_enu: Vector3,
                                        axis_angle: tuple[float, float, float, float]) -> Vector3:
    return _matvec(_transpose(webots_orientation_to_ned_matrix(axis_angle)),
                   webots_enu_to_ned_vector(angular_velocity_enu))


def webots_acceleration_to_body_frd(acceleration_enu: Vector3,
                                    axis_angle: tuple[float, float, float, float],
                                    gravity_mps2: float = 9.80665) -> Vector3:
    """Convert world kinematic acceleration to accelerometer specific force."""
    specific_enu = (acceleration_enu[0], acceleration_enu[1], acceleration_enu[2] + gravity_mps2)
    return _matvec(_transpose(webots_orientation_to_ned_matrix(axis_angle)),
                   webots_enu_to_ned_vector(specific_enu))
