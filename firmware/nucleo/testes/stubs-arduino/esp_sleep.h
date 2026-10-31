#ifndef STUB_SLEEP_H
#define STUB_SLEEP_H
#include <stdint.h>
typedef enum { ESP_SLEEP_WAKEUP_UNDEFINED = 0, ESP_SLEEP_WAKEUP_EXT0 = 2, ESP_SLEEP_WAKEUP_EXT1 = 3 } esp_sleep_wakeup_cause_t;
typedef int gpio_num_t;
#define GPIO_NUM_27 27
#define ESP_EXT1_WAKEUP_ANY_HIGH 1
inline esp_sleep_wakeup_cause_t esp_sleep_get_wakeup_cause() { return ESP_SLEEP_WAKEUP_UNDEFINED; }
inline void esp_sleep_enable_ext1_wakeup(uint64_t, int) {}
inline void esp_deep_sleep_start() {}
// Sono leve (FW-07 b): acorda pelo timer, a RAM e o I2C sobrevivem.
inline int esp_sleep_enable_timer_wakeup(uint64_t) { return 0; }
inline int esp_light_sleep_start() { return 0; }
class EspStub { public: void restart() {} };
extern EspStub ESP;
#endif
