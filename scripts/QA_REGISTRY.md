# P0-005 task-registry QA and reproducibility

## Scope and ownership
Chat 12 owns this registry validator, its Python unit tests and `p005-registry-qa.yml`.
Chat 02/P0-004 retains PR naming, code ownership, ready-for-review and path-conflict
policy in `integration/` and `.github/workflows/integration-gates.yml` on its draft
branch. This QA change does **not** duplicate or certify those live GitHub checks.
Until P0-004 is accepted, its policy is provisional. No branch protection is presumed.

## Reproduce on a clean checkout
Requires Python 3.12 (CI), Python standard library only, no pip dependencies.

~~~sh
python3 --version
python3 -m compileall -q scripts
python3 scripts/validate_registry.py
python3 -m unittest discover -s scripts/tests -p 'test_*.py' -v
python3 -O scripts/validate_registry.py
sha256sum tasks/pilot.json scripts/validate_registry.py scripts/tests/test_validate_registry.py
~~~

Successful exit status of all commands is **0**; the CLI prints `PASS: N tasks`;
`unittest` reports `OK`. A malformed registry exits **1** with `FAIL:` to stderr.
Tests use synthetic task objects for negative controls; they are not Android tests.
Run against a pinned commit, preserve command logs and file SHA-256 digests.
The `test_real_registry` test runs against the checked-out `tasks/pilot.json`;
missing file in an isolated test environment is explicitly skipped, not silently passed.
No requirements.txt or lock file is necessary with the standard library only.

## Contract
- IDs are unique and numerically ordered, roles `00` to `12`, statuses one of
  `TODO`, `IN_PROGRESS`, `BLOCKED`, `IN_REVIEW`, `DONE`; original P0-001…020
  are retained when validating the project registry, but supplementary tasks
  are allowed. A phase agrees with the task ID.
- Every task has nonblank title, acceptance and at least three nonblank steps,
  a valid active step, and valid unique dependency references forming a DAG.
- `DONE` requires all dependencies `DONE`, a completed final step, and an
  `evidence` array of absolute HTTPS references (e.g. GitHub PR and CI run).
  Evidence URLs are syntax-checked, **not fetched or authenticated**; independent
  reviewer verification is required before accepting a result or merging.
- The existing project registry contains only `TODO` tasks and is unchanged.
  This branch's draft PR is not itself evidence that P0-004 was accepted.

## Build and integration gates
Registry CI does not build AOSP, Android apps, a kernel, a system image or an APK.
Future build provenance should record exact source manifest and revision, toolchain
versions, commands, logs, artifacts' SHA-256, signatures where appropriate, and
reproducibility comparison on a separate host. Any true artifact needs a fresh
build and checks of signing-key custody, secrets, licenses, ABI/API compatibility
and release readiness. Run PR governance separately on Chat 02's integration branch
when available; no ownership or branch protection success is inferred here.
Rollback: close this unmerged draft PR or revert its commit(s) on a separate branch.
