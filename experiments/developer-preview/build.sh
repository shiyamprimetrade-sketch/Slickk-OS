#!/usr/bin/env bash
set -Eeuo pipefail
repo_root="$(pwd)"
work="$RUNNER_TEMP/slickk-dp01"
mkdir -p "$work" evidence
exec > >(tee -a "$repo_root/evidence/image-build.log") 2>&1
base=https://ci.android.com/builds/submitted/16644040/aosp_cf_x86_64_only_phone-userdebug/latest/raw
for name in aosp_cf_x86_64_only_phone-target_files-16644040.zip otatools.zip; do
  curl -fLsS --retry 3 "$base/$name" -o "$work/$name"
done
cd "$work"
printf '%s\n' '742a4f8aef4587ec6bfd1955b85a16d5d8635cc06111e8d097e67572ad2cd768  aosp_cf_x86_64_only_phone-target_files-16644040.zip' 'bc85557aa0c59a7d0b48b8175250948d67b2d0f293bd74eb8d5753ba4ad7781f  otatools.zip' | sha256sum -c -
unzip -q otatools.zip -d tools
unzip -q aosp_cf_x86_64_only_phone-target_files-16644040.zip -d target
export PATH="$work/tools/bin:$PATH"
cp target/META/misc_info.txt "$repo_root/evidence/upstream-misc-info.txt"
sha256sum target/IMAGES/*.img > "$repo_root/evidence/upstream-images.sha256"
cd "$repo_root"
bash experiments/slickk-home/build.sh
python3 experiments/developer-preview/customize.py "$work/target" experiments/slickk-home/dist/SlickkHome-debug.apk "$GITHUB_SHA" | tee evidence/identity.json
cp experiments/slickk-home/dist/SlickkHome-debug.apk evidence/
cd "$work/tools"
bin/add_img_to_target_files --add_missing "$work/target"
bin/build_super_image "$work/target" "$work/super.img"
cd "$work/target/IMAGES"
avbtool verify_image --image vbmeta.img --key "$work/tools/external/avb/test/data/testkey_rsa4096.pem" --follow_chain_partitions | tee "$repo_root/evidence/avb-verify.txt"
for name in vbmeta.img vbmeta_system.img; do
  avbtool info_image --image "$name" > "$repo_root/evidence/$name.info.txt"
  grep -Eq 'Flags: +0$' "$repo_root/evidence/$name.info.txt"
done
sha256sum *.img "$work/super.img" > "$repo_root/evidence/custom-images.sha256"
mkdir -p "$HOME/cf"
curl -fLsS --retry 3 "$base/aosp_cf_x86_64_only_phone-img-16644040.zip" -o "$work/stock-img.zip"
curl -fLsS --retry 3 "$base/cvd-host_package.tar.gz" -o "$work/host.tar.gz"
sha256sum "$work/stock-img.zip" "$work/host.tar.gz" > "$repo_root/evidence/runtime-archives.sha256"
unzip -q "$work/stock-img.zip" -d "$HOME/cf"
tar -xzf "$work/host.tar.gz" -C "$HOME/cf"
# Replace the actual boot inputs before the VM has ever been launched.
cp "$work/super.img" "$HOME/cf/super.img"
cp vbmeta_system.img "$HOME/cf/vbmeta_system.img"
sha256sum "$HOME/cf/super.img" "$HOME/cf/vbmeta_system.img" > "$repo_root/evidence/boot-inputs.sha256"
tar -czf "$repo_root/evidence/SlickkOS-DP01-image-overlay.tar.gz" -C "$HOME/cf" super.img vbmeta_system.img
sha256sum "$repo_root/evidence/SlickkOS-DP01-image-overlay.tar.gz" > "$repo_root/evidence/overlay.sha256"
echo 'IMAGE_BUILD_COMPLETE_BOOT_UNVERIFIED'
