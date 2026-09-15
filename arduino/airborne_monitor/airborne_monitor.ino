#include "config.h"
#include "flight_link.h"
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
  Serial3.begin(SERIAL_BAUD_XBEE);
  initializeHealth(health);

  const uint32_t nowMs = millis();
  initializeSensors(health, nowMs);
  initializeFlightLink(nowMs);
  initializeStorage(health, nowMs);
  initializeScheduler(scheduler, nowMs);

  Serial.println(F("Airborne environment monitor started"));
  printHealthSummary(health);
}

void loop() {
  const uint32_t nowMs = millis();
  // GNSS 문자는 샘플링 시점과 무관하게 매 loop에서 계속 파싱합니다.
  pollGnss();
  pollFlightLink(nowMs);
  serviceFlightLink(nowMs);

  serviceSensors(health, nowMs);
  serviceStorage(health, nowMs);

  if (!sampleIsDue(scheduler, nowMs, SAMPLE_INTERVAL_MS)) {
    return;
  }

  Measurement measurement;
  ++sequenceNumber;
  clearMeasurement(measurement, sequenceNumber, nowMs);
  sampleSensors(measurement, health, nowMs);
  applyFlightStatusToMeasurement(measurement, health, nowMs);
  measurement.sdOk = storageIsReady();

  // 이 행을 단 한 번 만든 다음 SD와 XBee 양쪽에 같은 버퍼를 전달합니다.
  const bool formatted = flightControllerPositionEnabled()
      ? formatCsvRowV2(measurement, currentFlightStatus(), csvRow, sizeof(csvRow))
      : formatCsvRow(measurement, csvRow, sizeof(csvRow));
  if (!formatted) {
    Serial.println(F("ERROR: CSV row buffer too small"));
    return;
  }

  appendStorageRow(csvRow, health, nowMs);
  sendTelemetryRow(csvRow);

  // USB debug에는 무선으로 보낸 것과 같은 행을 보여 줍니다.
  Serial.println(csvRow);
}
