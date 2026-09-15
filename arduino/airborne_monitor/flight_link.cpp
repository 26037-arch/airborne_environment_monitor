#include "flight_link.h"

#include <math.h>

#include "config.h"

#if POSITION_SOURCE == POSITION_SOURCE_FLIGHT_CONTROLLER
#include <mavlink.h>
#endif

static FlightStatus flightStatus;

static void clearFlightStatus() {
  flightStatus.connected = false;
  flightStatus.armed = false;
  flightStatus.attitudeValid = false;
  flightStatus.positionValid = false;
  flightStatus.motionValid = false;
  flightStatus.batteryValid = false;
  flightStatus.systemHealthValid = false;
  flightStatus.rollDeg = 0.0f;
  flightStatus.pitchDeg = 0.0f;
  flightStatus.yawDeg = 0.0f;
  flightStatus.latitude = 0.0;
  flightStatus.longitude = 0.0;
  flightStatus.gnssAltitudeM = 0.0f;
  flightStatus.estimatedAltitudeM = 0.0f;
  flightStatus.groundSpeedMps = 0.0f;
  flightStatus.verticalSpeedMps = 0.0f;
  flightStatus.batteryVoltage = 0.0f;
  flightStatus.batteryCurrent = 0.0f;
  flightStatus.flightMode = 0;
  flightStatus.systemHealth = 0;
  flightStatus.lastUpdateMs = 0;
}

void initializeFlightLink(uint32_t nowMs) {
  clearFlightStatus();
  flightStatus.lastUpdateMs = nowMs;
#if POSITION_SOURCE == POSITION_SOURCE_FLIGHT_CONTROLLER
  Serial2.begin(SERIAL_BAUD_FLIGHT_CONTROLLER);
  Serial.println(F("Flight link: MAVLink on Serial2"));
#else
  Serial.println(F("Flight link: disabled; direct GNSS on Serial2"));
#endif
}

#if POSITION_SOURCE == POSITION_SOURCE_FLIGHT_CONTROLLER
static void handleMessage(const mavlink_message_t& message, uint32_t nowMs) {
  flightStatus.connected = true;
  flightStatus.lastUpdateMs = nowMs;

  switch (message.msgid) {
    case MAVLINK_MSG_ID_HEARTBEAT: {
      mavlink_heartbeat_t value;
      mavlink_msg_heartbeat_decode(&message, &value);
      flightStatus.armed =
          (value.base_mode & MAV_MODE_FLAG_SAFETY_ARMED) != 0;
      flightStatus.flightMode = value.custom_mode;
      flightStatus.systemHealth = value.system_status;
      flightStatus.systemHealthValid = true;
      break;
    }
    case MAVLINK_MSG_ID_ATTITUDE: {
      mavlink_attitude_t value;
      mavlink_msg_attitude_decode(&message, &value);
      if (isfinite(value.roll) && isfinite(value.pitch) && isfinite(value.yaw)) {
        const float radiansToDegrees = 57.2957795f;
        flightStatus.rollDeg = value.roll * radiansToDegrees;
        flightStatus.pitchDeg = value.pitch * radiansToDegrees;
        flightStatus.yawDeg = value.yaw * radiansToDegrees;
        if (flightStatus.yawDeg < 0.0f) flightStatus.yawDeg += 360.0f;
        flightStatus.attitudeValid = true;
      }
      break;
    }
    case MAVLINK_MSG_ID_GLOBAL_POSITION_INT: {
      mavlink_global_position_int_t value;
      mavlink_msg_global_position_int_decode(&message, &value);
      const double latitude = value.lat / 10000000.0;
      const double longitude = value.lon / 10000000.0;
      if (latitude >= -90.0 && latitude <= 90.0 &&
          longitude >= -180.0 && longitude <= 180.0) {
        flightStatus.latitude = latitude;
        flightStatus.longitude = longitude;
        flightStatus.gnssAltitudeM = value.alt / 1000.0f;
        flightStatus.estimatedAltitudeM = value.relative_alt / 1000.0f;
        flightStatus.positionValid = true;
      }
      const float velocityNorth = value.vx / 100.0f;
      const float velocityEast = value.vy / 100.0f;
      const float verticalDown = value.vz / 100.0f;
      if (isfinite(velocityNorth) && isfinite(velocityEast) &&
          isfinite(verticalDown)) {
        flightStatus.groundSpeedMps =
            sqrtf(velocityNorth * velocityNorth + velocityEast * velocityEast);
        flightStatus.verticalSpeedMps = -verticalDown;
        flightStatus.motionValid = true;
      }
      break;
    }
    case MAVLINK_MSG_ID_SYS_STATUS: {
      mavlink_sys_status_t value;
      mavlink_msg_sys_status_decode(&message, &value);
      flightStatus.systemHealth = value.onboard_control_sensors_health;
      flightStatus.systemHealthValid = true;
      if (value.voltage_battery != UINT16_MAX && value.current_battery != -1) {
        flightStatus.batteryVoltage = value.voltage_battery / 1000.0f;
        flightStatus.batteryCurrent = value.current_battery / 100.0f;
        flightStatus.batteryValid = true;
      } else {
        flightStatus.batteryValid = false;
      }
      break;
    }
  }
}
#endif

void pollFlightLink(uint32_t nowMs) {
#if POSITION_SOURCE == POSITION_SOURCE_FLIGHT_CONTROLLER
  static mavlink_message_t message;
  static mavlink_status_t parserStatus;
  while (Serial2.available() > 0) {
    const uint8_t byteValue = static_cast<uint8_t>(Serial2.read());
    if (mavlink_parse_char(MAVLINK_COMM_0, byteValue, &message, &parserStatus)) {
      handleMessage(message, nowMs);
    }
  }
#else
  (void)nowMs;
#endif
}

void serviceFlightLink(uint32_t nowMs) {
  if (flightStatus.connected &&
      static_cast<uint32_t>(nowMs - flightStatus.lastUpdateMs) >
          FLIGHT_LINK_TIMEOUT_MS) {
    flightStatus.connected = false;
    flightStatus.armed = false;
    flightStatus.attitudeValid = false;
    flightStatus.positionValid = false;
    flightStatus.motionValid = false;
    flightStatus.batteryValid = false;
  }
}

const FlightStatus& currentFlightStatus() { return flightStatus; }

bool flightControllerPositionEnabled() {
#if POSITION_SOURCE == POSITION_SOURCE_FLIGHT_CONTROLLER
  return true;
#else
  return false;
#endif
}

void applyFlightStatusToMeasurement(Measurement& measurement,
                                    HealthState& health, uint32_t nowMs) {
#if POSITION_SOURCE == POSITION_SOURCE_FLIGHT_CONTROLLER
  const bool valid = flightStatus.connected && flightStatus.positionValid &&
                     flightStatus.motionValid && flightStatus.attitudeValid;
  if (valid) {
    measurement.latitude = flightStatus.latitude;
    measurement.longitude = flightStatus.longitude;
    measurement.gpsAltitudeM = flightStatus.gnssAltitudeM;
    measurement.gpsSpeedMps = flightStatus.groundSpeedMps;
    measurement.gpsCourseDeg = flightStatus.yawDeg;
    measurement.gpsValuesValid = true;
    health.gpsOk = true;
    health.lastGpsSuccessMs = nowMs;
  } else {
    measurement.gpsValuesValid = false;
    health.gpsOk = false;
  }
  measurement.gpsOk = health.gpsOk;
#else
  (void)measurement;
  (void)health;
  (void)nowMs;
#endif
}

