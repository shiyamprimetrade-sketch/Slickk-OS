# Slickk-OS: Independent Multi-Chat Execution Protocol (v2)

## Source of truth and authority
The repository and task-specific branches are authoritative; a chat transcript is not a reliable shared ledger.
The owner has **standing authorization for each role to research, design, code, test, commit to its assigned branch, and open a draft PR** without asking Chat 00 or the owner for approval at every substep.
This standing authorization is bounded by task scope, repository credentials, path ownership, test requirements, and hardware safety. It does **not** imply automatic execution while a conversation is closed, or permission to merge to main, flash devices, wipe data, leak secrets, or bypass safeguards.
A role may finish its own task without requesting another role's sign-off. **Task implemented** and **merged/accepted into main** are different evidence-backed states.

## Session startup (works in normal Chat or Work)
1. Fetch latest real repository status; inspect main plus `planning/slickk-os-foundation` while foundation PR #1 is pending. Do not assume that a draft PR has been merged.
2. Identify ROLE_ID and exactly one TASK_ID in `tasks/pilot.json` or a later explicit GitHub issue.
3. Read the source charter, interfaces, the task's existing branch/PR, dependencies and any relevant artifacts.
4. Declare concrete technology stack, exact owned paths, finite numbered Step 1..N plan, tests and completion proof.
5. If a prerequisite is another chat's unfinished *approval or documentation*, proceed with reversible independent research/implementation and record provisional assumptions; never pretend an unmet technical prerequisite is satisfied.
6. Choose and complete as many task steps as feasible **within the current response**. Do not manufacture a need to say Continue after each trivial step.

## Independent execution loop (within each user turn)
- Inspect actual files and choose the smallest complete implementation that meets the assigned acceptance contract.
- Write **real code** where the task calls for executable behavior, CI, validation, tests or integration tools; do not respond with only a plan if execution is possible.
- Use approved task branch `task/TASK-ID-short-description`. Never overwrite another active task branch or someone else's working files.
- Compile, lint, run tests and inspect actual exit codes when tools/environment allow. Reproduce and fix errors before claiming completion.
- Commit actual changes to the task branch and open/update a draft PR using authenticated GitHub tools. Verify the final commit SHA, changed files and CI status. If connector access fails, output a patch and say NOT UPLOADED.
- Do not claim an OS boots, APK installs, optimization wins, or phone support without independent proof.
- On success, conclude with **TASK IMPLEMENTATION COMPLETE** and links/evidence; stop. No more Continue prompts until a new TASK_ID is given.
- If genuinely unable to finish in one message due to tool limits, response/context limits or missing inputs: checkpoint exact Step X/N, changed files, branch, failures, reproducible commands; end **INCOMPLETE — CONTINUE SAME TASK**. A later Continue resumes from checkpoint, not from Step 1.

## Commands
- `Start TASK-ID`: claim/reload exactly that task and execute independently toward full completion.
- `Continue`: only when the active task is unfinished; resume and execute as far as possible in the next turn. If task is already complete, report COMPLETE and request a new TASK_ID; do not silently choose another task.
- `Status`: fetch live GitHub state and report verified work and pending PRs.
- `Review TASK-ID`: inspect existing changes and evidence; no fabricated approvals.
- `New TASK-ID`: begin a separately assigned task after previous task is complete.
- Chat 00 may assign task IDs and coordinate but is not a runtime dependency for Chat 01 or 02.

## Output constraints per response
- Maximum **1,500 lines of added/modified source code**; do not inflate or pad code.
- Maximum **8 changed file paths**.
- One active task per chat at a time; break an oversized task into internal numbered steps and persist checkpoints.
- Report actual outcomes, not a generic progress narrative. Avoid asking for unnecessary permission or confirmation when requirements suffice.

## Evidence labels and completion
VERIFIED: actual test/log/commit/CI evidence inspected; USER-REPORTED: provided by owner; UNTESTED: not run; HYPOTHESIS: proposed; BLOCKED: true environmental prerequisite.
A specialist can mark its *own assigned task implementation* complete when task acceptance criteria have objective supporting evidence and a branch/PR exists (or explicitly state NOT UPLOADED).
Task registry entry DONE means its defined acceptance contract was met, with accessible evidence; separate merge state must be tracked explicitly. Do not mark main integrated merely because a PR exists.
If tests cannot run, label **UNTESTED / NOT COMPLETE**, checkpoint and stop when no further feasible work remains.
Review required to merge critical OS/security/kernel work can be evidence-based and asynchronous via CI/review tools, but not an excuse to avoid coding.

## Git and safety
- Never push unfinished engineering directly to `main`; task branches and draft PRs are automatically authorized.
- Merging to main is a separate action and is **not** automatically authorized by this instruction; preserve CI/security and integration gates.
- No destructive device actions, unlocks, wipes, firmware flashes, kernel replacements, or external secret exposure without separately specified explicit user consent.
- Respect upstream AOSP and kernel licenses; do not copy proprietary vendor components or pretend to have trained a new AI model on the source code.
- Changes need compatible APIs, dependency checks and rollback plan. A missing human review does not block *writing and testing* a task, but an actual technical dependency may.

## Checkpoint, required fields
ROLE | TASK_ID | OBJECTIVE | SOURCE_COMMIT | OWNED_PATHS | TECH_STACK | STEP_X_OF_N | TEST_COMMANDS | ACTUAL_RESULTS | EVIDENCE_STATUS | BRANCH | PR_URL | BLOCKERS | NEXT_STEP.

## Chat 00 Work-limit resilience
Chat 00 is optional during a specialist's execution. Read tasks and checkpoints from Git, never assume Chat 00 can send messages.
If Chat 00 reaches Work usage limits, any new normal chat started with `prompts/00_normal_fallback.md` can resume coordination from the repository. This fallback cannot execute work asynchronously or automatically open other chats.
