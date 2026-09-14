# 구현 검증 기록

검증일: 2026-09-15

## Arduino Mega 2560 실제 compile

공식 Arduino Library Manager index에서 다음 버전을 설치한 임시 Arduino CLI 환경으로 `arduino:avr:mega`를 실제 컴파일했습니다.

| 구성 | 검증 버전 |
|---|---:|
| Arduino AVR Boards | 1.8.8 |
| Adafruit BME280 Library | 2.3.0 |
| Adafruit Unified Sensor | 1.1.15 |
| Adafruit BusIO | 1.17.4 |
| Sensirion UART SPS30 | 1.0.1 |
| Sensirion Core | 0.7.3 |
| TinyGPSPlus | 1.0.3 |
| SD | 1.3.0 |

실제 센서 build 결과:

```text
Sketch uses 35358 bytes (13%) of program storage space. Maximum is 253952 bytes.
Global variables use 2164 bytes (26%) of dynamic memory, leaving 6028 bytes. Maximum is 8192 bytes.
```

`MOCK_SENSORS=1` build도 성공했습니다. 최종 변경 후 두 mode를 다시 compile해 확인했습니다. 외부 library/core에서 발생한 warning을 제외하고 프로젝트 source의 compile error는 없습니다.

## Python 검증

Python source 전체 byte-compile과 다음 9개 unit test를 실행했습니다.

```text
CSV valid row parsing
NA sensor row parsing
invalid column count
invalid status flag
packet loss detection
sequence reset
logger header/row
logger no-overwrite naming
mock row parse/change
```

결과: `Ran 9 tests ... OK`

`python main.py --mock --headless --duration 2.2`도 실행해 1초 간격 3개 measurement 생성, parser 통과, PC CSV 생성과 flush를 확인했습니다.

## 요구사항 자체 점검

- Serial1=SPS30, Serial2=GNSS, Serial3=XBee; SoftwareSerial 없음
- GNSS parser는 main loop마다 Serial2 available bytes를 소비
- `delay()`와 무한 retry loop 없음
- 1 Hz scheduler는 unsigned `millis()` subtraction 사용
- 센서마다 invalid 값과 health flag가 독립적
- SPS30 `WARMUP/READY/ERROR` 상태 및 조정 가능한 warm-up
- 동적 문자열/JSON 없음; CSV buffer 256 bytes 고정
- 같은 `csvRow`를 SD append 후 XBee 전송
- SD 파일 자동 증가, header 우선 기록, failure 후 telemetry 지속
- Arduino와 Python header 모두 18열이며 순서 동일
- PC invalid row 제외, seq gap/reset 처리, serial 재연결
- GUI graph는 최근 N점만 유지, 전체 유효 데이터는 CSV flush
- PC mock과 Arduino compile-time mock 제공

실물 센서의 전기적 호환성, GNSS NMEA baud/fix, XBee RF 설정, SD 카드 품질은 실제 하드웨어에서 최종 통합 시험이 필요합니다.
