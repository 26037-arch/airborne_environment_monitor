# Telemetry CSV formats

One transparent-radio frame is one ASCII CSV row followed by `\n`. The parser selects v1, v2, or v3 by exact column count. Empty/invalid numeric values use `NA`; health flags accept only `0` or `1`.

## Schema v3 (current hardware)

```text
seq,time_ms,temperature_C,humidity_pct,pressure_hPa,barometric_altitude_m,latitude,longitude,gps_altitude_m,gps_speed_mps,gps_course_deg,accel_x_mps2,accel_y_mps2,accel_z_mps2,gyro_x_dps,gyro_y_dps,gyro_z_dps,rtc_unix_time,env_ok,imu_ok,gps_ok,rtc_ok,sd_ok
```

| group | fields | unit/meaning |
|---|---|---|
| sequence | `seq`, `time_ms` | uint32; Mega boot-relative milliseconds |
| environment | temperature, humidity, pressure, barometric altitude | °C, %RH, hPa, m |
| GNSS | latitude, longitude, GPS altitude, speed, course | degree, m, m/s ground speed, degree |
| IMU | accel x/y/z, gyro x/y/z | m/s², degree/s in sensor axes |
| RTC | `rtc_unix_time` | uint32 UTC Unix seconds; `NA` until trustworthy |
| health | ENV, IMU, GPS, RTC, SD | only 0 or 1 |

`env_ok=1` requires all four environment fields, `imu_ok=1` all six IMU fields, `gps_ok=1` all five GNSS fields, and `rtc_ok=1` a timestamp. A failed subsystem may be `NA` while other groups continue. `sd_ok` describes the known state immediately before that row's write; a failure during the write appears on the following transmitted row.

BMP280 altitude depends on `SEA_LEVEL_PRESSURE_HPA` and weather, so it is not guaranteed to match true or GNSS altitude.

## Compatibility

- v1: original 18-column BME280/SPS30/GNSS/SD format
- v2: v1 plus 11 optional Flight Controller fields
- v3: current 23-column physical-payload format; no PM fields

Old v1/v2 CSV replay and logging remain supported. Missing fields in the GUI display as `N/A`.
