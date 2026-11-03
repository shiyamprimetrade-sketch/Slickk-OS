# P0-016 — Kernel memory and power evaluation foundation

**Status:** read-only analysis and synthetic fixture tests VERIFIED locally, no physical-device or kernel-build evidence. Task depends on unmerged P0-002 and P0-007 draft PRs; the baseline and measurement assumptions are provisional pending integration.

## Source and compatibility baseline (checked 2026-10-31)

- Platform research baseline: Android 17 (`android-17.0.0_r1`), pinned by P0-002 on its draft PR; this is **not** the kernel version of the owner's phone.
- Android Common Kernel `kernel/common` official source: https://android.googlesource.com/kernel/common/ ; research branch `android17-6.18` at observed full commit `5a54d2ea7de67188274294d346e44a306e36cd03`: https://android.googlesource.com/kernel/common/+/5a54d2ea7de67188274294d346e44a306e36cd03 . Head is time-dependent; the immutable SHA is a *source-inspection* pin.
- Official Android 17 GKI **release family** `android17-6.18`, Sep-2026 build tag `android17-6.18-2026-09_r9` (Oct 21 release). See https://source.android.com/docs/core/architecture/kernel/gki-android17-6_18-release-builds . This release tag is distinct from the research branch commit above. No local clone or cryptographic verification of downloaded kernel objects was performed.
- Compatibility matrix and support: https://source.android.com/docs/core/architecture/kernel/android-common . Kernel family must match platform support and device KMI, module toolchain/config and vendor modules; same Android platform version **does not** imply image compatibility.
- GKI/KMI: https://source.android.com/docs/core/architecture/kernel/stable-kmi and https://source.android.com/docs/core/architecture/kernel/modules . Audit KMI version/generation, symbol allowlist/ABI, `uname -r`, vendor module `vermagic`, symbol dependencies, module partition, `vendor_boot`, vendor_dlkm, DT/DTBO, boot header, VINTF, SELinux/AVB, board firmware and vendor drivers. Runtime checks and VTS/CTS are required before any support claim.
- Build docs: https://source.android.com/docs/setup/build/building-kernels ; obtain official `kernel/manifest`, pin the manifests for GKI and toolchains, use Linux x86_64, Repo, Git, Bazel/Kleaf, Clang/LLVM, required host libraries, storage and RAM. An illustrative supported source-tree build target is `tools/bazel run //common:kernel_aarch64_dist` with optional destination; **not run** here and target must be confirmed in checked-out manifest.
- License: Linux kernel GPL-2.0-only where indicated; individual files may have other SPDX licenses including dual-license terms. Preserve per-file SPDX and `COPYING`, NOTICE/attribution and third-party obligations. No kernel code redistributed or changed here; this Python utility is project-authored.

## Executable commands (run at repository root)

```sh
python3 -m unittest discover -s kernel/tests -v
python3 kernel/analyze.py memory kernel/fixtures/meminfo.txt
python3 kernel/analyze.py cpu kernel/fixtures/stat_before.txt kernel/fixtures/stat_after.txt
python3 kernel/analyze.py power kernel/fixtures/power.json
python3 kernel/analyze.py config kernel/fixtures/config.txt --output /tmp/p0-016-config.json
```

All five fixture files in `kernel/fixtures/` are **SYNTHETIC**. Success exit code `0`; invalid/unreadable evidence returns `2`. Reports use JSON, carry `task=P0-016`, and are NOT proof of source provenance. The memory tool optionally accepts `--psi /proc/pressure/memory` and `--vmstat /proc/vmstat` *saved* text inputs. CPU requires two ordered `/proc/stat` snapshots; optional `--process-before` and `--process-after` accept the *same* `/proc/PID/stat` process with stable `starttime`. Power requires JSON `dataset_kind`, ordered samples (`t_s`, `battery_pct`, `charging`) and optionally cumulative `wakeups` and `suspend_s`. Do not place private identifiers in public snapshots. Do not use rootshell or modify the phone to collect data.

**Limitations:** snapshot memory ≠ per-process PSS; PSI `avg10/60/300` is historical pressure, not a performance win; CPU busy time ≠ scheduling latency, frequency or energy. `drain_percentage_points_per_hour` uses coarse state-of-charge, not calibrated energy. Power needs external/properly attributed counters and controlled repeated sessions. Missing data are unknown, never zero. Config checks are diagnostic; `enabled` is not a required/universal pass condition. No kernel binary, KMI, driver, boot or power gain is certified.

## Research-to-measurement mapping

| Domain | Reference mechanisms | Read-only evidence or next experiment |
|---|---|---|
| Scheduling | CFS history, EEVDF current branch implementation, schedutil/cpufreq, EAS, uclamp, cpuset/task profiles | Perfetto sched slices, per-CPU frequencies, runnable-to-running latency, wakeup histograms, foreground cold starts; profile thermal state |
| Memory | VM reclaim, page cache, slab, fragmentation, zram/swap, PSI, memcg, Android lmkd | meminfo, vmstat deltas, PSI, cgroup memory.events, OOM/lmkd log, per-app PSS and recovery latency under *reversible* lab stress |
| Power | CPU idle states, suspend/resume, alarm/timer frequency, wakeup sources, thermal governors | matched 8h unplugged idle sessions, wakeup and suspend counters, calibrated external energy where possible, temperature/network/ambient metadata |
| GKI compatibility | stable KMI ABI and symbol allowlist, module signatures, vendor_boot, VINTF, AVB | kernel/config metadata followed by module symbol/ABI checks, virtual boot tests, CTS/VTS, real-device test only after separate approval |

**Hypotheses only:** less background wakeup activity, finer reclaim tuning, or better foreground scheduling *might* improve smoothness or idle drain. Counter-hypotheses include app regression, OOMs, thermal throttling, battery worsening and vendor-driver failures. Do not apply a patch until before/after controlled trials.

## Reproducible no-regression gates (no passes claimed)

1. **Boot and startup:** unmodified GKI baseline and candidate boot Cuttlefish repeatedly; boot time, panic, dmesg regressions, verified recovery and cold-start app suite recorded. Reject any failure.
2. **Memory stability:** compare matched app PSS, MemAvailable, PSI, swap, lmkd kills/OOM, page reclaim/fragmentation across idle, camera, browser, memory-pressure workload; no new app failure or sustained pressure regression.
3. **CPU responsiveness:** Perfetto dispatch/wakeup-to-running p50/p95, app start, frames, sched and cpufreq; compare ≥5 sessions, thermal controlled. No critical latency regression.
4. **Thermal:** log ambient, sensor calibration, temperatures, throttling intervals under equivalent charging/state and workload; no higher sustained thermal load or safety limit violations.
5. **Battery:** ≥3 matched **8-hour** idle sessions per variant initially; identical phone, battery health, display/network/background setup, randomized test order; log uncertainty. No conclusion from a single percentage sample or synthetic dataset.
6. **Android app compatibility:** selected app suite with exact versions + API/ABI tests; VTS/CTS as applicable; reject crash, permissions, IPC/Binder, accessibility or telephony regressions.
7. **Drivers:** verify device/board-specific radio, Wi-Fi, Bluetooth, camera, audio, storage, GPU, sensors, charging and suspend wake sources. No blanket compatibility assertion.
8. **Security:** AVB, SELinux enforcing, seccomp, module verification/signing, KMI ABI, proper partitions, security bulletin maintenance and vulnerability scan; reject weakening controls.
9. **Recovery:** verified backups, boot image/OTA rollback, rescue/fastboot paths, A/B fallback where available; no flashing without fresh owner authorization and recovery proof.

**Integration gate:** reconcile kernel source selection with merged P0-002; use P0-007 metric schema for matched Android-vs-candidate comparisons. P0-016 only establishes the read-only evaluation foundation; does not complete those platform/device milestones.
