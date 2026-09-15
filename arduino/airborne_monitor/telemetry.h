#pragma once

#include <Arduino.h>

#include "measurement.h"

#define CSV_HEADER_V3_TEXT                                                  \
  "seq,time_ms,temperature_C,humidity_pct,pressure_hPa,"                   \
  "barometric_altitude_m,latitude,longitude,gps_altitude_m,gps_speed_mps," \
  "gps_course_deg,accel_x_mps2,accel_y_mps2,accel_z_mps2,gyro_x_dps,"     \
  "gyro_y_dps,gyro_z_dps,rtc_unix_time,env_ok,imu_ok,gps_ok,rtc_ok,sd_ok"

#define ACTIVE_CSV_HEADER_TEXT CSV_HEADER_V3_TEXT

bool formatCsvRowV3(const Measurement& measurement, char* output,
                    size_t outputSize);
void sendTelemetryRow(const char* row);
