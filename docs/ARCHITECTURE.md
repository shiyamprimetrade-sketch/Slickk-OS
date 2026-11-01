# Architecture and Technology Stack
## Strategy
Start from a **pinned and verified AOSP release tag**, not a fabricated from-scratch rewrite. Preserve the Android app/API contract and proven components; customize selectively using measured evidence.
Android source and licensing are references, not pretraining data that may be falsely claimed as a trained model.
## Supported modes
- Android device mode: normal APK launcher and companion apps, user-selected default launcher; no root required for supported functions.
- Full OS mode: AOSP-derived phone build booted in Cuttlefish, then model-specific device target after device tree, vendor partition, kernel, unlocking and recovery feasibility have been verified.
## Stack by layer
- Apps: Kotlin, Jetpack Compose where appropriate, Java interoperability, Android SDK, Gradle, accessibility tests.
- Framework: Java/Kotlin, AIDL Binder, existing platform build tools.
- Runtime and native: ART baseline, C++17/20 where supported, JNI and NDK for measured hotspots.
- Hardware: Stable AIDL HAL, compatible VINTF and vendor interfaces; never assume a HAL works without target vendor implementation.
- Kernel: Android Common Kernel/GKI appropriate to target, C, limited Rust if the toolchain and module support it, Kconfig.
- Boot/security: Android init, SELinux, AVB/Verified Boot, signing and OTA infrastructure.
- Builds: Linux x86_64 AOSP build host, Repo/Git, Soong/Ninja, Python 3, shell, GitHub Actions for lightweight validation.
- Tests: unit, instrumentation, Android Macrobenchmark, Perfetto, CTS/VTS when available, boot/power tests on matched real devices.
## Core principles
1. Contract-first and upstream-first.
2. Reversible optimizations behind flags.
3. Feature/dependency graph before deleting code.
4. Measured user experience over line count.
5. No unsupported device-specific claims.
## Build resource note
Full AOSP builds need substantially more resources than a typical phone; Google recommends a 64-bit Linux build host, 64 GB RAM and 400 GB free disk. GitHub Actions standard runners are not a substitute for a complete unoptimized AOSP build.
## Dependencies
Launcher APK can progress before OS image. Framework/HAL/kernel changes depend on AOSP tag and build host. Phone port depends on compatibility and explicit user consent.
