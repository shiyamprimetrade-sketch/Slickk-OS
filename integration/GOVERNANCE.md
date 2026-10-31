# P0-004: Branch and PR governance (implementation contract)

## Branching, roles and task authority
- Source of truth: tasks/pilot.json at the PR head; an explicit task owned_paths set overrides fallback roles in integration/ownership.json.
- Each role (00–12) uses exactly one active task/P0-NNN-lowercase-description branch per task. planning/slickk-os-foundation is the unmerged foundation; do not replace or force-push it.
- Task branches may stack on a completed task implementation branch before it merges. Record parent branch, exact parent commit and upstream PR. The GitHub PR base must be that parent branch for a narrow review diff. Rebase/retarget after upstream merges, then rerun checks.
- Roles 00 program; 01 architecture; 02 integration; 03 verification; 04 security; 05 kernel; 06 HAL/device; 07 runtime/native; 08 framework; 09 apps/UX; 10 graphics/media/network; 11 boot/update; 12 build/QA. No chat identifier is a GitHub user account. GitHub CODEOWNERS can be installed later only with real review accounts.
- Commit convention: feat(P0-NNN): ..., fix(P0-NNN): ..., test(P0-NNN): ..., docs(P0-NNN): .... Do not commit unfinished work to main or bypass owner merge authorization.
- Shared paths: request handoff and add explicit owned_paths in the authorized task registry before modifying; otherwise the validator fails. Treat same-path modifications in parallel branches as conflicts even when Git can auto-merge them.

## CI and review requirements
- integration/validate_pr.py checks task branch, PR title, metadata, registry ID, role/path ownership, changed filenames, task dependencies and ready-for-review state.
- Draft PRs may carry provisional missing-documentation dependencies as warnings. Making a PR ready for review fails if any task dependency is not DONE on the checked-out registry. A branch/PR alone is not a merge or accepted product.
- The workflow uses read-only permissions, checks out exact PR head, compares exact base SHA with HEAD, and runs unittest plus the existing registry validator. This is lightweight governance CI, not a Soong, Gradle, AOSP or device build.
- Reviewers inspect actual changed code, CI, upstream license notices, API/ABI/VINTF contract changes, task completion evidence, security/privacy, and any performance regression tests. Critical platform changes require appropriate specialist review. P0-004 does not certify those tests.
- Before merging, require green checks on the exact updated head, resolved reviews, owner authorization and an explicit rollback plan. Do not rely solely on an automatically generated mergeability flag.

## Main branch protection: requires owner UI action
- Live observation 2026-10-31: main protected=false; rulesets=[]; connector lacks branch protection mutation.
- Owner UI: repository Settings → Branches → Add branch protection rule, pattern main; enable required pull request reviews (when an independent reviewer is eligible), required passing checks (registry now; governance once running), conversation resolution, prohibit force pushes/deletions, and apply to administrators where the plan/UI supports it. Save, then verify GET /repos/{owner}/{repo}/branches/main returns protected: true and inspect actual required checks.
- Warning: main currently has only README; do not designate unobserved check names as required before a successful run exists. Protect against admin bypass and direct pushes if the GitHub plan offers those controls. No claim of configured branch protection is made by this PR.

## Conflicts, integration, rollback and checkpoint
1. Compare task PR with its declared parent SHA; inspect every changed path and overlapping active PRs. For ownership collisions, stop and obtain documented handoff rather than silently resolving one contributor's work away.
2. Validate package/API contracts (see integration/CONTRACTS.md); add component build checks only when real build inputs exist and hosts are capable. No claims of full AOSP runner feasibility.
3. Demonstrate rollback before merge: close a draft PR or delete its unmerged task branch after preserving its commit SHA. For an already merged change, use git revert <merge_or_squash_commit> on a new task branch, run CI and seek explicit approval to merge the revert. Never reset or force-push shared main.
4. Keep source/target SHA, task state, owned paths, test commands, exit statuses, CI run URLs, failing test logs, risk assessment and next steps under integration/checkpoints/. Preserve artifact name, source SHA, toolchain version, SHA-256 and build provenance when builds exist.
5. A blocked protection setting is a genuine acceptance exception, not evidence that protection is enabled. Do not mark the repository integrated merely because this draft PR exists.

## Reproduce
1. python3 -m unittest discover -s integration -p 'test_*.py' -v
2. python3 scripts/validate_registry.py
3. On an actual PR-head checkout with a saved GitHub PR event: python3 integration/validate_pr.py --event "$GITHUB_EVENT_PATH" --base "$PR_BASE_SHA"
