# P0-001 — Product and acceptance contract

Status: IMPLEMENTED PLANNING CONTRACT; runtime targets remain unachieved hypotheses. Merge/release acceptance is separate.
Author/owner: role 00, P0-001. Task input: f5da546b5f3a31852c7901ea96f395d0d449a81f. Authority: protocol v2 at foundation 7f178f5599c6cce507f71f477e3ba15dcecbc875 and the owner's standing authorization.
Purpose: preserve Android application compatibility while demonstrating specific improvements in user experience, energy, privacy and reliability. This document supplies the definitions referenced by the implemented project charter. No measured result or device support is asserted.

## Intended users and initial scope
- U1: everyday Android phone users who need to find/open apps, reach settings and complete essential tasks with less friction. Prioritize a representative resource-constrained/midrange pilot once target feasibility is established; no universal hardware claim.
- U2: people using screen readers, enlarged text or alternative navigation. These are first-class participants in the same critical journeys, not an optional post-release cohort.
- U3: technical evaluators of a reproducible AOSP-derived system. Their first platform target is Cuttlefish; physical-device testers are a later, explicitly supported cohort.
These are the initial engineering user cohorts selected within the owner's authorized task scope, not findings from completed user research or a claim of separate owner product ratification. P0-009 validates journey needs. Device model, minimum Android API, locale coverage and compatibility-app versions remain named decisions below.

## Three claim boundaries
| Track | Intended deliverable | Permitted claim after evidence | Limits |
|---|---|---|---|
| Experience | Normal launcher/companion APK using available Android APIs | Improvement in the measured APK/journey on stated device and stock build | No kernel/HAL/control privilege assumed; no claim that installing a launcher replaces Android or proves system-wide battery savings |
| Platform | Pinned AOSP-derived image, Cuttlefish baseline first | Reproducible boot/API behavior; later improvements on measured targets | Emulator timing does not prove phone performance or energy; target-specific vendor/boot requirements remain |
| Research | Source audit, traces and reversible experiment reports | A scoped bottleneck, supported optimization or rejected hypothesis | Code size alone is not value; unknown code is not safe to delete |

## Requirement-to-check contract
| ID | Requirement and observable acceptance check | Accountable role / task |
|---|---|---|
| R01 | Mission, U1–U3, track boundaries and metric IDs reviewed by the responsible role with accessible checks/checkpoint before P0-001 DONE; independent merge review and owner merge authorization tracked separately | 00 / P0-001 |
| R02 | Pin exact upstream provenance, release identity and license notices before platform changes; inventory inherited notices and restricted vendor materials | 01 / P0-002; 04 review through P0-006 |
| R03 | Versioned Android app/API/ABI suite passes required cases; no unapproved interface removal; unsupported cases disclosed | 08 / P0-013; 09 app implementation |
| R04 | Matched baseline/candidate evidence meets the named metric target using a protocol fixed before candidate measurements | 03 / P0-007; component owners implement |
| R05 | All declared critical screen-reader and large-text journeys pass; no lost controls or critical new barriers | 09 / P0-009, P0-011; 03 verification |
| R06 | Permission/data-flow inventory, explicit opt-in collection policy, retention/deletion controls and no new unresolved critical security finding | 04 / P0-006, P0-014 |
| R07 | Crash/ANR and thermal guardrails pass; any regression blocks acceptance of the optimization pending resolution | 03 / P0-007; 05 / P0-016; 10 / P0-017 |
| R08 | Before removing/replacing code: exact source, consumers, feature/config dependencies, license/security/accessibility effects, tests and rollback reviewed | 01 / P0-010; relevant component role |
| R09 | Device capability matrix records known/unknown/unsupported; any future destructive action needs separate owner authorization and validated recovery | 06 / P0-003, P0-019; 11 boot/recovery review |
| R10 | Separate task branches/draft PRs, dependency gates, disjoint ownership, exact-commit evidence and reviewed integration; owner separately authorizes merge/release | 02 / P0-004; 12 / P0-005; 00 acceptance |
| R11 | Measured host feasibility and repeatable Cuttlefish setup/boot-evidence plan; no fabricated build success | 12 / P0-018; 11 boot review |

## Measurement contract
All M01–M09 entries below are proposed targets/guardrails, not results. Method owner is role 03; listed partners supply domain-specific definitions. Applicable tracks and workloads must be declared before testing. A requirement cannot disappear through a post-result scope change.

For lower-is-better values, relative improvement = 100 * (baseline - candidate) / baseline, with baseline > 0. If baseline is zero, below instrument resolution or missing, relative improvement is NOT EVALUABLE; report absolute values and retain regression checks. Record raw per-run/per-session data, not only a favorable aggregate.

| ID | Observable value and proposed acceptance | Scope / accountable tasks |
|---|---|---|
| M01 responsiveness | Milliseconds from a scripted input event to a predefined ready-to-use UI state, with cold/warm scenarios separate. P95 candidate latency <= 0.80 * baseline for each preregistered primary journey; publish p50/p95 and failures | Experience and later platform on matched target; 03/P0-007 + 09/P0-009 |
| M02 energy | Battery energy used per controlled 8-hour idle session, preferably calibrated mWh; charge or battery-percentage proxies must be labeled and resolution assessed. Median candidate consumption <= 0.85 * baseline across matched sessions; active/background functionality must remain equivalent | Physical targets only; APK claims limited to whole-device measurements with only APK condition changed, not an inferred OS improvement; 03/P0-007 + 05/P0-016 |
| M03 usability | Successful task's count of discrete intentional actions (tap, swipe, voice command, navigation key); text-entry segments counted by a frozen rule. Count <= 0.75 * baseline for each selected primary journey; no lower completion rate or hidden essential/accessibility control | 09/P0-009 + P0-011, 03 verifies; human usability success needs actual participants, not simulated satisfaction |
| M04 smoothness | Proposed resolution of ambiguous "P95 frame jank": primary metric is fraction of observed frames missing their applicable presentation deadline in the fixed workload; candidate jank fraction <= 0.80 * baseline. P95 frame duration in ms reported separately as a diagnostic | 03/P0-007 + 10/P0-017; fixed device refresh mode; requires benchmark-document reconciliation before measurement |
| M05 accessibility | All declared critical journeys pass screen-reader labels/focus/order/actions and enlarged-text navigation/readability checks; zero new critical blockers versus baseline; report each configuration, not just an average | 09/P0-009 + P0-011, 03 verification; supported scale/input combinations frozen in protocol |
| M06 privacy | No unexplained permission or identifier addition; every retained permission/data flow justified; default opt-in telemetry OFF and controls/retention/deletion tests pass. Claim "fewer" only when a documented unnecessary permission/identifier is actually removed without broken behavior | 04/P0-006 + P0-014; manifest/dynamic inventory, relevant network/storage observations |
| M07 reliability | Crash/ANR counts, exposure (user-hours and completed journeys) and rates reported separately. Candidate rates must not exceed baseline under the predeclared comparison; no critical new failure. Zero observed events alone is insufficient proof of equal reliability | 03/P0-007 + 12 QA; matched workloads and minimum exposure/uncertainty plan required |
| M08 thermal | Report sustained-workload temperature rise above ambient and thermal-throttling duration/severity for fixed windows; candidate must not worsen the declared baseline guardrails or exceed target safety limits | 05/P0-016 + 10/P0-017, 03 verifies; valid sensors, windows and target limits unresolved until feasibility/protocol |
| M09 compatibility | 100% of the frozen required app journeys and system-interface tests pass; versions/results listed per case. Required CTS/VTS scope is identified for the pinned platform; unrun tests remain unverified and no certification claim is inferred | 08/P0-013 + 01/P0-002, 06/P0-019 for vendor contracts |

M04 is explicitly surfaced in the charter as a proposed clarification of docs/BENCHMARKS.md, which still uses the older ambiguous wording. P0-007 must reconcile the benchmark document and freeze the metric before an experiment; disagreement leaves the smoothness claim blocked.

## Evidence and decision rules
1. Freeze a protocol revision with source/build/app hashes, hardware, primary/secondary outcomes, inclusion/exclusion rules, run order, instrumentation overhead, failure handling and analysis before comparing a candidate. Do not change targets after seeing results.
2. Use matched device/build conditions, brightness/refresh/network/background activity, temperature and battery health; log deviations. APK comparison uses the same underlying stock OS. Platform comparison identifies all upstream and patch differences.
3. Preserve existing minimum pilot counts: five UI runs and three matched battery sessions. A run must contain enough observations for its chosen percentile; five isolated timings do not establish a useful tail estimate. Sample size/exposure and uncertainty method are P0-007 deliverables.
4. Report variation and uncertainty using the actual independent sampling unit (session/device/participant as appropriate). Do not treat correlated frames as independent battery sessions or independent people. Publish failures/exclusions and unsuccessful optimizations.
5. Threshold met with adequate prespecified evidence => metric PASS; threshold missed => FAIL; missing data, insufficient precision/power, zero denominator or unresolved definition => INCONCLUSIVE/BLOCKED. No advantage claim from an inconclusive pilot.
6. No trade of compatibility/security/accessibility/reliability for a speed score. Energy and thermal regressions block optimization acceptance. Where the pilot cannot resolve a guardrail, acceptance remains pending.
7. Every report records task/branch/commit, baseline/candidate IDs, commands/tool versions, environment, raw-evidence paths, checksums where files exist, analysis, limitations, reviewer and rollback. Public evidence must exclude secrets and personal phone data.
8. Emulators can establish functional evidence within their scope; only physical tests establish phone performance/energy. Source inspection can establish contracts, not tested runtime behavior.

## File ownership and dispatch contract
Authoritative allocations are in tasks/pilot.json. owned_paths reserves files for a task; it does not assert those files exist. planned_branch is a future name, not a claim that a branch or specialist conversation was created. Exact paths and trailing /** subtree reservations are supported. A subtree is not permission to exceed the response file/line limits.

Assigned roles have standing authorization to execute their tasks independently under protocol v2. Chats 01/P0-002 and 02/P0-004 need no Chat 00 approval or Work quota. Prerequisite documentation/approval may be provisional for reversible work; real technical dependencies must still be verified and recorded before dependent claims.
1. Read live task branch, registry and dependency evidence; record provisional assumptions.
2. Declare finite steps, stack, paths, checks and checkpoint; complete as much as feasible in the current turn.
3. Create/reuse the task branch and draft PR without routine approval; verify writes and CI.
4. Preserve other active owners' paths. Record any owner-authorized path reconciliation in checkpoint/PR.
5. Record one's own result in the task checkpoint and own task-branch registry entry; preserve other task results. Shared-ledger integration can occur asynchronously.
6. On objective task acceptance, mark implementation complete and stop until a new task is assigned. Merge, release and destructive actions remain separate.

The registry records Chat 01's architecture/** scope and Chat 02's integration/** and .github/** scope. The prior inactive workflow reservation for P0-005 is transferred to P0-004 to avoid overlapping ownership; P0-005 keeps its validator and validation report. The two role chats remain independently authorized; their TODO states in this branch are not claims about unobserved work elsewhere.

The launcher skeleton is contained under experience/launcher/ so Gradle root files are local to that subtree. Source/evidence subtree reservations are exclusive. Additional repository-root configuration requires explicit allocation; no incidental writes outside ownership.

Role 11 has reserved review assignments for P0-006 (boot/update threat assumptions), P0-018 (boot-evidence/recovery plan) and P0-020 (deferred boot/update gates). These are bounded review contributions to existing task IDs, not new pilot tasks. Each has a distinct report path and planned task branch/draft PR. Activate when a reviewable candidate exists; unfinished documentation may be provisional, but actual technical prerequisites remain explicit. Role 11 cannot approve its own implementation or substitute for owner authorization.

## Open decisions with accountable owners
| Decision | Owner / due gate | Effect until resolved |
|---|---|---|
| Validate U1–U3 through later journey research | 09 / P0-009 | Initial engineering scope is usable; no completed user research claimed |
| Choose upstream baseline and license record | 01 / P0-002 | Platform source contract not pinned |
| Choose actual device/API/locale support and read-only test access | 06 / P0-003 with 09 / P0-009; before launcher requirements/build | No claimed supported phone or universal compatibility |
| Freeze journeys, app versions, input/large-text configurations | 09 / P0-009, 08 / P0-013 | Runtime acceptance not executable yet |
| Resolve M04 and freeze statistical/measurement/exposure rules | 03 / P0-007 | No benchmark pass or advantage claim |
| Set hardware-specific thermal limits and available sensor evidence | 05 / P0-016 with 06 feasibility | Thermal guardrail unresolved |
| Protected-main settings and cross-branch integration | 02 / P0-004 | main remains observed unprotected; no direct engineering commits |
| Adequate builder and boot-evidence collection | 12 / P0-018 with 11 review | No full OS build claim |
| Independent integration review and owner merge authorization | PR review/merge gate | Does not block implementation completion or other chats; no merge claimed |

Unknown device/runtime details do not prevent a planning contract; they do prevent downstream runtime claims and acceptance until their named gates pass.

## Implementation acceptance and separate integration
The task's original acceptance is "Reviewed mission, intended users, tracked success criteria." The responsible director reviews those three elements, links the implemented charter and definitions, runs the registry and task-specific checks, records findings, and verifies the task branch/PR. This satisfies implementation review under protocol v2; it is not an independent review or an owner approval claim.

The six-step plan remains finite: inspect inputs; define contracts; amend charter; validate; persist PR/evidence; assess implementation acceptance. All may execute within one response. Old Step 2 restrictions demanding a separate Continue or owner/other-role approval before implementation completion are superseded by the owner's updated instructions and protocol v2.

The historical Step 2 JSON report describes that old snapshot only. The current checkpoint/registry and this contract govern continuation. The old roadmap Continue paragraph also yields to protocol v2: completed tasks stop; no automatic next task or phase.

Phase 0 remains incomplete until P0-020 and roadmap gates have evidence. A P0-012 toolchain blocker is not APK installation evidence. No merge, unlock, flash, wipe or public release is authorized here.
