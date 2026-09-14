from __future__ import annotations

import math
from dataclasses import dataclass


# U.S. Standard Atmosphere 1976, geopotential layers below 86 km.
G0 = 9.80665
EARTH_RADIUS_M = 6_356_766.0
R_AIR = 287.05287
SEA_LEVEL_T_K = 288.15
SEA_LEVEL_P_PA = 101_325.0
LAYER_BASE_H_M = (0.0, 11_000.0, 20_000.0, 32_000.0, 47_000.0, 51_000.0, 71_000.0, 84_852.0)
LAPSE_K_PER_M = (-0.0065, 0.0, 0.0010, 0.0028, 0.0, -0.0028, -0.0020)


@dataclass(frozen=True)
class StandardAtmosphereState:
    geometric_altitude_m: float
    geopotential_altitude_m: float
    temperature_K: float
    pressure_Pa: float
    density_kgm3: float


def _layer_bases() -> tuple[tuple[float, float], ...]:
    bases = [(SEA_LEVEL_T_K, SEA_LEVEL_P_PA)]
    for index, lapse in enumerate(LAPSE_K_PER_M[:-1]):
        h0, h1 = LAYER_BASE_H_M[index], LAYER_BASE_H_M[index + 1]
        t0, p0 = bases[-1]
        t1 = t0 + lapse * (h1 - h0)
        if lapse == 0.0:
            p1 = p0 * math.exp(-G0 * (h1 - h0) / (R_AIR * t0))
        else:
            p1 = p0 * (t0 / t1) ** (G0 / (R_AIR * lapse))
        bases.append((t1, p1))
    return tuple(bases)


LAYER_BASES = _layer_bases()


def standard_atmosphere(geometric_altitude_m: float) -> StandardAtmosphereState:
    """COESA 1976의 0–84.852 km geopotential layer 식을 계산합니다."""
    if geometric_altitude_m < 0.0:
        raise ValueError("standard atmosphere altitude는 0 m 이상이어야 합니다")
    h = EARTH_RADIUS_M * geometric_altitude_m / (EARTH_RADIUS_M + geometric_altitude_m)
    if h > LAYER_BASE_H_M[-1]:
        raise ValueError("이 구현은 geopotential altitude 84.852 km까지만 지원합니다")

    layer = len(LAPSE_K_PER_M) - 1
    for index in range(len(LAPSE_K_PER_M)):
        if h < LAYER_BASE_H_M[index + 1]:
            layer = index
            break
    h0 = LAYER_BASE_H_M[layer]
    t0, p0 = LAYER_BASES[layer]
    lapse = LAPSE_K_PER_M[layer]
    temperature = t0 + lapse * (h - h0)
    if lapse == 0.0:
        pressure = p0 * math.exp(-G0 * (h - h0) / (R_AIR * t0))
    else:
        pressure = p0 * (t0 / temperature) ** (G0 / (R_AIR * lapse))
    density = pressure / (R_AIR * temperature)
    return StandardAtmosphereState(
        geometric_altitude_m, h, temperature, pressure, density
    )

