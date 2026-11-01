"""P0-009 contract tests. Mutated records are SYNTHETIC, not user observations."""
import copy
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VALIDATOR = ROOT / "tools" / "validate_journeys.py"
spec = importlib.util.spec_from_file_location("ux_validator", VALIDATOR)
validator = importlib.util.module_from_spec(spec)
spec.loader.exec_module(validator)


class JourneyValidatorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.catalog = json.loads((ROOT / "journeys.json").read_text(encoding="utf-8"))

    def synthetic(self):
        """Clone valid catalog for synthetic negative/positive fixture."""
        return copy.deepcopy(self.catalog)

    def assert_error(self, data, code):
        errors = validator.validate_catalog(data)
        self.assertIn(code, {e["code"] for e in errors}, errors)
        self.assertTrue(all(e["path"].startswith("$") for e in errors))

    def test_catalog_positive(self):
        result = validator.report(self.catalog)
        self.assertTrue(result["ok"], result)
        self.assertEqual(result["journey_count"], 12)
        self.assertEqual(result["surface_counts"], {"launcher": 7, "system_ui": 5})

    def test_empty_catalog_negative(self):
        self.assert_error({"schema_version": 1, "journeys": []}, "EMPTY_CATALOG")

    def test_duplicate_id_negative(self):
        data = self.synthetic()
        data["journeys"][1]["id"] = data["journeys"][0]["id"]
        self.assert_error(data, "DUPLICATE_ID")

    def test_missing_steps_negative(self):
        data = self.synthetic()
        data["journeys"][0]["proposed_steps"] = []
        self.assert_error(data, "MISSING_STEPS")

    def test_invalid_action_and_sequence_negative(self):
        data = self.synthetic()
        step = data["journeys"][0]["baseline_steps"][0]
        step["action"] = "teleport"
        step["seq"] = 7
        self.assert_error(data, "INVALID_ACTION")
        self.assert_error(data, "STEP_SEQUENCE")

    def test_incomplete_accessibility_negative(self):
        data = self.synthetic()
        data["journeys"][0]["accessibility"].pop("screen_reader")
        self.assert_error(data, "ACCESSIBILITY")

    def test_unsupported_permission_negative(self):
        data = self.synthetic()
        data["journeys"][0]["required_permissions"] = ["android.permission.WRITE_SECURE_SETTINGS"]
        self.assert_error(data, "PERMISSION")

    def test_launcher_privilege_negative(self):
        data = self.synthetic()
        data["journeys"][0]["capabilities"] = ["change_wifi_connection"]
        self.assert_error(data, "PRIVILEGE")

    def test_invalid_measurement_negative(self):
        data = self.synthetic()
        data["journeys"][0]["interaction_target_max"] = -2
        self.assert_error(data, "MEASUREMENT")
        data = self.synthetic()
        data["journeys"][0]["evidence"]["observed_duration_ms"] = float("nan")
        self.assert_error(data, "MEASUREMENT")

    def test_inconsistent_evidence_negative(self):
        data = self.synthetic()
        data["journeys"][0]["evidence"]["baseline_status"] = "VERIFIED"
        self.assert_error(data, "EVIDENCE")
        data = self.synthetic()
        data["journeys"][0]["evidence"]["proposal_status"] = "VERIFIED"
        self.assert_error(data, "EVIDENCE")

    def test_null_measurements_positive(self):
        data = self.synthetic()
        self.assertTrue(all(j["evidence"]["observed_duration_ms"] is None for j in data["journeys"]))
        self.assertEqual(validator.validate_catalog(data), [])

    def test_cli_valid_and_invalid_exit_codes(self):
        with tempfile.TemporaryDirectory() as folder:
            folder = Path(folder)
            valid = folder / "valid.json"
            invalid = folder / "invalid.json"
            report_path = folder / "report.json"
            valid.write_text(json.dumps(self.catalog), encoding="utf8")
            bad_data = self.synthetic()
            bad_data["journeys"][0]["baseline_steps"] = []
            invalid.write_text(json.dumps(bad_data), encoding="utf8")
            good = subprocess.run([sys.executable, str(VALIDATOR), str(valid),
                                   "--report", str(report_path)], capture_output=True, text=True)
            self.assertEqual(good.returncode, 0, good.stderr + good.stdout)
            self.assertTrue(json.loads(report_path.read_text())["ok"])
            bad = subprocess.run([sys.executable, str(VALIDATOR), str(invalid)],
                                 capture_output=True, text=True)
            self.assertEqual(bad.returncode, 1)
            self.assertFalse(json.loads(bad.stdout)["ok"])
            absent = subprocess.run([sys.executable, str(VALIDATOR), str(folder / "missing.json")],
                                    capture_output=True, text=True)
            self.assertEqual(absent.returncode, 2)


if __name__ == "__main__":
    unittest.main()
