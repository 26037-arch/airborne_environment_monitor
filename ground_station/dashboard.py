from __future__ import annotations

import queue
import tkinter as tk
from collections import deque
from tkinter import ttk
from typing import Callable, Optional

from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure

import config
from data_logger import DataLogger
from data_model import Measurement, SequenceTracker
from serial_receiver import ConnectionState, ReceiverEvent


GRAPH_OPTIONS = {
    "Barometric altitude": ("barometric_altitude_m", "Barometric altitude (m)"),
    "GPS altitude": ("gps_altitude_m", "GPS altitude (m)"),
    "Temperature": ("temperature_C", "Temperature (°C)"),
    "Pressure": ("pressure_hPa", "Pressure (hPa)"),
    "GPS ground speed": ("gps_speed_mps", "GPS ground speed (m/s)"),
    "Acceleration Z": ("accel_z_mps2", "Acceleration Z (m/s²)"),
}


class Dashboard:
    def __init__(self, root: tk.Tk, events: queue.Queue[ReceiverEvent],
                 logger: DataLogger, tracker: SequenceTracker,
                 on_close: Callable[[], None]) -> None:
        self.root = root
        self.events = events
        self.logger = logger
        self.tracker = tracker
        self.on_close_callback = on_close
        self.invalid_count = 0
        self.times: deque[float] = deque(maxlen=config.GRAPH_POINT_COUNT)
        self.history: dict[str, deque[Optional[float]]] = {
            field: deque(maxlen=config.GRAPH_POINT_COUNT)
            for field, _ in GRAPH_OPTIONS.values()
        }
        self.value_labels: dict[str, ttk.Label] = {}
        self.root.title("Airborne Environment Ground Station")
        self.root.geometry("1260x760")
        self.root.minsize(1060, 660)
        self.root.protocol("WM_DELETE_WINDOW", self._close)
        self._build()
        self.root.after(100, self._process_events)

    def _metric_frame(self, parent, title: str,
                      rows: list[tuple[str, str]]) -> ttk.LabelFrame:
        frame = ttk.LabelFrame(parent, text=title, padding=10)
        frame.pack(fill="x", pady=(0, 8))
        for index, (caption, key) in enumerate(rows):
            ttk.Label(frame, text=caption).grid(
                row=index, column=0, sticky="w", padx=(0, 14), pady=2
            )
            label = ttk.Label(frame, text="N/A")
            label.grid(row=index, column=1, sticky="e", pady=2)
            self.value_labels[key] = label
        return frame

    def _build(self) -> None:
        top = ttk.Frame(self.root, padding=10)
        top.pack(fill="x")
        ttk.Label(top, text="Connection:", font=("Segoe UI", 11, "bold")).pack(side="left")
        self.connection_label = tk.Label(
            top, text="DISCONNECTED", fg="#b91c1c", font=("Segoe UI", 11, "bold")
        )
        self.connection_label.pack(side="left", padx=(6, 20))
        self.port_label = ttk.Label(top, text="Port: -")
        self.port_label.pack(side="left")
        ttk.Label(top, text=f"PC CSV: {self.logger.path}").pack(side="right")

        body = ttk.Frame(self.root, padding=(10, 0, 10, 10))
        body.pack(fill="both", expand=True)
        metrics = ttk.Frame(body)
        metrics.pack(side="left", fill="y", padx=(0, 10))
        self._metric_frame(metrics, "Environment", [
            ("Temperature", "temperature_C"), ("Humidity", "humidity_pct"),
            ("Pressure", "pressure_hPa"),
            ("Barometric altitude", "barometric_altitude_m"),
        ])
        self._metric_frame(metrics, "Position", [
            ("Latitude", "latitude"), ("Longitude", "longitude"),
            ("GPS altitude", "gps_altitude_m"),
            ("GPS ground speed", "gps_speed_mps"),
            ("GPS course", "gps_course_deg"),
        ])
        self._metric_frame(metrics, "IMU", [
            ("Acceleration x / y / z", "acceleration"),
            ("Gyro x / y / z", "gyro"),
        ])
        self._metric_frame(metrics, "System", [
            ("Schema", "schema"), ("Sequence / runtime", "sequence_runtime"),
            ("ENV / IMU / GPS / RTC / SD", "health"),
            ("RTC Unix time", "rtc_unix_time"),
            ("Packets received", "received"), ("Packets lost", "lost"),
            ("Packet loss", "loss"),
        ])

        plot_frame = ttk.LabelFrame(body, text="Recent data", padding=10)
        plot_frame.pack(side="left", fill="both", expand=True)
        selector_row = ttk.Frame(plot_frame)
        selector_row.pack(fill="x")
        ttk.Label(selector_row, text="Graph:").pack(side="left")
        self.graph_name = tk.StringVar(value=next(iter(GRAPH_OPTIONS)))
        selector = ttk.Combobox(
            selector_row, textvariable=self.graph_name, values=list(GRAPH_OPTIONS),
            state="readonly", width=28,
        )
        selector.pack(side="left", padx=8)
        selector.bind("<<ComboboxSelected>>", lambda _event: self._draw_graph())
        self.figure = Figure(figsize=(7, 5), dpi=100)
        self.axis = self.figure.add_subplot(111)
        self.canvas = FigureCanvasTkAgg(self.figure, master=plot_frame)
        self.canvas.get_tk_widget().pack(fill="both", expand=True, pady=(8, 0))
        self.message_label = ttk.Label(self.root, text="Ready", padding=8)
        self.message_label.pack(fill="x")

    @staticmethod
    def _number(value: Optional[float], unit: str = "", digits: int = 2) -> str:
        return "N/A" if value is None else f"{value:.{digits}f}{unit}"

    def _set_state(self, state: ConnectionState) -> None:
        colors = {
            ConnectionState.CONNECTED: "#15803d", ConnectionState.MOCK: "#1d4ed8",
            ConnectionState.RECONNECTING: "#b45309",
            ConnectionState.DISCONNECTED: "#b91c1c",
        }
        self.connection_label.configure(text=state.value, fg=colors[state])

    @staticmethod
    def _health_text(m: Measurement) -> str:
        if m.schema_version == 3:
            states = (m.env_ok, m.imu_ok, m.gps_ok, m.rtc_ok, m.sd_ok)
            return " / ".join("OK" if value else "FAIL" for value in states)
        # Legacy v1/v2 has no IMU or RTC health flags.
        return " / ".join((
            "OK" if m.bme_ok else "FAIL", "N/A",
            "OK" if m.gps_ok else "FAIL", "N/A", "OK" if m.sd_ok else "FAIL",
        ))

    def _handle_measurement(self, m: Measurement) -> None:
        missing = self.tracker.update(m.seq)
        try:
            self.logger.write(m)
        except (OSError, ValueError) as exc:
            self.message_label.configure(text=f"PC CSV error: {exc}")
        self.value_labels["schema"].configure(text=f"v{m.schema_version}")
        self.value_labels["sequence_runtime"].configure(
            text=f"{m.seq} / {m.time_ms / 1000.0:.1f} s"
        )
        self.value_labels["temperature_C"].configure(text=self._number(m.temperature_C, " °C"))
        self.value_labels["humidity_pct"].configure(text=self._number(m.humidity_pct, " %"))
        self.value_labels["pressure_hPa"].configure(text=self._number(m.pressure_hPa, " hPa"))
        self.value_labels["barometric_altitude_m"].configure(
            text=self._number(m.barometric_altitude_m, " m")
        )
        self.value_labels["latitude"].configure(text=self._number(m.latitude, digits=6))
        self.value_labels["longitude"].configure(text=self._number(m.longitude, digits=6))
        self.value_labels["gps_altitude_m"].configure(text=self._number(m.gps_altitude_m, " m"))
        self.value_labels["gps_speed_mps"].configure(text=self._number(m.gps_speed_mps, " m/s"))
        self.value_labels["gps_course_deg"].configure(text=self._number(m.gps_course_deg, "°"))
        self.value_labels["acceleration"].configure(text=" / ".join(
            self._number(value, " m/s²")
            for value in (m.accel_x_mps2, m.accel_y_mps2, m.accel_z_mps2)
        ))
        self.value_labels["gyro"].configure(text=" / ".join(
            self._number(value, "°/s")
            for value in (m.gyro_x_dps, m.gyro_y_dps, m.gyro_z_dps)
        ))
        self.value_labels["health"].configure(text=self._health_text(m))
        self.value_labels["rtc_unix_time"].configure(
            text="N/A" if m.rtc_unix_time is None else str(m.rtc_unix_time)
        )
        stats = self.tracker.stats
        self.value_labels["received"].configure(text=str(stats.received))
        self.value_labels["lost"].configure(text=str(stats.lost))
        self.value_labels["loss"].configure(text=f"{stats.loss_percent:.2f} %")
        if missing:
            self.message_label.configure(text=f"{missing} packet(s) missing before seq {m.seq}")
        self.times.append(m.time_ms / 1000.0)
        for field in self.history:
            self.history[field].append(getattr(m, field))
        self._draw_graph()

    def _draw_graph(self) -> None:
        field, ylabel = GRAPH_OPTIONS[self.graph_name.get()]
        points = [(x, y) for x, y in zip(self.times, self.history[field]) if y is not None]
        self.axis.clear()
        if points:
            x_values, y_values = zip(*points)
            self.axis.plot(x_values, y_values, color="#2563eb", linewidth=1.8)
        self.axis.set_xlabel("Runtime (s)")
        self.axis.set_ylabel(ylabel)
        self.axis.grid(True, alpha=0.25)
        self.figure.tight_layout()
        self.canvas.draw_idle()

    def _process_events(self) -> None:
        try:
            while True:
                event = self.events.get_nowait()
                if event.kind == "state":
                    self._set_state(event.value)
                elif event.kind == "port":
                    self.port_label.configure(text=f"Port: {event.value}")
                elif event.kind == "measurement":
                    self._handle_measurement(event.value)
                elif event.kind == "invalid":
                    self.invalid_count += 1
                    self.message_label.configure(
                        text=f"Invalid rows ignored: {self.invalid_count}: {event.value}"
                    )
                elif event.kind == "error":
                    self.message_label.configure(text=str(event.value))
        except queue.Empty:
            pass
        self.root.after(100, self._process_events)

    def _close(self) -> None:
        self.on_close_callback()
        self.root.destroy()
