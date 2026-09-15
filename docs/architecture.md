# Architecture

## Responsibility boundary

| component | responsibility |
|---|---|
| Mega 2560 | non-blocking GNSS drain, independent sensor sampling, fixed-buffer v3 formatting, SD append, HC-12 transmit |
| Uno | transparent HC-12 UART to USB Serial bridge only |
| PC | v1/v2/v3 parsing, durable logging, charts, comparisons, track/loss analysis and future fusion |
| Simulator | Earth truth, sensor measurement, failure injection, virtual radio and provenance |

The Mega uses one `Measurement` snapshot per 1 Hz cycle. `formatCsvRowV3()` creates the row once; SD and HC-12 consume the same fixed char buffer. Neither output re-reads a sensor. SD and radio failures are independent.

```text
every loop: drain GNSS bytes → retry failed subsystems → service SD
                                      │
millis() due: read each sensor → Measurement → fixed CSV buffer
                                            ├→ SD
                                            └→ HC-12
```

No Arduino `String`, JSON, dynamic container, or SoftwareSerial is used on the airborne Mega. The Uno alone uses SoftwareSerial so its hardware Serial remains available for USB.

## Simulator truth and measurement

`EarthEnvironment` remains the only environment truth facade. AHT20 and BMP280 models sample temperature/humidity and pressure from that truth. BMP altitude uses the configurable `sea_level_pressure_hpa`; it is not guaranteed to equal geometric or GNSS altitude.

The MPU6050 model uses Webots linear-velocity differences and angular velocity. World vectors are transformed into payload axes. If those states are unavailable, values are `NA` with `imu_ok=0`; they are not invented. RTC uses `simulation_epoch_unix + simulation time`. CAMS particulate truth remains available to analysis but is intentionally absent from v3 telemetry.

Set `telemetry_schema_version` to 1 or 2 only for a legacy simulator workflow. Version 2 is where the existing optional Flight Controller adapter composes its fields. The default is v3 and Flight Controller mode `OFF`.
