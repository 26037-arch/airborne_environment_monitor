#include "config.h"
#include "health.h"
#include "measurement.h"
#include "scheduler.h"
#include "sensors.h"
#include "storage.h"
#include "telemetry.h"

static HealthState health;
static SchedulerState scheduler;
static uint32_t sequenceNumber = 0;
static char csvRow[CSV_ROW_BUFFER_SIZE];

void setup() {
  Serial.begin(SERIAL_BAUD_DEBUG);
  Serial3.begin(SERIAL_BAUD_HC12);
  initializeHealth(health);
  const uint32_t nowMs = millis();
  initializeSensors(health, nowMs);
  initializeStorage(health, nowMs);
  initializeScheduler(scheduler, nowMs);
  Serial.println(F("Airborne environment monitor v3 started"));
  Serial.println(F("UART: Serial1=GNSS Serial2=reserved Serial3=HC-12"));
  printHealthSummary(health);
}

void loop() {
  const uint32_t nowMs = millis();
  pollGnss();
  serviceSensors(health, nowMs);
  serviceStorage(health, nowMs);
  if (!sampleIsDue(scheduler, nowMs, SAMPLE_INTERVAL_MS)) return;

  Measurement measurement;
  ++sequenceNumber;
  clearMeasurement(measurement, sequenceNumber, nowMs);
  sampleSensors(measurement, health, nowMs);
  measurement.sdOk = storageIsReady();

  if (!formatCsvRowV3(measurement, csvRow, sizeof(csvRow))) {
    Serial.println(F("ERROR: CSV row buffer too small; row not sent or logged"));
    return;
  }

  // The exact same immutable snapshot row goes to both independent sinks.
  appendStorageRow(csvRow, health, nowMs);
  sendTelemetryRow(csvRow);
  Serial.println(csvRow);
}
