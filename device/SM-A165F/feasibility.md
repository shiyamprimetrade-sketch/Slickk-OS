# P0-003 — SM-A165F feasibility and read-only audit

**Role:** Chat 06 | **Dependency:** P0-001 implemented on draft PR #2, unmerged | **Baseline:** foundation draft PR #1, unmerged | **Evidence date:** 2026-10-31.

## Evidence and decision

- **USER-REPORTED:** Samsung `SM-A165F`, Android `16`, `arm64-v8a`. Physical `getprop`/`uname` observations have not been provided. The checked-in `matrix.json` therefore marks 17 functional subsystems UNKNOWN and physical boot UNTESTED.
- **VERIFIED (source/specification only):** Android divides system and vendor code across partition and interface boundaries; VINTF matches the device manifest to framework compatibility matrices and vice versa. Stable AIDL is required for AIDL HAL IPC crossing vendor/system. Android GKI separates common kernel and vendor modules subject to KMI compatibility. Sources below.
- **UNTESTED:** exact SM-A165F firmware, current kernel, board DTS, vendor and ODM manifest fragments, VINTF matching, AIDL/HIDL service availability, KMI compatibility, supported recovery and phone boot. Presence of declared HAL XML never proves a working peripheral.
- **HYPOTHESIS:** optimized startup or batching may improve wakeups and energy. No benchmark or hardware change has been performed.
- **DECISION:** Cuttlefish first for full AOSP boot. On-device APK development may be independent of flashing. A GSI is **not** a validated ROM and requires separate Treble, unlock, partition and recovery checks.

## Three deployment levels

| Level | Uses stock vendor firmware | Bootloader operation | Evidence gate |
|---|---|---|---|
| APK launcher on existing Android | Yes | None | APK permission, functionality, accessibility tests |
| Generic System Image (GSI) | Usually retains target vendor implementation | Often requires unlocking and destructive partition operations | OEM-specific verified instructions, matching VINTF, recovery and owner permission |
| Device-specific AOSP operating system | Must integrate licensed, matching vendor/ODM modules and firmware | Device-specific verified boot chain and recovery | Device tree, kernel/KMI, HAL functionality, radio, security and CTS/VTS testing |

## Hardware route — reference architecture, NOT observed SM-A165F state

| Subsystem | Framework/native path | HAL/IPC contract | Kernel/vendor dependency |
|---|---|---|---|
| CPU/memory | ActivityManager, lmkd, PowerManager | Power AIDL HAL, Binder | scheduler, cpufreq, memory controller, thermal driver |
| Display/touch | WindowManager, SurfaceFlinger, InputReader | Composer/allocator; input events | DRM/display stack, touch driver, vendor panel init |
| GPU | SurfaceFlinger, HWUI, Vulkan/EGL | Composer, allocator/gralloc | GPU kernel module, userspace libraries, firmware |
| Camera | CameraService, Camera2 | camera provider/device HAL | sensor, ISP, autofocus, vendor algorithms and firmware |
| Audio | AudioFlinger, AudioPolicy | audio core HAL | ALSA, codecs, routing, DSP |
| Wi-Fi/Bluetooth | Wi-Fi framework/stack, Bluetooth stack | Wi-Fi HAL, Bluetooth HAL | wireless driver, controller and regulatory firmware |
| Cellular/SIM | Telephony framework, Radio service, IMS | radio HAL / vendor modem services | baseband, modem transport and vendor IMS; private identifiers excluded |
| Location | LocationManager, GNSS service | GNSS HAL | GNSS chipset/firmware, radio coexistence |
| Sensors | SensorManager, SensorService | sensors HAL | IIO/input drivers, sensor hub and calibration |
| Storage/USB | vold, StorageManager, USB framework | USB HAL; block/filesystem interfaces | UFS/eMMC, filesystem encryption, USB controller |
| Battery/charging | BatteryService, PowerManager | health and power HALs | fuel gauge, thermal, charger drivers |
| Biometrics/TEE | BiometricService, Keystore2 | fingerprint, KeyMint, Gatekeeper | secure firmware/TEE, trusted app and hardware |

These interface family names are architectural targets. The actual chosen AIDL/HIDL versions and HAL instances must be read and matched for each shipped firmware build.

## Read-only usage

From a Termux session that has Python 3 available, inside the cloned repository:

```sh
python3 -m unittest discover -s device/tests -v
python3 device/tools/compat.py validate device/SM-A165F/matrix.json
sh device/tools/inspect.sh sm-a165f-local.json termux
python3 device/tools/compat.py validate sm-a165f-local.json
```

From an authorized development computer with ADB, Python 3 and an attached device:

```sh
adb devices
sh device/tools/inspect.sh sm-a165f-local.json adb
```

The script executes **only** allowlisted `getprop` keys, `uname -r`, and reads four fixed VINTF XML paths. It keeps only recognized `android.hardware.*` HAL package names, not the raw XML, private logs, personal files, unique identifiers or full property dumps. Missing permission, absent manifest file or inaccessible shell command leaves data UNKNOWN; no diagnosis of hardware absence follows. VINTF fragments and runtime service registration are NOT yet inspected; this tool does not perform full `checkvintf` matching.

The generated local JSON should be reviewed before it is ever shared; it is not automatically uploaded. It intentionally contains no firmware flash commands. `collect` refuses an unexpectedly different device model. Running under ordinary Android app permissions can yield less information than ADB; a failed read does not mean the hardware feature fails.

## Feasibility gates and missing evidence

| Gate | Current status | Required before a phone build/flash |
|---|---|---|
| Bootloader unlock eligibility | UNKNOWN | Official exact-model/region policy; safe restore procedure, owner permission |
| Kernel source | UNKNOWN | Exact stock firmware build matched to Samsung OSRC release and licensing |
| Device tree/product config | UNKNOWN | Reviewed DTS, init, fstab, SELinux, board build configs |
| Vendor modules/firmware | UNKNOWN | Available permitted images, module dependency graph and matching GKI/KMI |
| Treble/VINTF/HAL | UNKNOWN | Actual manifest fragments; target FCM and matrix match; service/VTS tests |
| Recovery/boot path | UNKNOWN | Independently validated backup, AVB constraints and recovery workflow |
| Complete OS physical boot | UNTESTED | AOSP/Cuttlefish build first; then explicit, separate device authorization |

Public third-party kernels mentioning `SM-A165F` exist, including `Kernels-by-ravindu644/samsung_kernel_a165f`, which describes a Samsung-derived `5.10.226` base for a particular older build and assumes an already-unlocked phone. This is **not authoritative proof** that a matching kernel source or bootloader-unlock method exists for the owner's Android 16 firmware; do not download or flash such artifacts as part of this task.

## Candidate efficiency experiments — untested and reversible

| Candidate | AOSP baseline behavior | Suspected cost (hypothesis) | Controlled test and rollback |
|---|---|---|---|
| Lazy initialization of optional HAL clients | ServiceManager / AIDL service discovery and registration | Unused clients may add cold-start CPU and memory | Perfetto boot trace: time-to-ready, Binder transactions, faults, retained RSS, failed HAL lookups; rollback if startup or radio/camera availability regresses |
| Reduce repeated sensor delivery at low demand | Sensors HAL / SensorService batching and wake-up semantics | Frequent events may cause excess application processor wakeups | Hold sampling latency and correctness constant; count interrupts, wakeups and battery drain across matched runs; rollback on loss of event fidelity or privacy controls |
| Avoid redundant GPU/display work | SurfaceFlinger, composer transactions and frame scheduling | Unnecessary composition could increase CPU/GPU cycles | Perfetto + frame timeline and controlled workloads; reject if jank, visual correctness, thermal or CTS/VTS worsens |
| Restrict unused vendor module loading where supported | GKI/vendor modules and first-stage init | Modules can have boot/memory cost | Compare reproducible boot trace and module load logs in a virtual/device lab; reject if module dependencies, recovery, radio, security or KMI change |

No patch, measurement, claimed battery gain or functional HAL driver is part of P0-003. Changes must preserve Stable AIDL versions, service registration, vendor/system separation, VINTF match, SELinux, boot security and kernel KMI. Any implementation gets a feature flag and a testable rollback to stock behavior.

## Provenance and test

- AOSP: [VINTF objects](https://source.android.com/docs/core/architecture/vintf/objects), [compatibility matching](https://source.android.com/docs/core/architecture/vintf/match-rules), [Stable AIDL](https://source.android.com/docs/core/architecture/aidl/stable-aidl), [AIDL HALs](https://source.android.com/docs/core/architecture/aidl/aidl-hals).
- AOSP: [system/vendor partitions](https://source.android.com/docs/core/architecture/partitions), [GKI/KMI](https://source.android.com/docs/core/architecture/kernel), [kernel modules](https://source.android.com/docs/core/architecture/kernel/modules).
- AOSP: [GSI requirements](https://source.android.com/docs/core/tests/vts/gsi), [Cuttlefish](https://source.android.com/docs/devices/cuttlefish).
- Test: `python3 -m unittest discover -s device/tests -v`; synthetic passing tests validate the validator, not device support.

**Rollback:** close the draft task PR; no physical device state is changed. Next physical evidence is an opt-in local sanitized capture, not a ROM installation. Task P0-019 remains out of scope pending separate assignment.
