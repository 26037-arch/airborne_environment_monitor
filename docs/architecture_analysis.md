# 기존 architecture 분석과 수정 경계

이 표는 비행 제어 확장 전에 확인한 기존 모듈의 책임과 변경 정책을 기록한다.

| existing module | responsibility | input | output | dependencies | should_modify? |
|---|---|---|---|---|---|
| `arduino/sensors.*` | BME280, SPS30, 직접 GNSS 수집과 독립 failure 처리 | I2C, Serial1, Serial2 | `Measurement` | Adafruit BME280, Sensirion SPS30, TinyGPS++ | 최소: 위치 source 선택 조건만 |
| `arduino/telemetry.*` | 정적 buffer CSV 생성, XBee 전송 | `Measurement` | v1 CSV | Arduino core | 확장 formatter만 추가 |
| `arduino/storage.*` | microSD header/row append와 재시도 | 동일 CSV buffer | `FLIGHTnn.CSV` | SD/SPI | active header 선택만 |
| `arduino/health.*` | 센서/SD 상태 분리 | subsystem 결과 | health flags | 없음 | 아니오 |
| `shared/telemetry_schema.py` | 공용 CSV 검증/encode | CSV text/dict | immutable measurement | Python stdlib | v1 유지 + v2 감지 |
| `shared/telemetry_sources.py` | simulation/serial/replay 입력 통일 | UDP, COM, CSV | parsed measurement | socket, optional pyserial | v2 header 허용 |
| `ground_station/serial_receiver.py` | blocking I/O와 GUI thread 분리 | telemetry source | `queue.Queue` events | pyserial | 아니오 |
| `ground_station/dashboard.py` | 현재값, graph, packet 상태 표시 | queue events | Tk GUI | Tkinter, matplotlib | Flight/System panel 추가 |
| `simulator/environment/*` | ERA5/CAMS/COESA와 wind 계산 | 위치, 월, 고도, override | `EnvironmentSample` | numpy | **아니오** |
| `EarthEnvironment` | 환경 계산의 유일한 facade | environment query | true environment | 기존 environment modules | **아니오** |
| `simulator/sensors/*` | BME/SPS/GNSS 센서 모사와 failure injection | true environment/state | `SensorReadings` | 기존 noise model | 아니오 |
| `SimulationRuntime` | 환경→센서→telemetry orchestration | Webots state | force, CSV, environment | 위 모듈들 | flight source injection만 |
| Webots controllers/world | physics state, drag, radio bridge | config/environment | virtual state/UDP | Webots | adapter 호출만 |

수정 기준은 환경 계산이나 센서 모델을 복제하지 않고, 기존 경계에 작은 composition point를 추가하는 것이다.

## Regression 경계

- v1은 기존 18개 열, 순서, flag 의미를 그대로 유지한다.
- `POSITION_SOURCE_DIRECT_GNSS`가 Arduino 기본값이며 TinyGPS++ 경로를 유지한다.
- `SimulationConfig()` 기본은 flight source `OFF`라 기존 단위 테스트와 v1 output을 유지한다.
- GUI receiver thread와 `queue.Queue` 경계는 바꾸지 않는다.
- BME/SPS/SD/XBee failure는 Flight Controller link 상태와 독립적이다.

