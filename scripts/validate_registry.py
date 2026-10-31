#!/usr/bin/env python3
import json
from pathlib import Path
from collections import Counter

root = Path(__file__).resolve().parents[1]
data = json.loads((root / "tasks/pilot.json").read_text())
tasks = data["tasks"]
ids = [t["id"] for t in tasks]
assert len(tasks) == 20, "Expected exactly 20 pilot tasks"
assert len(set(ids)) == len(ids), "Duplicate task IDs"
assert ids == [f"P0-{n:03d}" for n in range(1,21)], "Missing/unsorted IDs"
lookup = {t["id"]: t for t in tasks}
for t in tasks:
    assert t["role"] in {f"{i:02d}" for i in range(13)}, t
    assert t["state"] in {"TODO","IN_PROGRESS","BLOCKED","IN_REVIEW","DONE"}, t
    assert t["acceptance"] and len(t["steps"]) >= 3, t
    for dep in t["depends_on"]:
        assert dep in lookup and dep != t["id"], (t["id"],dep)
seen = set()
def visit(tid, active):
    assert tid not in active, "Dependency cycle: " + tid
    if tid in seen: return
    for dep in lookup[tid]["depends_on"]:
        visit(dep, active | {tid})
    seen.add(tid)
for tid in ids: visit(tid, set())
for t in tasks:
    if t["state"] == "DONE":
        assert all(lookup[d]["state"] == "DONE" for d in t["depends_on"]), t["id"]
print(f"PASS: {len(tasks)} unique tasks; roles, states, dependencies and DAG valid.")
