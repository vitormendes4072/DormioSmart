#ifndef STUB_HTTP_H
#define STUB_HTTP_H
#include "Arduino.h"
#include "WiFiClientSecure.h"
class HTTPClient {
 public:
  void begin(WiFiClientSecure &, const char *) {}
  void begin(WiFiClientSecure &, const String &) {}
  void addHeader(const char *, const char *) {}
  void setTimeout(uint16_t) {}
  int POST(const char *) { return 201; }
  int POST(const String &) { return 201; }
  String getString() { return String(""); }
  void end() {}
};
#endif
