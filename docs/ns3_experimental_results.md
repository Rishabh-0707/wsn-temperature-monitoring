# Actual NS-3 experimental results

Executed 10 November 2026 with compiled NS-3 3.46, seed 123456 unless indicated. Each row is a separate 300-second experiment in the shared production backend. One sink is additional to the listed sensor count. Default interval 5 s, 18-byte payload, 50 m range, 20–35 °C walk, ACK timeout 1 s, maximum 3 attempts. Full configuration and source/binary hashes are in each manifest. Runs were fast (simulation-clock based); separate live runs exercised pacing and cancellation.

| Experiment | Unique TX | Unique RX | PDR % | Mean delay ms | Mean hops | Retries |
|---|---:|---:|---:|---:|---:|---:|
| [star_5](../ns3/results/24cfb921-31e7-43fe-b4ec-0ecea206672e/manifest.json) | 282 | 282 | 100.000 | 4.211 | 1.000 | 0 |
| [ladder_10](../ns3/results/6d0cc334-5678-4259-946a-c5de36ea7e7f/manifest.json) | 563 | 563 | 100.000 | 14.967 | 3.002 | 0 |
| [ladder_20](../ns3/results/e900771e-63f6-416e-9617-193d20396a88/manifest.json) | 1127 | 1127 | 100.000 | 32.123 | 5.506 | 6 |
| [interval_2](../ns3/results/603bd8bb-a71d-4937-9c80-5f3ec224578c/manifest.json) | 1401 | 1401 | 100.000 | 14.732 | 3.001 | 0 |
| [interval_10](../ns3/results/8da16db0-38bd-472d-b90a-aab19a19f2d0/manifest.json) | 283 | 283 | 100.000 | 15.055 | 3.004 | 0 |
| [loss_03](../ns3/results/e953e5bb-05f0-4632-80ef-5d07e6185573/manifest.json) | 563 | 548 | 97.336 | 357.693 | 3.011 | 444 |
| [range_35](../ns3/results/67c0f3de-394c-4760-86db-cb1fa7c05962/manifest.json) | 563 | 563 | 100.000 | 21.026 | 3.503 | 2 |
| [seed_42](../ns3/results/7731764c-c2ed-48da-b485-9435af12f341/manifest.json) | 564 | 564 | 100.000 | 18.098 | 2.998 | 2 |

These are single-run observations, not confidence intervals or claims that NS-3 and Cooja are physically equivalent. The star sensors are within direct range; ladder nodes use the original 35 m horizontal / 25 m vertical spacing. Static BFS routes are configured over that range graph, with actual IPv6 forwarding and LR-WPAN transmissions. The twenty-node run reaches ten wireless hops.

The 30% UDP receive-discard run transmitted 563 unique samples, received 548, lost 15, performed 444 application retries, saw 162 duplicate receptions and had 80 final ACK failures. ACK failures can occur after successful data reception. Retransmissions are not new unique packets. The 20 m disconnected test generated no-route samples, zero transmitted packets and zero wireless losses; PDR correctly remains unavailable. A 100% UDP discard test produced zero successful receptions and bounded retries.

## Executed evidence

- NS-3 network and header targets compiled; exact-byte/round-trip 18-byte header test passed.
- All eight matrix processes completed. `scripts/validate_ns3_results.py` independently reconciled JSONL unique identities, generated samples, retries, duplicates, ACK failures, delay, throughput and hop means with the backend; CSV row counts matched.
- Every accepted NetAnim XML parsed with the expected sensor-plus-sink node count and wireless packet records. GUI playback was not tested because NetAnim GUI is absent.
- Live API run produced readings while status was running, rejected concurrent launch, stopped safely and persisted cancelled status. Completed REST replay inserted zero new events; invalid shell-like/unknown/unbounded configurations were rejected.
- Original 4 Cooja runs, 6,184 events and 887 readings matched the online pre-integration SQLite backup row for row. The existing 5/10 archived Cooja validators passed (279 and 530 unique receptions). C wire-format regression passed.
- Python suite: 15 tests passed, including all 8 original tests. One upstream Starlette/AnyIO deprecation warning remains.
- Production frontend build passed (1,943 modules); the approximately 641 kB minified chart bundle causes a nonfatal size warning.
- Browser checks: historical Cooja and NS-3 selection, comparison tables/graphs, live dashboard launch and data updates, stop and terminal status, light/dark themes. UI live run `90481933-b887-43bd-bef6-6342aa9076e5` showed 28 unique readings before cancellation at about 42.5 simulation seconds.

Machine-readable evidence is under `ns3/results/verification/`; each accepted run contains raw JSONL, manifest, XML, summary, CSV and PNG/SVG plots. The production database is intentionally excluded from Git; recordings can reconstruct NS-3 history through `scripts/ns3_bridge.py`.

## Development failures retained honestly

Earlier development recordings remain separate from the accepted matrix. The initial ACK reuse triggered a packet-tag assertion; creating a fresh ACK packet corrected it. An IPv6 documentation prefix was deliberately rejected by NS-3 forwarding; the private ULA prefix `fd42:1::/64` and disabled ICMP redirects corrected routing. The optional PHY post-reception error hook caused a native LR-WPAN assertion at 142.159 s; its failed output was retained and the supported configurable loss mechanism now explicitly uses UDP receive discards. The files `matrix-development-routing.json` and `matrix-development-phy-loss.json` are diagnostic, not successful acceptance evidence.

## Final continuation checks — 12 November 2026

The interrupted extra Cooja check encountered a cloud-offloaded generated dependency cache (`Operation timed out`). Those generated caches were preserved separately and rebuilt without changing firmware source. The fresh Cooja run `acbdaa34-e0e5-4ea3-a342-5c221384557c` passed TEST OK, all-five-sensors and multi-hop checks: 39 unique TX/RX, 100% PDR, 44.728 ms delay, 6 no-route samples. It was ingested with the unchanged Cooja bridge into the same production backend. Its evidence is under `ns3/results/verification/cooja-regression/`; original baseline outputs remain unchanged.

The previously interrupted NS-3 repeat retains its own record and is not counted as a successful run. A fresh repeat through `bash scripts/run_ns3_experiment.sh 5 --duration 300 --fast` completed. Final restart/reproducibility and original-row checks are recorded in `verification/restart-reproducibility.json` and `verification/preservation.json`.

Fifteen Python tests passed on 12 November, including all eight original tests, interrupted-job recovery, transactional path bounds, incomplete recording rejection, partial-artifact status handling and the distinction between a running process and final event ingestion. Execution artifacts are written atomically; unreadable optional console metadata does not change database status or fail the endpoint.

Browser evidence from 10 November is preserved in `verification/browser.json`: 390 px viewport and 390 px document width, both themes, repeated engine switches, comparison graphs, live launch/readings/cancellation, and CSV download of exactly 1,127 rows. No browser console errors were observed.
