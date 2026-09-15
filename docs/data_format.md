# Telemetry CSV 형식 (v1/v2)

## Header와 열 순서

Arduino SD와 PC CSV는 정확히 같은 18개 열을 사용합니다.

```text
seq,time_ms,temperature_C,humidity_pct,pressure_hPa,pm1_ugm3,pm25_ugm3,pm4_ugm3,pm10_ugm3,latitude,longitude,gps_altitude_m,gps_speed_mps,gps_course_deg,bme_ok,sps_ok,gps_ok,sd_ok
```

| # | 열 | 단위/자료형 | invalid |
|---:|---|---|---|
| 1 | `seq` | uint32, 행마다 1 증가 | 허용 안 함 |
| 2 | `time_ms` | uint32, Arduino 부팅 후 ms | 허용 안 함 |
| 3 | `temperature_C` | °C | `NA` |
| 4 | `humidity_pct` | %RH | `NA` |
| 5 | `pressure_hPa` | hPa; BME 원본 Pa ÷ 100 | `NA` |
| 6 | `pm1_ugm3` | µg/m³ | `NA` |
| 7 | `pm25_ugm3` | µg/m³ | `NA` |
| 8 | `pm4_ugm3` | µg/m³ | `NA` |
| 9 | `pm10_ugm3` | µg/m³ | `NA` |
| 10 | `latitude` | decimal degree | `NA` |
| 11 | `longitude` | decimal degree | `NA` |
| 12 | `gps_altitude_m` | GNSS altitude, m | `NA` |
| 13 | `gps_speed_mps` | GNSS ground speed, m/s | `NA` |
| 14 | `gps_course_deg` | course, degree | `NA` |
| 15–18 | `*_ok` | 정상 1, 비정상/준비 중 0 | 0/1만 허용 |

정상 예:

```text
152,152000,18.42,55.30,942.83,4.10,7.20,8.30,9.60,37.123456,127.123456,523.40,3.82,124.30,1,1,1,1
```

SPS30 warm-up과 GNSS fix 없음의 예:

```text
3,3000,20.13,54.20,1008.41,NA,NA,NA,NA,NA,NA,NA,NA,NA,1,0,0,1
```

## 상태 의미

- `bme_ok=1`: 이 행의 BME 세 값이 유효합니다.
- `sps_ok=1`: warm-up이 끝났고 이 행의 SPS30 읽기가 성공했습니다.
- `gps_ok=1`: 위치, 고도, speed, course가 모두 valid이며 age가 설정 임계값 이하입니다.
- `sd_ok=1`: 행 생성 직전까지 SD가 초기화되어 있고 직전 상태가 정상입니다. 현재 append 실패는 다음 telemetry 상태에 반영됩니다.

PC parser는 정확히 18열인지, seq/time이 uint32인지, 숫자가 finite인지, flag가 0/1인지 확인합니다. 정상 flag가 1인데 해당 센서 값이 `NA`인 행도 버립니다.

## v2 Flight Controller 확장

v1의 18개 열은 앞부분에 순서와 의미를 그대로 유지한다. Flight Controller mode에서 다음 11개 열을 뒤에 붙인 29열 v2를 사용한다.

```text
estimated_altitude_m,vertical_speed_mps,roll_deg,pitch_deg,yaw_deg,battery_voltage_V,battery_current_A,flight_mode,armed,flight_link_ok,system_health
```

`armed`와 `flight_link_ok`는 항상 0/1이다. 연결되지 않았거나 아직 해당 MAVLink message를 받지 않은 수치는 `NA`다. `system_health`는 Flight Controller가 보고한 정수 status/bitmask이며 payload가 임의로 해석해 비행 제어에 사용하지 않는다.

Parser는 열 수로 v1/v2를 자동 감지한다. CSV replay와 PC logger도 첫 record의 version에 맞는 header를 사용하므로 과거 v1 파일은 변환 없이 읽힌다. 한 파일 안에서 version이 바뀌는 것은 logger가 거부한다.

완전한 예시는 `examples/example_flight_v2.csv`에 있다.

## Packet loss와 reset

수신 seq가 `152,153,155`라면 154 한 개를 손실로 셉니다. seq가 직전 값보다 작아지면 Arduino 재부팅 또는 uint32 wrap으로 보고, 손실을 대량으로 만들지 않고 새 기준점으로 시작합니다. 같은 seq가 연속으로 오면 duplicate로 세지만 loss는 추가하지 않습니다.

Loss percentage는 다음과 같습니다.

```text
lost / (valid rows received + lost) × 100
```

## 전송 framing

XBee Transparent Mode에서 한 measurement는 ASCII CSV 한 줄과 newline(`\n`)입니다. JSON, binary frame, `DATA,` prefix는 쓰지 않습니다. 손상되거나 중간부터 수신한 행은 PC parser가 무시하고 다음 newline부터 다시 동기화합니다.
