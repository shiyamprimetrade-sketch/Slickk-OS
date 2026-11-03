#!/usr/bin/env python3
"""P0-015: strict, read-only analyzer for *derived* native/runtime observations.

Does not parse raw Perfetto, simpleperf or ART binary traces; exporters must
create the documented observation schema and preserve their raw evidence.
"""
import argparse
import csv
import json
import math
import re
import statistics
import sys
from collections import defaultdict
from pathlib import Path

VERSION = "1.0"
TEXT_FIELDS = (
    "provenance", "environment_kind", "environment_id", "build_id",
    "source_tool", "source_ref", "experiment_id", "protocol_id",
    "runtime_mode", "workload", "variant", "metric", "unit", "sample_id",
)
FIELDS = set(TEXT_FIELDS) | {"value"}
METRICS = {
    "duration_ns": ("time", "lower"),
    "initialization_ns": ("time", "lower"),
    "startup_ns": ("time", "lower"),
    "gc_pause_ns": ("time", "lower"),
    "jni_transition_ns": ("time", "lower"),
    "allocation_count": ("count", "lower"),
    "allocated_bytes": ("memory", "lower"),
}
UNITS = {
    "time": {"ns": 1, "us": 1_000, "ms": 1_000_000, "s": 1_000_000_000},
    "count": {"count": 1},
    "memory": {"bytes": 1, "KiB": 1024},
}
CANONICAL = {"time": "ns", "count": "count", "memory": "bytes"}
PAIR_CONTEXT = ("provenance", "environment_kind", "environment_id",
                "source_tool", "protocol_id", "runtime_mode")
MIN_PAIRS = 5


class InvalidData(ValueError):
    """Invalid input or schema; separate from inconclusive experiments."""


def _str(value, name, index):
    if not isinstance(value, str) or not value.strip() or value != value.strip():
        raise InvalidData(f"row {index}: {name} must be a nonempty trimmed string")
    if len(value) > 512 or any(ord(c) < 32 for c in value):
        raise InvalidData(f"row {index}: invalid {name}")
    return value


def _number(value, index):
    if isinstance(value, bool) or value is None:
        raise InvalidData(f"row {index}: value must be numeric")
    try:
        number = float(value)
    except (TypeError, ValueError, OverflowError) as error:
        raise InvalidData(f"row {index}: value must be numeric") from error
    if not math.isfinite(number) or number < 0:
        raise InvalidData(f"row {index}: nonfinite or negative value")
    return number


def read_input(path):
    p = Path(path)
    if p.suffix.lower() == ".json":
        try:
            data = json.loads(p.read_text(encoding="utf-8"),
                              parse_constant=lambda x: (_ for _ in ()).throw(InvalidData(f"nonfinite {x}")))
        except (json.JSONDecodeError, UnicodeError) as error:
            raise InvalidData(f"JSON parse: {error}") from error
        if not isinstance(data, dict) or set(data) != {"schema_version", "observations"}:
            raise InvalidData("JSON requires only schema_version and observations")
        if data["schema_version"] != VERSION:
            raise InvalidData("unsupported schema version")
        rows = data["observations"]
    elif p.suffix.lower() == ".csv":
        try:
            with p.open(encoding="utf-8", newline="") as f:
                reader = csv.DictReader(f, strict=True)
                if reader.fieldnames is None or len(set(reader.fieldnames)) != len(reader.fieldnames):
                    raise InvalidData("missing or duplicate CSV columns")
                if set(reader.fieldnames) != FIELDS | {"schema_version"}:
                    raise InvalidData("CSV columns do not match schema")
                rows = list(reader)
                if any(r.pop("schema_version", None) != VERSION for r in rows):
                    raise InvalidData("unsupported CSV schema version")
        except (csv.Error, UnicodeError) as error:
            raise InvalidData(f"CSV parse: {error}") from error
    else:
        raise InvalidData("file must use .json or .csv")
    if not isinstance(rows, list) or not rows or len(rows) > 200_000:
        raise InvalidData("observations must be a nonempty list (maximum 200000)")
    validated = []
    seen = set()
    for index, row in enumerate(rows, 1):
        if not isinstance(row, dict) or set(row) != FIELDS:
            raise InvalidData(f"row {index}: unexpected or missing fields")
        item = {key: _str(row[key], key, index) for key in TEXT_FIELDS}
        if item["provenance"] not in ("synthetic", "measured"):
            raise InvalidData(f"row {index}: unknown provenance")
        if item["environment_kind"] not in ("host", "android_device", "emulator"):
            raise InvalidData(f"row {index}: unknown environment")
        if item["variant"] not in ("baseline", "candidate"):
            raise InvalidData(f"row {index}: unknown variant")
        if item["metric"] not in METRICS:
            raise InvalidData(f"row {index}: unsupported metric")
        family, _ = METRICS[item["metric"]]
        if item["unit"] not in UNITS[family]:
            raise InvalidData(f"row {index}: inconsistent unit for {item['metric']}")
        if item["provenance"] == "synthetic" and not item["source_ref"].startswith("synthetic:"):
            raise InvalidData(f"row {index}: synthetic evidence must have synthetic: prefix")
        if item["provenance"] == "measured" and item["source_ref"].startswith("synthetic:"):
            raise InvalidData(f"row {index}: measured row has synthetic evidence")
        if not re.fullmatch(r"[A-Za-z0-9_.:-]{1,128}", item["sample_id"]):
            raise InvalidData(f"row {index}: invalid sample_id")
        value = _number(row["value"], index)
        if family == "count" and not value.is_integer():
            raise InvalidData(f"row {index}: allocation count must be integral")
        item["value"] = value * UNITS[family][item["unit"]]
        if not math.isfinite(item["value"]):
            raise InvalidData(f"row {index}: converted value overflow")
        item["unit"] = CANONICAL[family]
        key = (item["experiment_id"], item["workload"], item["metric"],
               item["variant"], item["sample_id"])
        if key in seen:
            raise InvalidData(f"row {index}: duplicate experiment/metric/variant/sample")
        seen.add(key)
        validated.append(item)
    return validated


def percentile(values, q):
    ordered = sorted(values)
    pos = (len(ordered) - 1) * q
    low = int(pos)
    return ordered[low] + (ordered[min(low + 1, len(ordered) - 1)] - ordered[low]) * (pos - low)


def stats(values):
    if not values:
        return None
    mean = statistics.fmean(values)
    sd = statistics.stdev(values) if len(values) > 1 else None
    return {
        "n": len(values), "median": statistics.median(values),
        "p95": percentile(values, .95), "mean": mean,
        "sample_sd": sd, "cv_pct": 100 * sd / mean if sd is not None and mean else None,
        "minimum": min(values), "maximum": max(values),
    }


def analyze(rows, threshold_pct=5.0):
    if not 0 <= threshold_pct <= 100 or not math.isfinite(threshold_pct):
        raise InvalidData("invalid regression threshold")
    groups = defaultdict(list)
    for row in rows:
        groups[(row["experiment_id"], row["workload"], row["metric"])].append(row)
    reports = []
    for (experiment, workload, metric), group in sorted(groups.items()):
        variants = {v: [r for r in group if r["variant"] == v]
                    for v in ("baseline", "candidate")}
        contexts = {v: sorted(set(tuple(r[k] for k in PAIR_CONTEXT) for r in variants[v]))
                    for v in variants}
        builds = {v: sorted(set(r["build_id"] for r in variants[v])) for v in variants}
        result = {"experiment_id": experiment, "workload": workload, "metric": metric,
                  "unit": CANONICAL[METRICS[metric][0]],
                  "provenance": sorted(set(r["provenance"] for r in group)),
                  "environments": sorted(set(r["environment_kind"] for r in group)),
                  "builds": builds,
                  "variants": {v: stats([r["value"] for r in variants[v]]) for v in variants},
                  "claim_allowed": False}
        if not all(variants.values()):
            result.update(status="INSUFFICIENT", reason="missing variant")
        elif any(len(contexts[v]) != 1 for v in contexts) or contexts["baseline"] != contexts["candidate"]:
            result.update(status="INCOMPARABLE", reason="measurement context differs")
        elif any(len(builds[v]) != 1 for v in builds):
            result.update(status="INCOMPARABLE", reason="build varies within variant")
        else:
            baseline = {r["sample_id"]: r["value"] for r in variants["baseline"]}
            candidate = {r["sample_id"]: r["value"] for r in variants["candidate"]}
            shared = sorted(baseline.keys() & candidate.keys())
            result["paired_samples"] = len(shared)
            result["unmatched_samples"] = len(baseline) + len(candidate) - 2 * len(shared)
            if len(shared) < MIN_PAIRS:
                result.update(status="INSUFFICIENT", reason=f"fewer than {MIN_PAIRS} matched pairs")
            else:
                bs, cs = stats([baseline[k] for k in shared]), stats([candidate[k] for k in shared])
                # P95 for tail latency; median for allocation quantities.
                endpoint = "median" if METRICS[metric][0] in ("memory", "count") else "p95"
                b, c = bs[endpoint], cs[endpoint]
                result.update(endpoint=endpoint, baseline_paired=bs, candidate_paired=cs)
                if b == 0:
                    result.update(status="NO_CHANGE" if c == 0 else "REGRESSION",
                                  reason="zero baseline: relative comparison undefined", delta_pct=None)
                else:
                    delta = (c - b) / b * 100
                    result.update(delta_pct=delta,
                                  status="REGRESSION" if delta > threshold_pct else
                                  "IMPROVEMENT_CANDIDATE" if delta < -threshold_pct else "NO_CLEAR_CHANGE")
        reports.append(result)
    return {"schema_version": VERSION, "claim_allowed": False,
            "regression_threshold_pct": threshold_pct, "groups": reports}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", help=".json or .csv normalized observation file")
    parser.add_argument("--output", help="write deterministic JSON report")
    parser.add_argument("--regression-threshold-pct", type=float, default=5.0)
    parser.add_argument("--fail-on-regression", action="store_true")
    args = parser.parse_args(argv)
    try:
        report = analyze(read_input(args.input), args.regression_threshold_pct)
        payload = json.dumps(report, indent=2, sort_keys=True, allow_nan=False) + "\n"
        if args.output:
            Path(args.output).write_text(payload, encoding="utf-8")
        else:
            sys.stdout.write(payload)
        return 3 if args.fail_on_regression and any(
            g["status"] == "REGRESSION" for g in report["groups"]) else 0
    except (InvalidData, OSError) as error:
        print(f"INVALID: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
