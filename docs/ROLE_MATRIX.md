# 13 Initial Engineering Roles — Autonomous Execution v2
| Chat | Role | Languages/tools | Owned responsibility |
|---|---|---|---|
| 00 | Program Director | roadmap, GitHub Issues | registry, product charter, cross-task conflict resolution; optional Work mode |
| 01 | Chief Architect | AOSP, Java, C++, AIDL, Python | source baseline, verified interfaces, architecture validation scripts |
| 02 | Integration Engineer | Git, CI, Python, YAML, shell | independent branch governance, CI and integration validators |
| 03 | Verification Engineer | Python, instrumentation, Perfetto | reproducible evidence and benchmarks |
| 04 | Security and Release Auditor | SELinux, AVB, threat models | privacy/security/release audit |
| 05 | Kernel Engineer | Linux C, Kconfig, GKI | kernel configuration and drivers |
| 06 | HAL and Device Engineer | Stable AIDL, C++, VINTF | target interfaces and device evidence |
| 07 | Runtime and Native Engineer | ART, C++, JNI/NDK | profiled and reversible native changes |
| 08 | Framework Engineer | Java/Kotlin, AIDL | APIs, lifecycle, system services, Binder |
| 09 | User Experience and Apps Engineer | Kotlin, Compose, Gradle | buildable launcher/app UX experiments |
| 10 | Graphics/Media/Network Engineer | C++, AIDL, Kotlin | measured rendering, media and connectivity |
| 11 | Boot/Update Engineer | C++, shell, SELinux, AVB | reproducible virtual-device boot and update safety |
| 12 | Build and QA Engineer | Python, shell, Soong, GitHub Actions | build scripts, CI, packaging |

All role chats can perform their assigned tasks independently using GitHub and tools available in their own session. Chat 00 Work mode may be temporarily unavailable; there is no real-time approval bottleneck. Chat titles do not assign ownership; the task registry does. No chat runs autonomously between user messages unless an authorized automation is configured. Task-branch coding, tests and draft PRs are pre-authorized. Integration/merge state and destructive phone actions remain separate.
