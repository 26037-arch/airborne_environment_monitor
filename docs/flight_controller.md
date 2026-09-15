# Optional Flight Controller adapter

The current hardware runtime is a sensor payload only. It does not call `flight_link.*`, does not use Serial2, and does not emit schema v2. Serial2 is reserved for a future PX4/ArduPilot telemetry integration.

The existing read-only adapter files remain in the repository for compatibility and experimentation. They decode selected MAVLink state but contain no arming, mode-change, motor PWM, ESC, servo, launch, stabilization or autonomous-flight command.

In the simulator, explicitly set `telemetry_schema_version` to `2` and configure `flight_controller.mode` as `MOCK` or `MAVLINK` to exercise the legacy adapter path. Default configuration is schema v3 with the adapter `OFF`.

Before re-enabling an Arduino integration, update the composition point to the current v3 hardware design, install official MAVLink C headers, confirm Serial2 voltage/baud, and validate on SITL before hardware. HIL injection, vehicle dynamics and actuator closed-loop behavior are not implemented or verified here.
