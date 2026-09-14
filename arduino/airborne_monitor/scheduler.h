#pragma once

#include <Arduino.h>

struct SchedulerState {
  uint32_t lastSampleMs;
};

void initializeScheduler(SchedulerState& scheduler, uint32_t nowMs);
bool sampleIsDue(SchedulerState& scheduler, uint32_t nowMs,
                 uint32_t intervalMs);

