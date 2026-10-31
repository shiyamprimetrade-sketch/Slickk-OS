# Slickk-OS Project Charter — Phase 0
## Purpose
Create an Android-compatible smartphone operating system whose usability, responsiveness, energy efficiency, accessibility, reliability and privacy are demonstrably improved over matched Android baselines. This is an engineering goal, not an accomplished claim.
Owner decides product scope, supported devices, merges, flash actions and releases.
## Implementation status and authority
This charter is the P0-001 planning deliverable under [protocol v2](CONTINUATION_PROTOCOL.md). Task implementation completion, independent integration review, owner merge authorization and product release are separate states. The owner authorized routine task work and self-contained implementation acceptance; no owner approval of measured product results is implied.
The protocol from foundation commit 7f178f5599c6cce507f71f477e3ba15dcecbc875 supersedes older one-step-per-Continue and blocking-approval wording in the roadmap, older prompts and historical checkpoints.

## Intended users
- **U1 — Everyday Android users:** find and open apps, reach settings and finish essential tasks with less friction, initially evaluating resource-constrained/midrange use where feasible.
- **U2 — Accessibility users:** people using screen readers, large text and alternative navigation; critical journeys must work without losing controls.
- **U3 — Platform evaluators:** contributors evaluating a reproducible AOSP-derived platform in Cuttlefish first; physical-device testers follow verified device feasibility.
These are initial engineering cohorts, not completed market/user research. P0-009 validates their journeys. No supported phone, minimum API or locale matrix has yet been demonstrated.

## Distinct deployment tracks
1. **Experience track (APK)**: Slickk Launcher and companion apps running on existing Android phones without changing firmware. Works only to the extent Android APIs and device policy permit.
2. **Platform track (AOSP OS)**: Android-compatible system builds, Cuttlefish-first, then specific supported unlockable devices. Do not imply one ROM works on every phone.
3. **Research track**: source audit, traces, controlled experiments and reduction of unnecessary complexity with regressions tests.
Experience APK results apply to the measured app/journey on the named stock build; installing a launcher does not replace Android. Platform emulator results establish only their measured virtual-device scope. Phone performance and energy need matched physical-device evidence. Research retains required behavior and a rollback path.

## Tracked success criteria — HYPOTHESES, NOT ACHIEVED
Definitions, accountable task owners, measurement boundaries and uncertainty rules are in the [product contract](contracts/P0-001-product-contract.md). Requirement IDs R01–R11 map the mission and safeguards to observable checks.

| ID | Target or acceptance guardrail | Measurement owner |
|---|---|---|
| M01 | P95 task-completion latency at least 20% lower in declared primary journeys | 03/P0-007 with 09/P0-009 |
| M02 | Median energy consumed over matched 8-hour idle sessions at least 15% lower | 03/P0-007 with 05/P0-016 |
| M03 | At least 25% fewer intentional interactions in selected workflows without lower completion rate or hidden controls | 09/P0-009 and P0-011; 03 verifies |
| M04 | Proposed clarification: at least 20% lower missed-frame fraction; separately report P95 frame duration | 03/P0-007 with 10/P0-017 |
| M05 | All declared screen-reader/large-text critical journeys pass; no new critical accessibility blocker | 09/P0-009 and P0-011 |
| M06 | No unexplained permissions/identifiers; default opt-in telemetry OFF; justify retained data and test controls | 04/P0-006 and P0-014 |
| M07 | Crash/ANR rates no worse at defined exposure; no critical new failure | 03/P0-007 and 12 QA |
| M08 | Sustained thermal behavior no worse and within verified target safety limits | 05/P0-016 and 10/P0-017 |
| M09 | All frozen required app journeys/system-interface cases pass, with versions and unrun tests disclosed | 08/P0-013; 01/P0-002; 06/P0-019 |

**M04 reconciliation:** the existing benchmark document says "P95 frame jank." This charter exposes the proposed measurable interpretation rather than claiming the wording already agrees. P0-007 must reconcile and freeze the metric before measurement; until then smoothness acceptance is unresolved.
No percentage is an achieved result. Use raw repeated measurements on matched configurations, prespecified comparisons and uncertainty reporting. Missing/insufficient evidence is INCONCLUSIVE, not PASS. Zero/below-resolution baselines cannot support relative percentage gains. Minimum pilot counts are five UI runs and three battery sessions; those counts alone do not establish statistical sufficiency.

## Independent engineering and dependencies
The registry preserves all 20 task IDs, roles and dependencies. Chat 01 may implement P0-002 and Chat 02 may implement P0-004 independently using the available charter provisionally; neither waits for Chat 00 availability or routine approval. Unfinished documentation/approval is distinct from an unmet technical prerequisite. Never claim a source pin, build, policy enforcement or compatibility test that is not verified.
Task owners use separate branches/draft PRs and record scoped path ownership, tests, failures, assumptions and rollback. Their implementation completion does not imply integration into main.

## Non-negotiables
- Preserve Android application compatibility, privacy boundaries and verified-boot integrity where supported.
- Never claim an improvement without a matched before/after benchmark and methodology.
- Treat the 140M-line thought experiment as a planning constraint, **not** a product goal.
- Never remove code just because it looks verbose: prove it is unreachable, redundant, replaceable or unneeded for the supported configuration.
- Never flash or unlock the owner's daily phone without separate, explicit consent and a validated backup/recovery process.
- Never use or publish proprietary vendor code without permission.
## Task completion criteria and review
P0-001 acceptance: reviewed mission, intended users and tracked success criteria, with an accessible implementation/checkpoint and actual validation.
1. Mission and track boundaries documented; R01–R11 map requirements to checks/owners.
2. U1–U3 described and untested user assumptions labeled.
3. M01–M09 defined with targets/guardrails, evidence requirements and unresolved downstream decisions.
4. Original compatibility, accessibility, security, licensing and device-safety boundaries preserved.
5. Registry and task-specific validation run; exact branch/PR/commit and limitations recorded.
6. Responsible role's review identifies any remaining integration/runtime gates; no fabricated independent approval.

The [checkpoint](checkpoints/P0-001.md) records the assessment. Owner-authorized autonomous task completion is sufficient for this documentation task's implementation status; independent review and owner authorization remain separate merge/release gates.

## Open downstream decisions
AOSP source pin (01/P0-002); device/API/locale feasibility (06/P0-003 with 09/P0-009); versioned app/interface suite (08/P0-013); detailed benchmark/statistical protocol and M04 reconciliation (03/P0-007); target thermal limits (05/P0-016); branch protection (02/P0-004); builder feasibility (12/P0-018).
These are explicitly tracked future work, not accomplished facts or routine approval blocks on independent implementation.

## Release gates
A. Validated repository and roles; B. Installable user-experience APK; C. Reproducible Cuttlefish boot; D. Experimentally verified system improvements; E. Hardware port with recoverability; F. Security, compatibility, update and reliability review.
Current reality: public repository exists; planning bootstrap only; no OS image, app build or benchmark result.
