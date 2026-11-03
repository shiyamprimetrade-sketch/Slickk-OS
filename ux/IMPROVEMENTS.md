# P0-009 — Ranked UX experiment shortlist (ALL HYPOTHESES)

Ranked by likely implementation independence, broad utility and safety; **not** by demonstrated user-study value. Each proposal is reversible and must be compared with its matched stock Android flow.

| Priority | Candidate and friction | Design hypothesis / potential benefit | Surface; compatibility and accessibility guardrails | Effort / decisive test |
| --- | --- | --- | --- | --- |
| 1 | **Find apps by name:** users may search several pages | Visible opt-in app search may reduce navigation choices | Launcher; Android package visibility and launcher app listing rules; TalkBack results and keyboard focus | Small; randomized UX-001 success/time/actions, cold/warm launches |
| 2 | **Camera/dialer shortcuts:** important tools may be buried | Clearly labeled, optional shortcuts may aid discoverability | Launcher; invoke installed camera/dialer via safe intents, no silent call and no CAMERA/CALL_PHONE acquisition | Small; UX-002/003 time, mislaunch rate, TalkBack |
| 3 | **Internet entry:** opening Wi-Fi may require multiple gestures | One user-activated Settings Internet panel shortcut may reduce transitions | Launcher shortcut to system UI; API/device support verified at runtime, fallback to Wi-Fi settings; no direct Wi-Fi changes | Small–medium; UX-005 success and step count, fallback test |
| 4 | **Downloads entry:** file manager discovery can vary | Visible Downloads entry to system file UI may simplify retrieval | Launcher; use system file picker or existing file manager, avoid all-files permission; accessible navigation | Medium; UX-009 success/time with a seeded synthetic test file |
| 5 | **Settings entry and plain labels:** categories may be opaque | User-selected settings shortcut may improve discovery | Launcher to Android settings; no privileged toggles; large text and screen reader | Medium; UX-007 observed actions and errors |
| 6 | **Notification/privacy controls:** people may struggle to find options | OS-owned, clearer categories and explanations may reduce errors | Full platform/system UI, **not** normal launcher; preserves permission model; never read notification contents for analytics | High; UX-006/010 access audit and controlled task study |
| 7 | **Overview and one-handed navigation:** gestures vary by device | Reversible OS customization may improve reach and task switching | Full system UI, not third-party launcher privileged controls; gesture alternatives and switch access | High; UX-008/011 assistive-tech study and regression tests |

Before implementation: verify current Android API/device contracts, choose an explicit Android version/device matrix, assign feature flags and rollback, establish baseline logs, and pre-register success/guardrail criteria. More customization can *increase* cognitive burden; include a default/minimal version and never treat fewer visible controls as automatically better. Findings remain **HYPOTHESIS** until direct matched testing.
