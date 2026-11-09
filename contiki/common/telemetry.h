#ifndef WSN_TELEMETRY_H_
#define WSN_TELEMETRY_H_
#include "sys/energest.h"
#include "net/routing/rpl-lite/rpl.h"
#include "net/routing/rpl-lite/rpl-neighbor.h"
#include <inttypes.h>
#include <stdio.h>
static void telemetry(uint16_t id, uint32_t boot) {
  uip_ipaddr_t *parent = NULL;
  if(curr_instance.dag.preferred_parent) {
    parent = rpl_neighbor_get_ipaddr(curr_instance.dag.preferred_parent);
  }
  /* Cooja's link-local address ends in its mote ID (IDs 1..33 here). */
  printf("{\"type\":\"status\",\"node_id\":%u,\"boot_id\":%" PRIu32
         ",\"rank\":%u,\"parent_mote_id\":%u}\n", id, boot,
         curr_instance.dag.rank, parent ? ((unsigned)parent->u8[14] << 8) | parent->u8[15] : 0);
  energest_flush();
  printf("{\"type\":\"energy\",\"node_id\":%u,\"boot_id\":%" PRIu32
         ",\"cpu\":%" PRIu64 ",\"lpm\":%" PRIu64 ",\"deep_lpm\":%" PRIu64
         ",\"transmit\":%" PRIu64 ",\"listen\":%" PRIu64 ",\"ticks_per_second\":%lu}\n",
         id, boot, energest_type_time(ENERGEST_TYPE_CPU), energest_type_time(ENERGEST_TYPE_LPM),
         energest_type_time(ENERGEST_TYPE_DEEP_LPM), energest_type_time(ENERGEST_TYPE_TRANSMIT),
         energest_type_time(ENERGEST_TYPE_LISTEN), (unsigned long)ENERGEST_SECOND);
}
#endif
