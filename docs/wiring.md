# Wiring and power checklist

Disconnect power before wiring. Module names do not prove breakout-board supply or logic tolerance: **CHECK MODULE DATASHEET / BOARD SILKSCREEN**.

## Mega signal map

| subsystem | module signal | Mega 2560 | notes |
|---|---|---|---|
| AHT20/BMP280/MPU6050/RTC | SDA/SCL | D20/D21 | shared I2C bus |
| NEO-M8N | TX | RX1/D19 | receive path required |
| NEO-M8N | RX | TX1/D18 | optional; level-check before connecting |
| future Flight Controller | UART | Serial2 D17/D16 | reserved, not used by v3 runtime |
| HC-12 | TXD/RXD | RX3/D15, TX3/D14 | crossed UART, 9600 baud |
| microSD | MISO/MOSI/SCK | D50/D51/D52 | hardware SPI |
| microSD | CS | D4 | matches `SD_CS_PIN`; D53 remains OUTPUT |

I2C addresses: AHT20 `0x38`; BMP280 auto-detect `0x76` then `0x77`; MPU6050 configured `0x69`; RTC configured only after the actual IC/address is verified. If the RTC is `0x68`, set MPU6050 AD0 HIGH so it uses `0x69`. Startup prints an ACK summary and a configured collision warning.

The module marked `DM941` is **not assumed** to be DS3231. Default firmware leaves RTC disabled. Confirm the IC marking, datasheet, board schematic/silkscreen and I2C scan before setting `RTC_DRIVER_DS3231_COMPATIBLE`.

## Uno bridge

| HC-12 | Arduino Uno |
|---|---|
| TXD | D10 (`SoftwareSerial` RX) |
| RXD | D11 (`SoftwareSerial` TX; unused in receive-only default) |
| GND | GND |

## Electrical safety

- Mega GPIO is 5 V logic. Sensor/radio ICs may be 3.3 V only.
- Confirm every breakout's allowed VCC and I/O voltage separately.
- Check I2C pull-up voltage; a 3.3 V sensor board may pull SDA/SCL to 3.3 V, while another board may pull to 5 V.
- Confirm NEO-M8N breakout input tolerance before connecting Mega TX1.
- Confirm HC-12 supply range and UART logic level for the exact board revision.
- An SD card is 3.3 V internally; use only a module whose regulator and level shifting are verified for Mega.
- A DC-DC converter regulates supply voltage. It is **not** a UART/I2C/SPI logic-level shifter.

## Power architecture

```text
battery/source
  ├─ regulated 5 V rail  → Mega/Uno and verified 5 V loads
  └─ regulated 3.3 V rail → verified 3.3 V-only modules
all rails and modules share common GND
```

Do not route all peripheral current through the Arduino regulator. Determine each real board's supply range and peak current, then size converters and wiring with margin. Keep HC-12 transmit-current transients and SD write transients in the power budget. Add a logic-level shifter only where the checked I/O specifications require it.
