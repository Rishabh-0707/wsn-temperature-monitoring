#include "simulation-state.h"
namespace wsn::sim {
void AckTimeout(uint32_t id, uint32_t sequence, uint8_t attempt) {
  auto &s = states[id];
  if (!s.waiting || s.header.sequence != sequence ||
      s.header.attempt != attempt)
    return;
  EmitEvent("ack_timeout", id, &s.header);
  if (s.header.attempt < maxAttempts) {
    ++s.header.attempt;
    EmitEvent("retry", id, &s.header);
    Send(id);
  } else {
    s.waiting = false;
    EmitEvent("failed", id, &s.header);
  }
}
void Send(uint32_t id) {
  auto &s = states[id];
  sent[{s.header.node, s.header.boot, s.header.sequence}] = s.header;
  paths[{s.header.node, s.header.boot, s.header.sequence, s.header.attempt}] = {
      id};
  auto p = Create<Packet>();
  p->AddHeader(s.header);
  EmitEvent("tx", id, &s.header);
  if (sockets[id]->SendTo(
          p, 0, Inet6SocketAddress(interfaces.GetAddress(0, 1), 5678)) < 0)
    EmitEvent("drop", id, &s.header, ",\"reason\":\"socket_send_failed\"");
  Simulator::Schedule(Seconds(timeout), &AckTimeout, id, s.header.sequence,
                      s.header.attempt);
}
void Sample(uint32_t id) {
  auto &s = states[id];
  if (Simulator::Now().GetSeconds() + maxAttempts * timeout >= duration)
    return;
  if (s.waiting) {
    Simulator::Schedule(Seconds(interval), &Sample, id);
    return;
  }
  ++s.header.sequence;
  s.header.attempt = 1;
  s.header.uptime = Simulator::Now().GetMilliSeconds();
  s.header.temperature =
      std::clamp(int(s.header.temperature) + int(s.rng->GetInteger(0, 60)) - 30,
                 int(minTemp * 100), int(maxTemp * 100));
  EmitEvent("sample", id, &s.header);
  if (parent[id] < 0)
    EmitEvent("no_route", id, &s.header);
  else {
    s.waiting = true;
    Send(id);
  }
  Simulator::Schedule(Seconds(interval), &Sample, id);
}
} // namespace wsn::sim
