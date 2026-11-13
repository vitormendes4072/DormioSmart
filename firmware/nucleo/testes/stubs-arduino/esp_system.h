#ifndef STUB_ESP_SYSTEM_H
#define STUB_ESP_SYSTEM_H
#include <stdint.h>
// O heap do ESP32 (FW-13): no host nao ha heap do chip; o log do envio so
// precisa que as funcoes existam.
inline uint32_t esp_get_free_heap_size() { return 0; }
inline uint32_t esp_get_minimum_free_heap_size() { return 0; }
#endif
