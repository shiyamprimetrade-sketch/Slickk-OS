#!/usr/bin/env python3
"""Validate Slickk-OS task data without depending on Python assert statements."""
import argparse
import json
import re
import sys
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
ID_RE = re.compile(r"P(\d+)-(\d{3,})\Z")
STATES = {"TODO", "IN_PROGRESS", "BLOCKED", "IN_REVIEW", "DONE"}
ROLES = {f"{n:02d}" for n in range(13)}


class RegistryError(ValueError):
    """An invalid task registry or unusable task transition."""


def validate(data, *, require_core=False):
    """Return task count, or raise RegistryError with the first precise defect."""
    if not isinstance(data, dict) or data.get("project") != "Slickk-OS":
        raise RegistryError("project must be Slickk-OS")
    if type(data.get("version")) is not int or data["version"] < 1:
        raise RegistryError("version must be a positive integer")
    tasks = data.get("tasks")
    if not isinstance(tasks, list) or not tasks:
        raise RegistryError("tasks must be a nonempty list")

    by_id = {}
    order = []
    for index, task in enumerate(tasks):
        prefix = f"tasks[{index}]"
        if not isinstance(task, dict):
            raise RegistryError(f"{prefix}: expected object")
        tid = task.get("id")
        match = ID_RE.fullmatch(tid) if isinstance(tid, str) else None
        if match is None:
            raise RegistryError(f"{prefix}: invalid task ID {tid!r}")
        if tid in by_id:
            raise RegistryError(f"{tid}: duplicate task ID")
        by_id[tid] = task
        order.append((int(match[1]), int(match[2])))
        if type(task.get("phase")) is not int or task["phase"] != int(match[1]):
            raise RegistryError(f"{tid}: phase must match task ID")
        if not isinstance(task.get("role"), str) or task["role"] not in ROLES:
            raise RegistryError(f"{tid}: invalid role")
        if not isinstance(task.get("state"), str) or task["state"] not in STATES:
            raise RegistryError(f"{tid}: invalid state")
        if not isinstance(task.get("title"), str) or not task["title"].strip():
            raise RegistryError(f"{tid}: missing title")
        if not isinstance(task.get("acceptance"), str) or not task["acceptance"].strip():
            raise RegistryError(f"{tid}: missing acceptance criteria")
        steps = task.get("steps")
        if (not isinstance(steps, list) or len(steps) < 3
                or any(not isinstance(s, str) or not s.strip() for s in steps)):
            raise RegistryError(f"{tid}: requires at least three nonblank steps")
        if type(task.get("step")) is not int or not 1 <= task["step"] <= len(steps):
            raise RegistryError(f"{tid}: step outside execution range")
        deps = task.get("depends_on")
        if not isinstance(deps, list) or any(not isinstance(d, str) for d in deps):
            raise RegistryError(f"{tid}: depends_on must be a list of IDs")
        if len(deps) != len(set(deps)):
            raise RegistryError(f"{tid}: duplicate dependency")

    if order != sorted(order):
        raise RegistryError("tasks must be ordered by phase and numeric task ID")
    if require_core:
        missing = [f"P0-{n:03d}" for n in range(1, 21)
                   if f"P0-{n:03d}" not in by_id]
        if missing:
            raise RegistryError("missing original pilot tasks: " + ", ".join(missing))

    visiting, visited = set(), set()

    def visit(tid):
        if tid in visiting:
            raise RegistryError(f"{tid}: dependency cycle")
        if tid in visited:
            return
        visiting.add(tid)
        for dep in by_id[tid]["depends_on"]:
            if dep not in by_id:
                raise RegistryError(f"{tid}: unknown dependency {dep}")
            if dep == tid:
                raise RegistryError(f"{tid}: self dependency")
            visit(dep)
        visiting.remove(tid)
        visited.add(tid)

    for tid in by_id:
        visit(tid)

    for tid, task in by_id.items():
        evidence = task.get("evidence", [])
        if not isinstance(evidence, list):
            raise RegistryError(f"{tid}: evidence must be a list of HTTPS URLs")
        for item in evidence:
            if not isinstance(item, str):
                raise RegistryError(f"{tid}: evidence must contain URLs")
            link = urlparse(item)
            if link.scheme != "https" or not link.netloc or not link.path.strip("/"):
                raise RegistryError(f"{tid}: evidence must be an absolute HTTPS URL")
        if task["state"] == "DONE":
            if not evidence:
                raise RegistryError(f"{tid}: DONE requires linked evidence")
            if task["step"] != len(task["steps"]):
                raise RegistryError(f"{tid}: DONE requires final execution step")
            unfinished = [dep for dep in task["depends_on"]
                          if by_id[dep]["state"] != "DONE"]
            if unfinished:
                raise RegistryError(f"{tid}: DONE before dependencies {unfinished}")
    return len(tasks)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", nargs="?", type=Path, default=ROOT / "tasks/pilot.json")
    args = parser.parse_args(argv)
    try:
        data = json.loads(args.path.read_text(encoding="utf-8"))
        count = validate(data, require_core=args.path.resolve() == (ROOT / "tasks/pilot.json").resolve())
    except (OSError, UnicodeError, json.JSONDecodeError, RegistryError) as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1
    print(f"PASS: {count} tasks; IDs, roles, states, steps, evidence and DAG valid.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
