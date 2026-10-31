#ifndef STUB_ESP_PARTITION_H
#define STUB_ESP_PARTITION_H
// Stub da API de particoes do ESP-IDF, so com o que `midia_flash_esp32.h`
// usa. Serve para o `make sintaxe` conferir tipos e assinaturas; nao simula
// flash nenhuma (a simulacao da NOR esta em testes/testes_fila_flash.cpp).
#include <stddef.h>
#include <stdint.h>
typedef int esp_err_t;
#define ESP_OK 0
typedef enum { ESP_PARTITION_TYPE_APP = 0x00, ESP_PARTITION_TYPE_DATA = 0x01 } esp_partition_type_t;
typedef enum { ESP_PARTITION_SUBTYPE_ANY = 0xff } esp_partition_subtype_t;
typedef struct {
  esp_partition_type_t type;
  esp_partition_subtype_t subtype;
  uint32_t address;
  uint32_t size;
  char label[17];
} esp_partition_t;
inline const esp_partition_t *esp_partition_find_first(esp_partition_type_t, esp_partition_subtype_t,
                                                       const char *) { return 0; }
inline esp_err_t esp_partition_read(const esp_partition_t *, size_t, void *, size_t) { return ESP_OK; }
inline esp_err_t esp_partition_write(const esp_partition_t *, size_t, const void *, size_t) {
  return ESP_OK;
}
inline esp_err_t esp_partition_erase_range(const esp_partition_t *, size_t, size_t) { return ESP_OK; }
#endif
