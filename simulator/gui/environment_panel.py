from __future__ import annotations

from PySide6.QtWidgets import QComboBox, QDoubleSpinBox, QFormLayout, QGroupBox, QSpinBox


class EnvironmentPanel(QGroupBox):
    def __init__(self) -> None:
        super().__init__("Earth Environment")
        layout = QFormLayout(self)
        self.latitude = QDoubleSpinBox(); self.latitude.setRange(-90, 90); self.latitude.setDecimals(4); self.latitude.setValue(37.5)
        self.longitude = QDoubleSpinBox(); self.longitude.setRange(-180, 180); self.longitude.setDecimals(4); self.longitude.setValue(127.0)
        self.month = QSpinBox(); self.month.setRange(1, 12); self.month.setValue(9)
        self.mode = QComboBox(); self.mode.addItems(["EARTH CLIMATOLOGY", "STANDARD ATMOSPHERE", "CUSTOM SYNTHETIC TEST"])
        self.custom_temperature_c = QDoubleSpinBox(); self.custom_temperature_c.setRange(-100, 100); self.custom_temperature_c.setValue(15)
        self.custom_pressure_hpa = QDoubleSpinBox(); self.custom_pressure_hpa.setRange(1, 1200); self.custom_pressure_hpa.setValue(1013.25)
        self.custom_humidity = QDoubleSpinBox(); self.custom_humidity.setRange(0, 100); self.custom_humidity.setValue(50)
        self.custom_pm25 = QDoubleSpinBox(); self.custom_pm25.setRange(0, 1000); self.custom_pm25.setValue(0)
        self.custom_pm10 = QDoubleSpinBox(); self.custom_pm10.setRange(0, 1000); self.custom_pm10.setValue(0)
        for label, widget in (
            ("Latitude", self.latitude), ("Longitude", self.longitude),
            ("Month", self.month), ("Mode", self.mode),
            ("Custom temperature (°C)", self.custom_temperature_c),
            ("Custom pressure (hPa)", self.custom_pressure_hpa),
            ("Custom humidity (%)", self.custom_humidity),
            ("Custom PM2.5 (µg/m³)", self.custom_pm25),
            ("Custom PM10 (µg/m³)", self.custom_pm10),
        ):
            layout.addRow(label, widget)
        self.mode.currentTextChanged.connect(self._enable_custom)
        self._enable_custom(self.mode.currentText())

    def _enable_custom(self, mode: str) -> None:
        enabled = mode == "CUSTOM SYNTHETIC TEST"
        for widget in (self.custom_temperature_c, self.custom_pressure_hpa,
                       self.custom_humidity, self.custom_pm25, self.custom_pm10):
            widget.setEnabled(enabled)

    def values(self) -> dict[str, object]:
        custom = {}
        if self.mode.currentText() == "CUSTOM SYNTHETIC TEST":
            custom = {
                "temperature_K": self.custom_temperature_c.value() + 273.15,
                "pressure_Pa": self.custom_pressure_hpa.value() * 100.0,
                "relative_humidity_pct": self.custom_humidity.value(),
                "pm25_ugm3": self.custom_pm25.value(),
                "pm10_ugm3": self.custom_pm10.value(),
            }
        return {
            "latitude": self.latitude.value(), "longitude": self.longitude.value(),
            "month": self.month.value(), "atmosphere_mode": self.mode.currentText(),
            "custom_environment": custom,
        }

