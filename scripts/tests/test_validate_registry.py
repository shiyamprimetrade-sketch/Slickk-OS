"""Positive and mutation-based negative tests for the public task registry."""
import copy
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts/validate_registry.py"
spec = importlib.util.spec_from_file_location("registry_validator", SCRIPT)
registry = importlib.util.module_from_spec(spec)
spec.loader.exec_module(registry)


def task(tid="P0-001", depends=None, state="TODO"):
    return {"id": tid, "phase": 0, "role": "12", "title": "Test task",
            "acceptance": "Tests must pass", "state": state, "step": 1,
            "steps": ["Plan", "Implement", "Verify"], "depends_on": depends or []}


def fixture():
    return {"project": "Slickk-OS", "version": 2,
            "tasks": [task(), task("P0-002", ["P0-001"])]}


class RegistryTests(unittest.TestCase):
    def test_valid_synthetic(self):
        self.assertEqual(registry.validate(fixture()), 2)

    def test_real_registry(self):
        path = ROOT / "tasks/pilot.json"
        if not path.exists():
            self.skipTest("repository fixture unavailable in local isolated test environment")
        data = json.loads(path.read_text(encoding="utf-8"))
        self.assertGreaterEqual(registry.validate(data, require_core=True), 20)

    def rejects(self, change, message):
        data = fixture()
        change(data)
        with self.assertRaisesRegex(registry.RegistryError, message):
            registry.validate(data)

    def test_duplicate_task_id(self):
        self.rejects(lambda d: d["tasks"][1].update(id="P0-001"), "duplicate")

    def test_invalid_role(self):
        self.rejects(lambda d: d["tasks"][0].update(role="99"), "role")

    def test_non_string_role(self):
        self.rejects(lambda d: d["tasks"][0].update(role=["12"]), "role")

    def test_non_string_state(self):
        self.rejects(lambda d: d["tasks"][0].update(state=["DONE"]), "state")

    def test_invalid_state(self):
        self.rejects(lambda d: d["tasks"][0].update(state="FINISHED"), "state")

    def test_missing_dependency(self):
        self.rejects(lambda d: d["tasks"][1].update(depends_on=["P0-404"]), "unknown dependency")

    def test_self_dependency(self):
        self.rejects(lambda d: d["tasks"][0].update(depends_on=["P0-001"]), "self dependency|cycle")

    def test_dependency_cycle(self):
        self.rejects(lambda d: d["tasks"][0].update(depends_on=["P0-002"]), "cycle")

    def test_missing_acceptance(self):
        self.rejects(lambda d: d["tasks"][0].update(acceptance=" "), "acceptance")

    def test_empty_steps(self):
        self.rejects(lambda d: d["tasks"][0].update(steps=["Plan", "", "Verify"]), "steps")

    def test_step_out_of_range(self):
        self.rejects(lambda d: d["tasks"][0].update(step=4), "execution range")

    def test_unsorted_ids(self):
        self.rejects(lambda d: d["tasks"].reverse(), "ordered")

    def test_duplicate_dependencies(self):
        self.rejects(lambda d: d["tasks"][1].update(depends_on=["P0-001", "P0-001"]), "duplicate dependency")

    def test_done_requires_evidence(self):
        self.rejects(lambda d: d["tasks"][0].update(state="DONE", step=3), "evidence")

    def test_done_requires_final_step(self):
        self.rejects(lambda d: d["tasks"][0].update(state="DONE", evidence=["https://github.com/a/b/pull/1"]), "final")

    def test_done_requires_done_dependencies(self):
        self.rejects(lambda d: d["tasks"][1].update(state="DONE", step=3,
            evidence=["https://github.com/a/b/pull/2"]), "before dependencies")

    def test_valid_completed_chain(self):
        data = fixture()
        for t in data["tasks"]:
            t.update(state="DONE", step=3, evidence=["https://github.com/a/b/pull/1"])
        self.assertEqual(registry.validate(data), 2)

    def test_invalid_evidence_uri(self):
        self.rejects(lambda d: d["tasks"][0].update(state="DONE", step=3,
            evidence=["file:///tmp/fake.log"]), "HTTPS")

    def test_core_required(self):
        with self.assertRaisesRegex(registry.RegistryError, "original pilot"):
            registry.validate(fixture(), require_core=True)

    def test_cli_rejects_bad_fixture_and_python_optimized(self):
        bad = fixture()
        bad["tasks"][1]["state"] = "NOPE"
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "invalid.json"
            path.write_text(json.dumps(bad))
            for flags in ([], ["-O"]):
                result = subprocess.run([sys.executable, *flags, str(SCRIPT), str(path)],
                                        capture_output=True, text=True, check=False)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("invalid state", result.stderr)


if __name__ == "__main__":
    unittest.main()
