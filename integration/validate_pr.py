#!/usr/bin/env python3
"""Read-only, stdlib-only task PR governance validator for Slickk-OS."""
import argparse
import json
import re
import subprocess
import sys
from pathlib import Path, PurePosixPath

TASK_ID = re.compile(r"P0-\d{3}")
BRANCH = re.compile(r"^task/(P0-\d{3})-[a-z0-9]+(?:-[a-z0-9]+)*$")
FIELDS = ("Task ID", "Tests", "Rollback", "Security", "Compatibility", "Base commit")


def match_scope(path, scope):
    if scope.endswith("/**"):
        return path.startswith(scope[:-3] + "/")
    if scope.endswith("/"):
        return path.startswith(scope)
    return path == scope


def valid_path(path):
    return (bool(path) and not path.startswith("/") and "\\" not in path
            and all(part not in ("", ".", "..") for part in path.split("/"))
            and not any(ord(ch) < 32 for ch in path))


def extract_fields(body):
    values = {}
    for field in FIELDS:
        m = re.search(r"(?im)^" + re.escape(field) + r":\s*(.+?)\s*$", body)
        if m:
            values[field] = m.group(1).strip()
    return values


def audit(registry, ownership, *, head, title, body, changed, draft):
    """Return (blocking errors, nonblocking warnings), never modify repository state."""
    errors, warnings = [], []
    tasks = registry.get("tasks", [])
    entries = {t.get("id"): t for t in tasks}
    if len(entries) != len(tasks) or not entries:
        errors.append("Task registry contains duplicate IDs or is empty")
    m = BRANCH.fullmatch(head)
    if not m:
        return [*errors, "Branch must match task/P0-NNN-lowercase-description"], warnings
    task_id = m.group(1)
    task = entries.get(task_id)
    if not task:
        return [*errors, f"Unknown task ID: {task_id}"], warnings
    if not title.startswith(f"[{task_id}] "):
        errors.append(f"PR title must start with [{task_id}] ")
    values = extract_fields(body or "")
    for field in FIELDS:
        if not values.get(field) or values[field].lower() in ("tbd", "todo", "none", "n/a"):
            errors.append(f"Missing meaningful PR field: {field}")
    if values.get("Task ID") != task_id:
        errors.append("PR Task ID field does not match branch")
    base = values.get("Base commit", "")
    if not re.fullmatch(r"[0-9a-f]{40}", base):
        errors.append("Base commit field must be a full 40-character SHA")
    task_role = task.get("role")
    if task_role not in ownership.get("role_scopes", {}):
        errors.append(f"Unknown ownership role {task_role}")
    scopes = task.get("owned_paths") or ownership.get("role_scopes", {}).get(task_role, [])
    if not scopes or any(not valid_path(s.removesuffix("/**").rstrip("/")) for s in scopes):
        errors.append("Missing or unsafe ownership scopes")
    if not changed:
        errors.append("PR must change at least one file")
    for path in changed:
        if not valid_path(path):
            errors.append(f"Unsafe changed path: {path!r}")
        elif not any(match_scope(path, s) for s in scopes):
            errors.append(f"Out-of-scope modification: {path}")
    if len(changed) != len(set(changed)):
        errors.append("Duplicate changed file paths")
    for dep in task.get("depends_on", []):
        if dep not in entries:
            errors.append(f"Unknown task dependency: {dep}")
        elif entries[dep].get("state") != "DONE":
            msg = f"Dependency {dep} is {entries[dep].get('state')}, not DONE"
            (warnings if draft else errors).append(msg)
    if task.get("state") == "DONE" and not draft:
        warnings.append("Task marked DONE: still require independent review and authorized merge")
    if not draft and task.get("state") not in ("IN_REVIEW", "DONE"):
        errors.append("Ready-to-review PR requires task state IN_REVIEW or DONE")
    return errors, warnings


def changed_paths(repo, base):
    if not re.fullmatch(r"[0-9a-f]{40}", base):
        raise ValueError("Invalid base SHA")
    result = subprocess.run(["git", "-C", str(repo), "diff", "--name-only", "-z", base, "HEAD"],
                            capture_output=True, check=True)
    return [x.decode("utf-8") for x in result.stdout.split(b"\0") if x]


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--repo", type=Path, default=Path(__file__).resolve().parents[1])
    p.add_argument("--event", type=Path, required=True, help="GitHub pull_request JSON event")
    p.add_argument("--base", required=True, help="Exact base commit SHA (not a branch name)")
    args = p.parse_args(argv)
    try:
        event = json.loads(args.event.read_text(encoding="utf-8"))
        pr = event["pull_request"]
        if pr["base"]["sha"] != args.base:
            raise ValueError("PR event base SHA differs from supplied base")
        checked_out = subprocess.run(["git", "-C", str(args.repo), "rev-parse", "HEAD"],
                                     capture_output=True, text=True, check=True).stdout.strip()
        if pr["head"]["sha"] != checked_out:
            raise ValueError("Checkout HEAD differs from PR head SHA")
        registry = json.loads((args.repo / "tasks/pilot.json").read_text(encoding="utf-8"))
        ownership = json.loads((args.repo / "integration/ownership.json").read_text(encoding="utf-8"))
        files = changed_paths(args.repo, args.base)
        errors, warnings = audit(registry, ownership, head=pr["head"]["ref"],
                                  title=pr["title"], body=pr.get("body") or "",
                                  changed=files, draft=bool(pr["draft"]))
    except (OSError, ValueError, KeyError, subprocess.CalledProcessError, UnicodeDecodeError) as exc:
        print("FAIL: validation setup: " + str(exc), file=sys.stderr)
        return 2
    for w in warnings:
        print("WARN: " + w)
    for e in errors:
        print("FAIL: " + e, file=sys.stderr)
    print(f"Integration audit: task={pr['head']['ref']} files={len(files)} "
          f"errors={len(errors)} warnings={len(warnings)}")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
