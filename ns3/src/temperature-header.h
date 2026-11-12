#pragma once
#include "ns3/header.h"
#include <cstdint>
namespace wsn {
class TemperatureHeader : public ns3::Header {
public:
  uint8_t version{1}, attempt{1};
  uint16_t node{1};
  uint32_t sequence{1}, uptime{0}, boot{0};
  int16_t temperature{2500};
  static ns3::TypeId GetTypeId();
  ns3::TypeId GetInstanceTypeId() const override;
  uint32_t GetSerializedSize() const override;
  void Serialize(ns3::Buffer::Iterator i) const override;
  uint32_t Deserialize(ns3::Buffer::Iterator i) override;
  void Print(std::ostream &os) const override;
  bool Valid(uint16_t nodes = 32, uint8_t attempts = 3) const;
};
} // namespace wsn
