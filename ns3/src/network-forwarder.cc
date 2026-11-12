#include "simulation-state.h"
namespace wsn::sim {
void Forward(uint32_t id, const Ipv6Header &ip, Ptr<const Packet> packet,
             uint32_t interface) {
  if (ip.GetNextHeader() != 17)
    return;
  auto p = packet->Copy();
  UdpHeader udp;
  if (p->RemoveHeader(udp) == 0 || udp.GetDestinationPort() != 5678 ||
      p->GetSize() != 18)
    return;
  TemperatureHeader h;
  p->RemoveHeader(h);
  if (h.Valid(count, maxAttempts)) {
    paths[{h.node, h.boot, h.sequence, h.attempt}].push_back(id);
    EmitEvent("forward", h.node, &h,
              ",\"forwarding_node\":" + std::to_string(id));
  }
}
void ConfigureRoutes(const std::vector<Vector> &points) {
  Ipv6StaticRoutingHelper routes;
  // Breadth-first next-hop routes on the configured range graph. No RPL or
  // discovery traffic.
  for (uint32_t destination = 0; destination <= count; destination++) {
    std::vector<int> next(count + 1, -1);
    next[destination] = destination;
    std::queue<uint32_t> pending;
    pending.push(destination);
    while (!pending.empty()) {
      auto v = pending.front();
      pending.pop();
      for (uint32_t u = 0; u <= count; u++)
        if (next[u] < 0 && CalculateDistance(points[u], points[v]) <= range) {
          next[u] = v;
          pending.push(u);
        }
    }
    for (uint32_t u = 0; u <= count; u++) {
      if (destination == 0)
        parent[u] = next[u];
      if (u == destination || next[u] < 0)
        continue;
      auto ip = nodes.Get(u)->GetObject<Ipv6>();
      auto r = routes.GetStaticRouting(ip);
      r->AddHostRouteTo(interfaces.GetAddress(destination, 1),
                        interfaces.GetAddress(next[u], 1),
                        interfaces.GetInterfaceIndex(u));
    }
  }
}
} // namespace wsn::sim
