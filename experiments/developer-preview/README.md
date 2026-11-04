# Slickk-OS Developer Preview 0.1 — image creation

Development-only AOSP derivative. The official upstream build is Android 17, build 16644040, CP2A.260605.016. Original AOSP code and licenses remain upstream; this project adds a launcher and identity file.

## Reproduce
Use a clean Ubuntu 24.04 Linux x86_64 KVM runner with the Android SDK/JDK and official Cuttlefish base dependencies. Execute the workflow `.github/workflows/slickk-developer-image.yml` on this branch. It is push-triggered only for `integration/slickk-dp01` (and manually dispatchable where GitHub makes it available). No full AOSP checkout is required for this target-files reconstruction.

1. Validate SHA256-pinned official target-files and OTA-tools packages from build 16644040.
2. Compile the existing Java launcher; stage it under PRODUCT/app/SlickkHome and add PRODUCT/etc/slickk-os.json with source revision and APK hash.
3. Update filesystem ownership/modes, rebuild EROFS product and vbmeta_system with the packaged official tools and public development test key, then rebuild super.
4. Verify AVB signatures and descriptor chains and require verification flags zero. Replace super.img and vbmeta_system.img in the matching stock image bundle before its first launch.
5. Boot, require SELinux Enforcing and verity enforcing, verify APK path/hash and identity, set the user's HOME preference, tap the launcher Settings button, reboot, and repeat partition/identity/HOME checks.

Run locally without Android resources: `python3 -m unittest discover -s experiments/developer-preview -v`. Shell syntax: `bash -n experiments/developer-preview/build.sh` and `bash -n experiments/developer-preview/verify-boot.sh`.

## Artifacts and rollback
The workflow retains evidence including a compressed image overlay containing super.img and vbmeta_system.img, hashes, APK, identity, build/AVB/boot logs, source revision and screenshot for 14 days. Extract the overlay only into a fresh directory containing the exact same official image bundle, with no existing instance state. Keep the original bundle unchanged for rollback. A full downloadable source checkout is not supplied. Artifact availability expires; permanent release publication is not authorized here.

The launcher is a system product app, not privileged and not platform-signed. HOME selection is a per-user setup operation verified through reboot; a framework default-role overlay is not claimed. The custom identity is a product JSON file; the upstream fingerprint is intentionally retained as provenance.

## Security and limits
AVB uses publicly available development test keys, not production keys. No AVB-disable, SELinux-disable or writable-remount steps are permitted. Guest security enforcement and offline signature validity are distinct checks; report actual bootloader state separately. The old baseline explicitly disabled the host VMM sandbox; this workflow leaves its default enabled/selected behavior unchanged and does not pass that disabling option.

Existing launcher compilation creates a fresh debug signing key per execution: reproducible procedure does not imply bit-identical APK/image outputs. Published artifact hashes identify the exact tested build. Product timestamp/toolchain/input hashes must be considered before claiming deterministic outputs. CTS/VTS compliance, broad app compatibility, current security patches, phone compatibility and production release are not demonstrated by this smoke test.

## Checkpoint
Role: Chat 00. Task: Issue #14 Developer Preview directive. Branch: integration/slickk-dp01. Draft PR: #17. Steps 1–3 passed in workflow 41846746520 at source commit ba4ad28274598c0292984d5b84b1af03e8caaac2: contract tests, image reconstruction and offline AVB checks completed. Step 4 boot execution is pending; consult the actual workflow outcome before claiming boot. Archive hashes are emitted by the workflow and must be copied from its evidence, not guessed. Failed workflow attempts remain available in GitHub Actions. Do not repeat the successful stock baseline as a substitute for custom image evidence.
