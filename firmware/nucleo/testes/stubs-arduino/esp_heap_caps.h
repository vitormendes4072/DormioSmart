#ifndef STUB_ESP_HEAP_CAPS_H
#define STUB_ESP_HEAP_CAPS_H
#include <stddef.h>
// O maior bloco contiguo do heap (FW-14): o TLS precisa dele, nao do total.
#define MALLOC_CAP_8BIT (1 << 2)
inline size_t heap_caps_get_largest_free_block(unsigned) { return 0; }
#endif
