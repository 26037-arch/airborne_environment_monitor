#pragma once

#include <Arduino.h>

struct HealthState {
  bool bmeOk;
  bool spsOk;
  bool gpsOk;
  bool sdOk;

  uint32_t lastBmeSuccessMs;
  uint32_t lastSpsSuccessMs;
  uint32_t lastGpsSuccessMs;
  uint32_t lastSdSuccessMs;
};

void initializeHealth(HealthState& health);
void printHealthSummary(const HealthState& health);

