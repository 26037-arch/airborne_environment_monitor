#pragma once

#include <Arduino.h>

struct Measurement {
  uint32_t seq;
  uint32_t timeMs;

  float temperatureC;
  float humidityPct;
  float pressureHpa;
  bool bmeValuesValid;

  float pm1Ugm3;
  float pm25Ugm3;
  float pm4Ugm3;
  float pm10Ugm3;
  bool spsValuesValid;

  double latitude;
  double longitude;
  float gpsAltitudeM;
  float gpsSpeedMps;
  float gpsCourseDeg;
  bool gpsValuesValid;

  bool bmeOk;
  bool spsOk;
  bool gpsOk;
  bool sdOk;
};

void clearMeasurement(Measurement& measurement, uint32_t seq, uint32_t nowMs);

