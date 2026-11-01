# Slickk-OS Project Charter — Phase 0
## Purpose
Create an Android-compatible smartphone operating system whose usability, responsiveness, energy efficiency, accessibility, reliability and privacy are demonstrably improved over matched Android baselines. This is an engineering goal, not an accomplished claim.
Owner decides product scope, supported devices, merges, flash actions and releases.
## Distinct deployment tracks
1. **Experience track (APK)**: Slickk Launcher and companion apps running on existing Android phones without changing firmware. Works only to the extent Android APIs and device policy permit.
2. **Platform track (AOSP OS)**: Android-compatible system builds, Cuttlefish-first, then specific supported unlockable devices. Do not imply one ROM works on every phone.
3. **Research track**: source audit, traces, controlled experiments and reduction of unnecessary complexity with regressions tests.
## Non-negotiables
- Preserve Android application compatibility, privacy boundaries and verified-boot integrity where supported.
- Never claim an improvement without a matched before/after benchmark and methodology.
- Treat the 140M-line thought experiment as a planning constraint, **not** a product goal.
- Never remove code just because it looks verbose: prove it is unreachable, redundant, replaceable or unneeded for the supported configuration.
- Never flash or unlock the owner's daily phone without separate, explicit consent and a validated backup/recovery process.
- Never use or publish proprietary vendor code without permission.
## Release gates
A. Validated repository and roles; B. Installable user-experience APK; C. Reproducible Cuttlefish boot; D. Experimentally verified system improvements; E. Hardware port with recoverability; F. Security, compatibility, update and reliability review.
Current reality: public repository exists; planning bootstrap only; no OS image, app build or benchmark result.
