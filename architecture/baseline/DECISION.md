# ADR P0-002 — Pinned AOSP development baseline

**State:** IMPLEMENTED AS SOURCE PIN; not merged, built, booted, or release-certified.
**Author:** Chat 01, Chief Architect. **Date:** 2026-10-31.
**Task:** P0-002. **Rollback:** revert this ADR, the `pins.json` lock and associated verification; return to baseline-unselected. No device state changes.

## Decision and exact provenance

Select Google's open-source **Android 17 / API 37** **`android-17.0.0_r1`** as the first reproducible source-development baseline, not as a production-ready firmware or October-patched image. Official build `CP2A.260605.016` has published security patch level `2026-06-05`. `pins.json` stores the manifest annotated Git tag object (`7a9e46ba6ed424f922a3457f4964e67e0b966201`), its peeled commit (`5bc9a7ce1cd78dd53613bbfd0ebf506e1e4adb0f`), `default.xml` Git blob (`f8c6b343b51c94693108dcefb6bc41f51ae24791`), and the annotated tag objects and peeled commits for ART, framework base, build/make, system/core, and Cuttlefish.

**Manifest is the root source lock, not a single commit for the whole tree.** Its `<default revision="refs/tags/android-17.0.0_r1">` determines each tagged project; `build/make` has source repository `platform/build` rather than `platform/build/make`. All projects must still be resolved to immutable SHAs during a full `repo sync` and exported with `repo manifest -r` for a fully frozen checkout. The verifier checks an audited high-risk subset and the manifest blob; it does not certify every project transitively.

Official reference records (accessed 2026-10-31):

- `https://android.googlesource.com/platform/manifest/+/refs/tags/android-17.0.0_r1`
- `https://android.googlesource.com/platform/manifest/+/refs/tags/android-17.0.0_r1/default.xml`
- `https://android.googlesource.com/platform/art/+/refs/tags/android-17.0.0_r1`
- `https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1`
- `https://android.googlesource.com/platform/build/+/refs/tags/android-17.0.0_r1`
- `https://android.googlesource.com/platform/system/core/+/refs/tags/android-17.0.0_r1`
- `https://android.googlesource.com/device/google/cuttlefish/+/refs/tags/android-17.0.0_r1`
- `https://source.android.com/docs/setup/reference/build-numbers`
- `https://developer.android.com/guide/topics/manifest/uses-sdk-element`
- `https://source.android.com/docs/compatibility/17/android-17-cdd`
- `https://source.android.com/docs/devices/cuttlefish/cts`

## Alternatives and trade-off

- Android 16 (API 36): older, may suit some vendor targets but locks earlier framework expectations and requires a separate regression/maintenance track. Not selected until demonstrated need.
- Rolling `aosp-android-latest-release`: useful to discover fixes, **not reproducible** as a permanent source pin. Rejected for baseline.
- Android 17 release tag: API 37 and exact immutable identifiers; needs ongoing upstream security patches and availability of suitable build infrastructure. Selected for **development** only.

The October 2026 Android Security Bulletin requires 2026-10-01 or newer security fixes. This June-tagged source **does not qualify as patched**, and the source tag alone must never be used to claim a security patch level or shipping readiness. Before production, integrate applicable fixes with a separately versioned patch manifest, perform security review, and pass compatibility/regression testing. Reference: `https://source.android.com/docs/security/bulletin/2026/2026-10-01`.

## Cuttlefish reproducibility and hard boundary

Official Cuttlefish target exists: `aosp_cf_x86_64_only_phone-userdebug`. On a Linux x86_64 builder provisioned under build/virtualization documentation:

```bash
# Ubuntu/Linux x86_64. Do not run on the daily phone.
mkdir -p "$HOME/aosp17" && cd "$HOME/aosp17"
repo init -u https://android.googlesource.com/platform/manifest -b android-17.0.0_r1
repo sync -c -j4
python3 PATH_TO_SLICKK_OS/architecture/baseline/verify.py --remote --checkout "$HOME/aosp17"
repo manifest -r -o "$HOME/aosp17-resolved.xml"
source build/envsetup.sh
lunch aosp_cf_x86_64_only_phone-userdebug
m -j$(nproc)
# Only after virtualization and host cuttlefish tools are installed: launch_cvd
```

Google documents approximately **400 GB free disk** and **64 GB RAM** for AOSP builds, plus an appropriate virtual-device host. No project builder, Cuttlefish boot, CTS/VTS, or physical-phone vendor compatibility was verified as part of this task. The launch is a subsequent separate gate, not a claim in P0-002.

## Verification gates and results

1. Official release and API evidence; published AOSP annotated tag object, peeled commit and manifest XML paths: **PASS by source inspection**.
2. Executable pin validation with negative cases and real Git-tag fixture: **PASS locally; see test log in task PR**.
3. Actual remote Git tag revalidation, full checkout/`repo manifest -r` and build: **NOT RUN successfully: this execution container cannot resolve android.googlesource.com**.
4. Cuttlefish product presence: **SOURCE-VERIFIED; not built**.
5. App compatibility: Android 17 CDD/CTS required, not executed; CTS cannot be inferred from source pin.
6. Security patch currency: **FAIL FOR PRODUCTION**, tagged June 2026, October bulletin exists.

## Licensing and distribution

AOSP is a combination of differently licensed projects. Preserve file-level copyright/NOTICE and use `repo forall` / per-project `LICENSE`, `NOTICE`, `MODULE_LICENSE_*` and SPDX records for a dependency-specific bill of materials before distributing binaries. Significant Android userspace is Apache-2.0, Linux kernel components use GPLv2 and possibly other licenses. Do **not** assume a monolithic license or permission to redistribute proprietary vendor firmware, modem bits, device blobs, or Google Mobile Services. Google Play compatibility, certification and licensing are **not** implied by AOSP CTS success.

## Port and rollback policy

Cuttlefish is the only proposed initial system-image target. The owner's Samsung SM-A165F remains **unsupported/unverified** for a custom OS image until device tree, bootloader feasibility, GKI/KMI, vendor HAL/VINTF, proprietary licenses, partitions, radio stack, recovery, and explicit flash consent are independently confirmed. Do not use debug Cuttlefish signing keys for production. Roll back source changes by restoring this manifest/tag; roll back optimizations with independent feature flags and test all security invariants.

## Acceptance summary

The **upstream source baseline is pinned with exact, published upstream object identifiers, license constraints, APIs, source-defined virtual-device target, executable validators, and an explicit rollback plan**. This meets the bounded P0-002 source-pin contract, not the separate Phase 2 Cuttlefish build/boot gate. Status: implementation complete on task branch when tests and PR commit are verified; pending merge/integration review.
