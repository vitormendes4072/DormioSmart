#ifndef STUB_WIFI_H
#define STUB_WIFI_H
#include "Arduino.h"

#define WL_CONNECTED 3
#define WIFI_STA 1
#define WIFI_OFF 0

class IPAddressStub {
 public:
  String toString() const { return String("0.0.0.0"); }
};

// FW-16: o sketch resolve o nome do servidor de NTP antes do `configTime`.
class IPAddress {
 public:
  IPAddress() : v_(0) {}
  explicit IPAddress(uint32_t v) : v_(v) {}
  uint8_t operator[](int i) const { return static_cast<uint8_t>(v_ >> (8 * i)); }
  bool operator==(const IPAddress &o) const { return v_ == o.v_; }
 private:
  uint32_t v_;
};

class WiFiStub {
 public:
  // Como o core 3.3.12: 1 e sucesso (a falha devolve o codigo do erro, que NAO e 0).
  int hostByName(const char *, IPAddress &ip) { ip = IPAddress(0x04030201u); return 1; }
  int status() { return WL_CONNECTED; }
  void begin(const char *, const char *) {}
  void disconnect() {}
  bool disconnect(bool, bool = false) { return true; }
  void mode(int) {}
  IPAddressStub localIP() { return IPAddressStub(); }
};
extern WiFiStub WiFi;
#endif
