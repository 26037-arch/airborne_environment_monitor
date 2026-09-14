from __future__ import annotations

import json
import os
import shutil
from pathlib import Path

from PySide6.QtCore import QProcess, QProcessEnvironment, QTimer
from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QDoubleSpinBox, QFormLayout, QGridLayout, QGroupBox,
    QHBoxLayout, QLabel, QMainWindow, QMessageBox, QPushButton, QSpinBox,
    QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget,
)

from .environment_panel import EnvironmentPanel
from .graphs import HistoryGraph
from .wind_panel import WindPanel


class MainWindow(QMainWindow):
    def __init__(self, project_root: Path) -> None:
        super().__init__()
        self.project_root = Path(project_root)
        self.runs = self.project_root / "simulator" / "runs"
        self.process: QProcess | None = None
        self.graph_time = 0.0
        self.setWindowTitle("Earth Environment Simulator — Webots Control")
        self.resize(1240, 820)
        self._build()
        self.timer = QTimer(self); self.timer.timeout.connect(self._poll_status); self.timer.start(500)

    def _build(self) -> None:
        root = QWidget(); self.setCentralWidget(root)
        layout = QVBoxLayout(root)
        self.banner = QLabel("EARTH CLIMATOLOGY | CLIMATOLOGY, NOT CURRENT WEATHER")
        self.banner.setStyleSheet("font-size: 16px; font-weight: bold; padding: 8px; background: #16324f; color: white")
        layout.addWidget(self.banner)
        columns = QHBoxLayout(); layout.addLayout(columns, 1)
        left = QVBoxLayout(); columns.addLayout(left, 0)
        self.environment_panel = EnvironmentPanel(); left.addWidget(self.environment_panel)
        self.wind_panel = WindPanel(); left.addWidget(self.wind_panel)
        initial = QGroupBox("Payload / Sensor / Failure"); form = QFormLayout(initial)
        self.altitude = self._spin(0, 80000, 1000); self.v_east = self._spin(-500, 500, 0)
        self.v_north = self._spin(-500, 500, 0); self.v_vertical = self._spin(-500, 500, -5)
        self.mass = self._spin(0.01, 100, 1); self.cd = self._spin(0, 5, 0.8); self.area = self._spin(0, 10, 0.03, 4)
        self.noise_mode = QComboBox(); self.noise_mode.addItems(["IDEAL", "DATASHEET", "CUSTOM"])
        self.noise_enable = QCheckBox("Enable noise"); self.noise_strength = self._spin(0, 10, 1)
        self.radio_failure = QCheckBox("Enable failure test")
        self.loss = self._spin(0, 100, 0); self.latency = self._spin(0, 10000, 0)
        self.jitter = self._spin(0, 10000, 0); self.radio_range = self._spin(0, 1_000_000, 0)
        self.radio_range.setSpecialValueText("Unlimited")
        self.bme_fail = QCheckBox(); self.sps_fail = QCheckBox(); self.gps_fail = QCheckBox(); self.sd_fail = QCheckBox()
        for label, widget in (
            ("Initial altitude (m)", self.altitude), ("Velocity east (m/s)", self.v_east),
            ("Velocity north (m/s)", self.v_north), ("Velocity vertical (m/s)", self.v_vertical),
            ("Payload mass (kg)", self.mass), ("Drag coefficient", self.cd),
            ("Reference area (m²)", self.area), ("Sensor mode", self.noise_mode),
            ("Noise", self.noise_enable), ("Noise strength", self.noise_strength),
            ("Radio failure mode", self.radio_failure), ("Radio loss (%)", self.loss),
            ("Radio latency (ms)", self.latency), ("Radio jitter std (ms)", self.jitter),
            ("Radio max range (m)", self.radio_range),
            ("BME failure", self.bme_fail), ("SPS failure", self.sps_fail),
            ("GPS dropout", self.gps_fail), ("SD failure", self.sd_fail),
        ):
            form.addRow(label, widget)
        left.addWidget(initial)
        buttons = QHBoxLayout(); self.start_button = QPushButton("Start Webots"); self.source_button = QPushButton("Source / Provenance")
        buttons.addWidget(self.start_button); buttons.addWidget(self.source_button); left.addLayout(buttons)
        self.start_button.clicked.connect(self._start_webots); self.source_button.clicked.connect(self._show_source)

        right = QVBoxLayout(); columns.addLayout(right, 1)
        self.table = QTableWidget(8, 3); self.table.setHorizontalHeaderLabels(["Quantity", "EARTH TRUE VALUE", "SENSOR READING"])
        for row, name in enumerate(("Temperature °C", "Pressure hPa", "Humidity %", "PM2.5 µg/m³", "PM10 µg/m³", "Altitude m", "Ground speed m/s", "Status")):
            self.table.setItem(row, 0, QTableWidgetItem(name))
        self.table.horizontalHeader().setStretchLastSection(True); right.addWidget(self.table)
        self.vector_label = QLabel("TRUE WIND: -\nPAYLOAD GROUND VELOCITY: -\nRELATIVE AIR VELOCITY: -")
        self.vector_label.setStyleSheet("font-family: Consolas; padding: 8px"); right.addWidget(self.vector_label)
        graph_row = QHBoxLayout(); self.graph_choice = QComboBox(); self.graph_choice.addItems(["Altitude", "Temperature", "Pressure", "Humidity", "PM2.5", "PM10"])
        graph_row.addWidget(QLabel("Graph")); graph_row.addWidget(self.graph_choice); graph_row.addStretch(); right.addLayout(graph_row)
        self.graph = HistoryGraph(); right.addWidget(self.graph, 1)
        self.statusBar().showMessage("Webots를 시작하면 별도 3D 창이 열립니다.")

    @staticmethod
    def _spin(minimum, maximum, value, decimals=2):
        widget = QDoubleSpinBox(); widget.setRange(minimum, maximum); widget.setDecimals(decimals); widget.setValue(value); return widget

    def _config(self) -> dict[str, object]:
        seed = self.wind_panel.seed.value()
        values = self.environment_panel.values()
        values.update({
            "initial_altitude_m": self.altitude.value(), "initial_velocity_east_mps": self.v_east.value(),
            "initial_velocity_north_mps": self.v_north.value(), "initial_velocity_vertical_mps": self.v_vertical.value(),
            "payload_mass_kg": self.mass.value(), "drag_coefficient": self.cd.value(),
            "reference_area_m2": self.area.value(), "telemetry_interval_s": 1.0,
            "random_seed": seed, "wind": self.wind_panel.values(),
            "noise": {"mode": self.noise_mode.currentText(), "enabled": self.noise_enable.isChecked(), "strength": self.noise_strength.value(), "random_seed": seed},
            "failures": {"bme280_failure": self.bme_fail.isChecked(), "sps30_failure": self.sps_fail.isChecked(), "gps_dropout": self.gps_fail.isChecked(), "sd_failure": self.sd_fail.isChecked()},
            "radio": {"failure_test_enabled": self.radio_failure.isChecked(),
                      "packet_loss_probability": self.loss.value() / 100.0,
                      "latency_ms": self.latency.value(), "jitter_ms": self.jitter.value(),
                      "maximum_range_m": None if self.radio_range.value() == 0 else self.radio_range.value(),
                      "random_seed": seed},
        })
        return values

    def _webots_executable(self) -> str | None:
        found = shutil.which("webots") or shutil.which("webots.exe")
        if found: return found
        home = os.environ.get("WEBOTS_HOME")
        if home:
            candidate = Path(home) / "msys64" / "mingw64" / "bin" / "webots.exe"
            if candidate.exists(): return str(candidate)
        candidate = Path("C:/Program Files/Webots/msys64/mingw64/bin/webots.exe")
        return str(candidate) if candidate.exists() else None

    def _start_webots(self) -> None:
        executable = self._webots_executable()
        if not executable:
            QMessageBox.critical(self, "Webots not found", "Webots를 설치하거나 WEBOTS_HOME을 설정하세요.")
            return
        try:
            config = self._config()
        except ValueError as exc:
            QMessageBox.warning(self, "Invalid setting", str(exc)); return
        config_path = self.runs / "active_config.json"; self.runs.mkdir(parents=True, exist_ok=True)
        config_path.write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8")
        process = QProcess(self); environment = QProcessEnvironment.systemEnvironment()
        environment.insert("AEM_SIM_CONFIG", str(config_path)); environment.insert("AEM_SIM_RUN_DIR", str(self.runs))
        process.setProcessEnvironment(environment); process.setProgram(executable)
        process.setArguments([str(self.project_root / "simulator" / "webots" / "worlds" / "earth_environment.wbt")])
        process.start(); self.process = process
        mode = str(config["atmosphere_mode"])
        warning = "CLIMATOLOGY, NOT CURRENT WEATHER" if mode == "EARTH CLIMATOLOGY" else mode
        self.banner.setText(f"{mode} | {warning} | {config['latitude']}°, {config['longitude']}° | MONTH {config['month']}")
        self.statusBar().showMessage("Webots 시작 중… Ground Station: python main.py --simulation")

    def _latest_status(self) -> Path | None:
        paths = list(self.runs.glob("run_*/status.json"))
        return max(paths, key=lambda path: path.stat().st_mtime) if paths else None

    def _poll_status(self) -> None:
        path = self._latest_status()
        if path is None: return
        try: data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError): return
        true, sensor = data["true"], data["sensor"]
        ground = true["ground_velocity_enu_mps"]
        true_values = [true["temperature_C"], true["pressure_hPa"], true["humidity_pct"], true["pm25_ugm3"], true["pm10_ugm3"], true["altitude_m"], sum(v*v for v in ground[:2]) ** 0.5, data["mode"]]
        sensor_values = [sensor["temperature_C"], sensor["pressure_hPa"], sensor["humidity_pct"], sensor["pm25_ugm3"], sensor["pm10_ugm3"], sensor["gps_altitude_m"], sensor["gps_speed_mps"], f"BME={sensor['bme_ok']} SPS={sensor['sps_ok']} GPS={sensor['gps_ok']} SD={sensor['sd_ok']}"]
        for row, (earth, measured) in enumerate(zip(true_values, sensor_values)):
            self.table.setItem(row, 1, QTableWidgetItem("N/A" if earth is None else f"{earth:.3f}" if isinstance(earth, (int, float)) else str(earth)))
            self.table.setItem(row, 2, QTableWidgetItem("N/A" if measured is None else f"{measured:.3f}" if isinstance(measured, (int, float)) else str(measured)))
        radio = data.get("radio", {})
        self.vector_label.setText(
            f"→ TRUE WIND [cyan]: {true['wind_enu_mps']}\n"
            f"→ PAYLOAD GROUND VELOCITY [yellow]: {ground}\n"
            f"→ RELATIVE AIR VELOCITY [magenta]: {true['relative_air_velocity_enu_mps']}\n"
            f"RADIO delivered/dropped/pending: {radio.get('delivered', 0)}/"
            f"{radio.get('dropped', 0)}/{radio.get('pending', 0)}"
        )
        mapping = {"Altitude": (true["altitude_m"], "Altitude (m)"), "Temperature": (true["temperature_C"], "Temperature (°C)"), "Pressure": (true["pressure_hPa"], "Pressure (hPa)"), "Humidity": (true["humidity_pct"], "RH (%)"), "PM2.5": (true["pm25_ugm3"], "PM2.5 (µg/m³)"), "PM10": (true["pm10_ugm3"], "PM10 (µg/m³)")}
        self.graph_time = float(data.get("time_s", self.graph_time + 0.5))
        value, label = mapping[self.graph_choice.currentText()]; self.graph.append(self.graph_time, value, label)
        self.banner.setText(f"{data['mode']} | {'CAMS DATA: '+data['provenance'].get('cams_status','N/A')} | CLIMATOLOGY, NOT CURRENT WEATHER")

    def _show_source(self) -> None:
        path = self._latest_status()
        text = "아직 simulation status가 없습니다."
        if path:
            try: text = json.dumps(json.loads(path.read_text(encoding="utf-8"))["provenance"], ensure_ascii=False, indent=2)
            except Exception: pass
        QMessageBox.information(self, "Data provenance", text)
