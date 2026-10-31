#ifndef STUB_ESP_TIMER_H
#define STUB_ESP_TIMER_H
#include <stdint.h>
// Microssegundos desde o boot; no ESP32 continua contando no sono leve.
inline int64_t esp_timer_get_time() { return 0; }
#endif
