#pragma once

#include <Arduino.h>

#include "measurement.h"

#define CSV_HEADER_TEXT                                                     \
  "seq,time_ms,temperature_C,humidity_pct,pressure_hPa,pm1_ugm3,"          \
  "pm25_ugm3,pm4_ugm3,pm10_ugm3,latitude,longitude,gps_altitude_m,"        \
  "gps_speed_mps,gps_course_deg,bme_ok,sps_ok,gps_ok,sd_ok"

bool formatCsvRow(const Measurement& measurement, char* output,
                  size_t outputSize);
void sendTelemetryRow(const char* row);

