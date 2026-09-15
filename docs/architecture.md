# Architecture

## SITL closed loop

```text
EarthEnvironment -> wind/air --------------------------+
                                                        v
Webots ENU rigid-body truth -> ENU/NED+FLU/FRD adapter -> ArduPilot SITL JSON
       ^                                                   |
       |                                                   | binary PWM
       +---- body force/torque <- virtual actuator model <-+

Webots truth -> Payload SensorSuite -> telemetry v3 -> Ground Station
ArduPilot estimate -----------------> MAVLink source -> status/logging
```

`FlightPhysicsEngine` is independent from the existing read-only
`FlightTelemetrySource`. `ArduPilotSitlEngine` listens on UDP 9002 for the
official 16/32-channel binary servo packet and replies to its sender with JSON.
The timestamp is monotonic Webots simulation time; position, velocity and wind
are NED. Quaternion is scalar-first body-FRD to NED. Gyro is body FRD.
`accel_body` is specific force: world kinematic acceleration minus gravity,
rotated into FRD; therefore a stationary level vehicle reads `(0,0,-g)` and a
freely falling one reads zero.

The official schema's mandatory state is timestamp + gyro(3) + accel(3) +
velocity(3) + quaternion(4); position(3) is sent for local position support and
wind(3) is optional, for 20 total scalar values (19 excluding timestamp).
The current source marks `position` optional although the accompanying example
README lists it among required fields; this adapter always sends it, satisfying
both interpretations.

On timeout, malformed data, non-finite state, quaternion failure, SITL exit, or
Webots time reset, the command is invalidated and the virtual wrench becomes
zero. Network code does not know about serial or hardware actuators.

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
