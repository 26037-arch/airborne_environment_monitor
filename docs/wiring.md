# 배선 안내

반드시 전원을 끈 뒤 배선하십시오. 아래 표의 전원 전압은 “Mega 핀에 무조건 바로 연결”하라는 뜻이 아닙니다. 사용하는 breakout board와 센서 제조사 데이터시트에서 공급 전압, UART/I2C 논리 레벨, 내장 level shifter 유무를 먼저 확인하십시오.

## Arduino Mega 2560 통신 핀

| 장치 | 장치 핀 | Mega 2560 핀 | 비고 |
|---|---|---|---|
| BME280 | SDA | SDA / D20 | I2C |
| BME280 | SCL | SCL / D21 | I2C |
| BME280 | GND | GND | 공통 접지 |
| SPS30 | TX | RX1 / D19 | 교차 연결 |
| SPS30 | RX | TX1 / D18 | 교차 연결 |
| SPS30 | SEL | 연결하지 않음 | 공식 UART/SHDLC 선택 방식 |
| SPS30 | GND | GND | 공통 접지 |
| GNSS (direct mode) | TX | RX2 / D17 | 기존 TinyGPS++ NMEA 수신 |
| Flight Controller (권장) | telemetry TX | RX2 / D17 | MAVLink 수신 |
| Flight Controller (선택) | telemetry RX | TX2 / D16 | 현재 firmware는 command를 보내지 않음 |
| XBee/adapter | TX | RX3 / D15 | 교차 연결 |
| XBee/adapter | RX | TX3 / D14 | **5 V→3.3 V level 주의** |
| XBee/adapter | GND | GND | 공통 접지 |
| microSD | MISO | D50 | SPI |
| microSD | MOSI | D51 | SPI |
| microSD | SCK | D52 | SPI |
| microSD | CS | D4 | `SD_CS_PIN`과 일치시킬 것 |
| microSD | GND | GND | 공통 접지 |

## 전원과 논리 레벨 점검

- **BME280:** 센서 IC 자체와 breakout board의 허용 입력 전압은 같지 않을 수 있습니다. 보드의 regulator와 I2C level shifting 유무를 확인합니다.
- **SPS30:** Sensirion 공식 UART Arduino 안내는 SPS30 VDD 5 V, Mega Serial1 교차 연결을 제시합니다. 충분한 전류를 공급하고 케이블 pin 번호를 데이터시트에서 다시 확인합니다.
- **GNSS:** 많은 모듈이 3.3 V 논리를 사용합니다. 특히 Mega TX2→GNSS RX 경로는 level shifter 또는 divider가 필요한지 확인합니다. GNSS RX가 필요 없다면 연결하지 않아도 NMEA 수신은 가능합니다.
- **XBee:** XBee radio 자체는 일반적으로 3.3 V 계열입니다. 5 V tolerant adapter/breakout이 아닌 radio에 Mega TX3를 직접 연결하지 마십시오.
- **microSD:** SD card 자체는 3.3 V입니다. Mega용 module의 regulator/level shifter 유무를 확인합니다.
- **전류:** SPS30 fan과 무선 송신의 순간 부하를 고려합니다. Mega regulator의 한계를 넘지 않도록 적절한 외부 전원을 쓰되 GND는 공통으로 연결합니다.

## 포트 배정 확인

```text
Serial  = USB debug
Serial1 = SPS30 (D19 RX1, D18 TX1)
Serial2 = GNSS 또는 Flight Controller MAVLink (compile-time 선택)
Serial3 = XBee  (D15 RX3, D14 TX3)
I2C     = BME280 (D20/D21)
SPI     = microSD (D50/D51/D52 + configured CS)
```

SoftwareSerial은 사용하지 않습니다.

GNSS를 Flight Controller에 연결하는 권장 구성에서는 GNSS를 Mega Serial2에 동시에 연결하지 않는다. 설정과 MAVLink dependency는 [flight_controller.md](flight_controller.md)를 참고한다.
