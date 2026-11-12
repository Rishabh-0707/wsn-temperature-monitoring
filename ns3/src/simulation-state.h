#pragma once
#include "ns3/core-module.h"
#include "ns3/internet-module.h"
#include "ns3/lr-wpan-module.h"
#include "ns3/mobility-module.h"
#include "ns3/netanim-module.h"
#include "ns3/network-module.h"
#include "ns3/propagation-module.h"
#include "ns3/sixlowpan-module.h"
#include "ns3/spectrum-module.h"
#include "temperature-header.h"
#include <algorithm>
#include <cmath>
#include <fstream>
#include <map>
#include <queue>
#include <set>
#include <tuple>
namespace wsn::sim {
using namespace ns3;
extern uint32_t count, seed, maxAttempts;
extern double duration, interval, range, timeout, loss, minTemp, maxTemp;
extern bool realtime;
extern std::string topology, output, animation, runId;
extern std::ofstream logStream;
extern uint64_t eventNumber;
extern NodeContainer nodes;
extern Ipv6InterfaceContainer interfaces;
extern std::vector<int> parent;
extern std::vector<int64_t> lastReceived, lastEnergy, txTime, listenTime;
extern std::vector<bool> online;
extern std::vector<lrwpan::PhyEnumeration> phyState;
extern std::vector<Ptr<Socket>> sockets;
extern std::vector<Ptr<UniformRandomVariable>> lossRng;
struct State {
  TemperatureHeader header;
  bool waiting = false;
  Ptr<UniformRandomVariable> rng;
};
extern std::vector<State> states;
extern std::set<std::tuple<uint16_t, uint32_t, uint32_t>> received;
extern std::map<std::tuple<uint16_t, uint32_t, uint32_t, uint8_t>,
                std::vector<uint32_t>>
    paths;
extern std::map<std::pair<uint16_t, uint32_t>, uint32_t> highest;
extern std::map<std::tuple<uint16_t, uint32_t, uint32_t>, TemperatureHeader>
    sent;
void EmitEvent(const std::string &, uint32_t,
               const TemperatureHeader * = nullptr, const std::string & = "");
void EnergyTransition(uint32_t, lrwpan::PhyEnumeration, lrwpan::PhyEnumeration);
void Availability();
void EnergySample();
void AckTimeout(uint32_t, uint32_t, uint8_t);
void Send(uint32_t);
void Sample(uint32_t);
void Receive(uint32_t, Ptr<Socket>);
void Forward(uint32_t, const Ipv6Header &, Ptr<const Packet>, uint32_t);
void ConfigureRoutes(const std::vector<Vector> &points);
int RunExperiment(int argc, char **argv);
} // namespace wsn::sim
