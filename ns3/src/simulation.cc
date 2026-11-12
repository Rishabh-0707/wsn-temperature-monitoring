#include "simulation-state.h"
namespace wsn::sim {

uint32_t count = 5, seed = 123456, maxAttempts = 3;
double duration = 60, interval = 5, range = 50, timeout = 1, loss = 0,
       minTemp = 20, maxTemp = 35;
bool realtime = false;
std::string topology = "star", output = "events.jsonl",
            animation = "animation.xml", runId = "local";
std::ofstream logStream;
uint64_t eventNumber = 0;
NodeContainer nodes;
Ipv6InterfaceContainer interfaces;
std::vector<int> parent;
std::vector<int64_t> lastReceived;
std::vector<bool> online;
std::vector<int64_t> lastEnergy, txTime, listenTime;
std::vector<lrwpan::PhyEnumeration> phyState;

std::vector<Ptr<Socket>> sockets;
std::vector<Ptr<UniformRandomVariable>> lossRng;

std::vector<State> states;
std::set<std::tuple<uint16_t, uint32_t, uint32_t>> received;
std::map<std::tuple<uint16_t, uint32_t, uint32_t, uint8_t>,
         std::vector<uint32_t>>
    paths;
std::map<std::pair<uint16_t, uint32_t>, uint32_t> highest;
std::map<std::tuple<uint16_t, uint32_t, uint32_t>, TemperatureHeader> sent;

void Send(uint32_t id);

int RunExperiment(int argc, char **argv) {
  CommandLine cmd;
  cmd.AddValue("nodes", "Sensor count", count);
  cmd.AddValue("duration", "Seconds", duration);
  cmd.AddValue("interval", "Sampling seconds", interval);
  cmd.AddValue("range", "Range metres", range);
  cmd.AddValue("seed", "RNG seed", seed);
  cmd.AddValue("topology", "star or ladder", topology);
  cmd.AddValue("output", "JSON Lines path", output);
  cmd.AddValue("animation", "NetAnim XML path", animation);
  cmd.AddValue("runId", "Experiment ID", runId);
  cmd.AddValue("loss", "Independent UDP receive-discard probability", loss);
  cmd.AddValue("minTemp", "Minimum Celsius", minTemp);
  cmd.AddValue("maxTemp", "Maximum Celsius", maxTemp);
  cmd.AddValue("timeout", "ACK timeout seconds", timeout);
  cmd.AddValue("attempts", "Maximum attempts", maxAttempts);
  cmd.AddValue("realtime", "Pace with wall clock", realtime);
  cmd.Parse(argc, argv);
  for (double value :
       {duration, interval, range, timeout, loss, minTemp, maxTemp})
    if (!std::isfinite(value))
      return 2;
  if (runId.empty() || runId.size() > 100 ||
      !std::all_of(runId.begin(), runId.end(), [](unsigned char c) {
        return std::isalnum(c) || c == '-' || c == '_';
      }))
    return 2;
  if (count < 1 || count > 32 || duration < 20 || duration > 3600 ||
      interval < 2 || interval > 60 || range <= 0 || range > 1000 ||
      (topology != "star" && topology != "ladder"))
    return 2;
  if (loss < 0 || loss > 1 || minTemp < -50 || maxTemp > 125 ||
      minTemp >= maxTemp || timeout < 0.1 || timeout > 3 || maxAttempts < 1 ||
      maxAttempts > 3)
    return 2;
  if (realtime)
    GlobalValue::Bind("SimulatorImplementationType",
                      StringValue("ns3::RealtimeSimulatorImpl"));
  RngSeedManager::SetSeed(seed);
  RngSeedManager::SetRun(1);
  logStream.open(output);
  if (!logStream)
    return 3;
  lastReceived.resize(count + 1);
  online.resize(count + 1);
  lastEnergy.resize(count + 1);
  txTime.resize(count + 1);
  listenTime.resize(count + 1);
  phyState.resize(count + 1, lrwpan::IEEE_802_15_4_PHY_TRX_OFF);
  lossRng.resize(count + 1);
  for (uint32_t i = 0; i <= count; i++) {
    lossRng[i] = CreateObject<UniformRandomVariable>();
    lossRng[i]->SetStream(5000 + i);
  }
  nodes.Create(count + 1);
  states.resize(count + 1);
  parent.assign(count + 1, -1);
  sockets.resize(count + 1);
  MobilityHelper mobility;
  auto positions = CreateObject<ListPositionAllocator>();
  std::vector<Vector> points;
  points.emplace_back(0, 0, 0);
  positions->Add(points[0]);
  for (uint32_t i = 1; i <= count; i++) {
    Vector p = topology == "star"
                   ? Vector(30 * cos(i * 6.283185307 / count),
                            30 * sin(i * 6.283185307 / count), 0)
                   : Vector(35 * ((i + 1) / 2), i % 2 ? 0 : 25, 0);
    points.push_back(p);
    positions->Add(p);
  }
  mobility.SetPositionAllocator(positions);
  mobility.SetMobilityModel("ns3::ConstantPositionMobilityModel");
  mobility.Install(nodes);
  LrWpanHelper radio;
  radio.SetPropagationDelayModel("ns3::ConstantSpeedPropagationDelayModel");
  radio.AddPropagationLossModel("ns3::RangePropagationLossModel", "MaxRange",
                                DoubleValue(range));
  auto physical = radio.Install(nodes);
  radio.CreateAssociatedPan(physical, 0xabcd);
  radio.AssignStreams(physical, 1000);
  for (uint32_t i = 0; i <= count; i++) {
    auto phy = DynamicCast<lrwpan::LrWpanNetDevice>(physical.Get(i))->GetPhy();
    phy->TraceConnectWithoutContext("TrxStateValue",
                                    MakeBoundCallback(&EnergyTransition, i));
  }
  Config::SetDefault("ns3::Ipv6L3Protocol::SendIcmpv6Redirect",
                     BooleanValue(false));
  InternetStackHelper internet;
  internet.Install(nodes);
  SixLowPanHelper adaptation;
  auto devices = adaptation.Install(physical);
  Ipv6AddressHelper address;
  address.SetBase(Ipv6Address("fd42:1::"), Ipv6Prefix(64));
  interfaces = address.Assign(devices);
  ConfigureRoutes(points);
  EmitEvent("started", 0);
  for (uint32_t i = 0; i <= count; i++) {
    interfaces.SetForwarding(i, true);
    nodes.Get(i)->GetObject<Ipv6L3Protocol>()->TraceConnectWithoutContext(
        "UnicastForward", MakeBoundCallback(&Forward, i));
    auto s = Socket::CreateSocket(nodes.Get(i), UdpSocketFactory::GetTypeId());
    s->SetIpv6HopLimit(64);
    s->SetIpv6RecvHopLimit(true);
    s->Bind(Inet6SocketAddress(Ipv6Address::GetAny(), i ? 8765 : 5678));
    s->SetRecvCallback(MakeBoundCallback(&Receive, i));
    sockets[i] = s;
    EmitEvent("initialized", i);
    if (i && parent[i] >= 0)
      EmitEvent("route_established", i, nullptr,
                ",\"next_hop\":" + std::to_string(parent[i]));
    EmitEvent("status", i, nullptr,
              ",\"rank\":0,\"parent_mote_id\":" +
                  std::to_string(parent[i] < 0 ? 65535 : parent[i] + 1));
    if (i) {
      auto &state = states[i];
      state.rng = CreateObject<UniformRandomVariable>();
      state.rng->SetStream(100 + i);
      state.header.node = i;
      state.header.sequence = 0;
      state.header.boot = state.rng->GetInteger(1, 0xffffffff);
      state.header.temperature = int((minTemp + maxTemp) * 50);
      Simulator::Schedule(Seconds(15 + state.rng->GetValue(0, 5)), &Sample, i);
    }
  }
  AnimationInterface anim(animation);
  anim.EnablePacketMetadata(true);
  for (uint32_t i = 0; i <= count; i++) {
    anim.UpdateNodeDescription(i, i ? "Sensor " + std::to_string(i) : "Sink");
    anim.UpdateNodeColor(nodes.Get(i), i ? 40 : 200, 160, 120);
  }
  Simulator::Schedule(Seconds(5), &Availability);
  Simulator::Schedule(Seconds(5), &EnergySample);
  Simulator::Stop(Seconds(duration));
  Simulator::Run();
  EnergySample();
  for (const auto &[key, h] : sent)
    if (!received.contains(key))
      EmitEvent("drop", h.node, &h,
                ",\"reason\":\"not_received_by_observation_end\"");
  EmitEvent("completed", 0);
  Simulator::Destroy();
  return 0;
}
} // namespace wsn::sim
