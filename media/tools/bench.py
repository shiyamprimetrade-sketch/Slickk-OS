#!/usr/bin/env python3
"""P0-017 strict media/network comparison. Input is session-level JSON, not raw frames."""
import argparse
from collections import defaultdict
from datetime import datetime
import json
import math
from pathlib import Path
import re
import statistics
import sys

CATALOG = json.loads(Path(__file__).resolve().parents[1].joinpath("metrics.json").read_text())
METRICS = CATALOG["metrics"]
REQUIRED = {
    "dataset_kind", "variant", "workload", "metric", "unit", "value", "iteration",
    "sample_id", "session_id", "timestamp_utc", "evidence_ref", "artifact_sha256",
    "device_id", "device_model", "device_type", "os_build", "app_version", "test_version",
    "network", "brightness_pct", "refresh_hz", "start_temp_c", "battery_soc_pct",
    "profile_id", "exposure_s", "capture_tool", "source_revision", "order",
    "warmup_runs", "conditions", "valid", "error"
}
CONTROL = ("dataset_kind", "device_id", "device_model", "device_type", "app_version",
           "test_version", "network", "brightness_pct", "refresh_hz", "profile_id",
           "exposure_s", "capture_tool", "source_revision", "warmup_runs", "conditions")
PATTERN = re.compile(r"^[a-z][a-z0-9_]{1,63}$")
SHA = re.compile(r"^[0-9a-f]{64}$")


class ValidationError(ValueError):
    pass


def number(value, field, minimum=None, maximum=None, integer=False):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValidationError(f"{field}: expected finite number")
    if integer and (not isinstance(value, int) or isinstance(value, bool)):
        raise ValidationError(f"{field}: expected integer")
    if minimum is not None and value < minimum or maximum is not None and value > maximum:
        raise ValidationError(f"{field}: out of range")
    return value


def validate_row(row, idx):
    key = f"observations[{idx}]"
    if not isinstance(row, dict) or set(row) != REQUIRED:
        missing = sorted(REQUIRED - set(row)) if isinstance(row, dict) else sorted(REQUIRED)
        extra = sorted(set(row) - REQUIRED) if isinstance(row, dict) else []
        raise ValidationError(f"{key}: fields missing={missing} unexpected={extra}")
    for name in REQUIRED - {"value", "iteration", "order", "warmup_runs", "valid", "error",
                            "conditions", "brightness_pct", "refresh_hz", "start_temp_c",
                            "battery_soc_pct", "exposure_s"}:
        if not isinstance(row[name], str) or not row[name].strip():
            raise ValidationError(f"{key}.{name}: nonempty string required")
    if row["dataset_kind"] not in ("synthetic", "device", "host"):
        raise ValidationError(f"{key}: invalid provenance kind")
    if row["variant"] not in ("android", "slickk-os"):
        raise ValidationError(f"{key}: invalid variant")
    if row["network"] not in ("airplane", "wifi", "cellular", "offline", "ethernet", "bluetooth"):
        raise ValidationError(f"{key}: unsupported network transport")
    if row["device_type"] not in ("physical", "emulator", "host"):
        raise ValidationError(f"{key}: invalid device type")
    if row["dataset_kind"] == "device" and row["device_type"] == "host":
        raise ValidationError(f"{key}: host cannot claim device capture")
    if row["dataset_kind"] == "host" and row["device_type"] != "host":
        raise ValidationError(f"{key}: host data must identify host device type")
    if row["dataset_kind"] == "synthetic" and not row["evidence_ref"].startswith("synthetic:"):
        raise ValidationError(f"{key}: synthetic evidence must be labeled")
    if row["dataset_kind"] != "synthetic" and row["evidence_ref"].startswith("synthetic:"):
        raise ValidationError(f"{key}: incompatible evidence label")
    if row["artifact_sha256"] != "synthetic" and not SHA.fullmatch(row["artifact_sha256"]):
        raise ValidationError(f"{key}: artifact_sha256 must be lowercase SHA-256")
    if row["dataset_kind"] != "synthetic" and row["artifact_sha256"] == "synthetic":
        raise ValidationError(f"{key}: real evidence requires artifact SHA-256")
    if not PATTERN.fullmatch(row["workload"]):
        raise ValidationError(f"{key}: invalid workload identifier")
    spec = METRICS.get(row["metric"])
    if spec is None:
        raise ValidationError(f"{key}: unknown metric")
    if row["unit"] != spec["unit"]:
        raise ValidationError(f"{key}: invalid unit for {row['metric']}; expected {spec['unit']}")
    number(row["value"], f"{key}.value", 0, spec.get("max"), spec.get("integer", False))
    for field in ("iteration", "order", "warmup_runs"):
        number(row[field], f"{key}.{field}", 0 if field == "warmup_runs" else 1, 2 if field == "order" else None, True)
    for field, minimum, maximum in (("brightness_pct", 0, 100), ("refresh_hz", 1, None),
                                    ("start_temp_c", -30, 90), ("battery_soc_pct", 0, 100),
                                    ("exposure_s", 0.001, None)):
        number(row[field], f"{key}.{field}", minimum, maximum)
    if type(row["valid"]) is not bool or not isinstance(row["error"], str):
        raise ValidationError(f"{key}: valid must be bool and error must be string")
    if not row["valid"] or row["error"]:
        raise ValidationError(f"{key}: invalid/error observation is not comparable")
    if not isinstance(row["conditions"], dict) or not row["conditions"]:
        raise ValidationError(f"{key}: nonempty conditions dictionary required")
    if any(not isinstance(k, str) or not k or not isinstance(v, (str, int, float, bool))
           or isinstance(v, float) and not math.isfinite(v) for k, v in row["conditions"].items()):
        raise ValidationError(f"{key}: invalid conditions values")
    try:
        t = datetime.fromisoformat(row["timestamp_utc"].replace("Z", "+00:00"))
        if t.tzinfo is None or t.utcoffset().total_seconds() != 0:
            raise ValueError("not UTC")
    except (TypeError, AttributeError, ValueError) as exc:
        raise ValidationError(f"{key}: timestamp must be ISO-8601 UTC") from exc


def percentile(vals, fraction):
    vals = sorted(vals)
    pos = (len(vals) - 1) * fraction
    lo = math.floor(pos)
    return vals[lo] + (vals[math.ceil(pos)] - vals[lo]) * (pos - lo)


def stats(vals):
    mean = statistics.mean(vals)
    sd = statistics.stdev(vals) if len(vals) > 1 else 0
    return {"n": len(vals), "median": statistics.median(vals), "p95": percentile(vals, .95),
            "mean": mean, "sample_sd": sd, "cv_pct": sd / mean * 100 if mean else None}


def analyze(data, regression_pct=5):
    if not isinstance(data, dict) or set(data) != {"schema_version", "observations"} \
            or data["schema_version"] != "P0-017/1.0" or not isinstance(data["observations"], list):
        raise ValidationError("root requires schema_version=P0-017/1.0 and observations array")
    if not data["observations"]:
        raise ValidationError("empty observation array")
    number(regression_pct, "regression_pct", 0)
    grouped = defaultdict(lambda: defaultdict(dict))
    samples = set()
    sessions = set()
    for i, row in enumerate(data["observations"]):
        validate_row(row, i)
        unique = (row["sample_id"], row["variant"], row["metric"], row["workload"])
        if unique in samples:
            raise ValidationError(f"duplicate sample: {unique}")
        samples.add(unique)
        sess = (row["variant"], row["workload"], row["metric"], row["session_id"])
        if sess in sessions:
            raise ValidationError(f"duplicate session: {sess}")
        sessions.add(sess)
        slot = grouped[(row["workload"], row["metric"])][row["iteration"]]
        if row["variant"] in slot:
            raise ValidationError(f"duplicate iteration: {row['iteration']} {row['variant']}")
        slot[row["variant"]] = row
    output = []
    for (workload, metric), iterations in sorted(grouped.items()):
        spec = METRICS[metric]
        if len(iterations) < spec["min_runs"]:
            raise ValidationError(f"{workload}/{metric}: insufficient independent paired sessions")
        values = {"android": [], "slickk-os": []}
        stable_controls = None
        for iteration, pair in sorted(iterations.items()):
            if set(pair) != {"android", "slickk-os"}:
                raise ValidationError(f"{workload}/{metric}: iteration {iteration} missing variant")
            a, b = pair["android"], pair["slickk-os"]
            snapshot = tuple(json.dumps(a[k], sort_keys=True) for k in CONTROL)
            if stable_controls is not None and snapshot != stable_controls:
                raise ValidationError(f"{workload}/{metric}: inconsistent workload across iterations")
            stable_controls = snapshot
            if a["order"] == b["order"]:
                raise ValidationError(f"{workload}/{metric}: invalid trial order in pair {iteration}")
            if any(a[k] != b[k] for k in CONTROL):
                raise ValidationError(f"{workload}/{metric}: unmatched conditions at iteration {iteration}")
            if abs(a["start_temp_c"] - b["start_temp_c"]) > 2 or abs(a["battery_soc_pct"] - b["battery_soc_pct"]) > 5:
                raise ValidationError(f"{workload}/{metric}: thermal or battery confound in pair {iteration}")
            for label in values:
                values[label].append(pair[label]["value"])
        baseline, candidate = (stats(values[k]) for k in ("android", "slickk-os"))
        name = spec["aggregate"]
        x, y = baseline[name], candidate[name]
        relative = None if x == 0 else ((x - y) if spec["better"] == "lower" else (y - x)) / x * 100
        if x == 0:
            status = "INCONCLUSIVE_ZERO_BASELINE" if y != 0 else "NO_CHANGE"
        elif relative < -(0 if spec["unit"] in ("count", "percent") else regression_pct):
            status = "REGRESSION"
        elif relative > 0:
            status = "IMPROVEMENT_CANDIDATE"
        else:
            status = "NO_CHANGE"
        output.append({"workload": workload, "metric": metric, "subsystem": spec["subsystem"],
                       "unit": spec["unit"], "better": spec["better"], "aggregate": name,
                       "baseline": baseline, "candidate": candidate, "improvement_pct": relative,
                       "status": status})
    return {"schema_version": "P0-017/report-1", "valid": True,
            "dataset_kinds": sorted({r["dataset_kind"] for r in data["observations"]}),
            "claim_allowed": False, "comparisons": output}


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("observations", type=Path)
    p.add_argument("--output", type=Path)
    p.add_argument("--regression-pct", type=float, default=5)
    p.add_argument("--fail-on-regression", action="store_true")
    args = p.parse_args(argv)
    try:
        data = json.loads(args.observations.read_text(encoding="utf-8"),
                          parse_constant=lambda c: (_ for _ in ()).throw(ValidationError(c)))
        report = analyze(data, args.regression_pct)
        code = 3 if args.fail_on_regression and any(r["status"] == "REGRESSION" for r in report["comparisons"]) else 0
    except (OSError, ValueError, TypeError) as exc:
        report = {"valid": False, "claim_allowed": False, "errors": [str(exc)]}
        code = 2
    payload = json.dumps(report, sort_keys=True, indent=2, allow_nan=False) + "\n"
    if args.output:
        args.output.write_text(payload, encoding="utf-8")
    else:
        sys.stdout.write(payload)
    return code


if __name__ == "__main__":
    sys.exit(main())
