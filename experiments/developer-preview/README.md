# Slickk-OS Developer Preview 0.1 — image creation

Development-only AOSP derivative. The official upstream build is Android 17, build 16644040, CP2A.260605.016. Original AOSP code and licenses remain upstream; this project adds a launcher and identity file.

## Reproduce
Use a clean Ubuntu 24.04 Linux x86_64 KVM runner with the Android SDK/JDK and official Cuttlefish base dependencies. Execute the workflow `.github/workflows/slickk-developer-image.yml` on this branch. It is push-triggered only for `integration/slickk-dp01` (and manually dispatchable where GitHub makes it available). By default, it restores the immutable images from run 41848785937 and checks their hashes; dispatch with `rebuild: true` to reconstruct from target-files. No full AOSP checkout is required for this target-files reconstruction.

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
AVB uses publicly available development test keys, not production keys. No AVB-disable, SELinux-disable or writable-remount steps are permitted. Guest security enforcement and offline signature validity are distinct checks; report actual bootloader state separately. The old baseline explicitly disabled the host VMM sandbox; this workflow explicitly requires `-enable_sandbox=true`. Ubuntu 24.04 uses an executable-scoped AppArmor `userns` profile for the pinned crosvm binary, following the [Ubuntu 24.04 release notes](https://documentation.ubuntu.com/release-notes/24.04/) recommendation. The system-wide unprivileged-user-namespace restriction must remain 1; no global restriction is disabled.

Existing launcher compilation creates a fresh debug signing key per execution: reproducible procedure does not imply bit-identical APK/image outputs. Published artifact hashes identify the exact tested build. Product timestamp/toolchain/input hashes must be considered before claiming deterministic outputs. CTS/VTS compliance, broad app compatibility, current security patches, phone compatibility and production release are not demonstrated by this smoke test.

## Image provenance
Image source revision: `5c0c599b8a32215842f69a52e198db2872190b5b`. Repeated boot tests restore these exact bytes; test-harness commits do not change that image revision.

| Artifact | SHA-256 |
| --- | --- |
| super.img | `a4ae520c1829f9058913a59acd3b8372f962d2a6998e9402429eab4233726646` |
| vbmeta_system.img | `3649fc78b9c720b28d77be615da5e4a1f2577bafc96f806effe82ab483bdb02a` |
| SlickkOS-DP01-image-overlay.tar.gz | `53f636129bcea53381ddafabc7fac2fe8e7502b2a7a97b1a954808c042dbdddd` |

[Built image artifact](https://github.com/shiyamprimetrade-sketch/Slickk-OS/actions/runs/41848785937/artifacts/13334100921). Overlay extraction must accompany the exact stock and host archives checked by restore.sh. The tar.gz is a development image overlay, not a standalone phone ROM.

## Checkpoint
Role: Chat 00. Task: Issue #14 Developer Preview directive. Branch: integration/slickk-dp01. Draft PR: #17.

Steps 1–3: pinned inputs, product reconstruction and offline AVB verification passed. Four customization contract tests passed locally and in Actions.

Failure history: run 41848785937 reached the launcher timeout because crosvm/minijail could not create a mount namespace. Small recovered diagnostics are in run 41850269721. Run 42003230894 fixed that host permission using the scoped profile and proved actual custom-image boot, ADB, sys.boot_completed=1, product identity/APK hash and launcher start. Its UI test stopped at the swipe-only keyguard before reboot; this was not a full milestone pass.

Guest bootloader reports `orange` / `unlocked`, inherited from the official development virtual device. SELinux and verity checks passed. Public test keys and offline signature verification do not establish production trusted boot.

Run [42003975104](https://github.com/shiyamprimetrade-sketch/Slickk-OS/actions/runs/42003975104) at harness revision db352376689c5936ccb3761961ede329127db5b1 passed initial boot and actual reboot, sys.boot_completed=1, product identity/APK hash, HOME role/activity and Settings launch through the launcher. SELinux Enforcing and verity enforcing passed both times. Independently downloaded evidence ZIP SHA-256: `ce44ce40d829eb92f0fcfe0935d0232f4ce8681e03ac1adaec5667a96deda9fe`.

The screenshot from that run captured a transition frame. Harness revision 52b445d436be201386ef53a27d7886ddbce984e8 waits for visible HOME text and captures screenshots before/after reboot. [Final run 42004664442](https://github.com/shiyamprimetrade-sketch/Slickk-OS/actions/runs/42004664442) passed all gates, including rendered HOME UI before and after reboot and controlled shutdown. [Evidence artifact 13404492305](https://github.com/shiyamprimetrade-sketch/Slickk-OS/actions/runs/42004664442/artifacts/13404492305) includes logs, identity/hash records, device configuration and real screenshots. ZIP SHA-256 independently checked: `e12b5dd5032c089932116d9ad17f43dffa21fed56f937f0d29a66b8fe2356fca`. Independent artifact inspection confirmed matching before/after identity, APK hash, HOME role, visible launcher UI and enabled VMM sandbox. Registry validation run 42004671431 passed at the same harness revision.

Measured runner: Ubuntu 24.04 x86_64, KVM, 15 GiB reported RAM, 86 GiB initially available disk; cuttlefish-base 1.57.13, matching official host/image build 16644040. The launcher uses Java/Android SDK; image creation uses Python, Bash and official AOSP release tools. This is target-files image reconstruction, not a full source compilation.

Steps 1–5 complete for this development-image milestone. **SLICKK-OS DEVELOPER PREVIEW 0.1 — BUILD AND BOOT VERIFIED.** Implementation remains a draft PR for review, not an accepted release. No automatic next task, merge, publication or physical-device operation is authorized by this completion. Next action: review PR #17 and assign the next task separately.
