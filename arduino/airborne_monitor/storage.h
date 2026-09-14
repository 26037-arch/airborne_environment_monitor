#pragma once

#include <Arduino.h>

#include "health.h"

void initializeStorage(HealthState& health, uint32_t nowMs);
void serviceStorage(HealthState& health, uint32_t nowMs);
bool storageIsReady();
bool appendStorageRow(const char* row, HealthState& health, uint32_t nowMs);
const char* storageFilename();

