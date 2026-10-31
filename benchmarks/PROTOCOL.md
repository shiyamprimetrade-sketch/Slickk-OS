# P0-007 — Reproducible Performance Measurement Protocol v1.0

**Status:** Implemented benchmark processing infrastructure; NO REAL DEVICE RESULTS. Bundled data are SYNTHETIC. P0-008 device observation collection is a separate, unstarted task.

## 1. Experimental design and matched Android baseline

1. Preregister workload, metric, instrument/version, decision threshold, device/build, app/version, source commit, and exact scripted success criteria before collecting results. Preserve raw exports (Macrobenchmark, Perfetto, ADB) and their hashes in a separate evidence manifest; `evidence_ref` is only a reference and does not prove provenance.
2. Prefer the **same physical device**, pin brightness, refresh rate, thermal and power modes, connectivity, app version, user settings, locale, background services, permissions, compilation mode, battery health, test procedure, charging state and ambient conditions. Alternate or randomize Android/candidate AB/BA order, allowing cool-down periods. Document uncontrolled factors; withhold claims if confounded.
3. `android` means baseline stock Android; `slickk-os` denotes the candidate under experiment. A candidate launcher APK still runs on Android and is **not** a new OS build. Permit different `os_build` strings while requiring controlled conditions to match. Device ID is a locally assigned pseudonym; do not use IMEI, serial, Android ID or private user data.
4. Iterations are independently repeated sessions. Matched iteration identifiers denote AB/BA pairs. Avoid pseudoreplication (e.g., thousands of adjacent rendered frames are not thousands of independent sessions). Frames within a session must be aggregated to a session-level statistic before insertion.
5. Pilot floor: 5 iterations per variant for UI, memory, UX and reliability; 3 independent **8-hour** sessions per variant for idle battery. These floors are *not* evidence of statistical power or non-inferiority, particularly for rare crashes. Increase sample count, estimate uncertainty and investigate CV above 20%.
6. The machine-readable schema is in `benchmarks/schema.json`. JSON requires `{"schema_version":"1.0","observations":[...]}`; CSV requires all observation fields plus `schema_version`. `dataset_kind=device` is producer-asserted and **not authenticated**; all provided fixture rows have `dataset_kind=synthetic` and `synthetic:` evidence references.

## 2. Workloads, metrics and measurement boundaries

| Category | Example workload | Metric | Measurement rule |
|---|---|---|---|
| Cold application launch | camera_cold_launch | startup_cold_ms | Time to initial display frame; Macrobenchmark StartupMode.COLD (process killed before launch) |
| Warm application launch | camera_warm_launch | startup_warm_ms | Activity restart with process kept; Macrobenchmark StartupMode.WARM |
| Responsiveness | settings_toggle | ui_action_ms | Scripted input to visible result; P50/P95 across independent trials |
| Memory | camera_pss | memory_pss_kib, allocation_bytes | Same screen/GC stage; ADB dumpsys meminfo, allocation profiler |
| Low-memory/recovery | camera_recovery | recovery_ms, crash_count | Declared pressure limit, kill/recovery state; never silently stress owner device |
| Battery/idle | eight_hour_idle | idle_drain_pct_per_hour, energy_mwh | Unplugged ≥480-minute windows; calibrated external/rail energy where available; battery percentage is coarse |
| Background energy | background_sync | background_energy_mwh, thermal_peak_c | Fixed session, duty cycle, thermal/ambient conditions and network |
| Frames/jank | launcher_scroll | frame_time_ms, frame_jank_pct | Perfetto FrameTimeline on Android 12+; missed deadline / eligible frames ×100 per session |
| Reliability | one_hour_stress | crash_count, anr_count, recovery_ms | Same exposure seconds, logcat and reproducible failure definitions |
| User experience | open_wifi_settings | ux_steps, ux_task_ms | Complete identical task; count intentional taps/gestures and record success/errors |
| Accessibility | talkback_settings | accessibility_pass_pct | Frozen TalkBack/large-text critical journey suite; no hidden required controls |
| Compatibility | priority_app_suite | compatibility_pass_pct | Frozen app versions, APIs and cases; CTS/VTS only if truly run |
| Privacy | permission_audit | privacy_violation_count | Audited permissions/network collection; no tracking by default; absence of evidence is not a pass |

### M04 graphics reconciliation

Older `docs/BENCHMARKS.md` called this “P95 frame jank,” which is not a well-defined observable. Under the P0-001 charter's proposed interpretation, **`frame_jank_pct` = missed-frame fraction per session** and its **median** must improve at least 20% for a provisional target result. Publish **P95 frame duration** separately. No frame/smoothness improvement has actually been measured.

## 3. Statistical and validity gates

- Strictly reject bad units, missing fields, nonfinite/negative numbers, nonintegral counts, invalid UTC timestamps, duplicates, and invalid evidence labels. Battery idle sessions need `exposure_s >= 28800`. Event and background-energy exposure must be positive.
- Require matched device/model/type, test/app version, scenario/profile, network, brightness, display refresh and exposure. Initial thermal difference ≤2°C and battery SoC difference ≤5 percentage points. Mismatches or unpaired runs produce `INCONCLUSIVE`, never a performance win.
- Summarize count, minimum/maximum, arithmetic mean, median (P50), P95 using linear interpolation (type 7), sample standard deviation and CV. For latency and frame duration use P95; for energy, memory, steps and jank fraction use median; for event counts use P95. A critical single crash/ANR or accessibility failure blocks release regardless of aggregate.
- For lower-is-better metrics, improvement % = (baseline aggregate − candidate aggregate) / baseline aggregate ×100; higher-is-better pass rates reverse sign. A zero baseline is not a valid relative-percentage denominator. Regression default is deterioration greater than 5%; counts and pass-rate guardrails have zero-tolerance when their selected aggregate worsens.
- The analysis result is **INCONCLUSIVE**, **NO_CLEAR_CHANGE**, **REGRESSION**, **NO_CHANGE** or **IMPROVEMENT_CANDIDATE**. The latter is exploratory numeric evidence only, never proof of real-world superiority; reports always set `claim_allowed=false`. Provenance, statistical uncertainty and all reliability/compatibility/privacy guardrails require separate review.
- Exploratory charter targets only: ≥20% lower P95 launch/task latency; ≥15% less median matched idle energy; ≥25% fewer UX actions; ≥20% lower median missed-frame fraction. These are HYPOTHESES, not achieved results.
- Battery Historian/batterystats estimates attribution and are not automatically calibrated energy. Screen state/charging status/ambient conditions require separate raw evidence. Public CI only runs synthetic fixtures; keep trace archives and user data local or private.

## 4. Reproducible commands from repository root

~~~sh
python3 -m unittest discover -s tests -p 'test_benchmarks.py' -v
python3 benchmarks/analyze.py benchmarks/fixtures/synthetic_comparison.json --output benchmarks/reports/synthetic_summary.json
python3 benchmarks/analyze.py benchmarks/fixtures/synthetic_regression.csv --fail-on-regression
~~~

A valid input reports JSON and exits 0. Invalid input exits 2. `--fail-on-regression` exits **3** on a synthetic regression (expected negative-control result). Committed summary JSON is deterministic; workflow independently reproduces and diffs it.

## 5. Official tools, status and handoff

- Android Macrobenchmark: https://developer.android.com/topic/performance/benchmarking/macrobenchmark-overview
- Perfetto FrameTimeline: https://perfetto.dev/docs/data-sources/frametimeline
- Android battery profiling: https://developer.android.com/topic/performance/power/setup-battery-historian

The processor does NOT collect Android traces or certify source provenance. Actual Android 12+/device capture and P0-008 baseline observations remain separate future assignments. P0-001 implementation was reported complete on task branch and PR #2, but its merge into the foundation/main branch was still pending at the start of this task. Reconcile any revised target definitions before integration. No ROM, APK, bench hardware result or privacy audit is claimed.
