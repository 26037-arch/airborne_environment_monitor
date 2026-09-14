from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

import numpy as np


class NoiseMode(str, Enum):
    IDEAL = "IDEAL"
    DATASHEET = "DATASHEET"
    CUSTOM = "CUSTOM"


@dataclass(frozen=True)
class NoiseConfig:
    mode: NoiseMode = NoiseMode.IDEAL
    enabled: bool = False
    strength: float = 1.0
    random_seed: int = 12345


def generator(config: NoiseConfig, stream_id: int) -> np.random.Generator:
    return np.random.default_rng(np.random.SeedSequence([config.random_seed, stream_id]))

