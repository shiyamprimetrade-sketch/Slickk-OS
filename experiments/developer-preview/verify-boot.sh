#!/usr/bin/env bash
set -Eeuo pipefail
exec > >(tee -a evidence/custom-boot-verification.log) 2>&1
export PATH="$ANDROID_HOME/platform-tools:$PATH"
check_system() {
  test "$(adb shell getprop sys.boot_completed | tr -d '\r')" = 1
  test "$(adb shell getenforce | tr -d '\r')" = Enforcing
  test "$(adb shell getprop ro.boot.veritymode | tr -d '\r')" = enforcing
  adb shell getprop ro.boot.verifiedbootstate
  adb shell getprop ro.boot.vbmeta.device_state
  adb shell getprop ro.build.fingerprint
  adb shell cat /product/etc/slickk-os.json | tee "evidence/identity-$1.json"
  diff <(python3 -c 'import json; print(json.dumps(json.load(open("evidence/identity.json")),sort_keys=True))') <(python3 -c "import json; print(json.dumps(json.load(open('evidence/identity-$1.json')),sort_keys=True))")
  adb shell pm path online.slickk.os | tee "evidence/package-$1.txt"
  grep -Eq '^package:/product/app/SlickkHome/SlickkHome.apk' "evidence/package-$1.txt"
  adb shell pm list packages -s | grep -Fx 'package:online.slickk.os'
  adb shell sha256sum /product/app/SlickkHome/SlickkHome.apk | tee "evidence/apk-$1.sha256"
  test "$(cut -d' ' -f1 "evidence/apk-$1.sha256")" = "$(sha256sum evidence/SlickkHome-debug.apk | cut -d' ' -f1)"
}
check_system before
adb shell cmd package set-home-activity online.slickk.os/.HomeActivity
adb shell cmd role add-role-holder --user 0 android.app.role.HOME online.slickk.os
adb shell am start -W -n online.slickk.os/.HomeActivity | tee evidence/home-start.txt
grep -q 'Status: ok' evidence/home-start.txt
sleep 3
# Click the actual launcher's Settings button using its accessibility bounds.
adb shell uiautomator dump /sdcard/window.xml
adb pull /sdcard/window.xml evidence/window.xml
read -r x y < <(python3 - <<'PY'
import re, xml.etree.ElementTree as E
nodes=[n for n in E.parse('evidence/window.xml').iter('node') if n.get('text')=='Settings' and n.get('clickable')=='true']
assert len(nodes)==1, 'Settings button not uniquely visible'
a,b,c,d=map(int,re.findall(r'\d+',nodes[0].get('bounds')))
print((a+c)//2,(b+d)//2)
PY
)
adb shell input tap "$x" "$y"
sleep 3
adb shell dumpsys activity activities > evidence/settings-launch.txt
grep -E 'mResumedActivity.*com.android.settings' evidence/settings-launch.txt
adb shell input keyevent KEYCODE_HOME
adb exec-out screencap -p > evidence/slickk-system-home.png
adb reboot
timeout 180 adb wait-for-device
timeout 300 bash -c 'until [ "$(adb shell getprop sys.boot_completed 2>/dev/null | tr -d "\r")" = 1 ]; do sleep 5; done'
sleep 10
check_system after
adb shell cmd role get-role-holders --user 0 android.app.role.HOME | tr -d '\r' | tee evidence/home-role-after.txt
grep -Fx online.slickk.os evidence/home-role-after.txt
adb shell cmd package resolve-activity --brief -a android.intent.action.MAIN -c android.intent.category.HOME | tee evidence/home-resolve-after.txt
grep -F 'online.slickk.os/.HomeActivity' evidence/home-resolve-after.txt
adb shell am start -W -n online.slickk.os/.HomeActivity | tee evidence/home-after-start.txt
grep -q 'Status: ok' evidence/home-after-start.txt
adb logcat -d > evidence/custom-logcat.txt
adb shell getprop > evidence/custom-properties.txt
echo 'CUSTOM_PRODUCT_IMAGE_AND_REBOOT=VERIFIED' | tee evidence/custom-result.txt
