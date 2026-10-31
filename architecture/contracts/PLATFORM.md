# Slickk-OS platform compatibility contracts — P0-002 development baseline

**Reference:** `architecture/baseline/pins.json`; Android 17 (API 37), `android-17.0.0_r1`. These are *design contracts*, not an implemented replacement framework. A boundary may be altered only after its actual AOSP source revision, users, performance traces and regressions are documented.

| Layer | Keep / interface contract | Experiment and verification gate |
|---|---|---|
| Boot / init | Android first-stage init, partition/AVB integrity, SELinux enforcing policy, controlled boot services | Changes need verified Cuttlefish cold/warm boot, rollback and anti-rollback preservation |
| Framework / apps | API 37 SDK and existing API behavior; permissions, package manager, intents, lifecycle, non-SDK restrictions | CTS and representative unmodified real apps; no changed signatures or silent permission bypass |
| Runtime | Pinned ART, dexopt, class loading, JNI, APEX dependencies | ART unit/integration tests, startup latency, crash/ANR and ABI regression checks |
| Process / IPC | Binder/AIDL transaction behavior, ActivityManager/AMS and system server policy | Race/deadlock testing, process death/restart, same-version IPC and background limits |
| Graphics | SurfaceFlinger, HWComposer/Vulkan/OpenGL contracts, input and accessibility | Frame pacing/jank, screenshot fidelity, touch latency, screen reader and media DRM tests |
| HAL / devices | Stable AIDL/HIDL where required, Treble and matching VINTF matrices; no vendor blob assumption | VTS, manifest/compatibility matrices; per-device kernel and vendor partition audit |
| Kernel / memory | Target-appropriate Android GKI/KMI, scheduler, cgroups, low-memory killer and oom policy | Kernel tests, sustained memory pressure, leak and device battery/thermal benchmarks |
| Background / power | Doze, JobScheduler, alarms, notifications and foreground-service expectations | Repeatable wakeup/idle drain tests; preserve timely critical notifications and accessibility |
| Storage / updates | FBE/fscrypt user isolation, scoped storage, partition/update/recovery contracts | OTA and rollback rehearsal, integrity checks, cold reboot; never flash real phone without consent |
| Privacy / telemetry | Consent, sandbox, AppOps, permission UI and minimal local observability | Threat model and permission matrix; opt-in telemetry; prevent exfiltration or identifier expansion |

## App/deployment modes

- **Slickk Experience APK:** can only use documented SDK APIs/permissions; no privileged platform changes on stock Android. This is a separate build and has no implication of shipping a custom OS.
- **Slickk Platform image:** compile unmodified pinned AOSP in Cuttlefish first. Package compatibility must be demonstrated with Android 17 CDD, CTS, VTS when applicable, and a versioned priority app suite.
- **Physical ports:** each model is separate; test boot, telephony, camera, radio, sensors, Wi-Fi, Bluetooth, audio, modem and graphics. No generic Samsung compatibility claim.

## Change review contract

Every optimization proposal must identify AOSP repository + immutable commit + file(s), dependency/caller analysis, benchmark hypothesis, controls, expected benefit, test list, security and accessibility impact, kill-switch or one-commit rollback, and evidence artifacts. Unknown dependencies block deletion. Performance wins are not inferred from reduced line count. Use comparable devices and repeated trials; Perfetto and Android Macrobenchmark should provide raw traces before concluding improvements.

## Baseline acceptance vs release gates

P0-002: tag, immutable source provenance, API, licensing, virtual-device source and source-verifier tests. Phase 2: full reproducible image build/boot and resolved repo manifest. Later: CTS/VTS, device port, hardware recovery, signed updates, current security fixes and benchmarks. None of the latter are declared complete by this document.
