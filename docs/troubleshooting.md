# 문제 해결

문제를 한꺼번에 보지 말고 `sensor → Mega USB → SD → XBee terminal → 지상국` 순서로 분리해 확인하십시오.

## Arduino compile 오류

### `SensirionUartSps30.h: No such file`

Arduino Library Manager에서 **Sensirion UART SPS30**과 **Sensirion Core**를 설치합니다. `sps30.h`를 제공하는 legacy library는 이 코드와 API가 다릅니다.

### `Adafruit_BME280.h` 또는 `Adafruit_Sensor.h` 없음

**Adafruit BME280 Library**와 **Adafruit Unified Sensor**를 모두 설치합니다.

### `TinyGPS++.h` 없음

Library Manager에서 **TinyGPSPlus**를 설치합니다. include 파일 이름은 plus 기호 두 개가 들어간 `TinyGPS++.h`입니다.

## BME280: not found / `bme_ok=0`

1. SDA=D20, SCL=D21, GND 공통인지 확인합니다.
2. module의 공급/논리 전압 사양을 확인합니다.
3. 코드는 0x76과 0x77을 모두 확인합니다. I2C scanner로 실제 주소와 bus 충돌을 점검합니다.
4. BMP280을 BME280로 잘못 판매한 모듈은 humidity를 지원하지 않아 이 library가 정상 BME280로 인식하지 않습니다.

10초마다 한 번 재초기화하므로 일시 접촉 불량이 회복되면 다시 `bme_ok=1`이 될 수 있습니다.

## SPS30 start failed / 계속 `sps_ok=0`

1. TX→D19(RX1), RX→D18(TX1) 교차 연결을 확인합니다.
2. SEL pin은 공식 UART/SHDLC 배선대로 연결하지 않습니다.
3. SPS30 공급 전압과 전류 여유를 데이터시트 기준으로 확인합니다.
4. baud는 115200이어야 합니다.
5. 부팅 직후 기본 30초는 정상 warm-up이며 PM 값은 `NA`입니다.

읽기 실패 시 시스템은 멈추지 않고 10초 뒤 측정 시작을 다시 시도합니다.

## `gps_ok=0`, GNSS 값 `NA`

1. GNSS TX→D17(RX2)을 확인합니다.
2. 모듈 NMEA baud가 `SERIAL_BAUD_GNSS` 기본 9600과 같은지 확인합니다.
3. 실내에서는 fix에 오래 걸리거나 실패할 수 있으므로 하늘이 열린 곳에서 시험합니다.
4. 위치/고도/speed/course 중 하나라도 invalid이거나 3초보다 오래되면 한 snapshot 전체를 invalid로 기록합니다.
5. GNSS RX는 단순 NMEA 수신에 필수는 아닙니다. 연결한다면 Mega TX2의 5 V 논리 호환성을 확인합니다.

## `SD: unavailable`, `sd_ok=0`

1. FAT16/FAT32 포맷과 카드 삽입 방향을 확인합니다.
2. MISO=D50, MOSI=D51, SCK=D52, CS=D4를 확인합니다.
3. CS를 다른 pin에 연결했다면 `config.h`의 `SD_CS_PIN`을 바꿉니다.
4. SD card는 3.3 V 장치이므로 Mega 호환 level shifting module인지 확인합니다.
5. 카드의 write protection, 접점, 다른 카드도 시험합니다.

실패해도 XBee 전송은 계속됩니다. 재삽입 후 최대 약 5초 안에 새 `FLIGHTnn.CSV`를 만들려고 시도합니다. 기존 파일은 덮어쓰지 않습니다. `FLIGHT00.CSV`부터 `FLIGHT99.CSV`까지 이미 있으면 파일을 PC로 옮기고 카드를 정리하십시오.

## PC가 COM 포트를 못 찾음

```powershell
python main.py --list-ports
```

- Windows Device Manager에서 XBee USB adapter의 COM 번호와 driver 상태를 봅니다.
- 다른 serial terminal이 포트를 점유하고 있으면 닫습니다.
- XBee terminal에서 ASCII CSV와 줄바꿈이 실제로 오는지 먼저 확인합니다.
- 자동 탐색은 포트마다 기본 2.5초 기다립니다. 데이터 주기가 더 느리면 `config.py`의 `AUTO_DETECT_SECONDS_PER_PORT`를 늘립니다.
- 직접 지정: `python main.py --port COM5`

## CONNECTED인데 값이 안 나옴

- 연결 직후 손상된 partial line 하나는 의도적으로 버릴 수 있습니다.
- XBee 두 장치의 PAN/network, destination, Transparent Mode, UART 115200 8N1을 확인합니다.
- 잘못된 행 수는 화면 아래에 표시됩니다. `docs/data_format.md`의 정확한 18열과 비교합니다.
- Arduino Serial Monitor에서는 행이 보이지만 XBee에는 없으면 Serial3/D14/D15 배선과 논리 level을 확인합니다.

## 케이블 제거 후 복구 안 됨

지상국은 기본 3초 간격으로 재연결합니다. 장치가 다른 COM 번호로 다시 나타나면 기존 port 실패 후 다른 후보에서 정상 telemetry를 probe합니다. 그래도 안 되면 프로그램을 닫고 `--list-ports`, `--port`로 확인합니다.

## 그래프 창/`tkinter` 오류

공식 Windows Python installer에는 Tkinter가 포함됩니다. 최소 설치에서 Tcl/Tk를 제외했다면 Python 설치 관리자로 Modify한 뒤 Tcl/Tk를 추가하십시오. 다음으로 package를 다시 설치합니다.

```powershell
python -m pip install -r requirements.txt
```

GUI 없이 수신과 저장만 확인할 수 있습니다.

```powershell
python main.py --mock --headless --duration 10
```

## Packet loss가 높음

- 안테나 방향, 거리, 장애물, 전원 안정성, XBee RF channel/network 설정을 확인합니다.
- 115200 UART가 양쪽 XBee 설정과 같은지 확인합니다.
- SD CSV에는 seq가 연속인데 PC CSV만 gap이면 무선/USB 구간 문제입니다.
- 두 CSV 모두 같은 gap이면 Arduino reboot, 전원, sensor/SD의 과도한 blocking을 조사합니다.

