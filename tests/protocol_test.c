#include <assert.h>
#include <stdint.h>
#include <string.h>
#include "../contiki/common/protocol.h"

int main(void) {
  uint8_t packet[WSN_PACKET_SIZE] = {WSN_VERSION};
  const uint8_t expected[WSN_PACKET_SIZE] = {
    1, 0, 5, 0x12, 0x34, 0x56, 0x78, 0xfb, 0x2e,
    0, 0, 0x13, 0x88, 0xff, 0xff, 0xff, 0xff, 3
  };
  put16(packet + 1, 5);
  put32(packet + 3, 0x12345678);
  put16(packet + 7, (uint16_t)(int16_t)-1234);
  put32(packet + 9, 5000);
  put32(packet + 13, UINT32_MAX);
  packet[17] = 3;
  assert(memcmp(packet, expected, sizeof(packet)) == 0);
  assert(get16(packet + 1) == 5);
  assert(get32(packet + 3) == 0x12345678);
  assert((int16_t)get16(packet + 7) == -1234);
  assert(get32(packet + 9) == 5000);
  assert(get32(packet + 13) == UINT32_MAX);
  return 0;
}
