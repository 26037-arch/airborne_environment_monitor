#pragma once

#include <Arduino.h>

struct HealthState {
  bool ahtOk;
  bool bmpOk;
  bool imuOk;
  bool gpsOk;
  bool rtcOk;
  bool sdOk;
  uint32_t lastAhtSuccessMs;
  uint32_t lastBmpSuccessMs;
  uint32_t lastImuSuccessMs;
  uint32_t lastGpsSuccessMs;
  uint32_t lastRtcSuccessMs;
  uint32_t lastSdSuccessMs;
};

void initializeHealth(HealthState& health);
void printHealthSummary(const HealthState& health);
