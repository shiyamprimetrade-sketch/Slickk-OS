# P0-017 — Networking benchmark protocols

Tooling: `../media/tools/bench.py`, metric catalog `../media/metrics.json`. Network tests are **plans**, not measurements. No endpoint connections, captures, scans, radio or Android network-state changes have been executed for P0-017.

## Controlled capture matrix

| Scenario / session | Output metric | Allowed capture and controls |
|---|---|---|
| DNS cold/warm lookup on a test resolver under explicit control, pinned record, negative cache case separately | `dns_lookup_ms` | Application-level timing around name resolution; set resolver, cache warm/cold, network type, DNS mode and TTL in conditions; no private-domain enumeration |
| TCP SYN/handshake to an owned service, IPv4/IPv6 independently | `tcp_connect_ms` | monotonic elapsed time, pinned destination address/port, timeout, TLS excluded unless separate workload |
| Fixed-size upload/download to a local authorized test server | `network_throughput_mbps` | controlled capped bandwidth/duration, bytes and elapsed seconds; no saturation of third-party infrastructure |
| 100 bounded periodic request/replies to controlled endpoint | `network_rtt_ms`, `network_jitter_ms`, `packet_loss_pct` | monotonic RTT; define jitter as RFC 3550-style interarrival variation or sample absolute consecutive RTT differences *before* capture; fixed definition in profile, loss denominator tracked, max 100% |
| Wi-Fi↔cellular or validated Wi-Fi AP transition with explicit consent and stable server | `network_recovery_ms` | Android ConnectivityManager network callbacks + end-to-end application request restoration; record trigger and timeout, prohibit forced switches on owner's phone |
| Repeated short low-duty-cycle network tasks | `energy_mwh` | calibrated power monitoring and workload isolation, same transport/radio signal/charging condition |

**Repetitions:** at least 5 independent AB/BA session pairs; do not present 100 packets as 100 independent trials. Include `conditions` such as `{ "protocol":"tcp", "server_id":"lab-1", "payload_bytes":1048576, "ip_family":"IPv4", "resolver":"lab", "signal_band":"stable" }`. Never store private SSIDs, IPs that identify people, account credentials, payloads, IMEI, MAC or packet captures in public fixtures. Keep host measurements marked `host`, and distinguish system-connected Wi-Fi/cellular from userland controlled endpoints.

## Official architecture/compatibility notes

- AOSP [Network Stack module](https://source.android.com/docs/core/ota/modular-system/networking) contains IpClient/DHCP and captive-portal/provisioning components, with Mainline module and stable AIDL boundaries. A normal APK cannot modify these internals.
- Android SDK [ConnectivityManager](https://developer.android.com/reference/android/net/ConnectivityManager) and [NetworkCallback](https://developer.android.com/reference/android/net/ConnectivityManager.NetworkCallback) expose network state and transport observations subject to API/permission/lifecycle limitations. They do not prove TCP/UDP delivery or validate RF throughput by themselves.
- System connectivity policy, netd, DNS resolver and kernel TCP/UDP interact with Wi-Fi, cellular and Bluetooth vendor services. Handovers depend on OS policies, radio support, current subscription, VPN/private DNS and environmental conditions; do not attribute all changes to a single stack layer. Multicast, Bluetooth PAN and cellular VoLTE are distinct workloads requiring separate supported-device evidence.

The actual upstream [ConnectivityService.java](https://android.googlesource.com/platform/packages/modules/Connectivity/+/refs/heads/main/service/src/com/android/server/ConnectivityService.java) source was inspected from moving `main`, Gitiles blob `c870edc94f59c1e722b478dab9aa138c0df17ddf`. It explicitly references network callbacks, background restrictions and DNS/TCP diagnostics. This identifies architecture boundaries, not verified optimization headroom. No fixed release commit or physical network capture was inspected.

## Security, power, compatibility and rollback gates

Test with an owned server only, fixed payload/connection cap, conservative timeouts and user consent for network changes. No unauthorized scanning, packet interception, DNS diversion, certificate bypass or traffic interception. Preserve VPN, firewall, private DNS, proxy, captive portal, metered/roaming policy, IPv4/IPv6, DoH/DoT when configured, accessibility and app network permissions. Compare handover recovery, packet loss, retry behavior, CPU cost, battery and reconnection success; fail any security or functionality degradation even if latency appears better. No production stack changes are proposed; rollback for any future flag-guarded optimization is flag off/revert patch and repeat matched smoke/CTS/network tests.

Hypotheses only: fewer duplicate DNS resolutions, less redundant connectivity polling, improved cross-network retry pacing. Each must first be demonstrated in actual traces, then individually benchmarked and audited for privacy, compatibility and battery consequences. P0-007 draft protocol is provisional, and physical capture remains untested.
