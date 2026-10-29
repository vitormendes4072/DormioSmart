#ifndef STUB_ASENSOR_H
#define STUB_ASENSOR_H
struct Vec3 { float x, y, z; };
struct sensors_event_t {
  Vec3 acceleration;
  Vec3 gyro;
  float temperature;
};
#endif
