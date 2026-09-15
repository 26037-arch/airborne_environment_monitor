#include <SoftwareSerial.h>

#include "config.h"

SoftwareSerial hc12(HC12_RX_PIN, HC12_TX_PIN);

void setup() {
  Serial.begin(SERIAL_BAUD_USB);
  hc12.begin(SERIAL_BAUD_HC12);
}

void loop() {
  while (hc12.available() > 0) {
    Serial.write(hc12.read());
  }
#if BRIDGE_USB_TO_HC12
  while (Serial.available() > 0) {
    hc12.write(Serial.read());
  }
#endif
}
