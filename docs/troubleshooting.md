# Troubleshooting

Isolate the path in this order: sensor/I2C → Mega USB CSV → SD → airborne HC-12 → ground HC-12/Uno USB → PC parser.

## Arduino library errors

- `Adafruit_AHTX0.h`: install **Adafruit AHTX0**
- `Adafruit_BMP280.h`: install **Adafruit BMP280 Library**
- `Adafruit_MPU6050.h` or `Adafruit_Sensor.h`: install **Adafruit MPU6050** and **Adafruit Unified Sensor**
- `TinyGPS++.h`: install **TinyGPSPlus**
- `RTClib.h`: install **RTClib**, but only enable it after the RTC is confirmed DS3231-compatible

## I2C sensor is unavailable

Check SDA=D20, SCL=D21 and common GND. Read the startup ACK lines. AHT20 should be 0x38; BMP280 is probed at 0x76/0x77; firmware expects MPU6050 at 0x69. If a verified RTC is 0x68, MPU AD0 must be HIGH. Check pull-up voltage before reconnecting.

The firmware retries a failed sensor every 10 seconds without stopping other subsystems.

## RTC stays `rtc_ok=0`

This is expected with the default `RTC_DRIVER_DISABLED`. Do not infer the IC from `DM941`. Identify the IC and address, check the board datasheet/silkscreen, and only then select a compatible driver. A DS3231-compatible device that reports lost power must be set to a trusted time before its timestamp is accepted.

## GNSS stays `gps_ok=0`

NEO-M8N TX goes to Mega RX1/D19. Confirm its NMEA baud equals 9600, test outdoors with open sky, and wait for a fix. Location, altitude, speed and course must all be valid and no older than 3 seconds. `gps_speed_mps` is ground speed, not wind.

## SD unavailable

Confirm FAT16/FAT32, MISO D50, MOSI D51, SCK D52 and CS D4. Verify the module has suitable 3.3 V regulation and Mega-safe level shifting. SD failure does not stop HC-12; firmware retries after 5 seconds with a new `FLIGHTnn.CSV`.

## PC receives no valid rows

The Uno USB port is opened at 115200 baud, while both HC-12 UARTs are configured at 9600 baud. Confirm crossed TX/RX, shared GND, RF channel/address/mode, and exact 23-column v3 newline framing. Use `python ground_station/main.py --list-ports` and then an explicit `--port COMn`.

Compare SD sequence numbers with PC sequence numbers. Continuous SD with PC gaps points to the radio/Uno/USB path; gaps in both suggest reset, power instability or a blocking peripheral operation.
