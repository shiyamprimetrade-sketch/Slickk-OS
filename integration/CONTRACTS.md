# Integration boundaries (provisional until AOSP version is pinned)

| Layer | Interface contract | Required proof before integration |
|---|---|---|
| Linux/GKI kernel | KMI, module symbols, defconfig, driver target | exact upstream SHA, compatible kernel config and boot/runtime tests |
| HAL/device | Stable AIDL, VINTF manifests, vendor ownership | interface hash/version and VINTF checks on supported target |
| Runtime/native | ART, JNI/C++ ABI, NDK boundaries | repeatable ABI checks, unit tests, traced regressions |
| Framework/services | Binder/AIDL APIs, permission model | API compatibility and behavior/security regression tests |
| Apps/UX | SDK API levels, accessibility, manifest permissions | reproducible Gradle build, instrumentation tests and user journeys |
| Graphics/media/network | codec, audio, compositor and network APIs | deterministic functional benchmarks and network/privacy review |
| Boot/security/OTA | init, SELinux, AVB and update metadata | signed test provenance, Cuttlefish boot, rollback safety and security review |

Any module proposal must publish: declared upstream revision, public dependencies, build instructions, interface version, owned files, security/privacy impact, test matrix, baseline metrics, feature flag/rollback, and acceptance evidence. Unknown compatibility blocks integration. No proprietary vendor binaries, universal device claims or performance gains are implied by these contracts.
