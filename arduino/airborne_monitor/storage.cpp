#include "storage.h"

#include <SD.h>
#include <SPI.h>
#include <string.h>

#include "config.h"
#include "telemetry.h"

static bool ready = false;
static char filename[13] = "";
static uint32_t lastAttemptMs = 0;

static bool chooseNewFilename() {
  for (uint8_t index = 0; index < 100; ++index) {
    snprintf(filename, sizeof(filename), "FLIGHT%02u.CSV", index);
    if (!SD.exists(filename)) {
      return true;
    }
  }
  filename[0] = '\0';
  return false;
}

static bool startNewLog() {
  // Mega의 하드웨어 SS(53)는 SPI master 유지를 위해 OUTPUT으로 둡니다.
  pinMode(53, OUTPUT);
  pinMode(SD_CS_PIN, OUTPUT);
  if (!SD.begin(SD_CS_PIN) || !chooseNewFilename()) {
    return false;
  }

  File file = SD.open(filename, FILE_WRITE);
  if (!file) {
    return false;
  }
  const size_t headerLength = file.println(F(CSV_HEADER_TEXT));
  file.flush();
  file.close();
  return headerLength > 0;
}

void initializeStorage(HealthState& health, uint32_t nowMs) {
  lastAttemptMs = nowMs;
  ready = startNewLog();
  health.sdOk = ready;
  if (ready) {
    Serial.print(F("SD: logging to "));
    Serial.println(filename);
  } else {
    Serial.println(F("SD: unavailable; telemetry continues"));
  }
}

void serviceStorage(HealthState& health, uint32_t nowMs) {
  if (!ready && static_cast<uint32_t>(nowMs - lastAttemptMs) >=
                    SD_RETRY_INTERVAL_MS) {
    lastAttemptMs = nowMs;
    SD.end();
    ready = startNewLog();
    health.sdOk = ready;
  }
}

bool storageIsReady() { return ready; }

bool appendStorageRow(const char* row, HealthState& health, uint32_t nowMs) {
  if (!ready) {
    health.sdOk = false;
    return false;
  }

  File file = SD.open(filename, FILE_WRITE);
  if (!file) {
    ready = false;
    health.sdOk = false;
    lastAttemptMs = nowMs;
    return false;
  }

  const size_t rowLength = strlen(row);
  const bool wroteRow = file.write(reinterpret_cast<const uint8_t*>(row),
                                   rowLength) == rowLength;
  const bool wroteNewline = file.write('\n') == 1;
  file.flush();
  file.close();

  ready = wroteRow && wroteNewline;
  health.sdOk = ready;
  if (ready) {
    health.lastSdSuccessMs = nowMs;
  } else {
    lastAttemptMs = nowMs;
  }
  return ready;
}

const char* storageFilename() { return filename; }

