#!/usr/bin/env bash
# First unmodified AOSP baseline. No VM launch or device firmware operations.
set -Eeuo pipefail
if [[ $# != 2 || "$1" != "--run" || ! -d "$2" ]]; then
  echo "Usage: bash sprints/first_boot/build_aosp.sh --run /existing/build/volume" >&2
  exit 64
fi
volume="$(realpath "$2")"
here="$(cd "$(dirname "$0")" && pwd)"
pins="$here/../../architecture/baseline"
python3 "$here/preflight.py" "$volume" --strict
python3 "$pins/verify.py"
checkout="$volume/slickk-aosp"
# Never adopt an unrelated directory or hidden project override.
if [[ -e "$checkout" && ! -d "$checkout/.repo" ]] && [[ -n "$(ls -A "$checkout")" ]]; then
  echo "STOP: nonempty directory is not a Repo checkout" >&2; exit 3
fi
mkdir -p "$checkout"
cd "$checkout"
log_dir="$(mktemp -d "$volume/slickk-build-evidence-XXXXXXXX")"
exec > >(tee "$log_dir/build.log") 2>&1
trap 'rc=$?; printf "FAILED exit=%s line=%s\n" "$rc" "$LINENO" > "$log_dir/checkpoint.txt"; exit "$rc"' ERR
printf 'PIN=android-17.0.0_r1\n' > "$log_dir/checkpoint.txt"
if [[ ! -d .repo ]]; then
  repo init --partial-clone -b android-17.0.0_r1 -u https://android.googlesource.com/platform/manifest
fi
if [[ -e .repo/local_manifest.xml || -e .repo/local_manifests ]]; then
  echo "STOP: local manifests not permitted in unmodified baseline" >&2; exit 3
fi
expected="5bc9a7ce1cd78dd53613bbfd0ebf506e1e4adb0f"
actual="$(git -C .repo/manifests rev-parse HEAD)"
[[ "$actual" == "$expected" ]] || { echo "STOP: manifest HEAD mismatch"; exit 3; }
[[ -z "$(git -C .repo/manifests status --porcelain)" ]] || { echo "STOP: dirty manifest"; exit 3; }
# Refuse existing project edits before sync can update any working tree.
repo forall -e -c 'test -z "$(git status --porcelain)"'
echo SOURCE_SYNC > "$log_dir/checkpoint.txt"
repo sync -c -j4 --fail-fast
# Reject tracked/untracked edits in every project, not just the five pinned HEADs.
repo forall -e -c 'test -z "$(git status --porcelain)"'
python3 "$pins/verify.py" --checkout "$checkout" | tee "$log_dir/pin-verification.json"
repo manifest -r -o "$log_dir/locked-manifest.xml"
python3 "$here/preflight.py" --validate-manifest "$log_dir/locked-manifest.xml"
sha256sum "$log_dir/locked-manifest.xml" > "$log_dir/locked-manifest.sha256"
echo BUILD > "$log_dir/checkpoint.txt"
# AOSP shell functions are not guaranteed nounset-clean.
set +u
source build/envsetup.sh
lunch aosp_cf_x86_64_only_phone-aosp_current-userdebug
product_out="$(get_build_var PRODUCT_OUT)"
[[ -n "$product_out" ]] || { echo "STOP: empty PRODUCT_OUT"; exit 3; }
m -j4
set -u
python3 "$here/preflight.py" --capture-images "$product_out" --evidence-directory "$log_dir"
echo BUILD_ARTIFACTS_HASHED_NOT_BOOT_VERIFIED > "$log_dir/checkpoint.txt"
echo "Image hashes recorded in $log_dir. Actual Cuttlefish boot remains a separate gate."
