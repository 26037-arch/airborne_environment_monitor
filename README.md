# Airborne Environment Monitor

## ArduPilot closed-loop simulator

The simulator does not reimplement a flight controller. It executes ArduPilot
SITL as the actual flight-control calculation engine. Webots provides rigid-body
physics and environmental forces. Webots state is sent to ArduPilot through its
SITL JSON physics interface, and ArduPilot actuator outputs are applied only to
virtual Webots actuators. No SITL actuator output is forwarded to physical
motors, ESCs or servos.

시뮬레이터는 비행제어 알고리즘을 Python으로 다시 구현하지 않습니다. 공식
ArduPilot SITL이 EKF·항법·제어·mixer를 실행하고, Webots가 ENU 강체 물리와
환경력을 계산합니다. SITL PWM 출력은 Webots 내부의 가상 actuator에만 적용되며
Arduino, HC-12, 실제 모터·ESC·servo·arming 경로에는 연결되지 않습니다.

기본 설정은 계속 `physics_engine.mode = OFF`이므로 ArduPilot이 없어도 기존
payload-only simulation이 동작합니다. opt-in 예제와 점검 명령은
[`simulator/README.md`](simulator/README.md)에 있습니다.
상세한 SITL/WSL 실행법과 안전 경계는 [`docs/ardupilot_sitl.md`](docs/ardupilot_sitl.md)에 있습니다.

Arduino Mega 2560이 AHT20, BMP280, MPU6050, NEO-M8N, RTC를 읽어 같은 schema v3 CSV snapshot을 microSD에 우선 기록하고 HC-12로 전송합니다. 지상의 Arduino Uno는 HC-12 수신 바이트를 USB Serial로 그대로 넘기며, PC가 검증·로깅·그래프·packet loss 분석을 담당합니다.

이 프로젝트는 환경 측정 payload입니다. motor PWM, ESC/servo command, arming, 자동 이륙, 자세 안정화 또는 자율비행을 구현하지 않습니다. 기존 PX4/ArduPilot adapter 파일은 future/optional interface로 보존되지만 기본 Mega runtime과 simulator config에서는 사용하지 않습니다.

## Hardware architecture

```text
AHT20 ─┐
BMP280 ├─ I2C ─ Arduino Mega 2560 ─ SPI ─ microSD (primary record)
MPU6050┤                │
RTC ───┘                ├─ Serial1 ← NEO-M8N
                        ├─ Serial2   reserved/future FC
                        └─ Serial3 ↔ HC-12
                                      )) 433 MHz ((
                                  HC-12 ↔ Arduino Uno ↔ USB ↔ PC
```

보유 Arduino Uno는 폐기하지 않고 지상 수신기로 재사용합니다. 추가 구매의 필수 최소치는 Mega 2560 compatible board 1개와 HC-12 1개입니다. Logic-level shifter는 실제 breakout의 허용 전압을 확인한 뒤 필요한 경우에만 추가합니다.

보유 장비 중 NEO-M8N은 1개만 공중 payload에 사용하고 두 번째 모듈은 future `spare`로 기록합니다. AHT20+BMP280 복합 모듈, MPU6050, microSD, RTC, HC-12와 3.3 V/5 V DC-DC converter는 실제 board 표기와 전기 사양을 확인한 뒤 사용합니다.

## Quick start

하드웨어 없이 v3 Ground Station을 확인합니다.

```powershell
cd ground_station
python -m pip install -r requirements.txt
python main.py --mock
```

Mega IDE libraries:

- Adafruit AHTX0
- Adafruit BMP280 Library
- Adafruit MPU6050
- Adafruit Unified Sensor
- TinyGPSPlus
- RTClib: RTC 칩이 DS3231-compatible로 실제 확인된 경우에만
- Arduino SD/SPI

`arduino/airborne_monitor/config.h`에서 `SEA_LEVEL_PRESSURE_HPA`, SD CS, baud, MPU6050 offsets와 RTC driver를 설정합니다. `DM941` 표기만으로 RTC IC를 알 수 없으므로 기본값은 `RTC_DRIVER_DISABLED`입니다. 칩·주소를 확인한 뒤 DS3231-compatible일 때만 driver를 활성화하십시오.

두 HC-12의 UART 설정은 모두 `SERIAL_BAUD_HC12=9600`과 일치해야 합니다. Main runtime에서 HC-12 AT command mode를 사용하지 않습니다.

## Run and verify

1. 전원을 끄고 [배선/전원 주의사항](docs/wiring.md)을 확인합니다.
2. Mega sketch를 업로드하고 Serial Monitor 115200 baud에서 I2C probe와 health summary를 봅니다.
3. Uno에 `arduino/ground_hc12_bridge/ground_hc12_bridge.ino`를 업로드합니다.
4. PC에서 `python ground_station/main.py --port COM5`처럼 Uno 포트를 엽니다.
5. SD의 `FLIGHTnn.CSV`와 PC `ground_station/data/flight_*.csv`를 비교합니다.

SD가 실패해도 HC-12는 계속 전송하고, HC-12가 끊겨도 SD 기록은 계속 시도합니다. 한 센서 실패는 다른 센서·SD·radio를 중단하지 않습니다. `gps_speed_mps`는 풍속이 아니라 **GNSS ground speed**입니다.

## Telemetry and compatibility

Schema v3는 PM 필드가 없습니다. 보유 장비에 particulate sensor가 없기 때문입니다. 과거 v1/v2 parser, replay, logger와 legacy simulator encoder는 그대로 유지됩니다. 자세한 열과 `NA` 규칙은 [data_format.md](docs/data_format.md)를 참고하십시오.

Simulator는 기존 EarthEnvironment, ERA5/CAMS/COESA, wind, Webots physics와 provenance를 유지하면서 v3 AHT20/BMP280/MPU6050/NEO-M8N/RTC measurement를 생성합니다. CAMS PM은 truth에 남지만 v3 hardware telemetry에 복제하지 않습니다.

## Tests

```powershell
python -m unittest discover -v
python -m unittest discover -s ground_station/tests -v
```

Arduino CLI와 필요한 core/library가 설치된 경우:

```powershell
arduino-cli compile --fqbn arduino:avr:mega arduino/airborne_monitor
arduino-cli compile --fqbn arduino:avr:uno arduino/ground_hc12_bridge
```

상세 설계는 [architecture.md](docs/architecture.md), 변경 경계는 [architecture_analysis.md](docs/architecture_analysis.md), 검증 범위는 [validation.md](docs/validation.md)를 참고하십시오.
