from __future__ import annotations

from PySide6.QtWidgets import QComboBox, QDoubleSpinBox, QFormLayout, QGroupBox, QLineEdit, QSpinBox


class WindPanel(QGroupBox):
    def __init__(self) -> None:
        super().__init__("Wind Controls")
        layout = QFormLayout(self)
        self.mode = QComboBox(); self.mode.addItems(["CALM", "CONSTANT", "LAYERED", "GUST_RANDOM", "ERA5_CLIMATOLOGY"])
        self.speed = QDoubleSpinBox(); self.speed.setRange(0, 100)
        self.direction = QDoubleSpinBox(); self.direction.setRange(0, 360)
        self.vertical = QDoubleSpinBox(); self.vertical.setRange(-30, 30)
        self.gust = QDoubleSpinBox(); self.gust.setRange(0, 50)
        self.frequency = QDoubleSpinBox(); self.frequency.setRange(0, 10); self.frequency.setDecimals(3); self.frequency.setValue(0.1)
        self.turbulence = QDoubleSpinBox(); self.turbulence.setRange(0, 30)
        self.seed = QSpinBox(); self.seed.setRange(0, 2_147_483_647); self.seed.setValue(12345)
        self.layers = QLineEdit("0:100:2:90;100:500:5:120;500:2000:8:150")
        self.layers.setToolTip("min:max:speed:direction; ... (direction is where wind goes)")
        for label, widget in (
            ("Mode", self.mode), ("Speed / mean (m/s)", self.speed),
            ("Direction to (deg)", self.direction), ("Vertical (m/s)", self.vertical),
            ("Gust amplitude", self.gust), ("Gust frequency (Hz)", self.frequency),
            ("Turbulence std", self.turbulence), ("Random seed", self.seed),
            ("Layers", self.layers),
        ):
            layout.addRow(label, widget)

    def values(self) -> dict[str, object]:
        layers = []
        if self.mode.currentText() == "LAYERED":
            for item in self.layers.text().split(";"):
                minimum, maximum, speed, direction = map(float, item.split(":"))
                layers.append({
                    "minimum_altitude_m": minimum, "maximum_altitude_m": maximum,
                    "speed_mps": speed, "direction_to_deg": direction,
                    "vertical_mps": 0.0,
                })
        return {
            "mode": self.mode.currentText(), "speed_mps": self.speed.value(),
            "direction_to_deg": self.direction.value(), "vertical_mps": self.vertical.value(),
            "layers": layers, "mean_speed_mps": self.speed.value(),
            "mean_direction_to_deg": self.direction.value(),
            "gust_amplitude_mps": self.gust.value(),
            "gust_frequency_hz": self.frequency.value(),
            "turbulence_std_mps": self.turbulence.value(),
            "random_seed": self.seed.value(), "physics_rate_hz": 50.0,
        }

