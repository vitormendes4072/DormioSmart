#ifndef STUB_WCS_H
#define STUB_WCS_H
#include "Arduino.h"
class WiFiClientSecure {
 public:
  void setInsecure() {}
  void setCACert(const char *) {}
  void setTimeout(uint32_t) {}
  void stop() {}
  uint8_t connected() { return 0; }
};
#endif
