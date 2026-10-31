"""Synthetic contract tests. Never Android device results."""
import csv
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE))
import analyze  # noqa: E402


def observation(variant="baseline", sample="p1", value=100.0, **changes):
    data = {
        "provenance": "synthetic", "environment_kind": "host",
        "environment_id": "synthetic_lab", "build_id": "build_a" if variant == "baseline" else "build_b",
        "source_tool": "test_generator_v1", "source_ref": "synthetic:unit_test",
        "experiment_id": "test_1", "protocol_id": "protocol_v1",
        "runtime_mode": "native", "workload": "copy_and_checksum", "variant": variant,
        "metric": "duration_ns", "unit": "ns", "sample_id": sample, "value": value,
    }
    data.update(changes)
    return data


def paired(n=6, baseline=100.0, candidate=90.0):
    return [observation(v, f"p{i}", baseline if v == "baseline" else candidate)
            for i in range(n) for v in ("baseline", "candidate")]


class ParserTests(unittest.TestCase):
    def parse_rows(self, data, suffix=".json"):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / ("observations" + suffix)
            if suffix == ".json":
                p.write_text(json.dumps(data), encoding="utf8")
            else:
                with p.open("w", newline="", encoding="utf8") as f:
                    writer = csv.DictWriter(f, fieldnames=["schema_version", *sorted(analyze.FIELDS)])
                    writer.writeheader()
                    for row in data["observations"]:
                        writer.writerow({"schema_version": "1.0", **row})
            return analyze.read_input(p)

    def test_json_valid_and_units(self):
        row = observation(unit="ms", value=2.5)
        parsed = self.parse_rows({"schema_version": "1.0", "observations": [row]})
        self.assertEqual(parsed[0]["value"], 2_500_000)
        self.assertEqual(parsed[0]["unit"], "ns")

    def test_csv_valid(self):
        self.assertEqual(self.parse_rows({"observations": paired()}, ".csv")[0]["sample_id"], "p0")

    def test_wrong_version(self):
        with self.assertRaises(analyze.InvalidData):
            self.parse_rows({"schema_version": "2.0", "observations": paired()})

    def test_empty(self):
        with self.assertRaises(analyze.InvalidData):
            self.parse_rows({"schema_version": "1.0", "observations": []})

    def test_unexpected_field(self):
        with self.assertRaises(analyze.InvalidData):
            self.parse_rows({"schema_version": "1.0", "observations": [observation(secret=1)]})

    def test_missing_field(self):
        r = observation()
        del r["source_tool"]
        with self.assertRaises(analyze.InvalidData):
            self.parse_rows({"schema_version": "1.0", "observations": [r]})

    def test_wrong_time_unit(self):
        with self.assertRaisesRegex(analyze.InvalidData, "inconsistent unit"):
            self.parse_rows({"schema_version": "1.0", "observations": [observation(unit="count")]})

    def test_nonfinite(self):
        for value in ("NaN", "Infinity", float("-inf")):
            with self.subTest(value=value), self.assertRaises(analyze.InvalidData):
                self.parse_rows({"schema_version": "1.0", "observations": [observation(value=value)]})

    def test_negative_and_boolean(self):
        for value in (-1, True, None):
            with self.subTest(value=value), self.assertRaises(analyze.InvalidData):
                self.parse_rows({"schema_version": "1.0", "observations": [observation(value=value)]})

    def test_duplicate_pairs(self):
        with self.assertRaisesRegex(analyze.InvalidData, "duplicate"):
            self.parse_rows({"schema_version": "1.0", "observations": [observation(), observation()]})

    def test_count_integrality(self):
        with self.assertRaisesRegex(analyze.InvalidData, "integral"):
            self.parse_rows({"schema_version": "1.0", "observations": [observation(metric="allocation_count", unit="count", value=0.4)]})

    def test_memory_unit(self):
        r = self.parse_rows({"schema_version": "1.0", "observations": [observation(metric="allocated_bytes", unit="KiB", value=1)]})
        self.assertEqual(r[0]["value"], 1024)

    def test_measured_with_synthetic_ref(self):
        with self.assertRaises(analyze.InvalidData):
            self.parse_rows({"schema_version": "1.0", "observations": [observation(provenance="measured")]})

    def test_malformed_csv_fixture(self):
        with self.assertRaises(analyze.InvalidData):
            analyze.read_input(BASE / "fixtures" / "synthetic_malformed.csv")


class StatisticsTests(unittest.TestCase):
    def test_percentile_type7(self):
        self.assertEqual(analyze.percentile([1, 2, 3, 4, 5], .95), 4.8)

    def test_stats_singleton_variability_absent(self):
        s = analyze.stats([1])
        self.assertIsNone(s["sample_sd"])
        self.assertIsNone(s["cv_pct"])

    def test_detect_regression(self):
        r = analyze.analyze(paired(candidate=110))
        self.assertEqual(r["groups"][0]["status"], "REGRESSION")
        self.assertAlmostEqual(r["groups"][0]["delta_pct"], 10)
        self.assertFalse(r["claim_allowed"])

    def test_candidate_not_proof(self):
        self.assertEqual(analyze.analyze(paired(candidate=90))["groups"][0]["status"], "IMPROVEMENT_CANDIDATE")

    def test_small_sample(self):
        self.assertEqual(analyze.analyze(paired(n=4))["groups"][0]["status"], "INSUFFICIENT")

    def test_unpaired(self):
        data = paired(n=6)
        for item in data:
            if item["variant"] == "candidate":
                item["sample_id"] += "_different"
        self.assertEqual(analyze.analyze(data)["groups"][0]["status"], "INSUFFICIENT")

    def test_context_mismatch(self):
        data = paired()
        for item in data:
            if item["variant"] == "candidate":
                item["environment_id"] = "another_host"
        self.assertEqual(analyze.analyze(data)["groups"][0]["status"], "INCOMPARABLE")

    def test_mode_mismatch(self):
        data = paired()
        data[1]["runtime_mode"] = "jit"
        self.assertEqual(analyze.analyze(data)["groups"][0]["status"], "INCOMPARABLE")

    def test_variable_build_within_variant(self):
        data = paired()
        data[0]["build_id"] = "random"
        self.assertEqual(analyze.analyze(data)["groups"][0]["status"], "INCOMPARABLE")

    def test_zero_baseline(self):
        self.assertEqual(analyze.analyze(paired(baseline=0, candidate=1))["groups"][0]["status"], "REGRESSION")
        self.assertEqual(analyze.analyze(paired(baseline=0, candidate=0))["groups"][0]["status"], "NO_CHANGE")

    def test_count_uses_median(self):
        data = paired()
        for item in data:
            item.update(metric="allocation_count", unit="count", value=10 if item["variant"] == "baseline" else 11)
        self.assertEqual(analyze.analyze(data)["groups"][0]["endpoint"], "median")

    def test_no_candidate(self):
        self.assertEqual(analyze.analyze(paired()[:1])["groups"][0]["status"], "INSUFFICIENT")

    def test_invalid_threshold(self):
        with self.assertRaises(analyze.InvalidData):
            analyze.analyze(paired(), float("nan"))

    def test_fixture_cli_and_regression_exit(self):
        fixture = BASE / "fixtures" / "synthetic_pairs.json"
        good = subprocess.run([sys.executable, str(BASE / "analyze.py"), str(fixture)], capture_output=True, text=True)
        self.assertEqual(good.returncode, 0, good.stderr)
        self.assertFalse(json.loads(good.stdout)["claim_allowed"])
        fail = subprocess.run([sys.executable, str(BASE / "analyze.py"), str(fixture), "--fail-on-regression"], capture_output=True, text=True)
        self.assertEqual(fail.returncode, 3, fail.stderr)


if __name__ == "__main__":
    unittest.main()
