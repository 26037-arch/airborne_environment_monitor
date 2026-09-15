#include "sensors.h"

#include <math.h>

#include "config.h"

#if !MOCK_SENSORS
#include <Adafruit_AHTX0.h>
#include <Adafruit_BMP280.h>
#include <Adafruit_MPU6050.h>
#include <Adafruit_Sensor.h>
#include <TinyGPS++.h>
#include <Wire.h>
#if RTC_DRIVER == RTC_DRIVER_DS3231_COMPATIBLE
#include <RTClib.h>
#endif

static Adafruit_AHTX0 aht;
static Adafruit_BMP280 bmp;
static Adafruit_MPU6050 mpu;
static TinyGPSPlus gps;
#if RTC_DRIVER == RTC_DRIVER_DS3231_COMPATIBLE
static RTC_DS3231 rtc;
#endif
#endif

static bool ahtInitialized = false;
static bool bmpInitialized = false;
static bool imuInitialized = false;
static bool rtcInitialized = false;
static uint32_t lastAhtAttemptMs = 0;
static uint32_t lastBmpAttemptMs = 0;
static uint32_t lastImuAttemptMs = 0;
static uint32_t lastRtcAttemptMs = 0;

void clearMeasurement(Measurement& m, uint32_t seq, uint32_t nowMs) {
  m.seq = seq;
  m.timeMs = nowMs;
  m.temperatureC = 0.0f;
  m.humidityPct = 0.0f;
  m.ahtValuesValid = false;
  m.pressureHpa = 0.0f;
  m.barometricAltitudeM = 0.0f;
  m.bmpValuesValid = false;
  m.latitude = 0.0;
  m.longitude = 0.0;
  m.gpsAltitudeM = 0.0f;
  m.gpsSpeedMps = 0.0f;
  m.gpsCourseDeg = 0.0f;
  m.gpsValuesValid = false;
  m.accelXMps2 = 0.0f;
  m.accelYMps2 = 0.0f;
  m.accelZMps2 = 0.0f;
  m.gyroXDps = 0.0f;
  m.gyroYDps = 0.0f;
  m.gyroZDps = 0.0f;
  m.imuValuesValid = false;
  m.rtcUnixTime = 0;
  m.rtcValueValid = false;
  m.envOk = false;
  m.imuOk = false;
  m.gpsOk = false;
  m.rtcOk = false;
  m.sdOk = false;
}

#if !MOCK_SENSORS
static bool i2cResponds(uint8_t address) {
  Wire.beginTransmission(address);
  return Wire.endTransmission() == 0;
}

static void printI2cProbe(const __FlashStringHelper* name, uint8_t address) {
  Serial.print(F("I2C "));
  Serial.print(name);
  Serial.print(F(" 0x"));
  if (address < 0x10) Serial.print('0');
  Serial.print(address, HEX);
  Serial.println(i2cResponds(address) ? F(": ACK") : F(": no ACK"));
}

static bool tryInitializeAht() { return aht.begin(&Wire); }

static bool tryInitializeBmp() {
  if (bmp.begin(BMP280_ADDRESS_PRIMARY)) return true;
  return bmp.begin(BMP280_ADDRESS_SECONDARY);
}

static bool tryInitializeImu() {
  if (!mpu.begin(MPU6050_I2C_ADDRESS, &Wire)) return false;
  mpu.setAccelerometerRange(MPU6050_RANGE_8_G);
  mpu.setGyroRange(MPU6050_RANGE_500_DEG);
  mpu.setFilterBandwidth(MPU6050_BAND_21_HZ);
  return true;
}

static bool tryInitializeRtc() {
#if RTC_DRIVER == RTC_DRIVER_DS3231_COMPATIBLE
  if (!rtc.begin(&Wire)) return false;
  if (rtc.lostPower()) {
    Serial.println(F("RTC: lost power; set time before trusting timestamps"));
    return false;
  }
  return true;
#else
  return false;
#endif
}
#endif

void initializeSensors(HealthState& health, uint32_t nowMs) {
#if MOCK_SENSORS
  ahtInitialized = bmpInitialized = imuInitialized = rtcInitialized = true;
  health.ahtOk = health.bmpOk = health.imuOk = true;
  health.gpsOk = health.rtcOk = true;
  Serial.println(F("Sensors: MOCK mode"));
#else
  Wire.begin();
  Serial1.begin(SERIAL_BAUD_GNSS);
  printI2cProbe(F("AHT20"), AHT20_I2C_ADDRESS);
  printI2cProbe(F("BMP280 primary"), BMP280_ADDRESS_PRIMARY);
  printI2cProbe(F("BMP280 secondary"), BMP280_ADDRESS_SECONDARY);
  printI2cProbe(F("MPU6050"), MPU6050_I2C_ADDRESS);
#if RTC_DRIVER == RTC_DRIVER_DS3231_COMPATIBLE
  printI2cProbe(F("RTC"), RTC_I2C_ADDRESS);
  if (MPU6050_I2C_ADDRESS == RTC_I2C_ADDRESS) {
    Serial.println(F("ERROR: configured MPU6050/RTC I2C address collision"));
  }
#else
  Serial.println(F("RTC: disabled until module IC/address is verified"));
#endif
  lastAhtAttemptMs = lastBmpAttemptMs = lastImuAttemptMs = nowMs;
  lastRtcAttemptMs = nowMs;
  ahtInitialized = tryInitializeAht();
  bmpInitialized = tryInitializeBmp();
  imuInitialized = tryInitializeImu();
  rtcInitialized = tryInitializeRtc();
  health.ahtOk = ahtInitialized;
  health.bmpOk = bmpInitialized;
  health.imuOk = imuInitialized;
  health.rtcOk = rtcInitialized;
  Serial.println(ahtInitialized ? F("AHT20: ready") : F("AHT20: not found"));
  Serial.println(bmpInitialized ? F("BMP280: ready") : F("BMP280: not found"));
  Serial.println(imuInitialized ? F("MPU6050: ready") : F("MPU6050: not found"));
  Serial.println(rtcInitialized ? F("RTC: ready") : F("RTC: unavailable"));
#endif
}

void pollGnss() {
#if !MOCK_SENSORS
  while (Serial1.available() > 0) {
    gps.encode(static_cast<char>(Serial1.read()));
  }
#endif
}

void serviceSensors(HealthState& health, uint32_t nowMs) {
#if !MOCK_SENSORS
#define RETRY_SENSOR(initialized, lastAttempt, initCall, healthField)         \
  do {                                                                        \
    if (!(initialized) &&                                                     \
        static_cast<uint32_t>(nowMs - (lastAttempt)) >=                       \
            SENSOR_RETRY_INTERVAL_MS) {                                       \
      (lastAttempt) = nowMs;                                                   \
      (initialized) = (initCall);                                             \
      health.healthField = (initialized);                                     \
    }                                                                         \
  } while (0)
  RETRY_SENSOR(ahtInitialized, lastAhtAttemptMs, tryInitializeAht(), ahtOk);
  RETRY_SENSOR(bmpInitialized, lastBmpAttemptMs, tryInitializeBmp(), bmpOk);
  RETRY_SENSOR(imuInitialized, lastImuAttemptMs, tryInitializeImu(), imuOk);
  RETRY_SENSOR(rtcInitialized, lastRtcAttemptMs, tryInitializeRtc(), rtcOk);
#undef RETRY_SENSOR
#else
  (void)health;
  (void)nowMs;
#endif
}

void sampleSensors(Measurement& m, HealthState& health, uint32_t nowMs) {
#if MOCK_SENSORS
  const float t = nowMs / 1000.0f;
  m.temperatureC = 20.0f + 2.0f * sinf(t / 25.0f);
  m.humidityPct = 52.0f + 4.0f * sinf(t / 31.0f);
  m.pressureHpa = 1012.0f - 0.12f * t;
  m.barometricAltitudeM = 44330.0f *
      (1.0f - powf(m.pressureHpa / SEA_LEVEL_PRESSURE_HPA, 0.1903f));
  m.ahtValuesValid = m.bmpValuesValid = true;
  m.latitude = 37.123456 + 0.00001 * sin(t / 30.0f);
  m.longitude = 127.123456 + 0.00001 * cos(t / 30.0f);
  m.gpsAltitudeM = 100.0f + 0.6f * t;
  m.gpsSpeedMps = 3.0f + 0.5f * sinf(t / 8.0f);
  m.gpsCourseDeg = fmod(t * 2.0f, 360.0f);
  m.gpsValuesValid = true;
  m.accelXMps2 = 0.03f * sinf(t);
  m.accelYMps2 = 0.03f * cosf(t);
  m.accelZMps2 = 9.80665f;
  m.gyroXDps = 0.2f * sinf(t / 2.0f);
  m.gyroYDps = 0.2f * cosf(t / 2.0f);
  m.gyroZDps = 2.0f;
  m.imuValuesValid = true;
  m.rtcUnixTime = MOCK_RTC_EPOCH_UNIX + nowMs / 1000UL;
  m.rtcValueValid = true;
  health.ahtOk = health.bmpOk = health.imuOk = true;
  health.gpsOk = health.rtcOk = true;
#else
  if (ahtInitialized) {
    sensors_event_t humidityEvent, temperatureEvent;
    if (aht.getEvent(&humidityEvent, &temperatureEvent) &&
        isfinite(temperatureEvent.temperature) &&
        isfinite(humidityEvent.relative_humidity) &&
        humidityEvent.relative_humidity >= 0.0f &&
        humidityEvent.relative_humidity <= 100.5f) {
      m.temperatureC = temperatureEvent.temperature;
      m.humidityPct = humidityEvent.relative_humidity;
      m.ahtValuesValid = true;
      health.ahtOk = true;
      health.lastAhtSuccessMs = nowMs;
    } else {
      ahtInitialized = false;
      health.ahtOk = false;
      lastAhtAttemptMs = nowMs;
    }
  }

  if (bmpInitialized) {
    const float pressure = bmp.readPressure() / 100.0f;
    const float altitude = bmp.readAltitude(SEA_LEVEL_PRESSURE_HPA);
    if (isfinite(pressure) && isfinite(altitude) && pressure > 0.0f &&
        pressure < 2000.0f) {
      m.pressureHpa = pressure;
      m.barometricAltitudeM = altitude;
      m.bmpValuesValid = true;
      health.bmpOk = true;
      health.lastBmpSuccessMs = nowMs;
    } else {
      bmpInitialized = false;
      health.bmpOk = false;
      lastBmpAttemptMs = nowMs;
    }
  }

  if (imuInitialized) {
    sensors_event_t acceleration, gyro, temperature;
    if (mpu.getEvent(&acceleration, &gyro, &temperature)) {
      const float radiansToDegrees = 57.2957795f;
      m.accelXMps2 = acceleration.acceleration.x - MPU_ACCEL_OFFSET_X_MPS2;
      m.accelYMps2 = acceleration.acceleration.y - MPU_ACCEL_OFFSET_Y_MPS2;
      m.accelZMps2 = acceleration.acceleration.z - MPU_ACCEL_OFFSET_Z_MPS2;
      m.gyroXDps = gyro.gyro.x * radiansToDegrees - MPU_GYRO_OFFSET_X_DPS;
      m.gyroYDps = gyro.gyro.y * radiansToDegrees - MPU_GYRO_OFFSET_Y_DPS;
      m.gyroZDps = gyro.gyro.z * radiansToDegrees - MPU_GYRO_OFFSET_Z_DPS;
      m.imuValuesValid = isfinite(m.accelXMps2) && isfinite(m.accelYMps2) &&
          isfinite(m.accelZMps2) && isfinite(m.gyroXDps) &&
          isfinite(m.gyroYDps) && isfinite(m.gyroZDps);
    }
    health.imuOk = m.imuValuesValid;
    if (m.imuValuesValid) {
      health.lastImuSuccessMs = nowMs;
    } else {
      imuInitialized = false;
      lastImuAttemptMs = nowMs;
    }
  }

  const bool gpsFresh = gps.location.isValid() && gps.altitude.isValid() &&
      gps.speed.isValid() && gps.course.isValid() &&
      gps.location.age() <= GPS_MAX_AGE_MS && gps.altitude.age() <= GPS_MAX_AGE_MS &&
      gps.speed.age() <= GPS_MAX_AGE_MS && gps.course.age() <= GPS_MAX_AGE_MS;
  if (gpsFresh) {
    m.latitude = gps.location.lat();
    m.longitude = gps.location.lng();
    m.gpsAltitudeM = static_cast<float>(gps.altitude.meters());
    m.gpsSpeedMps = static_cast<float>(gps.speed.mps());
    m.gpsCourseDeg = static_cast<float>(gps.course.deg());
    m.gpsValuesValid = isfinite(m.latitude) && isfinite(m.longitude) &&
        isfinite(m.gpsAltitudeM) && isfinite(m.gpsSpeedMps) &&
        isfinite(m.gpsCourseDeg) && m.latitude >= -90.0 && m.latitude <= 90.0 &&
        m.longitude >= -180.0 && m.longitude <= 180.0 &&
        m.gpsSpeedMps >= 0.0f && m.gpsCourseDeg >= 0.0f &&
        m.gpsCourseDeg <= 360.0f;
  }
  health.gpsOk = m.gpsValuesValid;
  if (m.gpsValuesValid) health.lastGpsSuccessMs = nowMs;

#if RTC_DRIVER == RTC_DRIVER_DS3231_COMPATIBLE
  if (rtcInitialized) {
    const DateTime value = rtc.now();
    if (value.isValid()) {
      m.rtcUnixTime = value.unixtime();
      m.rtcValueValid = true;
      health.rtcOk = true;
      health.lastRtcSuccessMs = nowMs;
    } else {
      rtcInitialized = false;
      health.rtcOk = false;
      lastRtcAttemptMs = nowMs;
    }
  }
#endif
#endif
  m.envOk = m.ahtValuesValid && m.bmpValuesValid;
  m.imuOk = m.imuValuesValid;
  m.gpsOk = m.gpsValuesValid;
  m.rtcOk = m.rtcValueValid;
}
