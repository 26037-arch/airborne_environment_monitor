# Baseline architecture analysis

Baseline: `cd9064b4ecad0813336203480e490fffb716cff1` (remote `main` verified
2026-09-15).

Before this change, `payload_controller.py` read a spherical Webots Robot's ENU
position, velocity, axis-angle, derived world acceleration, and world angular
velocity. `SimulationRuntime` sampled `EarthEnvironment`, calculated aerodynamic
drag, simulated payload sensors, encoded v1/v2/v3 telemetry, polled an optional
read-only MOCK/MAVLink source, and logged truth. Only drag was returned to and
applied by Webots. There was no controller, actuator, force/torque, or closed
loop. Webots is explicitly ENU (`x=east, y=north, z=up`) at 20 ms.

Added files: `flight/frames.py`, `flight/ardupilot_json.py`,
`flight/actuators.py`, opt-in config, dependency/run helpers, and protocol/frame
tests. Modified files: configuration, runtime, Webots controller, logging, docs,
and default config. Dependencies remain unchanged: pymavlink was already the
optional telemetry dependency; ArduPilot SITL and Webots remain external.

Risks are coordinate convention errors, incorrect vehicle geometry, SITL not
being armed/configured, UDP port conflicts, and Webots/SITL rates. These are
contained by centralized transforms, a deliberately labelled demo vehicle,
bounded timeouts, zero-wrench failure behavior, and an OFF-by-default engine.

| module | current responsibility | keep/change/remove | reason |
|---|---|---|---|
| `shared/` | v1/v2 CSV contract and shared data types | change | add v3 auto-detection without changing v1/v2 |
| `arduino/airborne_monitor/` | BME280/SPS30/GNSS/XBee/SD and optional FC | change | use the available AHT20/BMP280/MPU6050/RTC/GNSS/HC-12 hardware |
| `arduino/ground_hc12_bridge/` | absent | new | reuse the Uno as a transparent ground receiver |
| `ground_station/` | parse, log, graph, sequence tracking | change | display v3 Environment/Position/IMU/System values |
| `simulator/environment/` and Webots physics | Earth truth, wind, drag, provenance | keep | this is the validated environment core |
| `simulator/sensors/` and encoder | legacy BME/SPS/GNSS measurement | change | add physical-payload v3 sensor models and failure injection |
| v1/v2 replay and optional FC adapters | compatibility/experimental interfaces | keep | old CSV files and existing workflows must remain readable |

No motor, ESC, servo, arming, launch, takeoff, stabilization, or autonomous-flight behavior is added.
