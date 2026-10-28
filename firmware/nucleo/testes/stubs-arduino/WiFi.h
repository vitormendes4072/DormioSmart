#ifndef STUB_WIFI_H
#define STUB_WIFI_H
#include "Arduino.h"

#define WL_CONNECTED 3
#define WIFI_STA 1

class IPAddressStub {
 public:
  String toString() const { return String("0.0.0.0"); }
};

class WiFiStub {
 public:
  int status() { return WL_CONNECTED; }
  void begin(const char *, const char *) {}
  void disconnect() {}
  void mode(int) {}
  IPAddressStub localIP() { return IPAddressStub(); }
};
extern WiFiStub WiFi;
#endif
