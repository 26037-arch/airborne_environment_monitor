# 설계 분석과 최종 architecture

이 문서는 코드를 작성하기 전에 요구사항을 모듈과 실패 경계로 바꾼 설계 기록입니다.

## 1. 최종 architecture

공중 계측부는 단일 loop와 작은 절차형 모듈로 구성합니다.

| 모듈 | 파일 | 책임 |
|---|---|---|
| Config | `config.h` | 주기, baud, pin, warm-up, mock 설정 |
| Sensors | `sensors.*`, `measurement.h` | BME280/SPS30/GNSS 초기화, GNSS 연속 parsing, snapshot 채우기 |
| Health | `health.*` | 장치별 상태와 마지막 성공 시각 |
| Scheduler | `scheduler.*` | `millis()` 기반 1 Hz 실행, wrap-safe 시간 비교 |
| Telemetry | `telemetry.*` | 18열 CSV를 고정 buffer에 한 번 생성, Serial3 전송 |
| Storage | `storage.*` | 새 8.3 파일명 선택, header/row 기록, 실패 후 유한 재시도 |

PC는 GUI thread와 수신 thread를 `queue.Queue`로 분리합니다. 수신 thread는 serial I/O와 재연결만 맡고, GUI thread가 검증된 measurement를 logger, packet tracker, 화면과 그래프에 보냅니다. MockReceiver도 SerialReceiver와 같은 event를 만들므로 GUI와 logger 코드는 공유됩니다.

Webots 확장에서는 `EarthEnvironment`만 ERA5/CAMS/표준대기를 읽습니다. Webots physics, 센서, GUI는 이 facade가 반환한 `EnvironmentSample`만 사용합니다. `SimulationSource`, `SerialSource`, `CSVReplaySource`는 모두 공용 `TelemetrySource` 인터페이스와 `shared.telemetry_schema` parser로 수렴합니다.

```text
offline ERA5/CAMS profile ─┐
COESA 1976 ────────────────┼─→ EarthEnvironment → Webots physics → true state
explicit user override ────┘                              │
                                                         ▼
                                                sensor simulation
                                                         │
                            ┌────────────────────────────┴──────────┐
                            ▼                                       ▼
                        truth.csv                     Arduino 18-column telemetry
                                                                    │
                           Webots Emitter → Receiver → SimulationSource
                                                                    │
                                                   existing Ground Station
```

## 2. Arduino와 PC 간 data flow

```text
loop마다 Serial2 bytes → TinyGPSPlus parser
                         │
1 Hz scheduler ──────────┼─→ 한 시점의 Measurement snapshot
BME280 read ─────────────┤
SPS30 read/warm-up ──────┘
                         │
                         ▼
             fixed char[256] CSV row 1회 생성
                    ┌────┴────┐
                    ▼         ▼
             microSD append   Serial3 → XBee transparent radio
                                         │
                                         ▼
Windows COM → 수신 thread → 18열/자료형 검증 → GUI queue
                                               ├─ PC CSV + flush
                                               ├─ sequence loss tracker
                                               ├─ current values/status
                                               └─ 최근 N점 graph
```

SD와 XBee용 데이터를 따로 계산하지 않습니다. `formatCsvRow()`가 만든 같은 `csvRow` 주소를 `appendStorageRow()`와 `sendTelemetryRow()`에 차례로 넘깁니다.

## 3. 선택한 라이브러리

| 기능 | 선택 | 사용 API |
|---|---|---|
| BME280 | Adafruit BME280 + Unified Sensor | `begin(addr, &Wire)`, `readTemperature`, `readHumidity`, `readPressure` |
| SPS30 | Sensirion UART SPS30 + Sensirion Core | `begin(Stream&)`, `startMeasurement(FLOAT)`, `readMeasurementValuesFloat` |
| GNSS | TinyGPSPlus | `encode`, `location.lat/lng`, `altitude.meters`, `speed.mps`, `course.deg`, `age` |
| SD | Arduino SD/SPI | `begin`, `exists`, `open(FILE_WRITE)`, `write`, `flush`, `close` |
| XBee | 별도 library 없음 | Transparent Mode의 `Serial3.println` |
| PC serial | pyserial | port enumeration, `Serial.readline`, exception handling |
| GUI/graph | Tkinter + matplotlib | Python 기본 GUI + 최근 point plot |

## 4. 예상 충돌 요소

- **SPS30 library 이름 충돌:** 구형 `sps30.h` API와 새 `SensirionUartSps30.h` API는 호환되지 않습니다. README의 정확한 Library Manager 항목을 설치해야 합니다.
- **UART 교차 배선:** 장치 TX는 Mega RX, 장치 RX는 Mega TX로 연결합니다. Serial1/2/3 핀은 서로 다르므로 software 충돌은 없습니다.
- **baud 불일치:** GNSS 기본 baud는 제품마다 다르고 XBee UART baud도 별도 설정입니다. 양쪽을 `config.h`와 맞춰야 합니다.
- **SPI CS:** Mega의 hardware SS인 D53을 OUTPUT으로 유지합니다. SD의 실제 CS는 기본 D4입니다. 향후 SPI 장치를 추가하면 모든 비활성 CS를 HIGH로 관리해야 합니다.
- **I2C 주소:** BME280은 0x76, 0x77을 차례로 확인합니다. 같은 주소의 다른 장치를 추가하면 충돌합니다.
- **USB 자동 탐색:** Arduino USB와 지상 XBee가 동시에 같은 schema를 내보내면 둘 다 정상 후보입니다. 확실한 운용은 `--port COM번호`로 고정합니다.

## 5. 메모리와 통신 위험

- Mega 2560 SRAM은 8 KB이므로 Arduino `String`, JSON, 동적 배열을 사용하지 않습니다. CSV는 256-byte 고정 buffer입니다.
- AVR에서 `double`은 일반적으로 32-bit입니다. 위·경도 6자리 출력은 가능하지만 과학용 고정밀 GNSS 처리에는 별도 정밀도 검토가 필요합니다.
- 약 150~190 bytes/row를 115200 baud로 1 Hz 전송하는 부하는 낮습니다. 다만 XBee RF 환경이 나쁘면 seq gap이 생기며, 지상국이 이를 손실로 표시합니다.
- SD는 데이터 보존을 우선해 매 행 open/write/flush/close합니다. 수십 ms의 bounded latency가 생길 수 있지만 1초 주기에는 여유가 있습니다. 불량 카드가 지나치게 오래 block하는 것은 SD library/하드웨어 수준의 한계입니다.
- SPS30 명령도 library 내부 timeout 동안 잠시 block할 수 있으나 무한 retry는 없습니다. 실패 후 10초 간격으로 한 번씩 다시 시작합니다.
- GNSS RX buffer overflow를 줄이기 위해 `pollGnss()`가 loop의 첫 부분에서 매번 Serial2를 비웁니다.
- `millis()`와 seq는 uint32입니다. scheduler는 subtraction 방식이라 시간 wrap에 안전하고, PC는 seq 감소/wrap을 새 session 기준점으로 처리합니다.

## 6. 파일 구조

최종 구조는 README의 파일 안내와 같습니다. 요구된 이름을 유지하면서 공통 측정 구조체 `measurement.h`, 엄격한 PC parser/sequence tracker `data_model.py`, mock 생성기 `mock_data.py`, 설계 기록인 이 파일을 추가했습니다.
