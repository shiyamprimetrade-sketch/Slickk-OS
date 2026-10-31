"""SYNTHETIC validation tests; no Android platform tests are executed."""
import copy
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "tools/validate_contracts.py"
MANIFEST = ROOT / "contracts/framework_contracts.json"
FIXTURES = Path(__file__).with_name("fixtures.json")
spec = importlib.util.spec_from_file_location("validator", SCRIPT)
validator = importlib.util.module_from_spec(spec)
spec.loader.exec_module(validator)


def mutate(root, path, value=None, remove=False):
    chunks = path.split(".")
    node = root
    for part in chunks[:-1]:
        node = node[int(part)] if isinstance(node, list) else node[part]
    last = int(chunks[-1]) if isinstance(node, list) else chunks[-1]
    if remove:
        del node[last]
    else:
        node[last] = value


class ContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.doc = json.loads(MANIFEST.read_text())
        cls.fixtures = json.loads(FIXTURES.read_text())

    def test_reference_contract_passes(self):
        self.assertEqual([], validator.validate(self.doc))

    def test_public_sdk_surfaces(self):
        self.assertGreaterEqual(sum(c["api"]["surface"] == "sdk"
                                    for c in self.doc["components"]), 2)

    def test_synthetic_fixture_catalog(self):
        self.assertIn("SYNTHETIC", self.fixtures["label"])
        self.assertGreaterEqual(len(self.fixtures["cases"]), 15)

    def test_negative_cases(self):
        for case in self.fixtures["cases"]:
            with self.subTest(case=case["name"]):
                bad = copy.deepcopy(self.doc)
                mutate(bad, case["path"], case.get("value"), case.get("remove", False))
                for key, value in case.get("extra", {}).items():
                    mutate(bad, key, value)
                self.assertTrue(any(case["expect"] in e for e in validator.validate(bad)),
                                validator.validate(bad))

    def test_malformed_json_exit_two(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "bad.json"
            path.write_text("{invalid", encoding="utf-8")
            p = subprocess.run([sys.executable, str(SCRIPT), str(path)],
                               capture_output=True, text=True)
            self.assertEqual(2, p.returncode)
            self.assertIn("malformed", p.stderr)

    def test_cli_valid_exit_zero(self):
        p = subprocess.run([sys.executable, str(SCRIPT), str(MANIFEST)],
                           capture_output=True, text=True)
        self.assertEqual(0, p.returncode, p.stderr)
        self.assertIn("NOT Android runtime compatibility proof", p.stdout)

    def test_cli_invalid_exit_one(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "invalid.json"
            bad = copy.deepcopy(self.doc)
            bad["components"][0]["api"]["max"] = 38
            path.write_text(json.dumps(bad), encoding="utf-8")
            p = subprocess.run([sys.executable, str(SCRIPT), str(path)],
                               capture_output=True, text=True)
            self.assertEqual(1, p.returncode)

    def test_nonobject_and_missing_input(self):
        self.assertTrue(validator.validate([]))
        p = subprocess.run([sys.executable, str(SCRIPT), "/not/present.json"],
                           capture_output=True, text=True)
        self.assertEqual(2, p.returncode)

    def test_invalid_lifecycle_value_does_not_crash(self):
        bad = copy.deepcopy(self.doc)
        bad["components"][9]["lifecycle"]["states"][0] = {"bad": "state"}
        self.assertTrue(validator.validate(bad))

    def test_service_cannot_skip_permission_assessment(self):
        bad = copy.deepcopy(self.doc)
        bad["components"][1]["permissions"]["enforcement"] = "not_applicable"
        self.assertTrue(any("service requires permission assessment" in e
                            for e in validator.validate(bad)))


if __name__ == "__main__":
    unittest.main()
