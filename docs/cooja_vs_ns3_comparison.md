# Cooja versus NS-3: descriptive comparison

Both experiments used one sink, ten sensors, the staggered ladder placement, nominal 50 m range, 5 s samples, 18-byte payload and 300 s duration. This does **not** make their radio, timing, MAC, routing or energy models equivalent.

Cooja baseline: `1619a095-5cb5-4ad1-a7f0-289113bee2b5`, unchanged original evidence. NS-3: `6d0cc334-5678-4259-946a-c5de36ea7e7f`, pinned 3.46. Cooja uses Contiki-NG RPL-Lite / 6LoWPAN / IEEE 802.15.4 and UDGM. NS-3 uses LR-WPAN / SixLoWPAN / IPv6 / UDP with range propagation and static destination-specific BFS next-hop routes. No NS-3 RPL implementation is claimed.

| Metric | Cooja | NS-3 |
|---|---:|---:|
| PDR (%) | 100.000 | 100.000 |
| Packet loss (%) | 0.000 | 0.000 |
| Mean delay (ms) | 77.809 | 14.967 |
| Useful throughput (bit/s) | 254.400 | 270.240 |
| Estimated energy (J) | 202.108 | 203.822 |
| Routing control output events | 164.000 | 0.000 |
| Observed mean hop count | Unavailable | 3.002 |
| Collected / generated samples (%) | 92.982 | 100.000 |
| Application retry attempts | 0.000 | 0.000 |

Cooja's original data did not record per-packet hop counts, so its hop value stays unavailable; RPL rank is not substituted for packet hops. Its routing convergence creates no-route samples. NS-3 installs routes before traffic and sends zero routing-discovery packets; that zero is not evidence of a superior dynamic routing protocol. IPv6 neighbor discovery and MAC traffic are not counted as RPL control events.

Electrical values use illustrative current/battery assumptions. Cooja uses Energest timings, NS-3 observed PHY-state timings with CPU assumed active. They are not calibrated measurements. Different first-sample times and deferral near experiment end also affect totals. Results are descriptive single-seed observations, not a controlled scientific comparison or statistically significant ranking.

The existing dashboard's **Simulation engines & comparison** panel accepts an explicit Cooja/NS-3 pair, displays tables and graphs, and exposes recorded configurations. No automatic mixing occurs in ordinary experiment views. The full API snapshots are in [comparison.json](../ns3/results/comparison.json); the comparison plot is [comparison.png](../ns3/results/comparison.png).
