#pragma once

#include <Arduino.h>

#include "config.h"
#include "measurement.h"
#include "flight_status.h"

#define CSV_HEADER_TEXT                                                     \
  "seq,time_ms,temperature_C,humidity_pct,pressure_hPa,pm1_ugm3,"          \
  "pm25_ugm3,pm4_ugm3,pm10_ugm3,latitude,longitude,gps_altitude_m,"        \
  "gps_speed_mps,gps_course_deg,bme_ok,sps_ok,gps_ok,sd_ok"

#define CSV_HEADER_V2_TEXT                                                  \
  CSV_HEADER_TEXT ",estimated_altitude_m,vertical_speed_mps,roll_deg,"    \
  "pitch_deg,yaw_deg,battery_voltage_V,battery_current_A,flight_mode,"     \
  "armed,flight_link_ok,system_health"

#if POSITION_SOURCE == POSITION_SOURCE_FLIGHT_CONTROLLER
#define ACTIVE_CSV_HEADER_TEXT CSV_HEADER_V2_TEXT
#else
#define ACTIVE_CSV_HEADER_TEXT CSV_HEADER_TEXT
#endif

bool formatCsvRow(const Measurement& measurement, char* output,
                  size_t outputSize);
bool formatCsvRowV2(const Measurement& measurement,
                    const FlightStatus& flightStatus, char* output,
                    size_t outputSize);
void sendTelemetryRow(const char* row);
