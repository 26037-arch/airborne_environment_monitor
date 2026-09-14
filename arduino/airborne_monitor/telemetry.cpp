#include "telemetry.h"

#include <stdlib.h>
#include <string.h>

static bool appendText(char* output, size_t outputSize, size_t& used,
                       const char* text) {
  const size_t length = strlen(text);
  if (used + length >= outputSize) {
    if (outputSize > 0) {
      output[outputSize - 1] = '\0';
    }
    return false;
  }
  memcpy(output + used, text, length);
  used += length;
  output[used] = '\0';
  return true;
}

static bool appendComma(char* output, size_t outputSize, size_t& used) {
  return appendText(output, outputSize, used, ",");
}

static bool appendUnsigned(char* output, size_t outputSize, size_t& used,
                           uint32_t value) {
  char token[16];
  snprintf(token, sizeof(token), "%lu", static_cast<unsigned long>(value));
  return appendText(output, outputSize, used, token);
}

static bool appendFloat(char* output, size_t outputSize, size_t& used,
                        double value, uint8_t decimals, bool valid) {
  if (!valid) {
    return appendText(output, outputSize, used, "NA");
  }
  char token[24];
  dtostrf(value, 0, decimals, token);
  const char* first = token;
  while (*first == ' ') {
    ++first;
  }
  return appendText(output, outputSize, used, first);
}

bool formatCsvRow(const Measurement& m, char* output, size_t outputSize) {
  if (output == NULL || outputSize == 0) {
    return false;
  }
  output[0] = '\0';
  size_t used = 0;

#define APPEND_OR_FAIL(expression) \
  do {                              \
    if (!(expression)) return false; \
  } while (0)
#define COMMA() APPEND_OR_FAIL(appendComma(output, outputSize, used))

  APPEND_OR_FAIL(appendUnsigned(output, outputSize, used, m.seq));
  COMMA();
  APPEND_OR_FAIL(appendUnsigned(output, outputSize, used, m.timeMs));
  COMMA();
  APPEND_OR_FAIL(appendFloat(output, outputSize, used, m.temperatureC, 2,
                             m.bmeValuesValid));
  COMMA();
  APPEND_OR_FAIL(appendFloat(output, outputSize, used, m.humidityPct, 2,
                             m.bmeValuesValid));
  COMMA();
  APPEND_OR_FAIL(appendFloat(output, outputSize, used, m.pressureHpa, 2,
                             m.bmeValuesValid));
  COMMA();
  APPEND_OR_FAIL(
      appendFloat(output, outputSize, used, m.pm1Ugm3, 2, m.spsValuesValid));
  COMMA();
  APPEND_OR_FAIL(
      appendFloat(output, outputSize, used, m.pm25Ugm3, 2, m.spsValuesValid));
  COMMA();
  APPEND_OR_FAIL(
      appendFloat(output, outputSize, used, m.pm4Ugm3, 2, m.spsValuesValid));
  COMMA();
  APPEND_OR_FAIL(
      appendFloat(output, outputSize, used, m.pm10Ugm3, 2, m.spsValuesValid));
  COMMA();
  APPEND_OR_FAIL(appendFloat(output, outputSize, used, m.latitude, 6,
                             m.gpsValuesValid));
  COMMA();
  APPEND_OR_FAIL(appendFloat(output, outputSize, used, m.longitude, 6,
                             m.gpsValuesValid));
  COMMA();
  APPEND_OR_FAIL(appendFloat(output, outputSize, used, m.gpsAltitudeM, 2,
                             m.gpsValuesValid));
  COMMA();
  APPEND_OR_FAIL(appendFloat(output, outputSize, used, m.gpsSpeedMps, 2,
                             m.gpsValuesValid));
  COMMA();
  APPEND_OR_FAIL(appendFloat(output, outputSize, used, m.gpsCourseDeg, 2,
                             m.gpsValuesValid));
  COMMA();
  APPEND_OR_FAIL(appendText(output, outputSize, used, m.bmeOk ? "1" : "0"));
  COMMA();
  APPEND_OR_FAIL(appendText(output, outputSize, used, m.spsOk ? "1" : "0"));
  COMMA();
  APPEND_OR_FAIL(appendText(output, outputSize, used, m.gpsOk ? "1" : "0"));
  COMMA();
  APPEND_OR_FAIL(appendText(output, outputSize, used, m.sdOk ? "1" : "0"));

#undef COMMA
#undef APPEND_OR_FAIL
  return true;
}

void sendTelemetryRow(const char* row) { Serial3.println(row); }

