from __future__ import annotations

import heapq
from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class VirtualRadioConfig:
    failure_test_enabled: bool = False
    packet_loss_probability: float = 0.0
    latency_ms: float = 0.0
    jitter_ms: float = 0.0
    maximum_range_m: float | None = None
    random_seed: int = 12345


class VirtualRadio:
    def __init__(self, config: VirtualRadioConfig) -> None:
        if not 0.0 <= config.packet_loss_probability <= 1.0:
            raise ValueError("packet loss probability는 0–1이어야 합니다")
        self.config = config
        self.rng = np.random.default_rng(config.random_seed)
        self.pending: list[tuple[float, int, str]] = []
        self.counter = 0
        self.attempted = 0
        self.dropped = 0
        self.delivered = 0

    def send(self, row: str, now_s: float, distance_m: float = 0.0) -> bool:
        config = self.config
        self.attempted += 1
        if not config.failure_test_enabled:
            heapq.heappush(self.pending, (now_s, self.counter, row))
            self.counter += 1
            return True
        if config.maximum_range_m is not None and distance_m > config.maximum_range_m:
            self.dropped += 1
            return False
        if float(self.rng.random()) < config.packet_loss_probability:
            self.dropped += 1
            return False
        jitter = float(self.rng.normal(0.0, config.jitter_ms)) if config.jitter_ms else 0.0
        due = now_s + max(0.0, config.latency_ms + jitter) / 1000.0
        heapq.heappush(self.pending, (due, self.counter, row))
        self.counter += 1
        return True

    def receive_ready(self, now_s: float) -> list[str]:
        rows: list[str] = []
        while self.pending and self.pending[0][0] <= now_s:
            rows.append(heapq.heappop(self.pending)[2])
            self.delivered += 1
        return rows

    @property
    def status(self) -> dict[str, int]:
        return {"attempted": self.attempted, "dropped": self.dropped,
                "delivered": self.delivered, "pending": len(self.pending)}
