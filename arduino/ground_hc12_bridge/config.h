#pragma once

#define SERIAL_BAUD_USB 115200UL
#define SERIAL_BAUD_HC12 9600UL
#define HC12_RX_PIN 10
#define HC12_TX_PIN 11

// Default is the requested receive-only HC-12 -> USB bridge.
#ifndef BRIDGE_USB_TO_HC12
#define BRIDGE_USB_TO_HC12 0
#endif
