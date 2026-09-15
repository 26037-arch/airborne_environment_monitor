from __future__ import annotations

import json
import math
from pathlib import Path

from shared.data_types import EnvironmentSample, PayloadState
from shared.flight_status import FlightStatus

from .configuration import SimulationConfig
from .environment.earth_environment import EarthEnvironment
from .flight.telemetry_source import FlightTelemetrySource, create_flight_source
from .flight.ardupilot_json import (ArduPilotSitlEngine, FlightPhysicsEngine,
                                    NullFlightPhysicsEngine, PhysicsInput)
from .flight.actuators import ActuatorCommand, ActuatorWrench, create_actuator_model
from .run_logging import RunLogger, create_error_report
from .sensors.sensor_suite import SensorSuite
from .telemetry.encoder import TelemetryEncoder
from .telemetry.virtual_radio import VirtualRadio


class SimulationRuntime:
    """Webots physics state를 환경→센서→telemetry pipeline에 연결합니다."""

    def __init__(self, config: SimulationConfig, data_root: Path,
                 run_directory: Path,
                 flight_source: FlightTelemetrySource | None = None,
                 physics_engine: FlightPhysicsEngine | None = None) -> None:
        self.config = config
        from .environment.wind_model import WindModel
        self.environment = EarthEnvironment(data_root, WindModel(config.wind), config.custom_environment)
        self.sensors = SensorSuite(
            config.noise, config.sea_level_pressure_hpa,
            config.simulation_epoch_unix,
        )
        self.encoder = TelemetryEncoder(config.telemetry_schema_version)
        self.radio = VirtualRadio(config.radio)
        self.flight_source = flight_source or create_flight_source(config.flight_controller.telemetry)
        physics_config = config.flight_controller.physics_engine
        self.physics_engine = physics_engine or (
            ArduPilotSitlEngine(
                physics_config.host, physics_config.port, physics_config.timeout_ms,
                physics_config.lockstep, physics_config.pwm_min, physics_config.pwm_max,
            ) if physics_config.mode == "ARDUPILOT_SITL_JSON" else NullFlightPhysicsEngine()
        )
        if (physics_engine is None and physics_config.mode == "ARDUPILOT_SITL_JSON" and
                physics_config.lifecycle == "MANAGED"):
            self.physics_engine.start_process(
                physics_config.binary, physics_config.arguments,
                physics_config.working_directory)
        self.actuator_model = create_actuator_model(config.vehicle)
        self.last_actuator = ActuatorCommand((), 0.0, False)
        self.last_wrench = ActuatorWrench()
        self.flight_status: FlightStatus | None = None
        self.logger = RunLogger(run_directory)
        self.run_directory = Path(run_directory)
        self.sequence = 0
        self.next_telemetry_s = 0.0
        self.provenance_written = False

    def step(self, state: PayloadState) -> tuple[tuple[float, float, float], list[str], EnvironmentSample]:
        self.flight_status = self.flight_source.poll(round(state.time_s * 1000), state)
        env = self.environment.sample(
            self.config.latitude, self.config.longitude, self.config.month,
            max(0.0, state.altitude_m), state.time_s, self.config.atmosphere_mode,
        )
        velocity = state.velocity_ground_mps
        relative = tuple(velocity[i] - env.wind_vector[i] for i in range(3))
        speed = math.sqrt(sum(component * component for component in relative))
        factor = -0.5 * env.air_density_kgm3 * self.config.drag_coefficient * self.config.reference_area_m2 * speed
        drag_enu = tuple(factor * component for component in relative)
        # WorldInfo.coordinateSystem="ENU": x=east, y=north, z=up.
        drag_webots = drag_enu

        if self.config.flight_controller.physics_engine.mode == "ARDUPILOT_SITL_JSON":
            try:
                self.last_actuator = self.physics_engine.step(PhysicsInput.from_webots(state, env))
                self.last_wrench = self.actuator_model.calculate(self.last_actuator)
            except (ValueError, OSError) as exc:
                self.last_actuator = ActuatorCommand((), state.time_s, False)
                self.last_wrench = ActuatorWrench()
                self.physics_engine.status.physics_connected = False
                self.physics_engine.status.last_error = str(exc)
        self.logger.write_actuator(state.time_s, self.last_actuator, self.last_wrench)

        if state.time_s + 1e-9 >= self.next_telemetry_s:
            self.sequence += 1
            sensor = self.sensors.read(
                env, state, self.config.failures,
                schema_version=self.config.telemetry_schema_version,
            )
            row = self.encoder.encode(
                self.sequence, round(state.time_s * 1000), sensor, self.flight_status
            )
            self.logger.write(row, state, env, relative, self.flight_status)
            if not self.provenance_written:
                self.logger.write_provenance({
                    **env.provenance,
                    "ardupilot_interface": {
                        "repository": "https://github.com/ArduPilot/ardupilot",
                        "verified_master_commit_2026-09-15": "bf080274049960688db099cd6798b6632184c080",
                        "backend": "libraries/SITL/SIM_JSON.*",
                        "json_listen_port": self.config.flight_controller.physics_engine.port,
                        "mavlink_endpoint": self.config.flight_controller.telemetry.endpoint,
                        "lockstep": self.config.flight_controller.physics_engine.lockstep,
                        "vehicle_profile": self.config.vehicle.profile_label,
                    },
                })
                self.provenance_written = True
            distance = math.sqrt(sum(value * value for value in state.position_m))
            self.radio.send(row, state.time_s, distance)
            self.next_telemetry_s += self.config.telemetry_interval_s
            self._write_status(state, env, sensor, relative)
        return drag_webots, self.radio.receive_ready(state.time_s), env

    def _write_status(self, state, env, sensor, relative) -> None:
        status = {
            "time_s": state.time_s, "mode": env.mode, "provenance": env.provenance,
            "true": {
                "altitude_m": state.altitude_m, "temperature_C": env.temperature_C,
                "pressure_hPa": env.pressure_hPa,
                "humidity_pct": env.relative_humidity_pct, "pm25_ugm3": env.pm25_ugm3,
                "pm10_ugm3": env.pm10_ugm3, "wind_enu_mps": env.wind_vector,
                "ground_velocity_enu_mps": state.velocity_ground_mps,
                "relative_air_velocity_enu_mps": relative,
            },
            "sensor": sensor.__dict__,
            "flight": None if self.flight_status is None else self.flight_status.__dict__,
            "ardupilot": {
                **self.physics_engine.status.to_dict(),
                "mavlink_connected": bool(self.flight_status and self.flight_status.connected),
                "last_input": {"timestamp_s": self.physics_engine.status.last_physics_timestamp_s},
                "last_actuator": {
                    "raw": self.last_actuator.raw_pwm,
                    "normalized": self.last_actuator.channels,
                    "valid": self.last_actuator.valid,
                    "force_body_flu_n": self.last_wrench.force_body_flu_n,
                    "torque_body_flu_nm": self.last_wrench.torque_body_flu_nm,
                },
            },
            "radio": self.radio.status,
        }
        (self.run_directory / "status.json").write_text(
            json.dumps(status, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    def close(self) -> dict[str, object]:
        self.flight_source.close()
        self.physics_engine.close()
        self.logger.close()
        return create_error_report(self.run_directory)
