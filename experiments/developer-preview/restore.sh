#!/usr/bin/env bash
# Retry boot using immutable, previously built and signed image bytes.
set -Eeuo pipefail
base=https://ci.android.com/builds/submitted/16644040/aosp_cf_x86_64_only_phone-userdebug/latest/raw
work="$RUNNER_TEMP/slickk-restore"
mkdir -p "$work" "$HOME/cf"
printf '%s  %s\n' 53f636129bcea53381ddafabc7fac2fe8e7502b2a7a97b1a954808c042dbdddd evidence/SlickkOS-DP01-image-overlay.tar.gz | sha256sum -c -
curl -fLsS --retry 3 "$base/aosp_cf_x86_64_only_phone-img-16644040.zip" -o "$work/stock.zip"
curl -fLsS --retry 3 "$base/cvd-host_package.tar.gz" -o "$work/host.tar.gz"
printf '%s  %s\n' eccdb248e171af6cb98711a6f2fbd5e5017e9c3a6e82337580181bbd4bb2c41b "$work/stock.zip" ec02c8e23985b37d9769732bf8bed992f10d851f40f7a835cf97128888900ecc "$work/host.tar.gz" | sha256sum -c -
unzip -q "$work/stock.zip" -d "$HOME/cf"
tar -xzf "$work/host.tar.gz" -C "$HOME/cf"
tar -xzf evidence/SlickkOS-DP01-image-overlay.tar.gz -C "$HOME/cf"
printf '%s  %s\n' a4ae520c1829f9058913a59acd3b8372f962d2a6998e9402429eab4233726646 "$HOME/cf/super.img" 3649fc78b9c720b28d77be615da5e4a1f2577bafc96f806effe82ab483bdb02a "$HOME/cf/vbmeta_system.img" | sha256sum -c -
echo "$ANDROID_HOME/platform-tools" >> "$GITHUB_PATH"
