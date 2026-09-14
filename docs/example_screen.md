# 예시 실행 화면 설명

실제 screenshot 대신 학교 PC마다 달라지지 않는 화면 구성과 판독 방법을 설명합니다.

```text
┌────────────────────────────────────────────────────────────────────┐
│ Connection: CONNECTED    Port: COM5       PC CSV: ..._001.csv       │
├──────────────────────────┬─────────────────────────────────────────┤
│ Current measurement      │ Graph: [Altitude vs Time ▼]             │
│ Sequence       152       │                                         │
│ Runtime        152.0 s   │             recent line graph           │
│ Temperature   18.42 °C   │                                         │
│ Humidity      55.30 %    │                                         │
│ Pressure     942.83 hPa  │                                         │
│ PM2.5          7.20 ...  │                                         │
│ GPS altitude 523.40 m    │                                         │
│ Ground speed   3.82 m/s  │                                         │
│ BME/SPS/GPS/SD OK/OK/... │                                         │
│ Received       151       │                                         │
│ Lost             1       │                                         │
│ Loss           0.66 %    │                                         │
└──────────────────────────┴─────────────────────────────────────────┘
```

- 초록 `CONNECTED`: 실제 COM port 수신 중
- 파랑 `MOCK`: `--mock` 가상 데이터
- 주황 `RECONNECTING`: 포트를 찾거나 여는 중
- 빨강 `DISCONNECTED`: 현재 serial 연결 없음
- `NA`: 해당 sensor가 warm-up, no fix 또는 오류 상태
- 아래 message bar: 잘못된 행, serial 오류, 최근 packet gap 표시

실제 화면에서 PM 단위는 µg/m³, altitude는 m, ground speed는 m/s입니다. 그래프는 최근 `config.py`의 `GRAPH_POINT_COUNT`개만 유지합니다.

