#include "health.h"

void initializeHealth(HealthState& health) {
  health.bmeOk = false;
  health.spsOk = false;
  health.gpsOk = false;
  health.sdOk = false;
  health.lastBmeSuccessMs = 0;
  health.lastSpsSuccessMs = 0;
  health.lastGpsSuccessMs = 0;
  health.lastSdSuccessMs = 0;
}

void printHealthSummary(const HealthState& health) {
  Serial.print(F("Health BME="));
  Serial.print(health.bmeOk ? 1 : 0);
  Serial.print(F(" SPS="));
  Serial.print(health.spsOk ? 1 : 0);
  Serial.print(F(" GPS="));
  Serial.print(health.gpsOk ? 1 : 0);
  Serial.print(F(" SD="));
  Serial.println(health.sdOk ? 1 : 0);
}

