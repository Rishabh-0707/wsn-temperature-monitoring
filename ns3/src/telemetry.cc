#include "simulation-state.h"
namespace wsn::sim {
void EnergyTransition(uint32_t id, lrwpan::PhyEnumeration oldState,
                      lrwpan::PhyEnumeration newState) {
  auto now = Simulator::Now().GetMicroSeconds();
  auto elapsed = now - lastEnergy[id];
  if (oldState == lrwpan::IEEE_802_15_4_PHY_BUSY_TX)
    txTime[id] += elapsed;
  if (oldState == lrwpan::IEEE_802_15_4_PHY_RX_ON ||
      oldState == lrwpan::IEEE_802_15_4_PHY_BUSY_RX)
    listenTime[id] += elapsed;
  lastEnergy[id] = now;
  phyState[id] = newState;
}
void EmitEvent(const std::string &type, uint32_t node,
               const TemperatureHeader *h, const std::string &extra) {
  logStream << "{\"run_id\":\"" << runId
            << "\",\"simulator\":\"ns3\",\"event_id\":\"e" << ++eventNumber
            << "\",\"type\":\"" << type << "\",\"node_id\":" << node
            << ",\"sim_time_us\":" << Simulator::Now().GetMicroSeconds();
  if (h)
    logStream << ",\"boot_id\":" << h->boot
              << ",\"sequence_number\":" << h->sequence
              << ",\"temperature_centi\":" << h->temperature
              << ",\"attempt\":" << unsigned(h->attempt)
              << ",\"sample_uptime_ms\":" << h->uptime
              << ",\"payload_bytes\":18";
  logStream << extra << "}\n";
  logStream.flush();
}
void Availability() {
  for (uint32_t id = 1; id <= count; id++)
    if (online[id] &&
        Simulator::Now().GetMicroSeconds() - lastReceived[id] > 15000000) {
      online[id] = false;
      EmitEvent("offline", id);
    }
  if (Simulator::Now().GetSeconds() + 5 < duration)
    Simulator::Schedule(Seconds(5), &Availability);
}
void EnergySample() {
  auto now = Simulator::Now().GetMicroSeconds();
  for (uint32_t id = 0; id <= count; id++) {
    EnergyTransition(id, phyState[id], phyState[id]);
    EmitEvent("energy", id, nullptr,
              ",\"cpu\":" + std::to_string(now) +
                  ",\"lpm\":0,\"deep_lpm\":0,\"ticks_per_second\":1000000,"
                  "\"transmit\":" +
                  std::to_string(txTime[id]) +
                  ",\"listen\":" + std::to_string(listenTime[id]));
  }
  if (Simulator::Now().GetSeconds() + 5 < duration)
    Simulator::Schedule(Seconds(5), &EnergySample);
}
} // namespace wsn::sim
