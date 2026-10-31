#!/usr/bin/env python3
"""P0-016: read-only procfs, energy-window and kernel-config audit CLI.

All inputs are supplied files. Reports never attest device provenance or compatibility.
"""
import argparse
import json
import math
import re
import sys
from pathlib import Path


class InputError(ValueError):
    """Invalid evidence; never silently coerce or invent values."""


def read(path):
    try:
        return Path(path).read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        raise InputError(f"cannot read {path}: {exc}") from exc


def number(raw, label):
    if isinstance(raw, bool):
        raise InputError(f"{label}: boolean is not numeric")
    try:
        n = float(raw)
    except (TypeError, ValueError) as exc:
        raise InputError(f"{label}: not numeric") from exc
    if not math.isfinite(n) or n < 0:
        raise InputError(f"{label}: expected nonnegative finite number")
    return n


def fields(text, unit="kB"):
    out = {}
    for line in text.splitlines():
        if not line.strip():
            continue
        m = re.fullmatch(r"\s*([A-Za-z_][A-Za-z_0-9()]*)\s*:\s*([0-9]+)(?:\s+([A-Za-z]+))?\s*", line)
        if not m:
            raise InputError(f"malformed statistic: {line[:75]}")
        key, count, found_unit = m.groups()
        if key in out or (found_unit is not None and found_unit != unit):
            raise InputError(f"duplicate key or invalid unit: {key}")
        out[key] = int(count)
    return out


def parse_psi(text):
    result = {}
    for line in text.splitlines():
        if not line.strip():
            continue
        parts = line.split()
        if len(parts) != 5 or parts[0] not in ("some", "full") or parts[0] in result:
            raise InputError("invalid PSI record")
        kv = {}
        for token in parts[1:]:
            if "=" not in token:
                raise InputError("invalid PSI token")
            name, value = token.split("=", 1)
            if name in kv or name not in ("avg10", "avg60", "avg300", "total"):
                raise InputError("duplicate/unknown PSI field")
            n = number(value, name)
            if name.startswith("avg") and n > 100:
                raise InputError("PSI average exceeds 100 percent")
            if name == "total" and not n.is_integer():
                raise InputError("PSI total must be integer microseconds")
            kv[name] = int(n) if name == "total" else n
        if set(kv) != {"avg10", "avg60", "avg300", "total"}:
            raise InputError("incomplete PSI record")
        result[parts[0]] = kv
    if "some" not in result:
        raise InputError("PSI missing some record")
    return result


def memory(meminfo, psi=None, vmstat=None):
    mem = fields(meminfo)
    total = mem.get("MemTotal")
    if not total:
        raise InputError("MemTotal must be present and positive")
    for key in ("MemFree", "MemAvailable", "SwapTotal", "SwapFree"):
        if key in mem and key in ("MemFree", "MemAvailable") and mem[key] > total:
            raise InputError(f"{key} exceeds MemTotal")
    if mem.get("SwapFree", 0) > mem.get("SwapTotal", 0):
        raise InputError("SwapFree exceeds SwapTotal")
    if "SwapFree" in mem and "SwapTotal" not in mem:
        raise InputError("SwapFree requires SwapTotal")
    available = mem.get("MemAvailable")
    report = {
        "mem_total_kib": total,
        "mem_available_kib": available,
        "mem_available_pct": round(100 * available / total, 4) if available is not None else None,
        "swap_used_kib": mem["SwapTotal"] - mem["SwapFree"] if {"SwapTotal", "SwapFree"} <= mem.keys() else None,
        "cached_kib": mem.get("Cached"),
        "slab_kib": mem.get("Slab"),
        "psi": parse_psi(psi) if psi is not None else None,
        "vmstat_counters": None,
        "limitations": ["meminfo is a snapshot, not a direct per-app PSS or OOM measurement"],
    }
    if available is None:
        report["limitations"].append("MemAvailable absent: no available-memory percentage")
    if psi is None:
        report["limitations"].append("PSI not supplied (not zero pressure)")
    if vmstat is not None:
        counters = {}
        for line in vmstat.splitlines():
            if not line.strip():
                continue
            part = line.split()
            if len(part) != 2 or not re.fullmatch(r"[a-z][a-z0-9_]*", part[0]) or not part[1].isdigit() or part[0] in counters:
                raise InputError("malformed vmstat counter")
            counters[part[0]] = int(part[1])
        report["vmstat_counters"] = {k: v for k, v in counters.items() if k.startswith(("pgscan", "pgsteal", "pswp", "allocstall", "compact"))}
        report["limitations"].append("vmstat cumulative counters require a matched interval for rates")
    return report


def cpu_ticks(text):
    record = next((x for x in text.splitlines() if x.startswith("cpu ")), None)
    if not record:
        raise InputError("aggregate cpu line missing")
    parts = record.split()
    if len(parts) < 5 or not all(x.isdigit() for x in parts[1:]):
        raise InputError("malformed aggregate cpu line")
    nums = list(map(int, parts[1:]))
    # /proc/stat: user nice system idle iowait irq softirq steal guest guest_nice.
    # guest fields are already included in user/nice; never add them to total.
    base = nums[:8]
    return sum(base), base[3] + (base[4] if len(base) > 4 else 0)


def process_ticks(text):
    # comm may contain spaces, parentheses and a closing ')' character.
    line = text.strip()
    m = re.fullmatch(r"(\d+) \((.*)\) ([A-Z]) (.*)", line)
    if not m:
        raise InputError("malformed /proc/PID/stat")
    tail = m.group(4).split()  # first item: ppid (field 4)
    if len(tail) < 19 or not all(tail[i].lstrip("-").isdigit() for i in (10, 11, 18)):
        raise InputError("process stat too short or invalid counters")
    # utime field 14 => tail[10]; stime 15 => tail[11]; starttime 22 => tail[18].
    values = list(map(int, (tail[10], tail[11], tail[18])))
    if any(x < 0 for x in values):
        raise InputError("negative process counter")
    return {"pid": int(m.group(1)), "comm": m.group(2), "ticks": values[0] + values[1], "starttime": values[2]}


def cpu(before, after, proc_before=None, proc_after=None):
    tb, ib = cpu_ticks(before)
    ta, ia = cpu_ticks(after)
    dt, di = ta - tb, ia - ib
    if dt <= 0 or di < 0 or di > dt:
        raise InputError("invalid cpu counter interval")
    result = {"cpu_busy_pct_aggregate": round(100 * (dt - di) / dt, 4),
              "cpu_total_jiffies_delta": dt, "process": None,
              "limitations": ["aggregate busy time includes IRQ, softirq and steal; iowait treated as idle", "two snapshots do not measure scheduler latency or energy"]}
    if (proc_before is None) != (proc_after is None):
        raise InputError("both process snapshots required")
    if proc_before is not None:
        p, q = process_ticks(proc_before), process_ticks(proc_after)
        if p["pid"] != q["pid"] or p["starttime"] != q["starttime"]:
            raise InputError("PID reuse or process mismatch")
        delta = q["ticks"] - p["ticks"]
        if delta < 0 or delta > dt:
            raise InputError("invalid process cpu interval")
        result["process"] = {"pid": p["pid"], "comm": q["comm"],
                             "cpu_pct_of_aggregate_capacity": round(100 * delta / dt, 4),
                             "cpu_jiffies_delta": delta}
    return result


def power(text, min_hours=8):
    try:
        inp = json.loads(text)
    except (TypeError, ValueError) as exc:
        raise InputError("invalid power JSON") from exc
    if not isinstance(inp, dict) or inp.get("dataset_kind") not in ("synthetic", "device"):
        raise InputError("dataset_kind must be synthetic or device")
    samples = inp.get("samples")
    if not isinstance(samples, list) or len(samples) < 2:
        raise InputError("at least two power samples required")
    prev = None
    for row in samples:
        if not isinstance(row, dict) or not {"t_s", "battery_pct", "charging"} <= row.keys() or type(row["charging"]) is not bool:
            raise InputError("invalid power sample structure")
        if any(not isinstance(row[k], (int, float)) or isinstance(row[k], bool) for k in ("t_s", "battery_pct")):
            raise InputError("timestamp and battery level require JSON numbers")
        t, level = number(row["t_s"], "t_s"), number(row["battery_pct"], "battery_pct")
        if level > 100 or row["charging"]:
            raise InputError("battery exceeds 100 or was charging")
        for optional in ("wakeups", "suspend_s", "temp_c"):
            if optional in row and row[optional] is not None:
                if not isinstance(row[optional], (int, float)) or isinstance(row[optional], bool):
                    raise InputError(f"{optional}: expected JSON number")
                number(row[optional], optional)
        if prev is not None:
            if t <= prev["t_s"] or level > prev["battery_pct"]:
                raise InputError("nonmonotonic time or battery increased")
            for counter in ("wakeups", "suspend_s"):
                if row.get(counter) is not None and prev.get(counter) is not None and row[counter] < prev[counter]:
                    raise InputError(f"{counter} decreased")
        prev = dict(row, t_s=t, battery_pct=level)
    start, end = samples[0], samples[-1]
    duration = number(end["t_s"], "end time") - number(start["t_s"], "start time")
    if duration < 3600 * min_hours or duration <= 0:
        raise InputError(f"power window shorter than {min_hours:g} hours")
    drain = number(start["battery_pct"], "start battery") - number(end["battery_pct"], "end battery")
    summary = {"duration_hours": round(duration / 3600, 5),
               "battery_drain_percentage_points": round(drain, 5),
               "drain_percentage_points_per_hour": round(drain * 3600 / duration, 5),
               "wakeups_per_hour": None, "suspend_fraction": None}
    if start.get("wakeups") is not None and end.get("wakeups") is not None:
        summary["wakeups_per_hour"] = round((end["wakeups"] - start["wakeups"]) * 3600 / duration, 5)
    if start.get("suspend_s") is not None and end.get("suspend_s") is not None:
        delta_suspend = end["suspend_s"] - start["suspend_s"]
        if delta_suspend > duration:
            raise InputError("suspend time exceeds wall duration")
        summary["suspend_fraction"] = round(delta_suspend / duration, 5)
    return {"dataset_kind": inp["dataset_kind"], "producer_asserted_provenance": True,
            "metrics": summary, "claim_allowed": False,
            "limitations": ["battery percentage is coarse, not calibrated energy", "samples do not prove workload, ambient, battery health or matched Android baseline", "wakeups counter semantics must be declared and consistent"]}


CHECKS = {
    "CONFIG_PSI": "memory pressure observation", "CONFIG_CGROUPS": "cgroup foundation",
    "CONFIG_MEMCG": "memory cgroup accounting", "CONFIG_SECCOMP": "syscall filtering",
    "CONFIG_SECURITY_SELINUX": "SELinux security framework", "CONFIG_MODULES": "loadable modules",
    "CONFIG_SUSPEND": "system suspend", "CONFIG_CPU_FREQ": "CPU frequency control",
    "CONFIG_THERMAL": "thermal framework", "CONFIG_ZRAM": "compressed swap option",
}


def config(text):
    values = {}
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        m = re.fullmatch(r"(CONFIG_[A-Z0-9_]+)=(.*)", line)
        off = re.fullmatch(r"# (CONFIG_[A-Z0-9_]+) is not set", line)
        if m:
            key, value = m.groups()
        elif off:
            key, value = off.group(1), "n"
        elif line.startswith("#"):
            continue
        else:
            raise InputError(f"invalid config entry: {line[:75]}")
        if key in values:
            raise InputError(f"duplicate config: {key}")
        if value not in ("y", "n", "m") and not re.fullmatch(r'[0-9]+|0[xX][0-9A-Fa-f]+|"[^"\n]*"', value):
            raise InputError(f"invalid config value: {key}")
        values[key] = value
    audit = {}
    for key, why in CHECKS.items():
        v = values.get(key)
        audit[key] = {"value": v, "state": "unknown" if v is None else ("enabled" if v in ("y", "m") else "disabled"), "purpose": why}
    return {"checks": audit, "missing_keys": [k for k in CHECKS if k not in values],
            "enabled_count": sum(x["state"] == "enabled" for x in audit.values()),
            "binary_compatibility_verified": False,
            "limitations": ["config alone cannot verify actual GKI/KMI ABI, module symbol CRC, boot, vendor drivers or security runtime", "policy depends on device and launch kernel; flags are signals, not universal requirements"]}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="mode", required=True)
    mem = sub.add_parser("memory")
    mem.add_argument("meminfo")
    mem.add_argument("--psi")
    mem.add_argument("--vmstat")
    cp = sub.add_parser("cpu")
    cp.add_argument("before")
    cp.add_argument("after")
    cp.add_argument("--process-before")
    cp.add_argument("--process-after")
    pw = sub.add_parser("power")
    pw.add_argument("input")
    pw.add_argument("--min-hours", type=float, default=8)
    cf = sub.add_parser("config")
    cf.add_argument("input")
    for command in (mem, cp, pw, cf):
        command.add_argument("--output", help="optional JSON result destination (otherwise stdout)")
    args = parser.parse_args(argv)
    try:
        if args.mode == "memory":
            out = memory(read(args.meminfo), read(args.psi) if args.psi else None, read(args.vmstat) if args.vmstat else None)
        elif args.mode == "cpu":
            out = cpu(read(args.before), read(args.after), read(args.process_before) if args.process_before else None, read(args.process_after) if args.process_after else None)
        elif args.mode == "power":
            if not math.isfinite(args.min_hours) or args.min_hours <= 0:
                raise InputError("min-hours must be finite and positive")
            out = power(read(args.input), args.min_hours)
        else:
            out = config(read(args.input))
        result = {"task": "P0-016", "source_type": "user_supplied_or_fixture", "report_kind": args.mode, "report": out}
        rendered = json.dumps(result, indent=2, sort_keys=True) + "\n"
        if args.output:
            try:
                Path(args.output).write_text(rendered, encoding="utf-8")
            except OSError as exc:
                raise InputError(f"cannot write output: {exc}") from exc
        else:
            print(rendered, end="")
    except InputError as exc:
        print(f"P0-016 input error: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
