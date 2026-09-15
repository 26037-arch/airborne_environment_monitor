#pragma once

#include <Arduino.h>

#include "flight_status.h"
#include "health.h"
#include "measurement.h"

void initializeFlightLink(uint32_t nowMs);
void pollFlightLink(uint32_t nowMs);
void serviceFlightLink(uint32_t nowMs);
const FlightStatus& currentFlightStatus();
bool flightControllerPositionEnabled();
void applyFlightStatusToMeasurement(Measurement& measurement,
                                    HealthState& health, uint32_t nowMs);

