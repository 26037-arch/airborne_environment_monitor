# Arduino Uno HC-12 ground bridge

The Uno performs no CSV parsing, logging, or sensor calculations. It forwards
every received HC-12 byte to USB Serial.

| Signal | Uno pin |
|---|---|
| HC-12 TXD | D10 (`SoftwareSerial` RX) |
| HC-12 RXD | D11 (`SoftwareSerial` TX) |
| HC-12 GND | GND |

USB uses 115200 baud. Both airborne and ground HC-12 UARTs use 9600 baud. The
default is receive-only; set `BRIDGE_USB_TO_HC12=1` only if a bidirectional
transparent bridge is needed.

Verify the exact HC-12 board supply and UART logic specifications before
wiring. A DC-DC regulator is not a logic-level shifter.
