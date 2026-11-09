#ifndef WSN_PROTOCOL_H_
#define WSN_PROTOCOL_H_
#include <stdint.h>
#define WSN_PORT 5678
#define WSN_CLIENT_PORT 8765
#define WSN_PACKET_SIZE 18
#define WSN_VERSION 1
static inline void put16(uint8_t *p, uint16_t v) { p[0] = v >> 8; p[1] = v; }
static inline void put32(uint8_t *p, uint32_t v) {
  p[0] = v >> 24; p[1] = v >> 16; p[2] = v >> 8; p[3] = v;
}
static inline uint16_t get16(const uint8_t *p) { return ((uint16_t)p[0] << 8) | p[1]; }
static inline uint32_t get32(const uint8_t *p) {
  return ((uint32_t)p[0] << 24) | ((uint32_t)p[1] << 16) | ((uint32_t)p[2] << 8) | p[3];
}
#endif
