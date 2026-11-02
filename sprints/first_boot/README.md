# Slickk-OS — First Boot Sprint (2026-11-02)

**Purpose:** convert 13 role chats' engineering into a verifiable AOSP-derived OS build and first virtual-device boot. These scripts do not claim a successful build or boot.

**Source:** Architect PR #3 pins Android 17 tag android-17.0.0_r1, manifest commit 5bc9a7ce1cd78dd53613bbfd0ebf506e1e4adb0f. The tag is for development, **not** proof of current production security fixes. Preserve upstream licensing; 100M+ inherited AOSP lines are not Slickk-authored code.

## Integration command for Chat 00 / Chat 02 / Chat 12

Review foundation PR #1 and all task PRs before merging. Confirm checked-out source revisions, tests, licenses, security, ownership, and failures. Chat 02 PR #4 targets the P0-001 task branch and needs base/chain review before integration. Consolidate only accepted commits into one integration candidate and run all existing tests. Do not silently merge main or claim that passing the task registry means the OS builds. Do not force-push another role branch. Prioritize actual blockers over code-line quantity.

## AOSP build-host gate

Google AOSP requirements: Linux x86_64, at least 64 GiB RAM and 400 GiB free disk for a full checkout/build. Install documented Ubuntu dependencies and git, repo, curl, python3, bash. A standard GitHub-hosted runner is not a substitute for this build host.

First, on the intended Linux build host:

    python3 sprints/first_boot/preflight.py /data

Then only if qualified and ready for substantial download/build:

    bash sprints/first_boot/build_aosp.sh --run /data

Script: read-only preflight, pinned repo init, manifest-commit check, sync, immutable manifest export, AOSP lunch + m, artifact hash attempt. Logs written under /data/slickk-aosp/.slickk-evidence. If the pinned build has different lunch products, inspect official source and document a change; never silently switch tags. This script NEVER flashes a phone, boots a virtual device, obtains production signing keys or installs packages.

## First genuine OS proof

1. SOURCE: immutable full repo manifest saved.
2. BUILD: m returns zero, boot/system artifacts exist and SHA-256 recorded.
3. BOOT: on a configured KVM-enabled Cuttlefish Linux host, launch the matching image and capture adb shell getprop sys.boot_completed returning "1", build fingerprint, serial-free logs and clean shutdown. Follow https://source.android.com/docs/devices/cuttlefish/get-started
4. TEST: run independent compatibility/security and usability tests; only then make claims within tested scope.

## Parallel workstreams

- Chats 00, 02, 12: integration review and CI; Chat 12 also assesses build host.
- Chat 01: pinned AOSP source, target/product validity, first image build.
- Chat 11: Cuttlefish boot, AVB/OTA validation, logs and recovery (never a physical phone).
- Chat 09: P0-011 launcher UX followed by separately assigned P0-012 buildable APK.
- Chats 03, 04, 05, 06, 07, 08, 10: run their actual test harnesses and supply reversible, source-pinned, evidence-backed changes; do not rewrite everything at once.

**Stop conditions:** insufficient build host, incompatible source pin, security break, missing vendor interface, unreproducible image, unknown device support. Synthetic fixtures are never physical performance evidence. Date/time goals are aspirational; report blocked work rather than inventing success.
