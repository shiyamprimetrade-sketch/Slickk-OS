"""Offline tests: fixture values are synthetic, never observed device results."""
import csv
import importlib.util
import json
import math
import tempfile
import unittest
from copy import deepcopy
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("analyze", ROOT / "benchmarks" / "analyze.py")
analyze = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(analyze)
FIXTURE = ROOT / "benchmarks" / "fixtures" / "synthetic_comparison.json"
REGRESSION = ROOT / "benchmarks" / "fixtures" / "synthetic_regression.csv"


class TestBenchmarkProcessor(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rows = analyze.load(FIXTURE)

    def test_json_fixture(self):
        self.assertEqual(len(self.rows), 16)
        self.assertEqual({r["dataset_kind"] for r in self.rows}, {"synthetic"})

    def test_csv_fixture(self):
        self.assertEqual(len(analyze.load(REGRESSION)), 10)

    def test_stats(self):
        self.assertEqual(analyze.percentile([1, 2, 3, 4, 5], .95), 4.8)
        self.assertEqual(analyze.summary([{"value": x} for x in [1, 2, 3]])["median"], 2)

    def test_single_sample_variability(self):
        self.assertIsNone(analyze.summary([{"value": 0}])["cv_pct"])

    def test_favorable_fixture_is_not_verified_hardware_win(self):
        report = analyze.compare(self.rows)
        self.assertEqual({c["status"] for c in report["comparisons"]}, {"IMPROVEMENT_CANDIDATE"})
        self.assertTrue(all(c["claim_allowed"] is False for c in report["comparisons"]))
        self.assertTrue(all(c["evidence_class"] == "SYNTHETIC_ONLY" for c in report["comparisons"]))

    def test_unfavorable_fixture(self):
        self.assertEqual(analyze.compare(analyze.load(REGRESSION))["comparisons"][0]["status"], "REGRESSION")
        self.assertEqual(analyze.main([str(REGRESSION), "--fail-on-regression"]), 3)

    def test_comparison_deterministic(self):
        self.assertEqual(analyze.compare(self.rows), analyze.compare(list(reversed(self.rows))))

    def test_insufficient_samples(self):
        one = [r for r in self.rows if r["metric"] == "startup_cold_ms" and r["iteration"] < 5]
        result = analyze.compare(one)["comparisons"][0]
        self.assertEqual(result["status"], "INCONCLUSIVE")
        self.assertIn("insufficient independent repetitions", " ".join(result["reasons"]))

    def test_mismatched_environment(self):
        rows = deepcopy(self.rows)
        rows[0]["brightness_pct"] += 1
        result = analyze.compare(rows)["comparisons"]
        self.assertTrue(any(c["status"] == "INCONCLUSIVE" for c in result))

    def test_temperature_mismatch(self):
        rows = deepcopy(self.rows)
        rows[0]["start_temp_c"] += 5
        self.assertTrue(any(c["status"] == "INCONCLUSIVE" for c in analyze.compare(rows)["comparisons"]))

    def test_mixed_provenance(self):
        rows = deepcopy(self.rows)
        rows[0]["dataset_kind"] = "device"
        rows[0]["evidence_ref"] = "local:raw-trace"
        self.assertTrue(any(c["status"] == "INCONCLUSIVE" for c in analyze.compare(rows)["comparisons"]))

    def test_missing_candidate(self):
        result = analyze.compare([r for r in self.rows if r["variant"] == "android"])
        self.assertTrue(all(c["status"] == "INCONCLUSIVE" for c in result["comparisons"]))

    def test_unpaired_iterations(self):
        rows = deepcopy(self.rows)
        rows = [r for r in rows if not (r["variant"] == "slickk-os" and r["iteration"] == 5)]
        result = analyze.compare(rows)["comparisons"]
        self.assertTrue(any("unpaired" in " ".join(c["reasons"]) for c in result))

    def test_zero_baseline_no_false_percentage(self):
        rows = [deepcopy(r) for r in self.rows if r["metric"] == "startup_cold_ms"]
        for r in rows:
            r["metric"] = "crash_count"
            r["unit"] = "count"
            r["exposure_s"] = 3600
            r["value"] = 0 if r["variant"] == "android" else 1
        result = analyze.compare(rows)["comparisons"][0]
        self.assertEqual(result["status"], "REGRESSION")
        self.assertIsNone(result["relative_improvement_pct"])

    def test_zero_both(self):
        rows = [deepcopy(r) for r in self.rows if r["metric"] == "startup_cold_ms"]
        for r in rows:
            r.update(metric="anr_count", unit="count", exposure_s=3600, value=0)
        self.assertEqual(analyze.compare(rows)["comparisons"][0]["status"], "NO_CHANGE")

    def test_wrong_units(self):
        row = deepcopy(self.rows[0]); row["unit"] = "seconds"
        with self.assertRaisesRegex(analyze.InvalidData, "unit mismatch"):
            analyze._validate_observation(row, 0)

    def test_nonfinite_and_boolean(self):
        for value in (math.nan, math.inf, -math.inf, True, "13"):
            row = deepcopy(self.rows[0]); row["value"] = value
            with self.subTest(value=value), self.assertRaises(analyze.InvalidData):
                analyze._validate_observation(row, 0)

    def test_negative_and_counts(self):
        row = deepcopy(self.rows[0]); row["value"] = -1
        with self.assertRaises(analyze.InvalidData): analyze._validate_observation(row, 0)
        row.update(metric="crash_count", unit="count", exposure_s=1, value=0.5)
        with self.assertRaisesRegex(analyze.InvalidData, "count must be integral"):
            analyze._validate_observation(row, 0)

    def test_battery_exposure(self):
        row = deepcopy(self.rows[-1]); row["exposure_s"] = 100
        with self.assertRaisesRegex(analyze.InvalidData, "8h"):
            analyze._validate_observation(row, 0)

    def test_missing_extra_and_date(self):
        row = deepcopy(self.rows[0]); row.pop("metric")
        with self.assertRaises(analyze.InvalidData): analyze._validate_observation(row, 0)
        row = deepcopy(self.rows[0]); row["secret_id"] = "not permitted"
        with self.assertRaises(analyze.InvalidData): analyze._validate_observation(row, 0)
        row = deepcopy(self.rows[0]); row["timestamp_utc"] = "2026-10-31T12:00:00"
        with self.assertRaises(analyze.InvalidData): analyze._validate_observation(row, 0)

    def test_duplicate_iteration(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "dup.json"
            path.write_text(json.dumps({"schema_version": "1.0", "observations": [self.rows[0]] * 2}))
            with self.assertRaisesRegex(analyze.InvalidData, "duplicate"):
                analyze.load(path)

    def test_malformed_json_csv(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "broken.json"; path.write_text("{invalid")
            with self.assertRaises(analyze.InvalidData): analyze.load(path)
            path = Path(temp) / "broken.csv"; path.write_text("hello,hello\n1,2\n")
            with self.assertRaises(analyze.InvalidData): analyze.load(path)

    def test_cli_roundtrip(self):
        with tempfile.TemporaryDirectory() as temp:
            dest = Path(temp) / "result.json"
            self.assertEqual(analyze.main([str(FIXTURE), "--output", str(dest)]), 0)
            report = json.loads(dest.read_text())
            self.assertEqual(report["comparison_count"], 2)
            self.assertEqual(analyze.main([str(FIXTURE), "--output", str(dest)]), 0)


if __name__ == "__main__":
    unittest.main()
