#include "ns3/packet.h"
#include "temperature-header.h"
#include <array>
#include <iostream>
#include <stdexcept>
#define CHECK(v)                                                               \
  do {                                                                         \
    if (!(v))                                                                  \
      throw std::runtime_error(#v);                                            \
  } while (0)
int main() {
  wsn::TemperatureHeader h;
  h.node = 32;
  h.sequence = 0xffffffff;
  h.temperature = -1234;
  h.uptime = 0x01020304;
  h.boot = 0x12345678;
  h.attempt = 3;
  auto p = ns3::Create<ns3::Packet>();
  p->AddHeader(h);
  CHECK(p->GetSize() == 18);
  std::array<uint8_t, 18> bytes{};
  p->CopyData(bytes.data(), 18);
  const std::array<uint8_t, 18> expected{1, 0, 32, 255, 255, 255, 255, 251, 46,
                                         1, 2, 3,  4,   18,  52,  86,  120, 3};
  CHECK(bytes == expected);
  wsn::TemperatureHeader out;
  CHECK(p->RemoveHeader(out) == 18);
  CHECK(out.Valid());
  CHECK(out.temperature == -1234);
  CHECK(out.sequence == 0xffffffff);
  CHECK(out.boot == h.boot);
  CHECK(out.uptime == h.uptime);
  for (auto value : {-5000, 0, 2850, 12500}) {
    h.temperature = value;
    auto q = ns3::Create<ns3::Packet>();
    q->AddHeader(h);
    q->RemoveHeader(out);
    CHECK(out.temperature == value);
    CHECK(out.Valid());
  }
  h.node = 0;
  CHECK(!h.Valid());
  h.node = 33;
  CHECK(!h.Valid());
  h.node = 1;
  h.sequence = 0;
  CHECK(!h.Valid());
  h.sequence = 1;
  CHECK(h.Valid());
  h.attempt = 0;
  CHECK(!h.Valid());
  std::cout << "18-byte header tests passed\n";
}
