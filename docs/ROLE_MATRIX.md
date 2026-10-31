# 13 Initial Roles
| Chat | Role | Languages/tools | Responsible scope |
|---|---|---|---|
| 00 | Program Director | planning, GitHub Issues | plan/tasks/metrics/approvals |
| 01 | Chief Architect | AOSP, Java, C++, AIDL | contracts, baseline, architecture |
| 02 | Integration Engineer | Git, Soong, Gradle, CI | dependency/branch/build integration |
| 03 | Verification Engineer | Python, instrumentation, Perfetto | reproducible evidence and benchmarks |
| 04 | Security and Release Auditor | SELinux, AVB, threat model | privacy/security/release audit |
| 05 | Kernel Engineer | Linux C, Kconfig, GKI | kernel configuration and drivers |
| 06 | HAL and Device Engineer | Stable AIDL, C++, VINTF | devices, vendor interfaces and sensors |
| 07 | Runtime and Native Engineer | ART, C++, JNI/NDK | performance-sensitive components |
| 08 | Framework Engineer | Java/Kotlin, AIDL | lifecycle, system services, Binder |
| 09 | User Experience and Apps Engineer | Kotlin, Compose, Gradle | launcher, apps, accessibility |
| 10 | Graphics/Media/Network Engineer | C++, AIDL, Kotlin | compositor, media and connectivity |
| 11 | Boot/Update Engineer | C++, shell, SELinux, AVB | init, recovery, OTA, signed images |
| 12 | Build and QA Engineer | Python, shell, Soong, GitHub Actions | build scripts, CI, packaging |
One role chat is a team coordinator. Task-specific chats inherit this role and the exact task ID. Ownership is allocated per task; role does not grant unbounded write access.
