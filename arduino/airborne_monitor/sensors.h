#pragma once

#include <Arduino.h>

#include "health.h"
#include "measurement.h"

enum SpsState {
  SPS_STATE_WARMUP,
  SPS_STATE_READY,
  SPS_STATE_ERROR
};

void initializeSensors(HealthState& health, uint32_t nowMs);
void pollGnss();
void serviceSensors(HealthState& health, uint32_t nowMs);
void sampleSensors(Measurement& measurement, HealthState& health, uint32_t nowMs);
SpsState getSpsState();

