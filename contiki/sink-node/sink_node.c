#include "contiki.h"
#include "net/netstack.h"
#include "net/routing/routing.h"
#include "net/ipv6/simple-udp.h"
#include "../common/protocol.h"
#include "../common/telemetry.h"

static struct simple_udp_connection conn;
static uint32_t high_sequence[WSN_MAX_NODES + 1], boots[WSN_MAX_NODES + 1];
PROCESS(sink_process, "Temperature sink");
AUTOSTART_PROCESSES(&sink_process);

static void receive(struct simple_udp_connection *c,
  const uip_ipaddr_t *sender, uint16_t sender_port,
  const uip_ipaddr_t *receiver, uint16_t receiver_port,
  const uint8_t *data, uint16_t length) {
  uint16_t id;
  uint32_t seq, boot;
  int16_t temp;
  uint8_t reordered;
  if(length != WSN_PACKET_SIZE || data[0] != WSN_VERSION) return;
  id = get16(data + 1); seq = get32(data + 3); boot = get32(data + 13);
  temp = (int16_t)get16(data + 7);
  if(id == 0 || id > WSN_MAX_NODES || seq == 0 || temp < -5000 || temp > 12500 ||
     data[17] == 0 || data[17] > WSN_MAX_ATTEMPTS) return;
  if(boots[id] != boot) { boots[id] = boot; high_sequence[id] = 0; }
  reordered = seq <= high_sequence[id];
  if(seq > high_sequence[id]) high_sequence[id] = seq;
  printf("{\"type\":\"rx\",\"node_id\":%u,\"boot_id\":%" PRIu32
         ",\"sequence_number\":%" PRIu32 ",\"temperature_centi\":%d,\"sample_uptime_ms\":%" PRIu32
         ",\"attempt\":%u,\"payload_bytes\":%u,\"duplicate_or_reordered\":%u}\n",
         id, boot, seq, temp, get32(data + 9), data[17], length, reordered);
  /* ACK duplicates too: an earlier ACK may have been lost. Full deduplication
   * and out-of-order reconciliation occur in the durable backend. */
  simple_udp_sendto(&conn, data, length, sender);
}

PROCESS_THREAD(sink_process, ev, data) {
  static struct etimer timer;
  PROCESS_BEGIN();
  NETSTACK_ROUTING.root_start();
  simple_udp_register(&conn, WSN_PORT, NULL, WSN_CLIENT_PORT, receive);
  etimer_set(&timer, 5 * CLOCK_SECOND);
  while(1) {
    PROCESS_WAIT_EVENT_UNTIL(etimer_expired(&timer));
    telemetry(0, 0);
    etimer_reset(&timer);
  }
  PROCESS_END();
}
