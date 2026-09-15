#include "health.h"

void initializeHealth(HealthState& health) {
  health.ahtOk = false;
  health.bmpOk = false;
  health.imuOk = false;
  health.gpsOk = false;
  health.rtcOk = false;
  health.sdOk = false;
  health.lastAhtSuccessMs = 0;
  health.lastBmpSuccessMs = 0;
  health.lastImuSuccessMs = 0;
  health.lastGpsSuccessMs = 0;
  health.lastRtcSuccessMs = 0;
  health.lastSdSuccessMs = 0;
}

void printHealthSummary(const HealthState& health) {
  Serial.print(F("Health AHT="));
  Serial.print(health.ahtOk ? 1 : 0);
  Serial.print(F(" BMP="));
  Serial.print(health.bmpOk ? 1 : 0);
  Serial.print(F(" IMU="));
  Serial.print(health.imuOk ? 1 : 0);
  Serial.print(F(" GPS="));
  Serial.print(health.gpsOk ? 1 : 0);
  Serial.print(F(" RTC="));
  Serial.print(health.rtcOk ? 1 : 0);
  Serial.print(F(" SD="));
  Serial.println(health.sdOk ? 1 : 0);
}
