from __future__ import annotations

import csv
import json
import math
from pathlib import Path

from shared.data_types import EnvironmentSample, PayloadState, SensorReadings
from shared.telemetry_schema import CSV_HEADER_V1, parse_csv_line


TRUTH_HEADER = (
    "time_ms", "true_x_m", "true_y_m", "true_z_m", "true_altitude_m",
    "true_velocity_east_mps", "true_velocity_north_mps", "true_velocity_vertical_mps",
    "true_temperature_C", "true_pressure_hPa", "true_humidity_pct",
    "true_pm1_ugm3", "true_pm25_ugm3", "true_pm10_ugm3",
    "true_wind_east_mps", "true_wind_north_mps", "true_wind_vertical_mps",
    "relative_air_east_mps", "relative_air_north_mps", "relative_air_vertical_mps",
)


class RunLogger:
    def __init__(self, directory: Path) -> None:
        self.directory = Path(directory)
        self.directory.mkdir(parents=True, exist_ok=True)
        self.telemetry_path = self.directory / "telemetry.csv"
        self.truth_path = self.directory / "truth.csv"
        self.telemetry_file = self.telemetry_path.open("w", encoding="utf-8", newline="")
        self.truth_file = self.truth_path.open("w", encoding="utf-8", newline="")
        self.telemetry_header: tuple[str, ...] = CSV_HEADER_V1
        self.telemetry_has_rows = False
        csv.writer(self.telemetry_file, lineterminator="\n").writerow(CSV_HEADER_V1)
        self.truth_writer = csv.writer(self.truth_file, lineterminator="\n")
        self.truth_writer.writerow(TRUTH_HEADER)

    @staticmethod
    def _value(value):
        return "NA" if value is None else value

    def write(self, row: str, state: PayloadState, environment: EnvironmentSample,
              relative_air: tuple[float, float, float]) -> None:
        measurement = parse_csv_line(row)
        if not self.telemetry_has_rows and self.telemetry_header != measurement.fieldnames:
            self.telemetry_header = measurement.fieldnames
            self.telemetry_file.seek(0)
            self.telemetry_file.truncate()
            csv.writer(self.telemetry_file, lineterminator="\n").writerow(
                self.telemetry_header
            )
        elif self.telemetry_header != measurement.fieldnames:
            raise ValueError("simulation 도중 telemetry schema version이 변경되었습니다")
        self.telemetry_file.write(row + "\n")
        self.telemetry_has_rows = True
        east, north, vertical = state.velocity_ground_mps
        self.truth_writer.writerow((
            round(state.time_s * 1000), *state.position_m, state.altitude_m,
            east, north, vertical, environment.temperature_C,
            environment.pressure_hPa, self._value(environment.relative_humidity_pct),
            self._value(environment.pm1_ugm3), self._value(environment.pm25_ugm3),
            self._value(environment.pm10_ugm3), environment.wind_east_mps,
            environment.wind_north_mps, environment.wind_vertical_mps, *relative_air,
        ))
        self.telemetry_file.flush()
        self.truth_file.flush()

    def write_provenance(self, provenance: dict[str, object]) -> None:
        (self.directory / "provenance.json").write_text(
            json.dumps(provenance, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    def close(self) -> None:
        self.telemetry_file.close()
        self.truth_file.close()


def create_error_report(run_directory: Path) -> dict[str, object]:
    run_directory = Path(run_directory)
    with (run_directory / "truth.csv").open(encoding="utf-8", newline="") as file:
        truth = {int(row["time_ms"]): row for row in csv.DictReader(file)}
    with (run_directory / "telemetry.csv").open(encoding="utf-8", newline="") as file:
        telemetry = list(csv.DictReader(file))
    mapping = {
        "temperature_C": "true_temperature_C",
        "pressure_hPa": "true_pressure_hPa",
        "humidity_pct": "true_humidity_pct",
        "pm1_ugm3": "true_pm1_ugm3",
        "pm25_ugm3": "true_pm25_ugm3",
        "pm10_ugm3": "true_pm10_ugm3",
        "gps_altitude_m": "true_altitude_m",
        "barometric_altitude_m": "true_altitude_m",
    }
    report: dict[str, object] = {"sample_count": len(telemetry), "metrics": {}}
    for sensor_name, truth_name in mapping.items():
        errors: list[float] = []
        for row in telemetry:
            reference = truth.get(int(row["time_ms"]))
            if (reference is None or sensor_name not in row or
                    row[sensor_name] in {"NA", ""} or
                    reference[truth_name] in {"NA", ""}):
                continue
            errors.append(float(row[sensor_name]) - float(reference[truth_name]))
        count = len(errors)
        report["metrics"][sensor_name] = {
            "bias": sum(errors) / count if count else None,
            "mae": sum(abs(error) for error in errors) / count if count else None,
            "rmse": math.sqrt(sum(error * error for error in errors) / count) if count else None,
            "maximum_absolute_error": max(map(abs, errors)) if count else None,
            "valid_data_fraction": count / len(telemetry) if telemetry else 0.0,
        }
    (run_directory / "error_report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return report
