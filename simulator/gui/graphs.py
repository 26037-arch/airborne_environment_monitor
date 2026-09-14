from __future__ import annotations

from collections import deque

from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure


class HistoryGraph(FigureCanvasQTAgg):
    def __init__(self, maximum_points: int = 300) -> None:
        self.figure = Figure(figsize=(6, 3), dpi=100)
        super().__init__(self.figure)
        self.axis = self.figure.add_subplot(111)
        self.times = deque(maxlen=maximum_points)
        self.values = deque(maxlen=maximum_points)

    def append(self, time_s: float, value: float | None, label: str) -> None:
        self.times.append(time_s)
        self.values.append(value)
        points = [(x, y) for x, y in zip(self.times, self.values) if y is not None]
        self.axis.clear()
        if points:
            x, y = zip(*points)
            self.axis.plot(x, y, color="#1976d2")
        self.axis.set_xlabel("Simulation time (s)")
        self.axis.set_ylabel(label)
        self.axis.grid(True, alpha=0.25)
        self.figure.tight_layout()
        self.draw_idle()

