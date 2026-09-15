# Flight Controller 연결

이 저장소의 Flight Controller 코드는 PX4/ArduPilot을 대체하지 않는다. MAVLink telemetry를 읽어 환경 측정 record에 합치는 read-only adapter이며 arming, mode 변경, PWM, motor command API는 없다.

## Arduino Mega mode

기본 build는 기존 직접 GNSS mode다.

```cpp
#define POSITION_SOURCE POSITION_SOURCE_DIRECT_GNSS
```

Flight Controller에 GNSS와 compass를 연결하고 Serial2를 telemetry port로 사용할 때는 다음으로 바꾼다.

```cpp
#define POSITION_SOURCE POSITION_SOURCE_FLIGHT_CONTROLLER
```

이 mode에는 공식 MAVLink `c_library_v2`가 생성하는 `mavlink.h`가 Arduino include path에 있어야 한다. Flight Controller telemetry port와 `SERIAL_BAUD_FLIGHT_CONTROLLER`를 같은 baud로 설정한다. `flight_link.cpp`는 CRC를 통과한 `HEARTBEAT`, `ATTITUDE`, `GLOBAL_POSITION_INT`, `SYS_STATUS`만 상태에 반영하고, `FLIGHT_LINK_TIMEOUT_MS` 동안 새 packet이 없으면 link를 disconnected로 표시한다.

권장 UART 배치는 다음과 같다.

```text
Serial  = USB debug
Serial1 = SPS30
Serial2 = PX4/ArduPilot MAVLink telemetry
Serial3 = XBee transparent telemetry
I2C     = BME280
SPI     = microSD
```

Flight Controller TX→Mega RX2가 최소 연결이다. 양방향 link를 구성할 때는 TX2→Flight Controller RX도 연결할 수 있지만 현재 payload firmware는 command를 전송하지 않는다. 양쪽의 전압과 logic level을 실제 board 문서에서 확인한다.

## Simulator source

`flight_controller.mode`은 다음 값 중 하나다.

- `OFF`: 기존 18열 v1 telemetry. Flight Controller 없음.
- `MOCK`: 상태 composition과 v2 pipeline을 hardware 없이 시험. 비행 안정화 engine이 아니다.
- `MAVLINK`: `pymavlink`로 PX4/ArduPilot endpoint를 non-blocking poll하고 v2에 포함.

예:

```json
{
  "flight_controller": {
    "mode": "MAVLINK",
    "endpoint": "udp:127.0.0.1:14550",
    "baud_rate": 115200,
    "timeout_ms": 3000
  }
}
```

현재 adapter는 SITL의 상태 telemetry 수신까지 구현한다. HIL sensor injection, PX4/ArduPilot별 Webots vehicle model, virtual actuator를 Webots dynamics에 적용하는 종단 closed loop는 실제 SITL/Webots 조합에서 별도 검증해야 한다. 검증되지 않은 actuator output을 실제 hardware에 보내지 않는다.

