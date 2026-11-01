#!/usr/bin/env python3
"""Validate P0-009 user-journey contracts, emitting machine-readable JSON."""
import argparse
import json
import math
import sys
from collections import Counter
from pathlib import Path

STATUS = {"VERIFIED", "USER-REPORTED", "UNTESTED", "HYPOTHESIS", "BLOCKED"}
ACTIONS = {"tap", "swipe", "type", "long_press", "voice_command", "open_app",
           "open_system_settings", "open_system_panel", "system_navigation", "select", "confirm"}
SURFACES = {"launcher", "system_ui", "external_app"}
CAPABILITIES = {
    "launch_apps": {"launcher", "system_ui"},
    "search_apps": {"launcher"},
    "open_camera_app": {"launcher", "system_ui", "external_app"},
    "open_dialer": {"launcher", "system_ui", "external_app"},
    "open_contacts_app": {"launcher", "system_ui", "external_app"},
    "open_settings": {"launcher", "system_ui"},
    "open_internet_panel": {"launcher", "system_ui"},
    "open_documents_ui": {"launcher", "system_ui", "external_app"},
    "accessible_navigation": {"launcher", "system_ui", "external_app"},
    "manage_notifications": {"system_ui"},
    "change_wifi_connection": {"system_ui"},
    "switch_system_tasks": {"system_ui"},
    "change_privacy_controls": {"system_ui"},
    "change_accessibility_settings": {"system_ui"},
    "one_handed_system_mode": {"system_ui"},
}
SAFE_PERMISSIONS = {"android.permission.POST_NOTIFICATIONS", "android.permission.CAMERA",
                    "android.permission.READ_CONTACTS"}
ACCESSIBILITY = ("screen_reader", "large_text", "motor", "contrast", "keyboard")
METRICS = ("observed_duration_ms", "observed_interactions", "observed_errors")


def validate_catalog(data):
    """Return nonempty list of {code, path, message} for invalid contracts."""
    errors = []

    def err(code, path, message):
        errors.append({"code": code, "path": path, "message": message})

    if not isinstance(data, dict) or data.get("schema_version") != 1:
        err("SCHEMA", "$", "catalog must be an object with schema_version=1")
        return errors
    journeys = data.get("journeys")
    if not isinstance(journeys, list) or not journeys:
        err("EMPTY_CATALOG", "$.journeys", "nonempty array required")
        return errors
    ids = set()
    for index, journey in enumerate(journeys):
        p = f"$.journeys[{index}]"
        if not isinstance(journey, dict):
            err("SCHEMA", p, "journey must be an object")
            continue
        jid = journey.get("id")
        if not isinstance(jid, str) or not jid.startswith("UX-") or len(jid) < 5:
            err("JOURNEY_ID", p + ".id", "ID must start with UX- and be nonempty")
        elif jid in ids:
            err("DUPLICATE_ID", p + ".id", f"duplicate journey ID {jid}")
        else:
            ids.add(jid)
        for field in ("title", "prerequisites", "friction", "success_criterion"):
            val = journey.get(field)
            if field == "prerequisites":
                if not isinstance(val, list) or not all(isinstance(x, str) and x.strip() for x in val):
                    err("PREREQUISITE", p + ".prerequisites", "array of nonempty descriptions required")
            elif not isinstance(val, str) or not val.strip():
                err("REQUIRED", p + "." + field, "nonempty text required")
        priority = journey.get("priority")
        if type(priority) is not int or priority not in (1, 2, 3):
            err("PRIORITY", p + ".priority", "priority must be 1, 2 or 3")
        for group in ("baseline_steps", "proposed_steps"):
            steps = journey.get(group)
            if not isinstance(steps, list) or not steps:
                err("MISSING_STEPS", p + "." + group, "at least one step required")
                continue
            for seq, step in enumerate(steps, 1):
                sp = f"{p}.{group}[{seq - 1}]"
                if not isinstance(step, dict):
                    err("STEP", sp, "step must be an object")
                    continue
                if type(step.get("seq")) is not int or step["seq"] != seq:
                    err("STEP_SEQUENCE", sp + ".seq", f"expected contiguous step number {seq}")
                if step.get("action") not in ACTIONS:
                    err("INVALID_ACTION", sp + ".action", "unknown action; consult ACTIONS")
                for field in ("target", "expected"):
                    if not isinstance(step.get(field), str) or not step[field].strip():
                        err("STEP", sp + "." + field, "nonempty text required")
        access = journey.get("accessibility")
        if not isinstance(access, dict):
            err("ACCESSIBILITY", p + ".accessibility", "accessibility object required")
        else:
            for field in ACCESSIBILITY:
                if not isinstance(access.get(field), str) or not access[field].strip():
                    err("ACCESSIBILITY", p + ".accessibility." + field, "explicit requirement required")
        surface = journey.get("surface")
        if surface not in SURFACES:
            err("SURFACE", p + ".surface", "must be launcher, system_ui or external_app")
        capabilities = journey.get("capabilities")
        if not isinstance(capabilities, list) or not capabilities:
            err("CAPABILITY", p + ".capabilities", "nonempty array required")
        else:
            for cap in capabilities:
                if cap not in CAPABILITIES:
                    err("CAPABILITY", p + ".capabilities", f"unsupported capability {cap!r}")
                elif surface not in CAPABILITIES[cap]:
                    err("PRIVILEGE", p + ".capabilities", f"{surface} cannot directly perform {cap}")
        permissions = journey.get("required_permissions")
        if not isinstance(permissions, list):
            err("PERMISSION", p + ".required_permissions", "permission array required (use [] if none)")
        elif any(not isinstance(x, str) or x not in SAFE_PERMISSIONS for x in permissions):
            err("PERMISSION", p + ".required_permissions", "unapproved/privileged permission assumption")
        evidence = journey.get("evidence")
        if not isinstance(evidence, dict):
            err("EVIDENCE", p + ".evidence", "evidence object required")
            continue
        baseline_status, proposal_status = evidence.get("baseline_status"), evidence.get("proposal_status")
        if baseline_status not in STATUS or proposal_status not in STATUS:
            err("EVIDENCE", p + ".evidence", "invalid evidence classification")
        if proposal_status == "VERIFIED" and not evidence.get("proposal_evidence_ref"):
            err("EVIDENCE", p + ".evidence.proposal_evidence_ref", "VERIFIED proposal needs traceable source")
        observed = evidence.get("observed")
        if type(observed) is not bool:
            err("EVIDENCE", p + ".evidence.observed", "observed must be boolean")
        if observed and (baseline_status != "VERIFIED" or not evidence.get("observation_source")):
            err("EVIDENCE", p + ".evidence", "observations need VERIFIED status and a source")
        if not observed and baseline_status == "VERIFIED":
            err("EVIDENCE", p + ".evidence", "unobserved baseline cannot claim VERIFIED")
        for metric in METRICS:
            value = evidence.get(metric, "MISSING")
            if value == "MISSING":
                err("MEASUREMENT", p + ".evidence." + metric, "field required; null when unmeasured")
            elif value is not None:
                if not observed:
                    err("EVIDENCE", p + ".evidence." + metric, "unobserved measurements must be null")
                if type(value) not in (int, float) or not math.isfinite(value) or value < 0:
                    err("MEASUREMENT", p + ".evidence." + metric, "finite nonnegative number required")
                elif metric != "observed_duration_ms" and type(value) is not int:
                    err("MEASUREMENT", p + ".evidence." + metric, "count must be integer")
        target = journey.get("interaction_target_max")
        if target is not None and (type(target) is not int or target < 1):
            err("MEASUREMENT", p + ".interaction_target_max", "null or positive integer required")
        if not isinstance(journey.get("privacy"), str) or not journey["privacy"].strip():
            err("PRIVACY", p + ".privacy", "describe data and permission implications")
    return errors


def report(data):
    errors = validate_catalog(data)
    journeys = data.get("journeys", []) if isinstance(data, dict) else []
    journeys = journeys if isinstance(journeys, list) else []
    valid = [j for j in journeys if isinstance(j, dict)]
    return {"ok": not errors, "journey_count": len(valid),
            "surface_counts": dict(Counter(j.get("surface", "unknown") for j in valid)),
            "evidence_counts": dict(Counter(j.get("evidence", {}).get("baseline_status", "unknown")
                                            for j in valid if isinstance(j.get("evidence"), dict))),
            "errors": errors,
            "journey_ids": [j.get("id") for j in valid]}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("catalog", type=Path)
    parser.add_argument("--report", type=Path, help="optional JSON report file")
    args = parser.parse_args(argv)
    try:
        data = json.loads(args.catalog.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        result = {"ok": False, "errors": [{"code": "INPUT", "path": str(args.catalog),
                                            "message": str(exc)}]}
        print(json.dumps(result, indent=2))
        return 2
    result = report(data)
    rendered = json.dumps(result, indent=2, allow_nan=False)
    print(rendered)
    if args.report:
        try:
            args.report.write_text(rendered + "\n", encoding="utf-8")
        except OSError as exc:
            print(f"cannot write report: {exc}", file=sys.stderr)
            return 2
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
