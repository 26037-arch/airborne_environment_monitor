#pragma once

#include <Arduino.h>

// Fixed-size, read-only state received from PX4/ArduPilot over MAVLink.
struct FlightStatus {
  bool connected;
  bool armed;
  bool attitudeValid;
  bool positionValid;
  bool motionValid;
  bool batteryValid;
  bool systemHealthValid;

  float rollDeg;
  float pitchDeg;
  float yawDeg;
  double latitude;
  double longitude;
  float gnssAltitudeM;
  float estimatedAltitudeM;
  float groundSpeedMps;
  float verticalSpeedMps;
  float batteryVoltage;
  float batteryCurrent;
  uint32_t flightMode;
  uint32_t systemHealth;
  uint32_t lastUpdateMs;
};

