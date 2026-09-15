# ArduPilot SITL JSON closed loop

The default remains payload-only (`physics_engine.mode: OFF`). The simulator
does not reimplement a controller: Webots owns rigid-body physics, official
ArduPilot SITL owns EKF/navigation/control/mixing, `EarthEnvironment` owns
environment truth, and the payload SensorSuite owns environmental measurement.

Start ArduCopter in WSL/Linux using the official JSON model, then launch Webots:

```bash
sim_vehicle.py -v ArduCopter -f quad --model JSON:127.0.0.1 --console --map
```

```powershell
python simulator/tools/check_ardupilot.py --source C:\path\to\ardupilot --binary C:\path\to\arducopter
python simulator/tools/run_webots.py --config simulator/configs/ardupilot_sitl.json
```

The backend listens on UDP 9002 and replies to the source address of SITL's
binary servo packet. MAVLink estimated state is independently read at the
configured endpoint (default `udp:127.0.0.1:14550`). For Windows Webots plus
WSL2 SITL, configure a mutually reachable host when localhost forwarding is not
available. `EXTERNAL` lifecycle is recommended. `MANAGED` is available only
when an explicit executable, working directory, and argument list are supplied;
it uses an argument vector and never a shell command.

The supplied quad profile is **DEMO ONLY - NOT HARDWARE CALIBRATED**. Arm or set
flight modes through external SITL tooling. No command is forwarded to Arduino,
HC-12, PWM, ESC, servo, or any physical arming path.

The current demo retains the repository's spherical Webots body and lets Webots
derive inertia from that geometry. Configure and validate a real airframe shape,
mass/inertia, rotor positions, rotation directions, thrust curve, and yaw torque
coefficient before treating vehicle motion as representative of hardware.

Each run includes `truth.csv`, `telemetry.csv`, `ardupilot_estimate.csv`,
`actuator.csv`, `status.json`, `provenance.json`, and `error_report.json`.

Protocol authority: official ArduPilot `libraries/SITL/SIM_JSON.*` and
`libraries/SITL/examples/JSON/readme.md`, master commit
`bf080274049960688db099cd6798b6632184c080`, verified 2026-09-15. ArduPilot is
an external executable dependency and is not vendored or installed here.
