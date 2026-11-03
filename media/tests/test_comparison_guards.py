"""P0-017 synthetic comparison integrity guards; no physical measurements."""
import importlib.util
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("bench", ROOT / "tools" / "bench.py")
bench = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(bench)


def synthetic_pairs():
    """Produce controlled five-pair synthetic session aggregates."""
    observations = []
    for iteration in range(1, 6):
        for variant in ("android", "slickk-os"):
            baseline = variant == "android"
            observations.append({
                "dataset_kind": "synthetic", "variant": variant,
                "workload": "scroll_stress", "metric": "frame_time_ms", "unit": "ms",
                "value": 24 + iteration if baseline else 20 + iteration,
                "iteration": iteration, "sample_id": f"{variant}-{iteration}",
                "session_id": f"{variant}-session-{iteration}",
                "timestamp_utc": "2026-11-01T00:00:00Z",
                "evidence_ref": f"synthetic:session:{variant}:{iteration}",
                "artifact_sha256": "synthetic", "device_id": "simulated-1",
                "device_model": "SYNTHETIC", "device_type": "emulator",
                "os_build": "stock-sim" if baseline else "slickk-sim",
                "app_version": "test-1", "test_version": "P0-017-1",
                "network": "offline", "brightness_pct": 50,
                "refresh_hz": 60, "start_temp_c": 30, "battery_soc_pct": 80,
                "profile_id": "synthetic_scroll", "exposure_s": 30,
                "capture_tool": "synthetic-generator", "source_revision": "synthetic",
                "order": (1 if iteration % 2 else 2) if baseline else (2 if iteration % 2 else 1),
                "warmup_runs": 2, "conditions": {"fixture": "synthetic"},
                "valid": True, "error": "",
            })
    return {"schema_version": "P0-017/1.0", "observations": observations}


class ComparisonIntegrityTest(unittest.TestCase):
    def test_control_valid(self):
        report = bench.analyze(synthetic_pairs())
        self.assertTrue(report["valid"])
        self.assertFalse(report["claim_allowed"])

    def test_reject_mixed_baseline_builds(self):
        data = synthetic_pairs()
        data["observations"][2]["os_build"] = "another-stock-build"
        with self.assertRaisesRegex(bench.ValidationError, "inconsistent OS builds"):
            bench.analyze(data)

    def test_reject_imbalanced_trial_sequence(self):
        data = synthetic_pairs()
        for row in data["observations"]:
            row["order"] = 1 if row["variant"] == "android" else 2
        with self.assertRaisesRegex(bench.ValidationError, "imbalanced AB/BA"):
            bench.analyze(data)


if __name__ == "__main__":
    unittest.main()
