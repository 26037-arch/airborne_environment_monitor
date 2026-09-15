# Validation record

Validation date: 2026-09-15

## Automated results

```text
python -m unittest discover -v
Ran 27 tests - OK

python -m unittest discover -s ground_station/tests -v
Ran 16 tests - OK

python -m compileall -q shared ground_station simulator
OK
```

Coverage includes v1 parser regression, v2 parser regression, v3 complete/missing GPS/missing RTC/missing IMU/missing environment, non-finite rejection, invalid flag rejection, v1/v2/v3 logger and replay selection, sequence loss, simulator-to-v3 parser, legacy v2 Flight adapter, and sensor failure isolation.

Headless Ground Station checks also passed:

- v3 mock generated and logged three valid changing rows
- `examples/example_flight_v3.csv` replay parsed and logged two rows

The environment core tests for COESA, ERA5/CAMS interpolation/conversion/fallback, deterministic wind/radio, provenance/error files and Webots asset declarations continue to pass.

## Arduino compile status

`arduino-cli` is not installed in the validation environment. Therefore neither the Mega firmware nor Uno bridge was compiled here, and no new flash/SRAM figure is claimed. Install the AVR core and documented libraries, then run:

```powershell
arduino-cli compile --fqbn arduino:avr:mega arduino/airborne_monitor
arduino-cli compile --fqbn arduino:avr:uno arduino/ground_hc12_bridge
```

RTC compilation with RTClib must be checked separately after the real RTC IC is identified and `RTC_DRIVER` is enabled.

## Not hardware-verified

- exact `DM941` RTC IC, address, register compatibility and battery state
- AHT20/BMP280/MPU6050 breakout supply and I2C pull-up voltage
- MPU6050 AD0 wiring and actual 0x69 response
- NEO-M8N breakout baud, fix performance and 5 V input tolerance
- HC-12 board supply/UART logic, RF pairing/range and sustained packet loss
- microSD module level shifting, card latency and power-transient behavior
- converter current margin, rail noise and full-system brownout behavior
- actual sensor offsets and `SEA_LEVEL_PRESSURE_HPA` calibration
- Webots GUI run and physical MPU axes against a real mounting orientation
- PX4/ArduPilot/SITL optional adapter end-to-end behavior

These items must not be labelled verified until tested with the exact boards.
