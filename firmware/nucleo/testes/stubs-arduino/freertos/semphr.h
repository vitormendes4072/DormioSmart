#ifndef STUB_FREERTOS_SEMPHR_H
#define STUB_FREERTOS_SEMPHR_H
#include "FreeRTOS.h"
inline SemaphoreHandle_t xSemaphoreCreateMutex() { return 0; }
inline BaseType_t xSemaphoreTake(SemaphoreHandle_t, TickType_t) { return pdTRUE; }
inline BaseType_t xSemaphoreGive(SemaphoreHandle_t) { return pdTRUE; }
#endif
