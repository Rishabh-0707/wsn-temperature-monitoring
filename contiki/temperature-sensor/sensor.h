#ifndef WSN_SENSOR_H_
#define WSN_SENSOR_H_
#include <stdint.h>
/* Provide int16_t wsn_read_temperature_centi(void) in an added source module
 * and build with CFLAGS+=-DWSN_HARDWARE_SENSOR to use a physical sensor. */
#ifdef WSN_HARDWARE_SENSOR
int16_t wsn_read_temperature_centi(void);
#else
#include "random.h"
static int16_t wsn_read_temperature_centi(void) {
  static int32_t value = (TEMP_MIN_CENTI + TEMP_MAX_CENTI) / 2;
  value += (int32_t)(random_rand() % 61) - 30;
  if(value < TEMP_MIN_CENTI) value = TEMP_MIN_CENTI;
  if(value > TEMP_MAX_CENTI) value = TEMP_MAX_CENTI;
  return (int16_t)value;
}
#endif
#endif
