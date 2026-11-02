#!/usr/bin/env bash
# Slickk-OS: safe first AOSP source/build attempt, never touches device firmware.
set -Eeuo pipefail
if [[ $# != 2 || "$1" != "--run" || ! -d "$2" ]]; then
  echo "Usage: bash sprints/first_boot/build_aosp.sh --run /existing/build/volume" >&2
  exit 64
fi
volume="$(realpath "$2")"
here="$(cd "$(dirname "$0")" && pwd)"
python3 "$here/preflight.py" "$volume" --strict

checkout="$volume/slickk-aosp"
mkdir -p "$checkout"
cd "$checkout"
log_dir="$checkout/.slickk-evidence"
mkdir -p "$log_dir"
exec > >(tee -a "$log_dir/build.log") 2>&1
echo "PIN=android-17.0.0_r1" > "$log_dir/checkpoint.txt"
if [[ ! -d .repo ]]; then
  repo init --partial-clone -b android-17.0.0_r1 -u https://android.googlesource.com/platform/manifest
fi
expected="5bc9a7ce1cd78dd53613bbfd0ebf506e1e4adb0f"
actual="$(git -C .repo/manifests rev-parse HEAD)"
if [[ "$actual" != "$expected" ]]; then
  echo "STOP: manifest commit mismatch expected=$expected actual=$actual" >&2
  exit 3
fi
echo SOURCE_SYNC > "$log_dir/checkpoint.txt"
repo sync -c -j4 --fail-fast
repo manifest -r -o "$log_dir/locked-manifest.xml"
sha256sum "$log_dir/locked-manifest.xml" > "$log_dir/locked-manifest.sha256"
echo BUILD > "$log_dir/checkpoint.txt"
source build/envsetup.sh
lunch aosp_cf_x86_64_only_phone-aosp_current-userdebug
m -j4
echo BUILD_COMMAND_SUCCESS > "$log_dir/checkpoint.txt"
find out/target/product -maxdepth 3 -type f \( -name 'boot.img' -o -name 'system.img' -o -name 'vendor.img' \) -print | sort > "$log_dir/images.txt"
while IFS= read -r path; do sha256sum "$path"; done < "$log_dir/images.txt" > "$log_dir/image-sha256.txt"
echo "Build attempted. Cuttlefish boot verification is a SEPARATE gate."
