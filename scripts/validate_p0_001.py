#!/usr/bin/env python3
"""Validate P0-001 planning contracts, ownership and completion evidence.
Standard library only. This does not validate Android/runtime behavior.
"""
import argparse
import copy
import json
import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TEXT_PATHS = (
    "docs/PROJECT_CHARTER.md",
    "docs/contracts/P0-001-product-contract.md",
    "docs/CONTINUATION_PROTOCOL.md",
    "prompts/00_master.md",
)
INVARIANTS = (
    "Preserve Android application compatibility",
    "Never claim an improvement without a matched before/after benchmark",
    "Never remove code just because it looks verbose",
    "Never flash or unlock the owner's daily phone",
    "Never use or publish proprietary vendor code without permission",
)
BLOCKERS = (
    "Only P0-001 is ACTIVE",
    "dependents not dispatched",
    "Dependencies DONE with acceptance evidence",
    "owner decision and independent review linked before P0-001 DONE",
)
def overlaps(a, b):
    def covers(pattern, path):
        return pattern == path or (
            pattern.endswith("/**") and (
                path == pattern[:-3] or path.startswith(pattern[:-2])
            )
        )
    return covers(a, b) or covers(b, a)

def validate(data, docs, require_complete=False):
    errors = []
    def need(condition, message):
        if not condition:
            errors.append(message)
    tasks = data.get("tasks", [])
    ids = [t.get("id") for t in tasks]
    need(ids == [f"P0-{i:03}" for i in range(1, 21)], "pilot IDs changed")
    lookup = {t.get("id"): t for t in tasks}
    need(len(lookup) == len(tasks), "duplicate task ID")
    def visit(tid, active):
        if tid in active:
            errors.append("dependency cycle")
            return
        if tid not in lookup:
            errors.append("unknown dependency " + str(tid))
            return
        for dep in lookup[tid].get("depends_on", []):
            visit(dep, active | {tid})
    for tid in ids:
        visit(tid, set())
    for task in tasks:
        need(task.get("role") in {f"{i:02}" for i in range(13)}, "unknown role")
        need(bool(task.get("technology_stack")), "missing stack " + task["id"])
        need(bool(task.get("acceptance")), "missing acceptance " + task["id"])
        need(len(task.get("steps", [])) >= 3, "missing finite plan " + task["id"])
        need(task.get("checkpoint") in task.get("owned_paths", []),
             "checkpoint not owned " + task["id"])
        if task.get("state") == "DONE":
            need(all(lookup.get(d, {}).get("state") == "DONE"
                     for d in task.get("depends_on", [])), "unmet DONE dependency")
    claims = []
    for item in tasks + data.get("review_assignments", []):
        owner = item.get("id", item.get("task_id", "") + "-review-" + item["role"])
        for path in item.get("owned_paths", []):
            safe = (isinstance(path, str) and not path.startswith("/")
                    and ".." not in path.split("/") and "\\" not in path
                    and ("*" not in path or
                         (path.endswith("/**") and "*" not in path[:-3])))
            need(safe, "unsafe reservation " + str(path))
            claims.append((owner, path))
    for i, (owner, path) in enumerate(claims):
        for other, target in claims[i + 1:]:
            need(not overlaps(path, target), "ownership collision: " + path + " / " + target)
    charter = docs["docs/PROJECT_CHARTER.md"]
    contract = docs["docs/contracts/P0-001-product-contract.md"]
    protocol = docs["docs/CONTINUATION_PROTOCOL.md"]
    for user in ("U1", "U2", "U3"):
        need(user in charter and user in contract, "missing user " + user)
    for track in ("Experience", "Platform", "Research"):
        need(track in charter and track in contract, "missing track " + track)
    for metric in (f"M{i:02}" for i in range(1, 10)):
        need(bool(re.search(r"^\| " + metric + r"(?: |\|)", charter, re.M)),
             "missing charter metric " + metric)
        need(bool(re.search(r"^\| " + metric + r"(?: |\|)", contract, re.M)),
             "missing contract metric " + metric)
    for req in (f"R{i:02}" for i in range(1, 12)):
        need("| " + req + " |" in contract, "missing requirement " + req)
    for text in INVARIANTS:
        need(text in charter, "missing invariant: " + text)
    for text in ("HYPOTHESES, NOT ACHIEVED", "M04 reconciliation", "INCONCLUSIVE"):
        need(text in charter, "missing evidence limitation: " + text)
    for text in (charter, contract):
        for task_id in re.findall(r"P0-\d{3}", text):
            need(task_id in lookup, "unknown contract task " + task_id)
        for blocker in BLOCKERS:
            need(blocker not in text, "obsolete execution blocker: " + blocker)
    policy = data.get("operating_protocol", {})
    need(policy.get("version") == 2, "protocol version not 2")
    need(policy.get("implementation_authorization") == "STANDING", "missing standing authority")
    need(policy.get("technical_dependencies") == "MUST_BE_VERIFIED", "technical gates relaxed")
    need(policy.get("merge_authorization") == "SEPARATE", "merge authorization conflated")
    need("Independent Multi-Chat Execution Protocol (v2)" in protocol, "old protocol text")
    for tid in ("P0-002", "P0-004"):
        need(lookup.get(tid, {}).get("dispatch_status") == "INDEPENDENTLY_AUTHORIZED",
             "independent chat blocked: " + tid)
    if require_complete:
        task = lookup.get("P0-001", {})
        need(task.get("state") == "DONE", "P0-001 not DONE")
        need(task.get("completed_steps") == list(range(1, 7)), "unfinished task steps")
        need(task.get("merge_status") == "NOT_MERGED", "merge status inaccurate")
        review = task.get("acceptance_review", {})
        need(review.get("type") == "RESPONSIBLE_ROLE_SELF_REVIEW", "review type missing")
        need(review.get("result") == "PASS", "acceptance review incomplete")
        need(review.get("independent_approval") == "NOT_CLAIMED", "invented independent approval")
    return sorted(set(errors))

def self_test(data, docs):
    class Cases(unittest.TestCase):
        def check_bad(self, mutate, expected):
            d, texts = copy.deepcopy(data), dict(docs)
            mutate(d, texts)
            self.assertTrue(any(expected in e for e in validate(d, texts)))
        def test_valid(self):
            self.assertEqual(validate(data, docs), [])
        def test_collision(self):
            self.check_bad(lambda d, _: d["tasks"][1]["owned_paths"].append(
                d["tasks"][0]["owned_paths"][0]), "ownership collision")
        def test_subtree_collision(self):
            self.check_bad(lambda d, _: d["tasks"][0]["owned_paths"].append(
                ".github/workflows/check.yml"), "ownership collision")
        def test_traversal(self):
            self.check_bad(lambda d, _: d["tasks"][0]["owned_paths"].append("../escape"),
                           "unsafe reservation")
        def test_unknown_dependency(self):
            self.check_bad(lambda d, _: d["tasks"][1]["depends_on"].append("P0-999"),
                           "unknown dependency")
        def test_cycle(self):
            self.check_bad(lambda d, _: d["tasks"][0]["depends_on"].append("P0-002"),
                           "dependency cycle")
        def test_missing_metric(self):
            self.check_bad(lambda _, x: x.__setitem__(TEXT_PATHS[0],
                x[TEXT_PATHS[0]].replace("| M04 |", "| REMOVED |")),
                "missing charter metric M04")
        def test_safety_removed(self):
            self.check_bad(lambda _, x: x.__setitem__(TEXT_PATHS[0],
                x[TEXT_PATHS[0]].replace(INVARIANTS[3], "removed")), "missing invariant")
        def test_chat_blocked(self):
            self.check_bad(lambda d, _: d["tasks"][1].__setitem__("dispatch_status", "RESERVED"),
                           "independent chat blocked")
        def test_unfinished_completion(self):
            d = copy.deepcopy(data)
            d["tasks"][0]["state"] = "IN_PROGRESS"
            self.assertIn("P0-001 not DONE", validate(d, docs, True))
    return unittest.TextTestRunner(verbosity=2).run(
        unittest.defaultTestLoader.loadTestsFromTestCase(Cases)).wasSuccessful()

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--require-complete", action="store_true")
    args = parser.parse_args()
    data = json.loads((ROOT / "tasks/pilot.json").read_text(encoding="utf-8"))
    docs = {p: (ROOT / p).read_text(encoding="utf-8") for p in TEXT_PATHS}
    if args.self_test and not self_test(data, docs):
        return 1
    errors = validate(data, docs, args.require_complete)
    print(json.dumps({"status": "FAIL" if errors else "PASS", "errors": errors,
                      "scope": "P0-001 planning contracts; no runtime proof",
                      "completion_checked": args.require_complete}, indent=2))
    return bool(errors)

if __name__ == "__main__":
    sys.exit(main())
