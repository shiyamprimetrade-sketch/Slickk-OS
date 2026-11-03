# P0-013 checkpoint - Chat 08

Task: P0-013; step 5/6 (submit & verify draft PR). Ownership: framework/** only.
Proposed AOSP baseline Android 17/API 37 android-17.0.0_r1 frameworks/base 94b4c163b7dfe5ce3607f7bb8456f9573f7de57d.
PR #1 foundation draft/unmerged; P0-002 PR #3 draft/unmerged; P0-006 unaccepted.
Verified upstream tag/commit via official AOSP tag index; individual pinned source file contents and permission guards uninspected.
Local independently prepared package: validator 12 components PASS; 10 unittest methods PASS, 15 SYNTHETIC negative fixture cases; Python 3.13.5; compileall PASS.
Note: GitHub-submitted validator/test implementation is separately authored and requires CI execution before claiming its test methods have run. Local test evidence does not establish equivalence or Android runtime compatibility.
No AOSP checkout, Cuttlefish, Soong, CTS, VTS, device flash, APK, benchmarks or verified gains.
Next: inspect GitHub commit/PR and run exact branch tests via CI or checked-out branch; reconcile provisional source and permission contracts once dependencies accepted.
