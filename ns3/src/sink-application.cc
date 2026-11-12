#include "simulation-state.h"
namespace wsn::sim {
void Receive(uint32_t id, Ptr<Socket> socket) {
  Address from;
  while (auto p = socket->RecvFrom(from)) {
    if (p->GetSize() != 18)
      continue;
    TemperatureHeader h;
    auto copy = p->Copy();
    copy->RemoveHeader(h);
    if (!h.Valid(count, maxAttempts))
      continue;
    if (lossRng[id]->GetValue() < loss) {
      EmitEvent("drop", h.node, &h,
                ",\"reason\":\"injected_udp_receive_discard\"");
      continue;
    }
    if (id == 0) {
      lastReceived[h.node] = Simulator::Now().GetMicroSeconds();
      if (!online[h.node]) {
        online[h.node] = true;
        EmitEvent("online", h.node);
      }
      auto key = std::make_tuple(h.node, h.boot, h.sequence);
      bool duplicate = !received.insert(key).second;
      auto &high = highest[{h.node, h.boot}];
      bool reordered = h.sequence <= high;
      high = std::max(high, h.sequence);
      SocketIpv6HopLimitTag tag;
      uint32_t hops = p->PeekPacketTag(tag) ? 65 - tag.GetHopLimit() : 0;
      auto path = paths[{h.node, h.boot, h.sequence, h.attempt}];
      path.push_back(0);
      std::string pathText = ",\"path\":[";
      for (size_t i = 0; i < path.size(); i++) {
        if (i)
          pathText += ",";
        pathText += std::to_string(path[i]);
      }
      pathText += "]";
      EmitEvent("rx", h.node, &h,
                pathText + ",\"duplicate_or_reordered\":" +
                    std::to_string(duplicate || reordered) +
                    ",\"hop_count\":" + std::to_string(hops));
      auto ack = Create<Packet>();
      ack->AddHeader(h);
      socket->SendTo(ack, 0, from);
    } else {
      auto &s = states[id];
      auto sender = Inet6SocketAddress::ConvertFrom(from);
      if (sender.GetIpv6() != interfaces.GetAddress(0, 1) || h.node != id ||
          h.boot != s.header.boot || h.sequence != s.header.sequence ||
          h.temperature != s.header.temperature ||
          h.uptime != s.header.uptime || !s.waiting)
        continue;
      s.waiting = false;
      EmitEvent("ack", id, &h);
    }
  }
}
} // namespace wsn::sim
