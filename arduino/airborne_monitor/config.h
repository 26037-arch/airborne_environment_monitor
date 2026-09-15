#pragma once

#define SAMPLE_INTERVAL_MS 1000UL
#define SENSOR_RETRY_INTERVAL_MS 10000UL
#define GPS_MAX_AGE_MS 3000UL
#define SD_RETRY_INTERVAL_MS 5000UL

#define SD_CS_PIN 4

#define SERIAL_BAUD_DEBUG 115200UL
#define SERIAL_BAUD_GNSS 9600UL
#define SERIAL_BAUD_FLIGHT_CONTROLLER 115200UL
#define SERIAL_BAUD_HC12 9600UL

#define SEA_LEVEL_PRESSURE_HPA 1013.25f

#define AHT20_I2C_ADDRESS 0x38
#define BMP280_ADDRESS_PRIMARY 0x76
#define BMP280_ADDRESS_SECONDARY 0x77
// Keep MPU6050 AD0 HIGH when a 0x68 RTC is present.
#define MPU6050_I2C_ADDRESS 0x69
#define RTC_I2C_ADDRESS 0x68

// The board marking "DM941" does not identify the RTC IC. Leave RTC support
// disabled until the chip and address have been checked on the actual module.
#define RTC_DRIVER_DISABLED 0
#define RTC_DRIVER_DS3231_COMPATIBLE 1
#ifndef RTC_DRIVER
#define RTC_DRIVER RTC_DRIVER_DISABLED
#endif

// Apply measured offsets without a blocking startup calibration.
#define MPU_ACCEL_OFFSET_X_MPS2 0.0f
#define MPU_ACCEL_OFFSET_Y_MPS2 0.0f
#define MPU_ACCEL_OFFSET_Z_MPS2 0.0f
#define MPU_GYRO_OFFSET_X_DPS 0.0f
#define MPU_GYRO_OFFSET_Y_DPS 0.0f
#define MPU_GYRO_OFFSET_Z_DPS 0.0f

#ifndef MOCK_SENSORS
#define MOCK_SENSORS 0
#endif
#define MOCK_RTC_EPOCH_UNIX 1767225600UL

// Retained only for the optional/future flight_link adapter. The v3 payload
// runtime does not call the adapter or use Serial2.
#define POSITION_SOURCE_DIRECT_GNSS 0
#define POSITION_SOURCE_FLIGHT_CONTROLLER 1
#ifndef POSITION_SOURCE
#define POSITION_SOURCE POSITION_SOURCE_DIRECT_GNSS
#endif
#define FLIGHT_LINK_TIMEOUT_MS 3000UL

// Calculated v3 worst case is below 260 bytes with the selected precision.
#define CSV_ROW_BUFFER_SIZE 320
