#pragma once

#include <Arduino.h>

struct Measurement {
  uint32_t seq;
  uint32_t timeMs;

  float temperatureC;
  float humidityPct;
  bool ahtValuesValid;

  float pressureHpa;
  float barometricAltitudeM;
  bool bmpValuesValid;

  double latitude;
  double longitude;
  float gpsAltitudeM;
  float gpsSpeedMps;
  float gpsCourseDeg;
  bool gpsValuesValid;

  float accelXMps2;
  float accelYMps2;
  float accelZMps2;
  float gyroXDps;
  float gyroYDps;
  float gyroZDps;
  bool imuValuesValid;

  uint32_t rtcUnixTime;
  bool rtcValueValid;

  bool envOk;
  bool imuOk;
  bool gpsOk;
  bool rtcOk;
  bool sdOk;
};

void clearMeasurement(Measurement& measurement, uint32_t seq, uint32_t nowMs);
