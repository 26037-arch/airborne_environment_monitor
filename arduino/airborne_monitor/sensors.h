#pragma once

#include <Arduino.h>

#include "health.h"
#include "measurement.h"

void initializeSensors(HealthState& health, uint32_t nowMs);
void pollGnss();
void serviceSensors(HealthState& health, uint32_t nowMs);
void sampleSensors(Measurement& measurement, HealthState& health,
                   uint32_t nowMs);
