#!/usr/bin/env python3
"""Validate and compare matched Slickk-OS/Android observations; no third-party deps."""
import argparse
import csv
import json
import math
import re
import statistics
import sys
from datetime import datetime, timezone
from pathlib import Path

SCHEMA = json.loads(Path(__file__).with_name("schema.json").read_text(encoding="utf-8"))
PROPS = SCHEMA["$defs"]["observation"]["properties"]
REQUIRED = set(SCHEMA["$defs"]["observation"]["required"])
METRICS = SCHEMA["x-metrics"]
NUMBERS = {k for k, v in PROPS.items() if v.get("type") in ("number", "integer")}
CONTROL_KEYS = ("device_id", "device_model", "device_type", "app_version", "test_version",
                "network", "brightness_pct", "refresh_hz", "profile_id", "exposure_s")


class InvalidData(ValueError):
    """Observations cannot be safely interpreted."""


def _number(value, name, integer=False):
    if isinstance(value, bool) or not isinstance(value, (float, int)):
        raise InvalidData(f"{name}: expected numeric value")
    if not math.isfinite(value) or (integer and not isinstance(value, int)):
        raise InvalidData(f"{name}: expected finite {'integer' if integer else 'number'}")
    return value


def _validate_observation(row, index):
    where = f"observations[{index}]"
    if not isinstance(row, dict):
        raise InvalidData(f"{where}: expected object")
    missing, extra = REQUIRED - set(row), set(row) - set(PROPS)
    if missing or extra:
        raise InvalidData(f"{where}: missing={sorted(missing)} unexpected={sorted(extra)}")
    for key, spec in PROPS.items():
        value = row[key]
        name = f"{where}.{key}"
        if "enum" in spec and value not in spec["enum"]:
            raise InvalidData(f"{name}: unsupported value {value!r}")
        if spec.get("type") in ("number", "integer"):
            value = _number(value, name, spec["type"] == "integer")
            if any(("minimum" in spec and value < spec["minimum"],
                    "maximum" in spec and value > spec["maximum"],
                    "exclusiveMinimum" in spec and value <= spec["exclusiveMinimum"])):
                raise InvalidData(f"{name}: out of range")
        elif isinstance(value, str):
            if not value and spec.get("minLength", 0):
                raise InvalidData(f"{name}: empty string")
            if "pattern" in spec and not re.fullmatch(spec["pattern"], value):
                raise InvalidData(f"{name}: invalid identifier")
        else:
            raise InvalidData(f"{name}: expected string")
    if row["metric"] not in METRICS:
        raise InvalidData(f"{where}: unsupported metric")
    metric = METRICS[row["metric"]]
    if row["unit"] != metric["unit"]:
        raise InvalidData(f"{where}: unit mismatch, expected {metric['unit']}")
    if row["metric"].endswith("_pct") and row["value"] > 100:
        raise InvalidData(f"{where}: percentage above 100")
    if row["metric"].endswith("_count") or row["metric"] == "ux_steps":
        if not float(row["value"]).is_integer():
            raise InvalidData(f"{where}: count must be integral")
    if row["dataset_kind"] == "synthetic" and not row["evidence_ref"].startswith("synthetic:"):
        raise InvalidData(f"{where}: synthetic evidence must be labeled synthetic:")
    if row["dataset_kind"] == "device" and row["evidence_ref"].startswith("synthetic:"):
        raise InvalidData(f"{where}: device evidence cannot be synthetic")
    try:
        stamp = datetime.fromisoformat(row["timestamp_utc"].replace("Z", "+00:00"))
        if stamp.tzinfo is None or stamp.utcoffset().total_seconds() != 0:
            raise ValueError("not UTC")
    except (ValueError, AttributeError) as error:
        raise InvalidData(f"{where}: timestamp_utc must be ISO-8601 UTC") from error
    if row["metric"] in ("idle_drain_pct_per_hour", "energy_mwh") and row["exposure_s"] < 480 * 60:
        raise InvalidData(f"{where}: idle-energy session requires >= 8h exposure")
    if row["metric"] in ("crash_count", "anr_count", "background_energy_mwh") and row["exposure_s"] <= 0:
        raise InvalidData(f"{where}: event/energy measurement needs positive exposure")


def load(path):
    """Load strict JSON array envelope or CSV with one observation per row."""
    path = Path(path)
    if path.suffix.lower() == ".json":
        try:
            data = json.loads(path.read_text(encoding="utf-8"), parse_constant=lambda v: (_ for _ in ()).throw(InvalidData(f"not finite: {v}")))
        except json.JSONDecodeError as error:
            raise InvalidData(f"invalid JSON: {error}") from error
        if not isinstance(data, dict) or set(data) != {"schema_version", "observations"} or data["schema_version"] != "1.0":
            raise InvalidData("JSON root requires schema_version=1.0 and observations")
        rows = data["observations"]
    elif path.suffix.lower() == ".csv":
        with path.open(encoding="utf-8", newline="") as file:
            reader = csv.DictReader(file, strict=True)
            if not reader.fieldnames or len(reader.fieldnames) != len(set(reader.fieldnames)):
                raise InvalidData("CSV needs unique header names")
            if set(reader.fieldnames) != REQUIRED | {"schema_version"}:
                raise InvalidData("CSV headers do not match required observation fields")
            rows = list(reader)
        for row in rows:
            if row.pop("schema_version") != "1.0":
                raise InvalidData("CSV schema_version must be 1.0")
            for key in NUMBERS:
                try:
                    row[key] = int(row[key]) if key == "iteration" else float(row[key])
                except (TypeError, ValueError, OverflowError) as error:
                    raise InvalidData(f"CSV nonnumeric {key}") from error
    else:
        raise InvalidData("use a .json or .csv input")
    if not isinstance(rows, list) or not rows:
        raise InvalidData("at least one observation required")
    seen = set()
    for i, row in enumerate(rows):
        _validate_observation(row, i)
        identity = (row["dataset_kind"], row["variant"], row["workload"], row["metric"], row["iteration"])
        if identity in seen:
            raise InvalidData(f"duplicate observation identity {identity}")
        seen.add(identity)
    return rows


def percentile(values, fraction):
    """Sorted finite values; Hyndman-Fan type 7 linear interpolation."""
    values = sorted(values)
    if not values:
        raise InvalidData("percentile requires observations")
    pos = (len(values) - 1) * fraction
    low = int(math.floor(pos))
    high = int(math.ceil(pos))
    return values[low] + (values[high] - values[low]) * (pos - low)


def summary(rows):
    vals = [float(r["value"]) for r in rows]
    mean = statistics.fmean(vals)
    return {"n": len(vals), "median": statistics.median(vals), "p95": percentile(vals, .95),
            "mean": mean, "stdev": statistics.stdev(vals) if len(vals) > 1 else None,
            "cv_pct": (statistics.stdev(vals) / mean * 100) if len(vals) > 1 and mean > 0 else None,
            "min": min(vals), "max": max(vals)}


def compare(rows, tolerance_pct=5):
    groups = {}
    for row in rows:
        groups.setdefault((row["workload"], row["metric"]), {}).setdefault(row["variant"], []).append(row)
    results = []
    for (workload, metric), variants in sorted(groups.items()):
        spec = METRICS[metric]
        out = {"workload": workload, "metric": metric, "unit": spec["unit"],
               "target_improvement_pct": spec["target_pct"], "aggregation": spec["aggregate"]}
        baseline = sorted(variants.get("android", []), key=lambda r: r["iteration"])
        candidate = sorted(variants.get("slickk-os", []), key=lambda r: r["iteration"])
        out["android"] = summary(baseline) if baseline else None
        out["slickk_os"] = summary(candidate) if candidate else None
        reasons = []
        if not baseline or not candidate:
            reasons.append("missing Android baseline or Slickk-OS candidate")
        else:
            exemplar = baseline[0]
            for row in baseline + candidate:
                if row["dataset_kind"] != exemplar["dataset_kind"]:
                    reasons.append("mixed synthetic/device evidence")
                    break
                if any(row[k] != exemplar[k] for k in CONTROL_KEYS):
                    reasons.append("mismatched controlled environment or exposure")
                    break
                if abs(row["start_temp_c"] - exemplar["start_temp_c"]) > 2:
                    reasons.append("initial thermal mismatch > 2 C")
                    break
                if abs(row["battery_soc_pct"] - exemplar["battery_soc_pct"]) > 5:
                    reasons.append("battery SoC mismatch > 5 points")
                    break
            if [r["iteration"] for r in baseline] != [r["iteration"] for r in candidate]:
                reasons.append("unpaired iteration identifiers")
            minimum = 3 if metric in ("idle_drain_pct_per_hour", "energy_mwh", "background_energy_mwh") else 5
            if len(baseline) < minimum or len(candidate) < minimum:
                reasons.append(f"insufficient independent repetitions; need >= {minimum} per variant")
        if reasons:
            out.update(status="INCONCLUSIVE", reasons=sorted(set(reasons)), relative_improvement_pct=None)
        else:
            measure = spec["aggregate"]
            a, b = out["android"][measure], out["slickk_os"][measure]
            better = (a - b) if spec["better"] == "lower" else (b - a)
            if a == 0:
                delta_pct = 0 if b == 0 else None
                # Baseline zero means percentage change is undefined.
                status = "NO_CHANGE" if b == 0 else ("REGRESSION" if better < 0 else "INCONCLUSIVE")
            else:
                delta_pct = 100 * better / a
                if delta_pct < -tolerance_pct or (spec["target_pct"] == 0 and better < 0 and metric in ("crash_count", "anr_count", "privacy_violation_count", "accessibility_pass_pct", "compatibility_pass_pct")):
                    status = "REGRESSION"
                elif delta_pct >= spec["target_pct"] and delta_pct > 0:
                    status = "IMPROVEMENT_CANDIDATE"
                else:
                    status = "NO_CLEAR_CHANGE"
            out.update(status=status, reasons=[], relative_improvement_pct=delta_pct)
            if any(s["cv_pct"] is not None and s["cv_pct"] > 20 for s in (out["android"], out["slickk_os"])):
                out["reasons"].append("high variability CV > 20%; increase repetitions")
        kinds = sorted({r["dataset_kind"] for r in baseline + candidate})
        out["evidence_class"] = "SYNTHETIC_ONLY" if kinds == ["synthetic"] else "DEVICE_UNVERIFIED" if kinds == ["device"] else "MIXED_OR_INCOMPLETE"
        out["claim_allowed"] = False  # device provenance, effect size and review required
        results.append(out)
    return {"schema_version": "1.0", "measurement_claim": "NONE; processor does not certify real-device provenance",
            "comparison_count": len(results), "comparisons": results}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", help=".json or .csv observations")
    parser.add_argument("--output", help="write deterministic JSON report")
    parser.add_argument("--fail-on-regression", action="store_true")
    args = parser.parse_args(argv)
    try:
        report = compare(load(args.input))
        content = json.dumps(report, indent=2, sort_keys=True, allow_nan=False) + "\n"
        if args.output:
            Path(args.output).write_text(content, encoding="utf-8")
        else:
            print(content, end="")
        return 3 if args.fail_on_regression and any(x["status"] == "REGRESSION" for x in report["comparisons"]) else 0
    except (InvalidData, OSError, csv.Error) as error:
        print(f"INVALID BENCHMARK DATA: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
