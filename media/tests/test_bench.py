"""Synthetic-only validation and statistical regressions for P0-017."""
import copy
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("bench", ROOT / "tools" / "bench.py")
bench = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(bench)
FIXTURE = json.loads((ROOT / "fixtures" / "synthetic_pairs.json").read_text())


class BenchTest(unittest.TestCase):
    def setUp(self):
        self.data = copy.deepcopy(FIXTURE)

    def fail_invalid(self, part):
        with self.assertRaises(bench.ValidationError) as found:
            bench.analyze(self.data)
        self.assertIn(part, str(found.exception))

    def test_valid_paired_synthetic(self):
        result = bench.analyze(self.data)
        self.assertFalse(result["claim_allowed"])
        self.assertEqual(result["dataset_kinds"], ["synthetic"])
        c = result["comparisons"][0]
        self.assertEqual((c["baseline"]["n"], c["candidate"]["n"]), (5, 5))
        self.assertEqual(c["status"], "IMPROVEMENT_CANDIDATE")

    def test_p95_interpolation(self):
        self.assertAlmostEqual(bench.percentile([1, 2, 3, 4, 5], .95), 4.8)
        self.assertEqual(bench.stats([10, 10, 10])["cv_pct"], 0)
        self.assertIsNone(bench.stats([0, 0, 0])["cv_pct"])

    def test_wrong_schema(self):
        self.data["schema_version"] = "1.0"
        self.fail_invalid("schema_version")

    def test_duplicate_sample(self):
        self.data["observations"][2]["sample_id"] = self.data["observations"][0]["sample_id"]
        self.fail_invalid("duplicate sample")

    def test_duplicate_session(self):
        self.data["observations"][2]["session_id"] = self.data["observations"][0]["session_id"]
        self.fail_invalid("duplicate session")

    def test_missing_unit(self):
        del self.data["observations"][0]["unit"]
        self.fail_invalid("missing=")

    def test_wrong_unit(self):
        self.data["observations"][0]["unit"] = "fps"
        self.fail_invalid("invalid unit")

    def test_negative_value(self):
        self.data["observations"][0]["value"] = -1
        self.fail_invalid("out of range")

    def test_nonfinite_value(self):
        self.data["observations"][0]["value"] = float("nan")
        self.fail_invalid("finite")

    def test_bool_not_numeric(self):
        self.data["observations"][0]["value"] = True
        self.fail_invalid("finite")

    def test_invalid_packet_loss(self):
        for r in self.data["observations"]:
            r.update(metric="packet_loss_pct", unit="percent")
        self.data["observations"][0]["value"] = 100.1
        self.fail_invalid("out of range")

    def test_invalid_integral_count(self):
        for r in self.data["observations"]:
            r.update(metric="audio_underrun_count", unit="count", value=1.5)
        self.fail_invalid("integer")

    def test_missing_iteration_pair(self):
        self.data["observations"].pop()
        self.fail_invalid("missing variant")

    def test_insufficient_independent_runs(self):
        self.data["observations"] = self.data["observations"][:8]
        self.fail_invalid("insufficient")

    def test_mismatched_refresh(self):
        self.data["observations"][0]["refresh_hz"] = 90
        self.fail_invalid("unmatched conditions")

    def test_mismatched_media_profile(self):
        self.data["observations"][0]["conditions"]["codec"] = "avc"
        self.fail_invalid("unmatched conditions")

    def test_inconsistent_workload_across_iterations(self):
        for row in self.data["observations"][2:4]:
            row["conditions"]["composition"] = "alternate"
        self.fail_invalid("inconsistent workload")

    def test_unknown_network(self):
        self.data["observations"][0]["network"] = "unknown"
        self.fail_invalid("unsupported network")

    def test_battery_temperature_confound(self):
        self.data["observations"][0]["start_temp_c"] = 34
        self.fail_invalid("thermal or battery")

    def test_invalid_provenance(self):
        self.data["observations"][0]["dataset_kind"] = "device"
        self.fail_invalid("incompatible evidence")

    def test_invalid_hash(self):
        self.data["observations"][0]["artifact_sha256"] = "pretend_hash"
        self.fail_invalid("artifact_sha256")

    def test_invalid_utc(self):
        self.data["observations"][0]["timestamp_utc"] = "2026-10-31T12:00:00+06:00"
        self.fail_invalid("ISO-8601 UTC")

    def test_invalid_sample_is_rejected(self):
        self.data["observations"][0]["valid"] = False
        self.data["observations"][0]["error"] = "capture failure"
        self.fail_invalid("not comparable")

    def test_trial_order_must_be_distinct(self):
        self.data["observations"][0]["order"] = self.data["observations"][1]["order"]
        self.fail_invalid("trial order")

    def test_higher_is_better(self):
        for r in self.data["observations"]:
            r["metric"], r["unit"] = "video_decode_fps", "fps"
            r["value"] = 40 if r["variant"] == "android" else 50
        self.assertEqual(bench.analyze(self.data)["comparisons"][0]["status"], "IMPROVEMENT_CANDIDATE")
        for r in self.data["observations"]:
            r["value"] = 50 if r["variant"] == "android" else 40
        self.assertEqual(bench.analyze(self.data)["comparisons"][0]["status"], "REGRESSION")

    def test_regression_and_gate(self):
        for r in self.data["observations"]:
            if r["variant"] == "slickk-os":
                r["value"] += 10
        self.assertEqual(bench.analyze(self.data)["comparisons"][0]["status"], "REGRESSION")
        with tempfile.TemporaryDirectory() as td:
            f = Path(td) / "data.json"
            f.write_text(json.dumps(self.data))
            p = subprocess.run([sys.executable, str(ROOT / "tools" / "bench.py"),
                                str(f), "--fail-on-regression"], capture_output=True, text=True)
            self.assertEqual(p.returncode, 3)
            self.assertTrue(json.loads(p.stdout)["valid"])

    def test_zero_baseline_not_percent_improvement(self):
        for r in self.data["observations"]:
            r.update(metric="packet_loss_pct", unit="percent", value=0)
        for r in self.data["observations"]:
            if r["variant"] == "slickk-os":
                r["value"] = 1
        c = bench.analyze(self.data)["comparisons"][0]
        self.assertIsNone(c["improvement_pct"])
        self.assertEqual(c["status"], "INCONCLUSIVE_ZERO_BASELINE")

    def test_cli_invalid_input_exit_2(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "bad.json"
            p.write_text('{not json')
            result = subprocess.run([sys.executable, str(ROOT / "tools" / "bench.py"), str(p)],
                                    capture_output=True, text=True)
            self.assertEqual(result.returncode, 2)
            self.assertFalse(json.loads(result.stdout)["valid"])

    def test_cli_valid_exit_0(self):
        r = subprocess.run([sys.executable, str(ROOT / "tools" / "bench.py"),
                            str(ROOT / "fixtures" / "synthetic_pairs.json")],
                           capture_output=True, text=True)
        self.assertEqual(r.returncode, 0)
        self.assertFalse(json.loads(r.stdout)["claim_allowed"])


if __name__ == "__main__":
    unittest.main()
