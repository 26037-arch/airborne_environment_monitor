#pragma once

// 이 파일의 값만 바꾸면 대부분의 학교 환경에 맞출 수 있습니다.
#define SAMPLE_INTERVAL_MS 1000UL
#define SPS30_WARMUP_MS 30000UL
#define SENSOR_RETRY_INTERVAL_MS 10000UL
#define GPS_MAX_AGE_MS 3000UL
#define FLIGHT_LINK_TIMEOUT_MS 3000UL
#define SD_RETRY_INTERVAL_MS 5000UL

#define SD_CS_PIN 4

#define SERIAL_BAUD_DEBUG 115200UL
#define SERIAL_BAUD_SPS30 115200UL
#define SERIAL_BAUD_GNSS 9600UL
#define SERIAL_BAUD_FLIGHT_CONTROLLER 115200UL
#define SERIAL_BAUD_XBEE 115200UL

// 1: BME280/SPS30/GNSS 없이 가상 측정값 생성, 0: 실제 센서 사용
#ifndef MOCK_SENSORS
#define MOCK_SENSORS 0
#endif

// Direct mode preserves the original TinyGPS++ path.  Select FLIGHT_CONTROLLER
// after installing the generated official MAVLink C headers for Arduino.
#define POSITION_SOURCE_DIRECT_GNSS 0
#define POSITION_SOURCE_FLIGHT_CONTROLLER 1
#ifndef POSITION_SOURCE
#define POSITION_SOURCE POSITION_SOURCE_DIRECT_GNSS
#endif

// 흔히 쓰이는 두 I2C 주소를 차례로 확인합니다.
#define BME280_ADDRESS_PRIMARY 0x76
#define BME280_ADDRESS_SECONDARY 0x77

// 한 행의 최대 길이. 18개 열과 종료 문자를 포함해 충분한 여유를 둡니다.
#define CSV_ROW_BUFFER_SIZE 384
