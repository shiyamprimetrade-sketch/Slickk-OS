"""Synthetic positive and negative P0-016 unit tests; no phone evidence."""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from analyze import InputError, config, cpu, fields, memory, parse_psi, power, process_ticks


class MemoryTests(unittest.TestCase):
    def setUp(self):
        self.mem = (ROOT / "fixtures/meminfo.txt").read_text()

    def test_memory_calculations(self):
        r = memory(self.mem)
        self.assertEqual(r["swap_used_kib"], 800000)
        self.assertAlmostEqual(r["mem_available_pct"], 39.0625)
        self.assertIsNone(r["psi"])

    def test_missing_optional_available(self):
        r = memory("MemTotal: 1024 kB\n")
        self.assertIsNone(r["mem_available_pct"])
        self.assertIn("MemAvailable absent", " ".join(r["limitations"]))

    def test_missing_total(self):
        with self.assertRaises(InputError):
            memory("MemFree: 12 kB")

    def test_unrealistic_counters(self):
        with self.assertRaises(InputError):
            memory("MemTotal: 100 kB\nMemAvailable: 200 kB")
        with self.assertRaises(InputError):
            memory("MemTotal: 100 kB\nSwapTotal: 2 kB\nSwapFree: 3 kB")

    def test_duplicate_bad_unit_malformed(self):
        for s in ("MemTotal: 100 kB\nMemTotal: 90 kB", "MemTotal: 100 MB", "MemTotal: nan kB", "MemTotal: -10 kB"):
            with self.subTest(s=s), self.assertRaises(InputError):
                fields(s)

    def test_psi(self):
        psi = "some avg10=0.20 avg60=0.10 avg300=0.05 total=1234\nfull avg10=0.00 avg60=0.00 avg300=0.00 total=10\n"
        self.assertEqual(memory(self.mem, psi)["psi"]["some"]["total"], 1234)
        for s in ("", "some avg10=inf avg60=0 avg300=0 total=2", "some avg10=101 avg60=0 avg300=0 total=2", "some avg10=0 avg10=0 avg300=0 total=2"):
            with self.subTest(s=s), self.assertRaises(InputError):
                parse_psi(s)

    def test_vmstat(self):
        result = memory(self.mem, vmstat="pgscan_kswapd 300\npswpin 40\npgfault 7\n")
        self.assertEqual(result["vmstat_counters"], {"pgscan_kswapd": 300, "pswpin": 40})
        with self.assertRaises(InputError):
            memory(self.mem, vmstat="pswpin -2")


class CpuTests(unittest.TestCase):
    def setUp(self):
        self.before = (ROOT / "fixtures/stat_before.txt").read_text()
        self.after = (ROOT / "fixtures/stat_after.txt").read_text()

    def test_busy_aggregate(self):
        # Delta: busy 140, idle+iowait 60, total 200.
        self.assertAlmostEqual(cpu(self.before, self.after)["cpu_busy_pct_aggregate"], 70.0)

    def test_counter_regression(self):
        with self.assertRaises(InputError):
            cpu(self.after, self.before)
        with self.assertRaises(InputError):
            cpu(self.before, self.before)
        with self.assertRaises(InputError):
            cpu("cpu 1 nope 3 4", self.after)

    @staticmethod
    def proc(pid=42, utime=10, stime=20, start=999, comm="some (test) name"):
        fields = ["1"] * 19
        fields[10], fields[11], fields[18] = str(utime), str(stime), str(start)
        return f"{pid} ({comm}) S " + " ".join(fields)

    def test_process(self):
        a, b = self.proc(), self.proc(utime=30, stime=30)
        self.assertEqual(process_ticks(a)["comm"], "some (test) name")
        self.assertAlmostEqual(cpu(self.before, self.after, a, b)["process"]["cpu_pct_of_aggregate_capacity"], 30 * 100 / 200)

    def test_bad_process_and_pid_reuse(self):
        for a, b in ((self.proc(), self.proc(start=1000)), (self.proc(), self.proc(pid=43)), (self.proc(utime=50), self.proc()), ("bad", self.proc())):
            with self.subTest(a=a, b=b), self.assertRaises(InputError):
                cpu(self.before, self.after, a, b)
        with self.assertRaises(InputError):
            cpu(self.before, self.after, self.proc(), None)


class PowerTests(unittest.TestCase):
    def setUp(self):
        self.doc = json.loads((ROOT / "fixtures/power.json").read_text())

    def test_synthetic_is_not_proof(self):
        r = power(json.dumps(self.doc))
        self.assertEqual(r["dataset_kind"], "synthetic")
        self.assertFalse(r["claim_allowed"])
        self.assertEqual(r["metrics"]["drain_percentage_points_per_hour"], .75)
        self.assertEqual(r["metrics"]["wakeups_per_hour"], 125)
        self.assertAlmostEqual(r["metrics"]["suspend_fraction"], 27400 / 28800, places=5)

    def test_noncharging_and_time_and_battery(self):
        for key, value in (("charging", True), ("t_s", -1), ("battery_pct", 101), ("battery_pct", 92), ("wakeups", 0), ("suspend_s", 50000)):
            doc = json.loads(json.dumps(self.doc))
            doc["samples"][-1][key] = value
            with self.subTest(key=key, value=value), self.assertRaises(InputError):
                power(json.dumps(doc))

    def test_bad_samples_or_duration(self):
        for d in (dict(self.doc, samples=[]), dict(self.doc, dataset_kind="real"), dict(self.doc, samples=[self.doc["samples"][0], self.doc["samples"][1]])):
            with self.assertRaises(InputError):
                power(json.dumps(d))
        with self.assertRaises(InputError):
            power("not json")

    def test_missing_wakeups_are_unknown(self):
        doc = json.loads(json.dumps(self.doc))
        for row in doc["samples"]:
            row.pop("wakeups")
        self.assertIsNone(power(json.dumps(doc))["metrics"]["wakeups_per_hour"])


class ConfigTests(unittest.TestCase):
    def test_audit_not_device_proof(self):
        r = config((ROOT / "fixtures/config.txt").read_text())
        self.assertEqual(r["enabled_count"], 10)
        self.assertFalse(r["binary_compatibility_verified"])
        self.assertEqual(r["checks"]["CONFIG_ZRAM"]["value"], "m")

    def test_missing_disabled_and_duplicate(self):
        r = config("CONFIG_PSI=y\n# CONFIG_MODULES is not set")
        self.assertEqual(r["checks"]["CONFIG_MEMCG"]["state"], "unknown")
        self.assertEqual(r["checks"]["CONFIG_MODULES"]["state"], "disabled")
        with self.assertRaises(InputError):
            config("CONFIG_PSI=y\nCONFIG_PSI=n")
        with self.assertRaises(InputError):
            config("CONFIG_PSI y")


class CliTests(unittest.TestCase):
    def run_cli(self, *args):
        return subprocess.run([sys.executable, str(ROOT / "analyze.py"), *map(str, args)], text=True, capture_output=True)

    def test_success_four_modes(self):
        f = ROOT / "fixtures"
        for cmd in (("memory", f / "meminfo.txt"), ("cpu", f / "stat_before.txt", f / "stat_after.txt"), ("power", f / "power.json"), ("config", f / "config.txt")):
            with self.subTest(cmd=cmd):
                p = self.run_cli(*cmd)
                self.assertEqual(p.returncode, 0, p.stderr)
                self.assertEqual(json.loads(p.stdout)["task"], "P0-016")

    def test_missing_input(self):
        p = self.run_cli("memory", "/no/such/file")
        self.assertEqual(p.returncode, 2)
        self.assertIn("cannot read", p.stderr)

    def test_output_file(self):
        with tempfile.TemporaryDirectory() as td:
            dest = Path(td) / "result.json"
            p = self.run_cli("config", ROOT / "fixtures/config.txt", "--output", dest)
            self.assertEqual(p.returncode, 0, p.stderr)
            self.assertEqual(json.loads(dest.read_text())["report_kind"], "config")


if __name__ == "__main__":
    unittest.main()
