#include "temperature-header.h"
namespace wsn {
NS_OBJECT_ENSURE_REGISTERED(TemperatureHeader);
ns3::TypeId TemperatureHeader::GetTypeId() {
  static ns3::TypeId id = ns3::TypeId("wsn::TemperatureHeader")
                              .SetParent<ns3::Header>()
                              .AddConstructor<TemperatureHeader>();
  return id;
}
ns3::TypeId TemperatureHeader::GetInstanceTypeId() const { return GetTypeId(); }
uint32_t TemperatureHeader::GetSerializedSize() const { return 18; }
void TemperatureHeader::Serialize(ns3::Buffer::Iterator i) const {
  i.WriteU8(version);
  i.WriteHtonU16(node);
  i.WriteHtonU32(sequence);
  i.WriteHtonU16(static_cast<uint16_t>(temperature));
  i.WriteHtonU32(uptime);
  i.WriteHtonU32(boot);
  i.WriteU8(attempt);
}
uint32_t TemperatureHeader::Deserialize(ns3::Buffer::Iterator i) {
  if (i.GetRemainingSize() < 18)
    return 0;
  version = i.ReadU8();
  node = i.ReadNtohU16();
  sequence = i.ReadNtohU32();
  auto raw = i.ReadNtohU16();
  temperature = raw >= 32768 ? static_cast<int32_t>(raw) - 65536 : raw;
  uptime = i.ReadNtohU32();
  boot = i.ReadNtohU32();
  attempt = i.ReadU8();
  return 18;
}
bool TemperatureHeader::Valid(uint16_t nodes, uint8_t attempts) const {
  return version == 1 && node > 0 && node <= nodes && sequence > 0 &&
         temperature >= -5000 && temperature <= 12500 && attempt > 0 &&
         attempt <= attempts;
}
void TemperatureHeader::Print(std::ostream &os) const {
  os << node << ":" << boot << ":" << sequence
     << " temperature=" << temperature;
}
} // namespace wsn
