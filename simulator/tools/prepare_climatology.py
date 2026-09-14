"""검증된 ERA5/CAMS NetCDF를 작은 오프라인 NPZ profile로 변환합니다.

이 도구는 Copernicus 다운로드 API를 흉내 내지 않습니다. 사용자가 공식 포털에서
받은 파일과 그 파일에서 확인한 변수명을 명시적으로 입력해야 합니다.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import xarray as xr

G0 = 9.80665
R_AIR = 287.05287


def _hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _units(variable: xr.DataArray) -> str:
    return str(variable.attrs.get("units", "")).strip().lower().replace("³", "3")


def _require_units(variable: xr.DataArray, accepted: set[str], label: str) -> None:
    actual = _units(variable)
    if actual not in accepted:
        raise ValueError(f"{label} units={actual!r}; 허용 단위={sorted(accepted)}")


def _coord_name(dataset: xr.Dataset, requested: str) -> str:
    if requested not in dataset.coords and requested not in dataset.dims:
        raise ValueError(f"coordinate {requested!r}가 파일에 없습니다")
    return requested


def _normalise_longitude(value: float, coordinate: xr.DataArray) -> float:
    values = np.asarray(coordinate.values, dtype=float)
    if values.min() >= 0.0 and value < 0.0:
        return value % 360.0
    return value


def _select_point_month(dataset: xr.Dataset, args: argparse.Namespace) -> xr.Dataset:
    lat = _coord_name(dataset, args.lat_coord)
    lon = _coord_name(dataset, args.lon_coord)
    selected = dataset.sel(
        {lat: args.latitude, lon: _normalise_longitude(args.longitude, dataset[lon])},
        method="nearest",
    )
    if args.time_coord in selected.coords:
        time = selected[args.time_coord]
        month_mask = time.dt.month == args.month
        if int(month_mask.sum()) == 0:
            raise ValueError(f"month={args.month}인 time sample이 없습니다")
        selected = selected.sel({args.time_coord: month_mask}).mean(args.time_coord)
    return selected


def _profile(variable: xr.DataArray, level: str, label: str) -> np.ndarray:
    squeezed = variable.squeeze(drop=True)
    if set(squeezed.dims) != {level}:
        raise ValueError(f"{label}은 {level!r}만 남는 1-D profile이어야 합니다: {squeezed.dims}")
    return np.asarray(squeezed.transpose(level).values, dtype=float)


def prepare_era5(args: argparse.Namespace) -> None:
    source = Path(args.input).resolve()
    with xr.open_dataset(source) as dataset:
        required = [args.temperature_var, args.rh_var, args.geopotential_var,
                    args.u_var, args.v_var, args.level_coord]
        missing = [name for name in required if name not in dataset]
        if missing:
            raise ValueError(f"ERA5 변수/좌표 누락: {missing}")
        selected = _select_point_month(dataset, args)
        level = args.level_coord
        _require_units(selected[args.temperature_var], {"k", "kelvin"}, "temperature")
        _require_units(selected[args.rh_var], {"%", "percent", "percentage"}, "relative humidity")
        _require_units(selected[args.geopotential_var], {"m**2 s**-2", "m2 s-2", "m^2 s^-2"}, "geopotential")
        _require_units(selected[args.u_var], {"m s**-1", "m s-1", "m/s"}, "u wind")
        _require_units(selected[args.v_var], {"m s**-1", "m s-1", "m/s"}, "v wind")
        _require_units(selected[level], {"hpa", "millibars", "millibar", "mb"}, "pressure level")

        temperature = _profile(selected[args.temperature_var], level, "temperature")
        rh = _profile(selected[args.rh_var], level, "relative humidity")
        altitude = _profile(selected[args.geopotential_var], level, "geopotential") / G0
        east = _profile(selected[args.u_var], level, "u wind")
        north = _profile(selected[args.v_var], level, "v wind")
        pressure = np.asarray(selected[level].values, dtype=float) * 100.0
        if pressure.ndim != 1 or len(pressure) != len(altitude):
            raise ValueError("pressure level과 geopotential profile 길이가 다릅니다")
        if not all(np.all(np.isfinite(array)) for array in (temperature, rh, altitude, east, north, pressure)):
            raise ValueError("ERA5 profile에 NaN/Inf가 있습니다")
        if np.any((rh < 0.0) | (rh > 100.0)) or np.any(temperature <= 0.0):
            raise ValueError("ERA5 temperature/RH의 물리 범위가 잘못되었습니다")
        order = np.argsort(altitude)
        altitude, temperature, rh, east, north, pressure = [
            array[order] for array in (altitude, temperature, rh, east, north, pressure)
        ]
        if np.any(np.diff(altitude) <= 0.0) or np.any(np.diff(pressure) >= 0.0):
            raise ValueError("고도는 증가하고 압력은 감소해야 합니다")
        density = pressure / (R_AIR * temperature)
        actual_lat = float(selected[args.lat_coord])
        actual_lon = float(selected[args.lon_coord])

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(
        output, altitude_m=altitude, temperature_K=temperature,
        pressure_Pa=pressure, density_kgm3=density,
        relative_humidity_pct=rh, wind_east_mps=east,
        wind_north_mps=north, wind_vertical_mps=np.zeros_like(east),
    )
    metadata = {
        "dataset": "ERA5 monthly averaged data on pressure levels",
        "provider": "Copernicus Climate Change Service / ECMWF",
        "dataset_url": "https://cds.climate.copernicus.eu/datasets/reanalysis-era5-pressure-levels-monthly-means",
        "input_sha256": _hash(source), "input_file": source.name,
        "latitude": actual_lat, "longitude": actual_lon, "month": args.month,
        "requested_latitude": args.latitude, "requested_longitude": args.longitude,
        "averaging": "mean of every input time sample matching the selected calendar month",
        "height_conversion": "geopotential / 9.80665 = geopotential height (m)",
        "vertical_wind_source": "UNAVAILABLE; stored as 0 only because ERA5 pressure-level product has no vertical m/s field",
        "variables": {"temperature": args.temperature_var, "relative_humidity": args.rh_var,
                      "geopotential": args.geopotential_var, "u_wind": args.u_var,
                      "v_wind": args.v_var, "pressure_level": args.level_coord},
        "temperature_source": "ERA5 monthly means", "humidity_source": "ERA5 monthly means",
        "pressure_source": "ERA5 pressure levels", "density_source": "p/(R_d*T)",
        "wind_source": "ERA5 monthly means; horizontal only",
    }
    output.with_suffix(".json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")


def prepare_cams(args: argparse.Namespace) -> None:
    source = Path(args.input).resolve()
    with xr.open_dataset(source) as dataset:
        required = [args.pm25_var, args.pm10_var]
        missing = [name for name in required if name not in dataset]
        if missing:
            raise ValueError(f"CAMS 변수 누락: {missing}")
        selected = _select_point_month(dataset, args)
        _require_units(selected[args.pm25_var], {"kg m**-3", "kg m-3", "kg/m3", "kg m^-3"}, "PM2.5")
        _require_units(selected[args.pm10_var], {"kg m**-3", "kg m-3", "kg/m3", "kg m^-3"}, "PM10")
        pm25 = np.asarray(selected[args.pm25_var].squeeze(drop=True).values, dtype=float)
        pm10 = np.asarray(selected[args.pm10_var].squeeze(drop=True).values, dtype=float)
        if args.altitude_var:
            if args.altitude_var not in selected:
                raise ValueError(f"altitude variable {args.altitude_var!r}가 파일에 없습니다")
            altitude = np.asarray(selected[args.altitude_var].squeeze(drop=True).values, dtype=float)
            _require_units(selected[args.altitude_var], {"m", "metres", "meters"}, "altitude")
        else:
            if pm25.ndim != 0 or pm10.ndim != 0:
                raise ValueError("다차원 CAMS 값에는 --altitude-var가 필요합니다")
            altitude, pm25, pm10 = np.array([0.0]), np.array([float(pm25)]), np.array([float(pm10)])
        if altitude.ndim != 1 or pm25.shape != altitude.shape or pm10.shape != altitude.shape:
            raise ValueError("CAMS altitude/PM profile shape가 다릅니다")
        if not all(np.all(np.isfinite(array)) for array in (altitude, pm25, pm10)):
            raise ValueError("CAMS profile에 NaN/Inf가 있습니다")
        if np.any(pm25 < 0.0) or np.any(pm10 < 0.0):
            raise ValueError("CAMS PM 농도는 음수일 수 없습니다")
        order = np.argsort(altitude)
        altitude, pm25, pm10 = altitude[order], pm25[order], pm10[order]
        if len(altitude) > 1 and np.any(np.diff(altitude) <= 0.0):
            raise ValueError("CAMS altitude는 증가해야 합니다")
        actual_lat = float(selected[args.lat_coord])
        actual_lon = float(selected[args.lon_coord])

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(output, altitude_m=altitude, pm25_kgm3=pm25, pm10_kgm3=pm10)
    metadata = {
        "dataset": "CAMS global reanalysis (EAC4) monthly averaged fields",
        "provider": "Copernicus Atmosphere Monitoring Service / ECMWF",
        "dataset_url": "https://ads.atmosphere.copernicus.eu/datasets/cams-global-reanalysis-eac4-monthly",
        "input_sha256": _hash(source), "input_file": source.name,
        "latitude": actual_lat, "longitude": actual_lon, "month": args.month,
        "requested_latitude": args.latitude, "requested_longitude": args.longitude,
        "averaging": "mean of every input time sample matching the selected calendar month",
        "variables": {"pm25": args.pm25_var, "pm10": args.pm10_var,
                      "altitude": args.altitude_var or "surface-only (0 m marker)"},
        "source_units": "kg m-3", "runtime_conversion": "multiply by 1e9 to µg m-3",
        "pm25_source": "CAMS EAC4", "pm10_source": "CAMS EAC4",
        "pm1_source": "UNAVAILABLE", "pm4_source": "UNAVAILABLE",
    }
    output.with_suffix(".json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("input", type=Path)
    common.add_argument("output", type=Path)
    common.add_argument("--latitude", type=float, required=True)
    common.add_argument("--longitude", type=float, required=True)
    common.add_argument("--month", type=int, choices=range(1, 13), required=True)
    common.add_argument("--lat-coord", default="latitude")
    common.add_argument("--lon-coord", default="longitude")
    common.add_argument("--time-coord", default="valid_time")
    commands = result.add_subparsers(dest="kind", required=True)
    era5 = commands.add_parser("era5", parents=[common])
    era5.add_argument("--level-coord", default="pressure_level")
    era5.add_argument("--temperature-var", default="t")
    era5.add_argument("--rh-var", default="r")
    era5.add_argument("--geopotential-var", default="z")
    era5.add_argument("--u-var", default="u")
    era5.add_argument("--v-var", default="v")
    era5.set_defaults(function=prepare_era5)
    cams = commands.add_parser("cams", parents=[common])
    cams.add_argument("--pm25-var", required=True,
                      help="실제 파일에서 확인한 PM2.5 variable name")
    cams.add_argument("--pm10-var", required=True,
                      help="실제 파일에서 확인한 PM10 variable name")
    cams.add_argument("--altitude-var",
                      help="직접 제공된 고도 좌표만 지정; 없으면 surface scalar만 허용")
    cams.set_defaults(function=prepare_cams)
    return result


def main() -> None:
    args = parser().parse_args()
    args.function(args)


if __name__ == "__main__":
    main()
