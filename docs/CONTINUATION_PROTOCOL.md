# Multi-Chat Operating Protocol (single source of truth: Git)
## Conversation startup
1. Read README.md, docs/STATUS.md, docs/ROLE_MATRIX.md, docs/ROADMAP.md, tasks/pilot.json and this protocol from the actual repository branch.
2. State assigned ROLE_ID, TASK_ID, latest known commit and any missing access.
3. Confirm dependencies and owned paths. If absent, enter BLOCKED, do not invent state.
4. Enumerate a finite plan 1..N with acceptance check for each step and persistent state.
## Commands
- "Continue": execute the next unfinished, dependency-ready step of the active task, not a new project or arbitrary improvement. Re-read fresh repository status first.
- "Status": read actual registry, PR/checkpoint/test evidence; do not claim progress based on conversational recollection.
- "Review TASK-ID": independently inspect patch, CI and invariants; report evidence and defects.
- "Approve phase N": only owner can authorize next phase after documented exit gate.
- "Pause": checkpoint without pretending ongoing work.
## Output limits
At most 1,500 net new/modified source lines and 8 paths per response; at most one task increment per Continue. If over limit, split into increments and update plan. Reasonable text verbosity, no padded code.
## Git safety
No engineering commits to main. Read branch head and verify permissions. Create task branch "task/TASK-ID-short-name", create draft PR. Never assume push succeeded; report exact commit/PR URL only from tool output. Do not merge without explicit owner authorization and green checks. An untested draft may contain experimental code only when clearly marked UNTESTED; never label accepted.
## Evidence vocabulary
VERIFIED: actual test/log/commit inspected.
USER-REPORTED: user supplied result, not independently reproduced.
UNTESTED: code created, no execution evidence.
HYPOTHESIS: experimental possibility/target.
BLOCKED: material missing dependency or environment.
No fake telemetry, tests, benchmarks, uploads, boot images or hardware compatibility.
## Checkpoint format
ROLE, TASK, BRANCH, BASE_COMMIT, OWNED_PATHS, STEP_X_OF_N, CHANGES, COMMANDS, RESULTS, TEST_ENVIRONMENT, LABEL, OPEN_BLOCKERS, NEXT_STEP, PR_URL.
On finishing: ask review workflow, mark pending review, do not mark DONE until all gates pass.
## Repository concurrency
Never two chats own the same file without explicit integration lead handoff. Pull before committing or use a new branch; resolve conflicts deliberately. Task registry is authoritative for assignment; chat title is not.
