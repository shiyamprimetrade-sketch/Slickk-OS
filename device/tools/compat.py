#!/usr/bin/env python3
"""Slickk-OS P0-003: sanitized read-only capture and strict capability audit.

No device mutation, identifiers, proprietary blobs, or proof of OS boot support.
"""
import argparse
import copy
import json
import re
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CAPABILITIES = set("cpu_memory display_touch gpu camera audio wifi bluetooth nfc cellular gps motion_sensors usb battery_charging storage fingerprint tee encryption".split())
FEASIBILITY = set("bootloader_unlockable kernel_source device_tree vendor_modules vintf_hal recovery physical_os_boot".split())
VINTF_PATHS = ("/vendor/etc/vintf/manifest.xml", "/odm/etc/vintf/manifest.xml", "/system/etc/vintf/manifest.xml", "/vendor/etc/vintf/compatibility_matrix.xml")
PROPERTIES = {
    "android_release": "ro.build.version.release",
    "api_level": "ro.build.version.sdk",
    "abi": "ro.product.cpu.abi",
    "model": "ro.product.model",
}
SENSITIVE_KEY = re.compile(r"(?:imei|imsi|iccid|meid|serial(?:no|number)?|mac[_-]?address|android[_-]?id|subscriber[_-]?id|sim[_-]?id)", re.I)
SENSITIVE_VALUE = re.compile(r"(?:\b(?:imei|imsi|iccid|meid|serial(?:no|number)?|mac address|android id)\s*[:=]\s*\S+)|(?:\b\d{15}\b)|(?:\b(?:[0-9a-f]{2}:){5}[0-9a-f]{2}\b)", re.I)
HAL_NAME = re.compile(r"android\.hardware\.[a-zA-Z0-9_.]+\Z")


def private_content(obj, path="$", errors=None):
    """Reject potential identifiers before emitting any data-derived error text."""
    errors = [] if errors is None else errors
    if isinstance(obj, dict):
        for key, value in obj.items():
            if SENSITIVE_KEY.search(str(key)):
                errors.append(f"{path}: forbidden identifier key (value not shown)")
            private_content(value, path + "." + str(key), errors)
    elif isinstance(obj, list):
        for i, value in enumerate(obj):
            private_content(value, f"{path}[{i}]", errors)
    elif isinstance(obj, str) and SENSITIVE_VALUE.search(obj):
        errors.append(f"{path}: possible sensitive value (value not shown)")
    return errors


def schema_errors(value, schema, definitions, path="$", errors=None):
    """Local validator for precisely the JSON Schema keywords used in schema.json."""
    errors = [] if errors is None else errors
    if "$ref" in schema:
        return schema_errors(value, definitions[schema["$ref"].split("/")[-1]], definitions, path, errors)
    allowed = schema.get("type")
    if allowed is not None:
        choices = allowed if isinstance(allowed, list) else [allowed]
        matches = {
            "object": lambda v: isinstance(v, dict),
            "array": lambda v: isinstance(v, list),
            "string": lambda v: isinstance(v, str),
            "integer": lambda v: isinstance(v, int) and not isinstance(v, bool),
            "boolean": lambda v: isinstance(v, bool),
            "null": lambda v: v is None,
        }
        if not any(matches[t](value) for t in choices):
            errors.append(f"{path}: incorrect type")
            return errors
    if "const" in schema and value != schema["const"]:
        errors.append(f"{path}: unexpected constant")
    if "enum" in schema and value not in schema["enum"]:
        errors.append(f"{path}: unrecognized enum")
    if isinstance(value, dict):
        props = schema.get("properties", {})
        for required in schema.get("required", []):
            if required not in value:
                errors.append(f"{path}: missing {required}")
        for name, item in value.items():
            rule = props.get(name, schema.get("additionalProperties", True))
            if rule is False:
                errors.append(f"{path}: unexpected field")
            elif isinstance(rule, dict):
                schema_errors(item, rule, definitions, path + "." + name, errors)
    elif isinstance(value, list):
        if schema.get("uniqueItems") and len(set(json.dumps(x, sort_keys=True) for x in value)) != len(value):
            errors.append(f"{path}: duplicate items")
        if "items" in schema:
            for i, item in enumerate(value):
                schema_errors(item, schema["items"], definitions, f"{path}[{i}]", errors)
    elif isinstance(value, str):
        if len(value) < schema.get("minLength", 0) or len(value) > schema.get("maxLength", 1_000_000):
            errors.append(f"{path}: invalid string length")
        if "pattern" in schema and not re.search(schema["pattern"], value):
            errors.append(f"{path}: invalid string pattern")
    elif isinstance(value, int) and not isinstance(value, bool):
        if not schema.get("minimum", -1_000_000_000) <= value <= schema.get("maximum", 1_000_000_000):
            errors.append(f"{path}: out-of-range integer")
    return errors


def validate(data):
    errors = private_content(data)
    if errors:  # Never report raw fields containing private values.
        return errors
    schema = json.loads((ROOT / "schema.json").read_text(encoding="utf-8"))
    errors.extend(schema_errors(data, schema, schema["$defs"]))
    if errors:
        return errors
    evidence = {e["id"]: e for e in data["evidence"]}
    if len(evidence) != len(data["evidence"]):
        errors.append("evidence: duplicate IDs")
    if not data["synthetic"] and any(e["kind"] == "synthetic_test" for e in evidence.values()):
        errors.append("evidence: synthetic record in physical-device matrix")

    def references(ids, path):
        result = []
        for ident in ids:
            if ident not in evidence:
                errors.append(f"{path}: missing evidence reference")
            else:
                result.append(evidence[ident])
        return result

    model_proof = references([data["device"]["model_evidence"]], "device.model")
    expected_kind = "device_observation" if data["device"]["model_status"] == "VERIFIED" else "user_report"
    if model_proof and (model_proof[0]["kind"] != expected_kind or model_proof[0]["scope"] != "exact_device"):
        errors.append("device.model: incorrect evidence provenance")
    software = data["software"]
    for field in ("android_release", "api_level", "abi", "kernel_release"):
        source_id = software["evidence"].get(field)
        if (software[field] is None) != (source_id is None):
            errors.append(f"software.{field}: value/evidence must appear together")
        if source_id:
            proofs = references([source_id], f"software.{field}")
            if proofs and proofs[0]["scope"] != "exact_device":
                errors.append(f"software.{field}: generic evidence is insufficient")
    if software["android_release"] == "16" and software["api_level"] not in (None, 36):
        errors.append("software: Android 16 requires stable API 36")
    for group, expected in (("capabilities", CAPABILITIES), ("feasibility", FEASIBILITY)):
        seen = [c["name"] for c in data[group]]
        if set(seen) != expected or len(seen) != len(expected):
            errors.append(f"{group}: missing, unexpected, or duplicate capability names")
        for i, claim in enumerate(data[group]):
            path = f"{group}[{i}]"
            proofs = references(claim["evidence"], path)
            status = claim["status"]
            kinds = {p["kind"] for p in proofs if p["scope"] == "exact_device"}
            if data["synthetic"]:
                kinds |= {p["kind"] for p in proofs if p["kind"] == "synthetic_test"}
            if status in ("VERIFIED", "NOT_SUPPORTED"):
                needed = {"device_test", "synthetic_test"} if group == "capabilities" else {"device_test", "official_doc", "synthetic_test"}
                if not kinds.intersection(needed):
                    errors.append(f"{path}: conclusive claim lacks device-specific test/evidence")
            if status == "USER-REPORTED" and "user_report" not in kinds:
                errors.append(f"{path}: user report citation required")
            if status == "BLOCKED" and not claim["notes"].strip():
                errors.append(f"{path}: access blocker requires explanation")
            if status in ("UNKNOWN", "UNTESTED") and any(p["kind"] in ("device_test", "synthetic_test") for p in proofs):
                errors.append(f"{path}: test evidence contradicts unknown/untested status")
    paths = [item["path"] for item in data["interfaces"]]
    if set(paths) != set(VINTF_PATHS) or len(paths) != len(VINTF_PATHS):
        errors.append("interfaces: incomplete or duplicate VINTF path inventory")
    for i, item in enumerate(data["interfaces"]):
        proofs = references(item["evidence"], f"interfaces[{i}]")
        observed = any(p["kind"] == "device_observation" and p["scope"] == "exact_device" for p in proofs)
        if item["status"] != "UNKNOWN" and not observed:
            errors.append(f"interfaces[{i}]: observed evidence required")
        if item["declared_hal_packages"] and (item["status"] != "VERIFIED" or not observed):
            errors.append(f"interfaces[{i}]: unverified HAL declaration list")
    return errors


def report(data, errors):
    if errors:
        return "INVALID DEVICE MATRIX\n" + "\n".join("- " + e for e in errors) + "\n"
    statuses = {name: {c["status"]: sum(x["status"] == c["status"] for x in data[name]) for c in data[name]} for name in ("capabilities", "feasibility")}
    rows = ["SLICKK-OS P0-003 DEVICE FEASIBILITY", "VALID MATRIX: YES", f"MODEL: {data['device']['model']} ({data['device']['model_status']})", f"SYNTHETIC: {str(data['synthetic']).lower()}"]
    for name in ("capabilities", "feasibility"):
        rows.append(name.upper() + ": " + ", ".join(f"{k}={v}" for k, v in sorted(statuses[name].items())))
        rows.extend(f"  {c['name']}: {c['status']}" for c in data[name])
    rows += ["PHYSICAL OS BOOT: NOT VERIFIED BY THIS TOOL", "VINTF DECLARATIONS DO NOT PROVE RUNNING HAL SERVICES", "NO FLASH, UNLOCK OR PARTITION MODIFICATIONS PERFORMED"]
    return "\n".join(rows) + "\n"


def read_command(argv, mode, limit=8192):
    command = (["adb", "shell"] if mode == "adb" else []) + list(argv)
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=5, check=False)
    except (OSError, subprocess.TimeoutExpired):
        return None
    return result.stdout.strip()[:limit] if result.returncode == 0 else None


def collect(template, mode):
    data = copy.deepcopy(template)
    if data["synthetic"]:
        raise ValueError("cannot capture into synthetic template")
    observed = {}
    for field, prop in PROPERTIES.items():
        raw = read_command(["getprop", prop], mode)
        if raw and not private_content(raw) and "\n" not in raw and len(raw) <= 160:
            observed[field] = raw
    kernel = read_command(["uname", "-r"], mode)
    if kernel and not private_content(kernel) and "\n" not in kernel:
        observed["kernel_release"] = kernel
    if "api_level" in observed:
        try:
            observed["api_level"] = int(observed["api_level"])
        except ValueError:
            del observed["api_level"]
    if observed.get("model") and observed["model"] != data["device"]["model"]:
        raise ValueError("connected device model differs from selected template; no record written")
    if observed:
        data["evidence"].append({"id": "read-only-capture", "kind": "device_observation", "scope": "exact_device", "source": f"{mode} allowlisted getprop/uname", "detail": "Non-identifying values only; no hardware functionality test"})
        if "model" in observed:
            data["device"].update(model_status="VERIFIED", model_evidence="read-only-capture")
        for field in ("android_release", "api_level", "abi", "kernel_release"):
            if field in observed:
                data["software"][field] = observed[field]
                data["software"]["evidence"][field] = "read-only-capture"
    for item in data["interfaces"]:
        path = item["path"]
        xml = read_command(["cat", path], mode, limit=1048576)
        if xml is None:
            continue  # Missing or permission denied is UNKNOWN, not absence of HAL support.
        try:
            parsed = ET.fromstring(xml)
        except ET.ParseError:
            continue
        names = sorted({(n.text or "").strip() for n in parsed.findall(".//hal/name") if HAL_NAME.fullmatch((n.text or "").strip())})
        if "read-only-capture" not in {e["id"] for e in data["evidence"]}:
            data["evidence"].append({"id": "read-only-capture", "kind": "device_observation", "scope": "exact_device", "source": f"{mode} allowlisted VINTF XML paths", "detail": "Only Android HAL package names retained; no raw manifests saved"})
        item.update(status="VERIFIED", evidence=["read-only-capture"], declared_hal_packages=names)
    return data


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("validate", "collect"))
    parser.add_argument("matrix", nargs="?", type=Path)
    parser.add_argument("--mode", choices=("termux", "adb"), default="termux")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    try:
        if args.action == "collect":
            template = args.matrix or ROOT / "SM-A165F" / "matrix.json"
            data = collect(json.loads(template.read_text(encoding="utf-8")), args.mode)
        else:
            if args.matrix is None:
                parser.error("validate requires a matrix filename")
            data = json.loads(args.matrix.read_text(encoding="utf-8"))
        errors = validate(data)
        print(report(data, errors), end="")
        if errors:
            return 2
        if args.action == "collect":
            if not args.output:
                parser.error("collect requires --output")
            args.output.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
            print(f"SANITIZED OUTPUT: {args.output}")
        elif args.output:
            args.output.write_text(report(data, errors), encoding="utf-8")
        return 0
    except (ValueError, OSError, json.JSONDecodeError) as exc:
        print("VALIDATION ERROR: " + type(exc).__name__ + " (details suppressed)", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
