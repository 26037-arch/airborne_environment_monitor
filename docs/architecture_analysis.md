# Existing-module analysis before the v3 change

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
