#ifndef STUB_FREERTOS_H
#define STUB_FREERTOS_H
// Stub do FreeRTOS do ESP-IDF, so com o que o `sketch.ino` usa (FW-07 b).
// Assinaturas do ESP-IDF; nada aqui agenda tarefa nenhuma.
#include <stdint.h>
typedef void *TaskHandle_t;
typedef void *SemaphoreHandle_t;
typedef uint32_t TickType_t;
typedef int BaseType_t;
typedef unsigned UBaseType_t;
#define pdTRUE 1
#define pdFALSE 0
#define pdPASS 1
#define portMAX_DELAY ((TickType_t)0xffffffffu)
#define pdMS_TO_TICKS(ms) ((TickType_t)(ms))
#endif
