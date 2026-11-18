#ifndef STUB_FREERTOS_TASK_H
#define STUB_FREERTOS_TASK_H
#include "FreeRTOS.h"
typedef void (*TaskFunction_t)(void *);
inline BaseType_t xTaskCreatePinnedToCore(TaskFunction_t, const char *, const uint32_t, void *,
                                          UBaseType_t, TaskHandle_t *, const BaseType_t) {
  return pdPASS;
}
inline void vTaskDelay(const TickType_t) {}
inline void vTaskDelete(TaskHandle_t) {}
inline BaseType_t xTaskNotifyGive(TaskHandle_t) { return pdPASS; }
inline uint32_t ulTaskNotifyTake(BaseType_t, TickType_t) { return 0; }
// No ESP-IDF a marca d'agua da pilha vem em BYTES (no FreeRTOS puro, em
// palavras): o que nunca foi usado desde que a tarefa nasceu.
inline UBaseType_t uxTaskGetStackHighWaterMark(TaskHandle_t) { return 0; }
#endif
