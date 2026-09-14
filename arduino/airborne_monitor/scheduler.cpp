#include "scheduler.h"

void initializeScheduler(SchedulerState& scheduler, uint32_t nowMs) {
  scheduler.lastSampleMs = nowMs;
}

bool sampleIsDue(SchedulerState& scheduler, uint32_t nowMs,
                 uint32_t intervalMs) {
  // unsigned subtraction으로 millis() 약 49.7일 wrap에도 안전합니다.
  if (static_cast<uint32_t>(nowMs - scheduler.lastSampleMs) < intervalMs) {
    return false;
  }
  scheduler.lastSampleMs = nowMs;
  return true;
}

