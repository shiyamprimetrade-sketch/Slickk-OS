# P0-013 - Android framework contract baseline (provisional)

Goal: static compatibility validation, not a replacement framework or proof of Android app compatibility.

## Source basis
- AOSP Android 17 API 37 tag android-17.0.0_r1, frameworks/base commit 94b4c163b7dfe5ce3607f7bb8456f9573f7de57d; official tag index: https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1
- P0-002 branch architecture/baseline/pins.json supplies the proposed release decision; PR #3 not merged.
- Official AOSP SystemServer and ActivityThread HEAD pages were inspected; HEAD is not the pinned revision. All component file locations and method-level guard claims in this manifest remain provisional until audited at the pinned commit.
- Reference: https://android.googlesource.com/platform/frameworks/base/+/HEAD/services/java/com/android/server/SystemServer.java
- Reference: https://android.googlesource.com/platform/frameworks/base/+/master/core/java/android/app/ActivityThread.java
- Reference: https://developer.android.com/guide/components/activities/activity-lifecycle
- Reference: https://source.android.com/docs/core/architecture/aidl/stable-aidl
- An internal framework AIDL is not automatically Stable AIDL. Do not invent transaction ABI stability.

## Host checks

    python3 framework/tools/validate_contracts.py framework/contracts/framework_contracts.json
    python3 -m unittest discover -s framework/tests -v
    python3 -m compileall -q framework/tools framework/tests

Validator exit status: 0 structural pass; 1 contract rejection; 2 file or JSON error. Unknown permissions remain unknown, not a pass for method-level permission correctness. SYNTHETIC mutation fixtures validate rejection behavior only.

## Required platform gates (not run)
1. Check out exact AOSP pin and confirm file blobs, public SDK signatures, Binder/AIDL descriptors, consumers, service registry names, transactions, user boundary and actual method-level guard enforcement.
2. Compare SDK surfaces using metalava/API checks; compile with Soong. Review hidden API policies, class loading, ART and JNI ABI boundaries.
3. Boot unmodified pinned Cuttlefish first, then test system-server service lookup, Binder identity, timeouts, death recipients, malformed parcel inputs, permission/AppOps denials and multi-user segregation.
4. Run Android 17 matching CTS, targeted atest framework suites, instrumentation ActivityScenario lifecycle tests, package-signing tests, process death/restart, background and notification behavior, secure windows, and accessibility.
5. Run CTS Verifier where applicable, VTS/VINTF when native HAL interfaces are involved, SELinux enforcing checks, and a priority real-app test suite.
6. Measure paired traces on same build/device with Perfetto and Macrobenchmark; p50/p95 latency, frame jank, memory, energy, crash/ANR. No optimization accepted without performance and security non-regression evidence.

CTS setup: https://source.android.com/docs/compatibility/cts/setup

## Change policy
Do not remove or change public SDK methods, Binder transaction semantics, permission checks, app lifecycle callbacks, package signing, process sandbox or SELinux enforcement without proven compatible consumers, source evidence, reproducible tests and rollback.
Every performance candidate in audits/optimization_register.json is a hypothesis, not a measured result.

## Current limits
Foundation PR #1 and P0-002 PR #3 are draft/unmerged. P0-006 security dependency unaccepted. No source checkout, full Android build, CTS, VTS, APK, emulator or phone testing claimed.
