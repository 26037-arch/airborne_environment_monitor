#include "sensors.h"

#include <math.h>

#include "config.h"

#if !MOCK_SENSORS
#include <Adafruit_BME280.h>
#include <SensirionUartSps30.h>
#if POSITION_SOURCE == POSITION_SOURCE_DIRECT_GNSS
#include <TinyGPS++.h>
#endif
#include <Wire.h>

static Adafruit_BME280 bme;
static SensirionUartSps30 sps30;
#if POSITION_SOURCE == POSITION_SOURCE_DIRECT_GNSS
static TinyGPSPlus gps;
#endif
#endif

static bool bmeInitialized = false;
static SpsState spsState = SPS_STATE_ERROR;
static uint32_t spsStartedMs = 0;
#if !MOCK_SENSORS
static uint32_t lastBmeAttemptMs = 0;
static uint32_t lastSpsAttemptMs = 0;
#endif

void clearMeasurement(Measurement& m, uint32_t seq, uint32_t nowMs) {
  m.seq = seq;
  m.timeMs = nowMs;
  m.temperatureC = 0.0f;
  m.humidityPct = 0.0f;
  m.pressureHpa = 0.0f;
  m.bmeValuesValid = false;
  m.pm1Ugm3 = 0.0f;
  m.pm25Ugm3 = 0.0f;
  m.pm4Ugm3 = 0.0f;
  m.pm10Ugm3 = 0.0f;
  m.spsValuesValid = false;
  m.latitude = 0.0;
  m.longitude = 0.0;
  m.gpsAltitudeM = 0.0f;
  m.gpsSpeedMps = 0.0f;
  m.gpsCourseDeg = 0.0f;
  m.gpsValuesValid = false;
  m.bmeOk = false;
  m.spsOk = false;
  m.gpsOk = false;
  m.sdOk = false;
}

#if !MOCK_SENSORS
static bool tryInitializeBme() {
  if (bme.begin(BME280_ADDRESS_PRIMARY, &Wire)) {
    return true;
  }
  return bme.begin(BME280_ADDRESS_SECONDARY, &Wire);
}

static bool tryStartSps(uint32_t nowMs) {
  // 전원이 다시 들어온 경우에도 Idle 상태로 만든 뒤 float 출력을 시작합니다.
  sps30.stopMeasurement();
  const int16_t error =
      sps30.startMeasurement(SPS30_OUTPUT_FORMAT_OUTPUT_FORMAT_FLOAT);
  if (error == 0) {
    spsState = SPS_STATE_WARMUP;
    spsStartedMs = nowMs;
    return true;
  }
  spsState = SPS_STATE_ERROR;
  return false;
}
#endif

void initializeSensors(HealthState& health, uint32_t nowMs) {
#if MOCK_SENSORS
  bmeInitialized = true;
  spsState = SPS_STATE_WARMUP;
  spsStartedMs = nowMs;
  health.bmeOk = true;
  health.spsOk = false;
  health.gpsOk = true;
  Serial.println(F("Sensors: MOCK mode"));
#else
  Wire.begin();
  Serial1.begin(SERIAL_BAUD_SPS30);
#if POSITION_SOURCE == POSITION_SOURCE_DIRECT_GNSS
  Serial2.begin(SERIAL_BAUD_GNSS);
#endif

  lastBmeAttemptMs = nowMs;
  bmeInitialized = tryInitializeBme();
  health.bmeOk = bmeInitialized;
  Serial.println(bmeInitialized ? F("BME280: ready") : F("BME280: not found"));

  sps30.begin(Serial1);
  lastSpsAttemptMs = nowMs;
  const bool spsStarted = tryStartSps(nowMs);
  health.spsOk = false;  // warm-up이 끝나고 첫 읽기에 성공해야 true
  Serial.println(spsStarted ? F("SPS30: warming up") : F("SPS30: start failed"));
#endif
}

void pollGnss() {
#if !MOCK_SENSORS && POSITION_SOURCE == POSITION_SOURCE_DIRECT_GNSS
  while (Serial2.available() > 0) {
    gps.encode(static_cast<char>(Serial2.read()));
  }
#endif
}

void serviceSensors(HealthState& health, uint32_t nowMs) {
#if MOCK_SENSORS
  if (spsState == SPS_STATE_WARMUP &&
      static_cast<uint32_t>(nowMs - spsStartedMs) >= SPS30_WARMUP_MS) {
    spsState = SPS_STATE_READY;
    health.spsOk = true;
  }
#else
  if (!bmeInitialized &&
      static_cast<uint32_t>(nowMs - lastBmeAttemptMs) >=
          SENSOR_RETRY_INTERVAL_MS) {
    lastBmeAttemptMs = nowMs;
    bmeInitialized = tryInitializeBme();
    health.bmeOk = bmeInitialized;
  }

  if (spsState == SPS_STATE_WARMUP &&
      static_cast<uint32_t>(nowMs - spsStartedMs) >= SPS30_WARMUP_MS) {
    spsState = SPS_STATE_READY;
  }

  if (spsState == SPS_STATE_ERROR &&
      static_cast<uint32_t>(nowMs - lastSpsAttemptMs) >=
          SENSOR_RETRY_INTERVAL_MS) {
    lastSpsAttemptMs = nowMs;
    tryStartSps(nowMs);
    health.spsOk = false;
  }
#endif
}

void sampleSensors(Measurement& m, HealthState& health, uint32_t nowMs) {
#if MOCK_SENSORS
  const float t = nowMs / 1000.0f;
  m.temperatureC = 20.0f + 2.0f * sinf(t / 25.0f);
  m.humidityPct = 52.0f + 4.0f * sinf(t / 31.0f);
  m.pressureHpa = 1012.0f - 0.12f * t + 0.8f * sinf(t / 18.0f);
  m.bmeValuesValid = true;
  health.bmeOk = true;
  health.lastBmeSuccessMs = nowMs;

  if (spsState == SPS_STATE_READY) {
    m.pm1Ugm3 = 3.0f + sinf(t / 7.0f);
    m.pm25Ugm3 = 5.0f + 1.5f * sinf(t / 9.0f);
    m.pm4Ugm3 = 6.0f + 1.8f * sinf(t / 10.0f);
    m.pm10Ugm3 = 8.0f + 2.0f * sinf(t / 12.0f);
    m.spsValuesValid = true;
    health.spsOk = true;
    health.lastSpsSuccessMs = nowMs;
  }

  m.latitude = 37.123456 + 0.00001 * sin(t / 30.0f);
  m.longitude = 127.123456 + 0.00001 * cos(t / 30.0f);
  m.gpsAltitudeM = 100.0f + 0.6f * t + 3.0f * sinf(t / 12.0f);
  m.gpsSpeedMps = 3.0f + 0.5f * sinf(t / 8.0f);
  m.gpsCourseDeg = fmod(t * 2.0f, 360.0f);
  m.gpsValuesValid = true;
  health.gpsOk = true;
  health.lastGpsSuccessMs = nowMs;
#else
  if (bmeInitialized) {
    const float temperature = bme.readTemperature();
    const float humidity = bme.readHumidity();
    const float pressureHpa = bme.readPressure() / 100.0f;
    if (isfinite(temperature) && isfinite(humidity) && isfinite(pressureHpa) &&
        temperature >= -100.0f && temperature <= 150.0f &&
        humidity >= 0.0f && humidity <= 100.5f && pressureHpa > 0.0f &&
        pressureHpa < 2000.0f) {
      m.temperatureC = temperature;
      m.humidityPct = humidity;
      m.pressureHpa = pressureHpa;
      m.bmeValuesValid = true;
      health.bmeOk = true;
      health.lastBmeSuccessMs = nowMs;
    } else {
      bmeInitialized = false;
      health.bmeOk = false;
      lastBmeAttemptMs = nowMs;
    }
  }

  if (spsState == SPS_STATE_READY) {
    float nc05, nc1, nc25, nc4, nc10, typicalSize;
    const int16_t error = sps30.readMeasurementValuesFloat(
        m.pm1Ugm3, m.pm25Ugm3, m.pm4Ugm3, m.pm10Ugm3, nc05, nc1,
        nc25, nc4, nc10, typicalSize);
    const bool valuesReasonable =
        isfinite(m.pm1Ugm3) && isfinite(m.pm25Ugm3) && isfinite(m.pm4Ugm3) &&
        isfinite(m.pm10Ugm3) && m.pm1Ugm3 >= 0.0f && m.pm25Ugm3 >= 0.0f &&
        m.pm4Ugm3 >= 0.0f && m.pm10Ugm3 >= 0.0f &&
        m.pm1Ugm3 < 100000.0f && m.pm25Ugm3 < 100000.0f &&
        m.pm4Ugm3 < 100000.0f && m.pm10Ugm3 < 100000.0f;
    if (error == 0 && valuesReasonable) {
      m.spsValuesValid = true;
      health.spsOk = true;
      health.lastSpsSuccessMs = nowMs;
    } else {
      spsState = SPS_STATE_ERROR;
      lastSpsAttemptMs = nowMs;
      health.spsOk = false;
    }
  }

#if POSITION_SOURCE == POSITION_SOURCE_DIRECT_GNSS
  const bool gpsFresh = gps.location.isValid() && gps.altitude.isValid() &&
                        gps.speed.isValid() && gps.course.isValid() &&
                        gps.location.age() <= GPS_MAX_AGE_MS &&
                        gps.altitude.age() <= GPS_MAX_AGE_MS &&
                        gps.speed.age() <= GPS_MAX_AGE_MS &&
                        gps.course.age() <= GPS_MAX_AGE_MS;
  if (gpsFresh) {
    const double latitude = gps.location.lat();
    const double longitude = gps.location.lng();
    const float altitude = static_cast<float>(gps.altitude.meters());
    const float speed = static_cast<float>(gps.speed.mps());
    const float course = static_cast<float>(gps.course.deg());
    if (isfinite(latitude) && isfinite(longitude) && isfinite(altitude) &&
        isfinite(speed) && isfinite(course) && latitude >= -90.0 &&
        latitude <= 90.0 && longitude >= -180.0 && longitude <= 180.0 &&
        speed >= 0.0f && course >= 0.0f && course <= 360.0f) {
      m.latitude = latitude;
      m.longitude = longitude;
      m.gpsAltitudeM = altitude;
      m.gpsSpeedMps = speed;
      m.gpsCourseDeg = course;
      m.gpsValuesValid = true;
      health.gpsOk = true;
      health.lastGpsSuccessMs = nowMs;
    } else {
      health.gpsOk = false;
    }
  } else {
    health.gpsOk = false;
  }
#endif
#endif

  m.bmeOk = health.bmeOk;
  m.spsOk = health.spsOk;
  m.gpsOk = health.gpsOk;
}

SpsState getSpsState() { return spsState; }
