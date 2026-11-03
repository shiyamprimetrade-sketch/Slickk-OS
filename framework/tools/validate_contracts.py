#!/usr/bin/env python3
"""Static Android framework manifest checker. No CTS/runtime compatibility inference."""
import argparse
import json
import re
import sys
from pathlib import Path

HEX = re.compile(r"^[0-9a-f]{40}$")
ID = re.compile(r"^[a-z][a-z0-9_]*$")
BINDER = re.compile(r"^[A-Za-z_$][\w$]*(?:\.[A-Za-z_$][\w$]*)+$")
STATES = {"CREATED", "STARTED", "RESUMED", "PAUSED", "STOPPED", "DESTROYED"}


def validate(doc):
    errors = []

    def check(ok, at, issue):
        if not ok:
            errors.append(f"{at}: {issue}")

    if not isinstance(doc, dict):
        return ["root: expected object"]
    for field in ("schema_version", "baseline", "assumptions", "components"):
        check(field in doc, "root", f"missing {field}")
    check(type(doc.get("schema_version")) is int and doc.get("schema_version") == 1,
          "root", "unsupported schema_version")
    base = doc.get("baseline")
    if not isinstance(base, dict):
        base = {}
        errors.append("baseline: expected object")
    for key in ("tag", "commit", "repository", "android_release", "api_level", "acceptance"):
        check(key in base, "baseline", f"missing {key}")
    check(isinstance(base.get("tag"), str) and base.get("tag", "").startswith("android-"),
          "baseline", "missing AOSP tag")
    check(isinstance(base.get("repository"), str) and base.get("repository", "").startswith("platform/"),
          "baseline", "invalid repository")
    check(isinstance(base.get("commit"), str) and bool(HEX.fullmatch(base.get("commit", ""))),
          "baseline", "invalid source revision")
    api = base.get("api_level")
    check(type(api) is int and 1 <= api <= 1000, "baseline", "invalid API level")
    check(base.get("acceptance") in ("provisional", "accepted"), "baseline", "unsupported acceptance")
    assumptions = doc.get("assumptions")
    if not isinstance(assumptions, list):
        errors.append("assumptions: expected array")
        assumptions = []
    assumption_ids = set()
    for i, a in enumerate(assumptions):
        at = f"assumptions[{i}]"
        if not isinstance(a, dict):
            errors.append(f"{at}: expected object")
            continue
        k = a.get("id")
        check(isinstance(k, str) and bool(ID.fullmatch(k)), at, "invalid id")
        check(k not in assumption_ids, at, "duplicate id")
        assumption_ids.add(k)
        check(a.get("status") in ("verified", "provisional"), at, "unsupported assumption status")
        check(isinstance(a.get("reason"), str) and bool(a.get("reason", "").strip()),
              at, "assumption needs evidence or rationale")
    components = doc.get("components")
    if not isinstance(components, list) or not components:
        errors.append("components: nonempty array required")
        components = []
    ids, dependency_map, descriptors = set(), {}, {}
    for i, c in enumerate(components):
        at = f"components[{i}]"
        if not isinstance(c, dict):
            errors.append(f"{at}: expected object")
            continue
        for field in ("id", "kind", "criticality", "api", "source", "permissions",
                      "dependencies", "interfaces", "verification"):
            check(field in c, at, f"missing {field}")
        name = c.get("id")
        valid_name = isinstance(name, str) and bool(ID.fullmatch(name))
        check(valid_name, at, "invalid component id")
        if valid_name:
            check(name not in ids, at, "duplicate component id")
            ids.add(name)
        check(c.get("kind") in ("bootstrap", "service", "app_process", "sdk_api"),
              at, "unsupported component kind")
        check(c.get("criticality") in ("mandatory", "optional", "unknown"), at, "missing criticality")
        a = c.get("api")
        if not isinstance(a, dict):
            errors.append(f"{at}: invalid API contract")
        else:
            lo, hi = a.get("min"), a.get("max")
            check(type(lo) is int and type(hi) is int and 1 <= lo <= hi
                  and type(api) is int and hi <= api, at, "unsupported API range")
            check(a.get("surface") in ("sdk", "system", "internal"), at, "invalid API surface")
        source = c.get("source")
        if not isinstance(source, dict):
            errors.append(f"{at}: missing source")
        else:
            path = source.get("path")
            check(source.get("commit") == base.get("commit")
                  and source.get("repository") == base.get("repository"), at, "source pin mismatch")
            check(isinstance(path, str) and bool(path) and not path.startswith("/")
                  and ".." not in Path(path).parts and path.endswith((".java", ".aidl", ".kt"))
                  if isinstance(path, str) else False, at, "invalid upstream source path")
            check(source.get("inspection") in ("provisional_path", "inspected_at_pin"),
                  at, "unsupported source inspection")
        p = c.get("permissions")
        if not isinstance(p, dict):
            errors.append(f"{at}: incomplete permission requirements")
            p = {}
        mode, guards = p.get("enforcement"), p.get("guards")
        check(mode in ("unknown", "method_specific", "not_applicable"),
              at, "incomplete permission requirements")
        check(isinstance(guards, list) and all(isinstance(g, str) and bool(g.strip())
              for g in guards), at, "invalid permission guards")
        if mode == "unknown":
            check(isinstance(p.get("reason"), str) and bool(p.get("reason", "").strip()),
                  at, "unknown permission policy needs reason")
        if mode == "method_specific":
            check(isinstance(guards, list) and bool(guards),
                  at, "method-specific permission needs guard")
        if c.get("kind") == "service":
            check(mode != "not_applicable", at, "service requires permission assessment")
        entries = c.get("interfaces")
        if not isinstance(entries, list):
            errors.append(f"{at}: missing interface declarations")
            entries = []
        local_names = set()
        for j, x in enumerate(entries):
            loc = f"{at}.interfaces[{j}]"
            if not isinstance(x, dict):
                errors.append(f"{loc}: expected object")
                continue
            for field in ("name", "kind", "descriptor", "status", "permission"):
                check(field in x, loc, f"missing {field}")
            label, desc = x.get("name"), x.get("descriptor")
            check(isinstance(label, str) and bool(label.strip()), loc, "invalid interface name")
            check(label not in local_names, loc, "duplicate interface name")
            local_names.add(label)
            check(x.get("kind") in ("aidl", "sdk", "internal"), loc, "invalid interface kind")
            check(x.get("status") in ("verified", "provisional", "unknown"), loc,
                  "unsupported interface status")
            check(desc is None or (isinstance(desc, str) and bool(BINDER.fullmatch(desc))),
                  loc, "malformed Binder descriptor")
            if x.get("kind") == "aidl" and x.get("status") == "verified":
                check(bool(desc), loc, "verified AIDL needs descriptor")
            if x.get("kind") != "aidl":
                check(desc is None, loc, "non-AIDL cannot declare Binder descriptor")
            check(x.get("permission") in ("unknown", "guarded", "not_applicable"), loc,
                  "incomplete interface permission")
            if x.get("permission") == "guarded":
                check(mode == "method_specific", loc, "requires documented guard")
            if isinstance(desc, str) and desc:
                signature = (name, label, x.get("permission"))
                check(desc not in descriptors or descriptors[desc] == signature,
                      loc, "conflicting Binder descriptor")
                descriptors[desc] = signature
        deps = c.get("dependencies")
        if not isinstance(deps, list) or not all(isinstance(x, str) for x in deps):
            errors.append(f"{at}: invalid dependencies")
            deps = []
        check(len(deps) == len(set(deps)), at, "duplicate dependency")
        if valid_name:
            dependency_map[name] = deps
        methods = c.get("verification")
        check(isinstance(methods, list) and bool(methods)
              and all(isinstance(m, str) and bool(m.strip()) for m in methods),
              at, "verification methods required")
        if "lifecycle" in c:
            life = c["lifecycle"]
            if not isinstance(life, dict):
                errors.append(f"{at}: invalid lifecycle")
                continue
            states, edges = life.get("states"), life.get("transitions")
            if not isinstance(states, list) or not states or any(not isinstance(s, str)
                 or s not in STATES for s in states) or len(states) != len(set(map(str, states))):
                errors.append(f"{at}: invalid lifecycle states")
                states = []
            if not isinstance(edges, list):
                errors.append(f"{at}: invalid lifecycle transitions")
                edges = []
            accepted = []
            for edge in edges:
                if not isinstance(edge, list) or len(edge) != 2 or edge[0] not in states \
                   or edge[1] not in states or edge[0] == "DESTROYED":
                    errors.append(f"{at}: illegal lifecycle edge")
                else:
                    accepted.append(tuple(edge))
            check(len(accepted) == len(set(accepted)), at, "duplicate lifecycle edge")
            reach = {"CREATED"}
            for _ in states:
                reach.update(b for a, b in accepted if a in reach)
            check("CREATED" in states and "DESTROYED" in states and set(states) == reach,
                  at, "unreachable lifecycle state")
            check(isinstance(life.get("invariants"), list) and bool(life["invariants"]),
                  at, "missing lifecycle invariants")
    for owner, deps in dependency_map.items():
        for dep in deps:
            check(dep in ids, owner, "unknown dependency")
            check(dep != owner, owner, "self-dependency")
    visited, active = set(), set()
    def walk(node):
        if node in active:
            errors.append(f"{node}: dependency cycle")
            return
        if node in visited:
            return
        active.add(node)
        for dep in dependency_map.get(node, []):
            if dep in dependency_map:
                walk(dep)
        active.remove(node)
        visited.add(node)
    for node in dependency_map:
        walk(node)
    return errors


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    args = parser.parse_args(argv)
    try:
        doc = json.loads(args.manifest.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as err:
        print(f"FAIL: malformed/unreadable JSON: {err}", file=sys.stderr)
        return 2
    errors = validate(doc)
    for err in errors:
        print("FAIL:", err, file=sys.stderr)
    if errors:
        return 1
    print(f"PASS: {len(doc['components'])} structural contracts; NOT Android runtime compatibility proof")
    return 0


if __name__ == "__main__":
    sys.exit(main())
