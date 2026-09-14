# Arduino Mega 2560 공중 환경 측정 시스템

BME280, SPS30, GNSS 측정값을 Arduino Mega 2560에서 같은 CSV 행으로 만들어 microSD와 XBee Transparent Mode에 동시에 보내고, Windows PC에서 저장·상태 표시·실시간 그래프를 제공하는 교육용 프로젝트입니다. 발사, 점화, 분리, 낙하산, 서보 등 기계 제어 기능은 포함하지 않습니다.

처음 검토할 때는 [architecture.md](docs/architecture.md), 배선할 때는 [wiring.md](docs/wiring.md), 문제가 생기면 [troubleshooting.md](docs/troubleshooting.md)를 보세요.

## 가장 빠른 시작: 하드웨어 없이 확인

Windows에서 Python 3.11을 설치한 뒤 PowerShell 또는 명령 프롬프트를 엽니다.

```powershell
cd ground_station
python -m pip install -r requirements.txt
python main.py --mock
```

또는 `ground_station/run_mock.bat`을 더블 클릭합니다. GUI가 열리고, 1초마다 가상 데이터가 표시되며 `ground_station/data/`에 CSV가 생깁니다.

GUI 없이 5초만 점검하려면 다음을 실행합니다.

```powershell
python main.py --mock --headless --duration 5
```

## 1. 구성품

- Arduino Mega 2560
- BME280 I2C 센서 모듈
- Sensirion SPS30 (UART/SHDLC)
- NMEA를 출력하는 GNSS 모듈
- Mega 호환 microSD SPI 모듈과 FAT16/FAT32 카드
- 공중용 XBee와 PC용 XBee USB 어댑터 한 쌍
- 모듈 사양에 맞는 전원, 배선, 필요 시 논리 레벨 변환기

모듈 이름이 같아도 breakout board의 입력 전압과 논리 레벨은 다를 수 있습니다. 특히 Mega의 UART TX는 5 V 논리입니다. 제조사 회로도와 데이터시트를 확인한 후 연결하십시오. 모든 장치는 GND를 공통으로 연결해야 합니다.

## 2. Arduino IDE 준비

Arduino IDE 2.x의 Library Manager에서 다음 이름으로 설치합니다.

1. `Adafruit BME280 Library`
2. `Adafruit Unified Sensor` (BME280 의존성)
3. `Sensirion UART SPS30`
4. `Sensirion Core` (SPS30 의존성)
5. `TinyGPSPlus`

`SD`와 `SPI`는 Arduino AVR 보드 패키지에 포함됩니다. SPS30에는 이름이 비슷한 구형/비공식 라이브러리가 여럿 있으므로 이 프로젝트는 `#include <SensirionUartSps30.h>`를 제공하는 공식 **Sensirion UART SPS30** 라이브러리를 사용합니다.

공식 참고 자료:

- [Adafruit BME280 Library](https://github.com/adafruit/Adafruit_BME280_Library)
- [Sensirion UART SPS30](https://github.com/Sensirion/arduino-uart-sps30)
- [TinyGPSPlus](https://github.com/mikalhart/TinyGPSPlus)
- [Arduino SD](https://github.com/arduino-libraries/SD)

## 3. Arduino 설정과 업로드

1. [wiring.md](docs/wiring.md)의 표에 따라 전원을 끈 상태에서 배선합니다.
2. microSD를 FAT16 또는 FAT32로 포맷하고 삽입합니다.
3. Arduino IDE에서 `arduino/airborne_monitor/airborne_monitor.ino`를 엽니다.
4. Board를 `Arduino Mega or Mega 2560`, Processor를 `ATmega2560`으로 선택합니다.
5. 보드가 연결된 Port를 선택하고 업로드합니다.
6. Serial Monitor를 115200 baud로 열어 초기화 결과와 1 Hz CSV 행을 확인합니다.

학교 환경에서 바꿀 값은 [config.h](arduino/airborne_monitor/config.h)에 모았습니다. 기본값은 다음과 같습니다.

| 설정 | 기본값 | 의미 |
|---|---:|---|
| `SAMPLE_INTERVAL_MS` | 1000 | 측정 주기, 1 Hz |
| `SPS30_WARMUP_MS` | 30000 | PM 값이 `NA`인 워밍업 시간 |
| `SD_CS_PIN` | 4 | SD 모듈 CS 핀 |
| `SERIAL_BAUD_DEBUG` | 115200 | USB Serial Monitor |
| `SERIAL_BAUD_SPS30` | 115200 | Serial1 |
| `SERIAL_BAUD_GNSS` | 9600 | Serial2; GNSS 설정과 맞출 것 |
| `SERIAL_BAUD_XBEE` | 115200 | Serial3와 두 XBee의 UART baud |
| `MOCK_SENSORS` | 0 | 1이면 센서 대신 Arduino 가상값 |

`MOCK_SENSORS=1`도 SD와 XBee는 실제로 사용합니다. 센서 입력, CSV 포맷, scheduler를 분리해서 확인하기 위한 모드입니다. SPS30 워밍업을 기다리기 싫으면 시험할 때만 `SPS30_WARMUP_MS`를 줄이십시오.

## 4. XBee 설정

두 XBee를 같은 네트워크로 구성하고 UART를 115200 baud, 8 data bits, no parity, 1 stop bit로 맞춥니다. 공중 XBee의 목적지가 지상 XBee가 되도록 제조사 설정 도구에서 주소를 지정합니다. 이 프로젝트는 XBee API frame을 사용하지 않고 Transparent Mode에서 `CSV + newline`만 전송합니다.

무선 링크를 먼저 제조사 terminal 도구로 시험한 뒤 지상국을 실행하면 문제를 빠르게 분리할 수 있습니다.

## 5. PC 지상국 설치

Python 3.11 설치 화면에서 `Add python.exe to PATH`를 선택합니다. 그다음:

```powershell
cd ground_station
python -m pip install -r requirements.txt
python main.py
```

프로그램은 COM 포트를 하나씩 잠시 읽고 정상 18열 telemetry를 보내는 장치를 선택합니다. 자동 탐색에 실패하면 포트 목록을 출력하고 terminal 실행에서는 번호 선택 기회를 줍니다. 연결이 나중에 끊겨도 창은 닫히지 않고 `DISCONNECTED → RECONNECTING → CONNECTED` 상태로 재접속합니다.

포트를 직접 지정할 수도 있습니다.

```powershell
python main.py --port COM5
```

사용 가능한 포트만 보려면:

```powershell
python main.py --list-ports
```

## 6. 정상 실행 순서

1. 전원을 끄고 배선과 논리 레벨을 확인합니다.
2. FAT16/FAT32 microSD를 삽입합니다.
3. Arduino 코드를 업로드합니다.
4. Serial Monitor 115200 baud에서 BME/SPS/SD 초기화 메시지를 봅니다.
5. 공중/지상 XBee의 전원과 Transparent Mode 설정을 확인합니다.
6. 지상 XBee USB 어댑터를 Windows PC에 연결합니다.
7. `python main.py` 또는 `run_ground_station.bat`을 실행합니다.
8. 화면의 `CONNECTED`와 수신 sequence 증가를 확인합니다.
9. 종료 후 Arduino SD의 `FLIGHTnn.CSV`와 PC `data/flight_날짜_nnn.csv`를 비교합니다.

## 7. 화면에서 보이는 것

왼쪽에는 현재 sequence, runtime, 온도, 습도, 기압, PM1/2.5/4/10, 위치, GNSS 고도, 지상속도, 네 장치 상태, 수신/손실 packet 수가 표시됩니다. 오른쪽 dropdown에서 고도·온도·기압·PM2.5·PM10·지상속도 그래프를 선택할 수 있습니다. 메모리와 redraw 비용을 제한하기 위해 최근 120점만 그리지만 CSV에는 모든 유효 행을 즉시 기록합니다.

`gps_speed_mps`는 **GNSS ground speed**이며 실제 풍속이 아닙니다.

## 8. 실패 시 동작

- BME280 실패: 온도/습도/기압은 `NA`, `bme_ok=0`; 다른 기능 계속
- SPS30 워밍업/실패: 네 PM 값은 `NA`, `sps_ok=0`; 다른 기능 계속
- GNSS fix 없음/오래됨: 다섯 GNSS 값은 `NA`, `gps_ok=0`; NMEA parsing 계속
- SD 없음/쓰기 실패: `sd_ok=0`; XBee 전송 계속, 5초 간격 재초기화
- XBee/USB 단절: Arduino SD 기록 계속; PC는 재연결 시도
- 손상된/부분 CSV: PC 저장·그래프에서 제외하고 오류 수만 표시
- Arduino 재부팅: seq 감소를 PC가 reset으로 보고 새 기준점에서 추적

SD 쓰기 결과는 미리 알 수 없으므로 한 행의 `sd_ok`는 **그 행을 쓰기 직전까지 확인된 SD 상태**입니다. 실제 쓰기가 실패하면 해당 행은 무선으로는 전달되고, 다음 행부터 `sd_ok=0`이 됩니다.

## 9. 테스트

외부 test framework 없이 Python 표준 `unittest`를 사용합니다.

```powershell
cd ground_station
python -m unittest discover -s tests -v
```

테스트 범위는 정상/비정상 CSV parsing, `NA`, 열 수, 상태 flag, packet loss, sequence reset, 덮어쓰기 방지 logger, mock 변화입니다.

Arduino CLI가 설치된 PC에서는 라이브러리를 설치한 뒤 다음처럼 실제 컴파일 검증을 할 수 있습니다.

```powershell
arduino-cli compile --fqbn arduino:avr:mega arduino/airborne_monitor
```

현재 소스의 CSV formatter는 센서 객체와 분리된 순수 함수 `formatCsvRow()`이며, 고정 256-byte 버퍼 밖에 쓰지 않으면 `false`를 반환합니다.

## 10. 파일 안내

```text
airborne_environment_monitor/
├─ README.md
├─ docs/
│  ├─ architecture.md
│  ├─ wiring.md
│  ├─ data_format.md
│  ├─ troubleshooting.md
│  ├─ example_screen.md
│  └─ validation.md
├─ arduino/airborne_monitor/
│  ├─ airborne_monitor.ino
│  ├─ config.h
│  ├─ measurement.h
│  ├─ sensors.h/.cpp
│  ├─ telemetry.h/.cpp
│  ├─ storage.h/.cpp
│  ├─ scheduler.h/.cpp
│  └─ health.h/.cpp
├─ ground_station/
│  ├─ main.py
│  ├─ config.py
│  ├─ data_model.py
│  ├─ serial_receiver.py
│  ├─ data_logger.py
│  ├─ mock_data.py
│  ├─ dashboard.py
│  ├─ requirements.txt
│  ├─ run_ground_station.bat
│  ├─ run_mock.bat
│  ├─ data/
│  └─ tests/
└─ examples/example_flight.csv
```
