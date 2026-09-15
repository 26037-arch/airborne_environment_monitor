#include "telemetry.h"

#include <string.h>

static bool appendText(char* output, size_t outputSize, size_t& used,
                       const char* text) {
  const size_t length = strlen(text);
  if (used + length >= outputSize) {
    if (outputSize > 0) output[outputSize - 1] = '\0';
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
  const int written = snprintf(
      token, sizeof(token), "%lu", static_cast<unsigned long>(value));
  return written > 0 && static_cast<size_t>(written) < sizeof(token) &&
      appendText(output, outputSize, used, token);
}

static bool appendFloat(char* output, size_t outputSize, size_t& used,
                        double value, uint8_t decimals, bool valid) {
  if (!valid) return appendText(output, outputSize, used, "NA");
  char token[24];
  dtostrf(value, 0, decimals, token);
  const char* first = token;
  while (*first == ' ') ++first;
  return appendText(output, outputSize, used, first);
}

bool formatCsvRowV3(const Measurement& m, char* output, size_t outputSize) {
  if (output == NULL || outputSize == 0) return false;
  output[0] = '\0';
  size_t used = 0;

#define APPEND_OR_FAIL(expression) do { if (!(expression)) return false; } while (0)
#define COMMA() APPEND_OR_FAIL(appendComma(output, outputSize, used))
#define FLOAT_FIELD(value, decimals, valid)                                  \
  do { COMMA(); APPEND_OR_FAIL(appendFloat(                                  \
      output, outputSize, used, value, decimals, valid)); } while (0)
#define FLAG_FIELD(value)                                                    \
  do { COMMA(); APPEND_OR_FAIL(appendText(                                   \
      output, outputSize, used, (value) ? "1" : "0")); } while (0)

  APPEND_OR_FAIL(appendUnsigned(output, outputSize, used, m.seq));
  COMMA();
  APPEND_OR_FAIL(appendUnsigned(output, outputSize, used, m.timeMs));
  FLOAT_FIELD(m.temperatureC, 2, m.ahtValuesValid);
  FLOAT_FIELD(m.humidityPct, 2, m.ahtValuesValid);
  FLOAT_FIELD(m.pressureHpa, 2, m.bmpValuesValid);
  FLOAT_FIELD(m.barometricAltitudeM, 2, m.bmpValuesValid);
  FLOAT_FIELD(m.latitude, 6, m.gpsValuesValid);
  FLOAT_FIELD(m.longitude, 6, m.gpsValuesValid);
  FLOAT_FIELD(m.gpsAltitudeM, 2, m.gpsValuesValid);
  FLOAT_FIELD(m.gpsSpeedMps, 2, m.gpsValuesValid);
  FLOAT_FIELD(m.gpsCourseDeg, 2, m.gpsValuesValid);
  FLOAT_FIELD(m.accelXMps2, 3, m.imuValuesValid);
  FLOAT_FIELD(m.accelYMps2, 3, m.imuValuesValid);
  FLOAT_FIELD(m.accelZMps2, 3, m.imuValuesValid);
  FLOAT_FIELD(m.gyroXDps, 3, m.imuValuesValid);
  FLOAT_FIELD(m.gyroYDps, 3, m.imuValuesValid);
  FLOAT_FIELD(m.gyroZDps, 3, m.imuValuesValid);
  COMMA();
  if (m.rtcValueValid) {
    APPEND_OR_FAIL(appendUnsigned(output, outputSize, used, m.rtcUnixTime));
  } else {
    APPEND_OR_FAIL(appendText(output, outputSize, used, "NA"));
  }
  FLAG_FIELD(m.envOk);
  FLAG_FIELD(m.imuOk);
  FLAG_FIELD(m.gpsOk);
  FLAG_FIELD(m.rtcOk);
  FLAG_FIELD(m.sdOk);

#undef FLAG_FIELD
#undef FLOAT_FIELD
#undef COMMA
#undef APPEND_OR_FAIL
  return true;
}

void sendTelemetryRow(const char* row) {
  Serial3.print(row);
  Serial3.write('\n');
}
