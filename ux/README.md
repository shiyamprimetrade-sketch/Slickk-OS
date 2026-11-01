# P0-009 — Essential user journeys (provisional)

This directory specifies **12 essential journeys** with prerequisites, candidate baseline and proposed steps, friction, user-visible success, privacy, explicit accessibility requirements and an API/surface boundary. The catalog is **not a record of device observations**. Every baseline is `UNTESTED`; proposals are `HYPOTHESIS`; timing, action counts and errors are `null` until a real session with source evidence is added. Task dependency P0-001 has a separate charter PR; its unmerged status does not block this reversible specification.

## Reproduce

From the repository root, run:

```sh
python3 ux/tools/validate_journeys.py ux/journeys.json --report /tmp/ux-p009-report.json
python3 -m unittest discover -s ux/tests -p 'test_*.py' -v
```

First command exits 0 on valid catalog, 1 on invalid contract and 2 on input/output failure, and emits machine-readable JSON to stdout and optionally file. Negative tests use **synthetic** mutations; passing them does not prove any UX benefit or Android integration.

## Collection and evaluation contract

1. **Start/stop**: define each task's start state and success screen before testing; measure elapsed `monotonic` time from a randomized task cue to independently confirmed end state. Record incomplete/cancelled attempts without treating them as zero latency.
2. **Actions**: count intentional discrete taps, swipes, key activations and voice commands; capture text entry separately (characters and events). Avoid equating system-generated animations or accidental touches with user decisions.
3. **Task success**: binary outcome according to the journey's criterion, with failure and recovery reasons. Report successes/eligible attempts and confidence interval; never drop failures from denominator.
4. **Errors**: count wrong destinations, unintended launches, rejected attempts and recovery actions; report per attempt and number of attempts with at least one error. Keep hardware and service failures separately identified.
5. **Navigation complexity**: count level transitions, backtracks, decision branches at each point and return-to-task recoveries; provide maximum depth and distributions, not only mean tap count.
6. **Responsiveness**: record input-to-visible-feedback and input-to-ready-to-interact with trace-derived timestamps (Perfetto/Macrobenchmark where available). Report median, p95, outliers, cold/warm state and frame metrics separately.
7. **Accessibility**: verify TalkBack names/focus order/announcements, 200% text scale, 48dp targets, contrast/non-color cues, keyboard/switch traversal and orientation/small screens. Record blocks by journey, never average them away; include assistive-tech users in later studies with consent.
8. **Satisfaction**: after each attempt record an optional, plain-language 1–5 ease rating and an open-ended friction note; ask identically on matched versions, randomize presentation, preserve skipped answers.

### Matched baseline protocol

Pair identical phone model, OS/patch baseline, app versions, accounts seeded with **nonpersonal test data**, locale, language, accessibility mode, font size, display brightness, network quality, battery/thermal range and permissions. Baseline is the stock/default launcher on the same build; treatment is the Slickk Experience app (or a separately identified OS build). Counterbalance AB/BA order, predefine success and failure rules, collect at least five pilot attempts per condition then increase trials based on variance; stratify by assistive needs and cold/warm starts. Archive raw anonymous attempt-level logs, tool versions, build IDs, timestamp provenance and exclusions. Report differences with uncertainty and regressions. Do **not** claim percent gains if baseline values are zero or unavailable. No telemetry without explicit opt-in and retention policy. Minimize personal data and never record contact names, Wi-Fi secrets or notification contents.

### Preliminary acceptance thresholds — HYPOTHESES

- At least 25% fewer intentional interactions on *preselected eligible workflows*, without lower completion or any critical accessibility regression (charter M03).
- At least 20% lower p95 completion latency on *declared primary journeys*, controlled for conditions (charter M01).
- All critical screen-reader and large-text journeys pass, with no critical accessibility blocker (charter M05).
- Do not combine different populations or device/build versions into a single unqualified performance claim.

## Capability boundaries and sources

A third-party HOME/launcher implementation can offer app/search shortcuts and open supported intents; it cannot silently replace privileged Wi-Fi management, Overview/Recents or permission-control components. Wi-Fi connection changes occur in Android-owned system UI, e.g. an Internet Settings panel where supported; availability is device/API-dependent and requires graceful fallback. Launcher must not request `CALL_PHONE` just to open `ACTION_DIAL`, nor bulk storage/contacts permission to open their existing apps. `surface` denotes **where the proposed change is actually implemented**, not where the journey happens to start.

Official API/quality references (read as API contracts, **not** observed UX trial evidence):
- Home role: https://developer.android.com/reference/android/app/role/RoleManager
- Intent categories: https://developer.android.com/reference/android/content/Intent
- Settings intents: https://developer.android.com/guide/components/intents-common
- Internet panel (API 29+): https://developer.android.com/reference/android/provider/Settings.Panel
- Accessibility and 48dp touch targets: https://developer.android.com/guide/topics/ui/accessibility/apps

## Provenance and handoff

Source of truth is GitHub task branch `task/P0-009-user-journeys`; this bounded artifact does not authorize P0-011 or P0-012. No APK, on-device traces, real user timing or satisfaction study is claimed. Record later observed measurements with identifiers, consenting collection conditions and raw logs rather than revising hypotheses silently.
