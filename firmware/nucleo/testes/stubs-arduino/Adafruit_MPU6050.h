#ifndef STUB_MPU_H
#define STUB_MPU_H
#include "Arduino.h"
#include "Adafruit_Sensor.h"
#define MPU6050_RANGE_8_G 0
#define MPU6050_RANGE_500_DEG 0
#define MPU6050_BAND_21_HZ 0
class Adafruit_MPU6050 {
 public:
  bool begin() { return true; }
  void setAccelerometerRange(int) {}
  void setGyroRange(int) {}
  void setFilterBandwidth(int) {}
  void getEvent(sensors_event_t *a, sensors_event_t *g, sensors_event_t *t) {
    (void)a; (void)g; (void)t;
  }
};
#endif
