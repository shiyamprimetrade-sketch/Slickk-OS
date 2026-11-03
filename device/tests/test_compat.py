"""P0-003 synthetic tests. Passing does NOT verify physical-phone support."""
import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import compat  # noqa: E402


def fixture(name="SM-A165F/matrix.json"):
    return json.loads((ROOT / name).read_text(encoding="utf-8"))


class DeviceAuditTests(unittest.TestCase):
    def setUp(self):
        self.base = fixture()

    def assert_invalid(self, value, term=None):
        errors = compat.validate(value)
        self.assertTrue(errors)
        if term:
            self.assertIn(term, " ".join(errors))

    def test_reported_matrix_passes(self):
        self.assertEqual(compat.validate(self.base), [])

    def test_supported_fixture_is_synthetic(self):
        data = fixture("fixtures/synthetic_supported.json")
        self.assertEqual(compat.validate(data), [])
        self.assertIn("SYNTHETIC: true", compat.report(data, []))
        self.assertIn("PHYSICAL OS BOOT: NOT VERIFIED", compat.report(data, []))

    def test_restricted_absent_and_unknown_fixture(self):
        data = fixture("fixtures/synthetic_restricted.json")
        self.assertEqual(compat.validate(data), [])
        self.assertEqual(data["capabilities"][3]["status"], "BLOCKED")
        self.assertEqual(data["capabilities"][7]["status"], "NOT_SUPPORTED")

    def test_missing_required_top_field(self):
        del self.base["capabilities"]
        self.assert_invalid(self.base, "missing capabilities")

    def test_extra_top_field(self):
        self.base["secret"] = "redacted"
        self.assert_invalid(self.base, "unexpected field")

    def test_unrecognized_status(self):
        self.base["capabilities"][0]["status"] = "SUPPORTED"
        self.assert_invalid(self.base, "enum")

    def test_forged_verified_capability(self):
        self.base["capabilities"][0]["status"] = "VERIFIED"
        self.base["capabilities"][0]["evidence"] = ["owner-input"]
        self.assert_invalid(self.base, "conclusive claim")

    def test_forged_unsupported_capability(self):
        self.base["capabilities"][0]["status"] = "NOT_SUPPORTED"
        self.assert_invalid(self.base, "conclusive claim")

    def test_user_report_requires_report(self):
        self.base["capabilities"][0]["status"] = "USER-REPORTED"
        self.base["capabilities"][0]["evidence"] = ["aosp-vintf"]
        self.assert_invalid(self.base, "user report")

    def test_missing_evidence_reference(self):
        self.base["capabilities"][0]["evidence"] = ["missing"]
        self.assert_invalid(self.base, "missing evidence reference")

    def test_duplicate_evidence_id(self):
        self.base["evidence"].append(copy.deepcopy(self.base["evidence"][0]))
        self.assert_invalid(self.base, "duplicate IDs")

    def test_synthetic_proof_must_be_labeled(self):
        sample = fixture("fixtures/synthetic_supported.json")
        sample["synthetic"] = False
        self.assert_invalid(sample, "synthetic record")

    def test_missing_capability(self):
        self.base["capabilities"].pop()
        self.assert_invalid(self.base, "missing, unexpected")

    def test_duplicate_capability(self):
        self.base["capabilities"][1]["name"] = "cpu_memory"
        self.assert_invalid(self.base, "duplicate capability")

    def test_bad_api_release_pair(self):
        self.base["software"]["api_level"] = 35
        self.base["software"]["evidence"]["api_level"] = "owner-input"
        self.assert_invalid(self.base, "API 36")

    def test_software_value_without_proof(self):
        self.base["software"]["kernel_release"] = "6.1.0"
        self.assert_invalid(self.base, "value/evidence")

    def test_model_verified_from_user_report_is_invalid(self):
        self.base["device"]["model_status"] = "VERIFIED"
        self.assert_invalid(self.base, "incorrect evidence")

    def test_manifest_names_need_observation(self):
        self.base["interfaces"][0]["declared_hal_packages"] = ["android.hardware.camera.provider"]
        self.assert_invalid(self.base, "unverified HAL")

    def test_manifest_without_observation_cannot_be_verified(self):
        self.base["interfaces"][0]["status"] = "VERIFIED"
        self.assert_invalid(self.base, "observed evidence")

    def test_imei_blocked_without_echo(self):
        self.base["evidence"][0]["detail"] = "imei: 123456789012345"
        errors = compat.validate(self.base)
        self.assertTrue(errors)
        self.assertNotIn("123456789012345", " ".join(errors))

    def test_mac_blocked(self):
        self.base["device"]["model"] = "aa:bb:cc:dd:ee:ff"
        self.assert_invalid(self.base, "sensitive value")

    def test_sensitive_field_blocked(self):
        self.base["device"]["serial_number"] = "anything"
        self.assert_invalid(self.base, "identifier key")

    def test_boolean_api_not_integer(self):
        self.base["software"]["api_level"] = True
        self.base["software"]["evidence"]["api_level"] = "owner-input"
        self.assert_invalid(self.base, "incorrect type")

    def test_bad_hal_name(self):
        self.base["interfaces"][0]["declared_hal_packages"] = ["vendor.private.serial"]
        self.assert_invalid(self.base, "string pattern")

    def test_collect_sanitizes_and_keeps_unknown_hardware(self):
        answers = {("getprop", "ro.product.model"): "SM-A165F",
                   ("getprop", "ro.build.version.release"): "16",
                   ("getprop", "ro.build.version.sdk"): "36",
                   ("getprop", "ro.product.cpu.abi"): "arm64-v8a",
                   ("uname", "-r"): "6.1.23"}
        with patch.object(compat, "read_command", side_effect=lambda argv, mode, **kwargs: answers.get(tuple(argv))):
            result = compat.collect(self.base, "termux")
        self.assertEqual(compat.validate(result), [])
        self.assertEqual(result["device"]["model_status"], "VERIFIED")
        self.assertEqual(result["software"]["api_level"], 36)
        self.assertTrue(all(x["status"] == "UNKNOWN" for x in result["capabilities"]))

    def test_collect_wrong_device_refused(self):
        with patch.object(compat, "read_command", side_effect=lambda argv, mode, **kwargs: "OTHER" if argv == ["getprop", "ro.product.model"] else None):
            with self.assertRaises(ValueError):
                compat.collect(self.base, "adb")

    def test_collect_manifest_declared_not_hardware_proven(self):
        xml = '<manifest><hal><name>android.hardware.camera.provider</name></hal></manifest>'
        with patch.object(compat, "read_command", side_effect=lambda argv, mode, **kwargs: xml if argv == ["cat", compat.VINTF_PATHS[0]] else None):
            result = compat.collect(self.base, "adb")
        self.assertEqual(compat.validate(result), [])
        self.assertEqual(result["interfaces"][0]["status"], "VERIFIED")
        self.assertEqual(result["capabilities"][3]["status"], "UNKNOWN")

    def test_cli_good_and_bad_exit_codes(self):
        tool = ROOT / "tools" / "compat.py"
        self.assertEqual(subprocess.run([sys.executable, str(tool), "validate", str(ROOT / "SM-A165F/matrix.json")], capture_output=True).returncode, 0)
        with tempfile.TemporaryDirectory() as folder:
            bad = Path(folder) / "bad.json"
            bad.write_text("{}")
            self.assertEqual(subprocess.run([sys.executable, str(tool), "validate", str(bad)], capture_output=True).returncode, 2)


if __name__ == "__main__":
    unittest.main()
