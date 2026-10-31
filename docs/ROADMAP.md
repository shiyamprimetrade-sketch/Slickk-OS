# Phase Roadmap — Sequential Release Gates
## Phase 0 — Program foundation (20-task pilot)
Steps 1–20: see tasks/pilot.json. Exit only if role prompts, pinned baseline decision, engineering contracts, CI and measurable test plan are reviewed. No unverified code-generation volume targets.
## Phase 1 — Slickk Experience on existing Android
1. Define top user journeys.
2. Prototype launcher and settings-facing UX.
3. Implement smallest installable APK.
4. Test accessibility, crashes and permissions.
5. Collect matched Android baseline and post-change usability/performance data.
Exit: APK builds and installs on a supported Android device, usable without root; important regressions absent.
## Phase 2 — AOSP platform baseline
1. Pin AOSP branch/tag, verify provenance and licenses.
2. Prepare adequate Linux builder.
3. Build unmodified Cuttlefish image.
4. Boot and preserve logs.
5. Confirm app compatibility and tests.
Exit: repeatable baseline boot and images with exact source commit, build commands and logs.
## Phase 3 — Verified optimizations
1. Rank measured bottlenecks.
2. Create reversible single-variable patch.
3. Run tests and comparative benchmarks.
4. Reject patch if security/compatibility/energy worsens.
5. Integrate accepted patch.
Exit: at least one measured improvement with no critical regression.
## Phase 4 — Physical phone compatibility
1. Choose one documented device target.
2. Audit bootloader unlockability, vendor partitions, kernel KMI, firmware licenses.
3. Prepare backups and restore process.
4. Ask owner separately before any flashing.
5. Validate boot, telephony, sensors, radio, audio, camera, storage, updates.
Exit: reproducible supported-device tests and safe recovery.
## Phase 5 — Production safety and updates
1. Threat model, SELinux/AVB, secure build keys.
2. CTS/VTS and device compatibility gates.
3. Battery, stability, accessibility, migration tests.
4. OTA and rollback validation.
5. Release candidate review.
Exit: documented release evidence, no unresolved critical security defect.
## Phase 6 — Public release
Publish supported device matrix, images, source, reproducible build steps, licensing, security updates and warranty/limitations. Never advertise untested device support.
## Continue semantics
One Continue advances the current assigned task by one verified increment. At a phase gate with documented PASSED acceptance evidence, a subsequent owner Continue authorizes advancing to the next phase. It never authorizes a merge, release, device unlock, flash, or wipe.
