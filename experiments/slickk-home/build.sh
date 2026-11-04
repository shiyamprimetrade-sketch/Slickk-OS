#!/usr/bin/env bash
# Debug APK for virtual AOSP only. No OS image or phone writes.
set -Eeuo pipefail
here="$(cd "$(dirname "$0")" && pwd)"
sdk="$ANDROID_HOME"
if [[ ! -d "$sdk/build-tools" || ! -d "$sdk/platforms" ]]; then
  echo "Android SDK missing; set ANDROID_HOME" >&2
  exit 2
fi
bt="$(find "$sdk/build-tools" -mindepth 1 -maxdepth 1 -type d | sort -V | tail -1)"
jar="$(find "$sdk/platforms" -maxdepth 2 -name android.jar | sort -V | tail -1)"
test -f "$jar" && test -x "$bt/aapt2" && test -x "$bt/d8" && test -x "$bt/apksigner"
tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT
mkdir -p "$tmp/classes" "$tmp/dex" "$here/dist"
"$bt/aapt2" link --manifest "$here/AndroidManifest.xml" -I "$jar" -o "$tmp/base.apk"
javac -source 8 -target 8 -classpath "$jar" -d "$tmp/classes" \
  "$here/src/online/slickk/os/HomeActivity.java"
"$bt/d8" --min-api 26 --lib "$jar" --output "$tmp/dex" \
  "$tmp/classes/online/slickk/os/HomeActivity.class"
(cd "$tmp/dex" && zip -q "$tmp/base.apk" classes.dex)
"$bt/zipalign" -f 4 "$tmp/base.apk" "$tmp/aligned.apk"
keytool -genkeypair -noprompt -keystore "$tmp/debug.keystore" \
  -alias androiddebugkey -storepass android -keypass android \
  -keyalg RSA -keysize 2048 -validity 3650 \
  -dname "CN=SlickkOS Debug,O=Development,C=BD" >/dev/null 2>&1
"$bt/apksigner" sign --ks "$tmp/debug.keystore" --ks-key-alias androiddebugkey \
  --ks-pass pass:android --key-pass pass:android \
  --out "$here/dist/SlickkHome-debug.apk" "$tmp/aligned.apk"
"$bt/apksigner" verify --verbose "$here/dist/SlickkHome-debug.apk"
sha256sum "$here/dist/SlickkHome-debug.apk"
