#include "contiki.h"
#include "net/netstack.h"
#include "net/routing/routing.h"
#include "net/ipv6/simple-udp.h"
#include "sys/node-id.h"
#include "random.h"
#include "../common/protocol.h"
#include "../common/telemetry.h"
#include "sensor.h"
#include <string.h>

PROCESS(temperature_process, "Temperature telemetry");
AUTOSTART_PROCESSES(&temperature_process);
static struct simple_udp_connection conn;
static uint8_t packet[WSN_PACKET_SIZE];
static uint8_t acknowledged;
static uip_ipaddr_t root;

static void receive_ack(struct simple_udp_connection *c,
  const uip_ipaddr_t *sender, uint16_t sender_port,
  const uip_ipaddr_t *receiver, uint16_t receiver_port,
  const uint8_t *data, uint16_t length) {
  if(length == WSN_PACKET_SIZE && uip_ipaddr_cmp(sender, &root) &&
     memcmp(data, packet, WSN_PACKET_SIZE - 1) == 0) {
    acknowledged = 1;
    process_poll(&temperature_process);
  }
}

PROCESS_THREAD(temperature_process, ev, data) {
  static struct etimer sample_timer, ack_timer;
  static uint16_t logical_id;
  static uint32_t sequence, boot;
  static uint8_t attempt;
  static int16_t temperature;
  PROCESS_BEGIN();
  logical_id = node_id > 1 ? node_id - 1 : node_id;
  boot = ((uint32_t)random_rand() << 16) | random_rand();
  simple_udp_register(&conn, WSN_CLIENT_PORT, NULL, WSN_PORT, receive_ack);
  etimer_set(&sample_timer, (15 * CLOCK_SECOND) + random_rand() % (5 * CLOCK_SECOND));
  while(1) {
    PROCESS_WAIT_EVENT_UNTIL(etimer_expired(&sample_timer));
    etimer_set(&sample_timer, SAMPLE_INTERVAL_SECONDS * CLOCK_SECOND);
    sequence++;
    temperature = wsn_read_temperature_centi();
    packet[0] = WSN_VERSION;
    put16(packet + 1, logical_id);
    put32(packet + 3, sequence);
    put16(packet + 7, (uint16_t)temperature);
    put32(packet + 9, (uint32_t)((uint64_t)clock_time() * 1000 / CLOCK_SECOND));
    put32(packet + 13, boot);
    telemetry(logical_id, boot);
    printf("{\"type\":\"sample\",\"node_id\":%u,\"boot_id\":%" PRIu32 ",\"sequence_number\":%" PRIu32 "}\n", logical_id, boot, sequence);
    if(NETSTACK_ROUTING.node_is_reachable() && NETSTACK_ROUTING.get_root_ipaddr(&root)) {
      acknowledged = 0;
      for(attempt = 1; attempt <= WSN_MAX_ATTEMPTS && !acknowledged; attempt++) {
        packet[17] = attempt;
        printf("{\"type\":\"tx\",\"node_id\":%u,\"boot_id\":%" PRIu32
               ",\"sequence_number\":%" PRIu32 ",\"temperature_centi\":%d,\"attempt\":%u,\"payload_bytes\":%u}\n",
               logical_id, boot, sequence, temperature, attempt, WSN_PACKET_SIZE);
        simple_udp_sendto(&conn, packet, sizeof(packet), &root);
        etimer_set(&ack_timer, CLOCK_SECOND);
        PROCESS_WAIT_EVENT_UNTIL(acknowledged || etimer_expired(&ack_timer));
        etimer_stop(&ack_timer);
      }
      printf("{\"type\":\"%s\",\"node_id\":%u,\"boot_id\":%" PRIu32 ",\"sequence_number\":%" PRIu32 "}\n",
             acknowledged ? "ack" : "failed", logical_id, boot, sequence);
    } else {
      printf("{\"type\":\"no_route\",\"node_id\":%u,\"boot_id\":%" PRIu32 ",\"sequence_number\":%" PRIu32 "}\n", logical_id, boot, sequence);
    }
  }
  PROCESS_END();
}
