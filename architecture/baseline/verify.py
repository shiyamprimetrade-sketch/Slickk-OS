#!/usr/bin/env python3
"""Verify AOSP tag/manifest pins without implying a successful Android build.

Exit 0: all requested checks passed; 1: mismatch; 2: environment/network error.
Use --remote on a host with Gitiles network access, --manifest after repo sync,
or --checkout on an actual synced AOSP checkout. No third-party packages.
"""
import argparse
import hashlib
import json
import re
import subprocess
import sys
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

HEX40 = re.compile(r"[0-9a-f]{40}\Z")
TAG = re.compile(r"android-[0-9]+\.[0-9]+\.[0-9]+_r[0-9]+\Z")


class InvalidPin(ValueError):
    pass


class Unavailable(RuntimeError):
    pass


def blob_sha(content):
    """Git blob object SHA-1, not the raw file's SHA-1."""
    return hashlib.sha1(b"blob " + str(len(content)).encode() + b"\0" + content).hexdigest()


def validate_pin(pin):
    if pin.get("schema") != 1 or not TAG.fullmatch(pin.get("tag", "")):
        raise InvalidPin("schema or tag invalid")
    if pin.get("android_release") != "17" or pin.get("api_level") != 37:
        raise InvalidPin("release/API mismatch")
    if pin.get("upstream") != "https://android.googlesource.com":
        raise InvalidPin("unexpected upstream")
    entries = [pin.get("manifest", {})] + pin.get("projects", [])
    if len(entries) < 5:
        raise InvalidPin("not enough pinned projects")
    seen_repos, seen_paths = set(), set()
    for item in entries:
        repo = item.get("repository", "")
        if not re.fullmatch(r"[A-Za-z0-9_./-]+", repo) or ".." in repo.split("/") or repo.startswith("/"):
            raise InvalidPin("unsafe repository path")
        if repo in seen_repos:
            raise InvalidPin("duplicate repository: " + repo)
        seen_repos.add(repo)
        for key in ("tag_object", "commit"):
            if not HEX40.fullmatch(item.get(key, "")):
                raise InvalidPin("invalid " + key + " for " + repo)
        if "path" in item:
            path = item["path"]
            if not path or path.startswith("/") or ".." in path.split("/") or path in seen_paths:
                raise InvalidPin("invalid/duplicate checkout path")
            seen_paths.add(path)
    if pin["manifest"]["repository"] != "platform/manifest":
        raise InvalidPin("manifest repository mismatch")
    if not HEX40.fullmatch(pin["manifest"].get("default_xml_blob", "")):
        raise InvalidPin("invalid manifest XML blob")
    if not {"art", "frameworks/base", "build/make", "system/core", "device/google/cuttlefish"}.issubset(seen_paths):
        raise InvalidPin("required baseline project missing")


def check_manifest(data, pin, verify_blob=True):
    if verify_blob and blob_sha(data) != pin["manifest"]["default_xml_blob"]:
        raise InvalidPin("default.xml Git blob hash mismatch")
    root = ET.fromstring(data)
    if root.tag != "manifest":
        raise InvalidPin("default.xml is not a repo manifest")
    default = root.find("default")
    if default is None or default.get("revision") != "refs/tags/" + pin["tag"]:
        raise InvalidPin("manifest default revision is not pinned tag")
    matches = {}
    for element in root.findall("project"):
        path = element.get("path") or element.get("name")
        if path in matches:
            raise InvalidPin("duplicate manifest project path: " + path)
        matches[path] = element
    for item in pin["projects"]:
        element = matches.get(item["path"])
        if element is None or element.get("name") != item["repository"]:
            raise InvalidPin("manifest missing/mismatched: " + item["path"])
        # Project-specific revisions must not silently override the release tag.
        if element.get("revision", "refs/tags/" + pin["tag"]) != "refs/tags/" + pin["tag"]:
            raise InvalidPin("project overrides tag: " + item["path"])
    return len(matches)


def ls_remote(repo_url, tag):
    refs = ("refs/tags/" + tag, "refs/tags/" + tag + "^{}")
    try:
        p = subprocess.run(["git", "ls-remote", repo_url, *refs], capture_output=True,
                           text=True, check=False, timeout=45)
    except (FileNotFoundError, subprocess.TimeoutExpired) as exc:
        raise Unavailable("git/remote unavailable: " + str(exc)) from exc
    if p.returncode:
        raise Unavailable("git ls-remote error for " + repo_url + ": " + p.stderr.strip()[:400])
    actual = {}
    for line in p.stdout.splitlines():
        sha, sep, ref = line.partition("\t")
        if sep and HEX40.fullmatch(sha):
            actual[ref] = sha
    if refs[0] not in actual or refs[1] not in actual:
        raise InvalidPin("missing annotated tag or peeled commit: " + repo_url)
    return actual[refs[0]], actual[refs[1]]


def check_remote(pin):
    base, tag = pin["upstream"], pin["tag"]
    for entry in [pin["manifest"], *pin["projects"]]:
        url = base + "/" + entry["repository"]
        tag_sha, commit = ls_remote(url, tag)
        if tag_sha != entry["tag_object"] or commit != entry["commit"]:
            raise InvalidPin("remote tag/commit drift: " + entry["repository"])
    url = base + "/platform/manifest/+/refs/tags/" + tag + "/default.xml?format=TEXT"
    try:
        with urllib.request.urlopen(url, timeout=40) as response:
            import base64
            data = base64.b64decode(response.read(), validate=True)
    except (OSError, ValueError) as exc:
        raise Unavailable("Gitiles manifest download failed: " + str(exc)) from exc
    return check_manifest(data, pin)


def check_checkout(pin, root):
    for item in pin["projects"]:
        folder = root / item["path"]
        if not folder.is_dir():
            raise InvalidPin("checkout folder missing: " + str(folder))
        try:
            process = subprocess.run(["git", "-C", str(folder), "rev-parse", "HEAD"],
                                     capture_output=True, text=True, timeout=20, check=False)
        except (FileNotFoundError, subprocess.TimeoutExpired) as exc:
            raise Unavailable(str(exc)) from exc
        if process.returncode or process.stdout.strip() != item["commit"]:
            raise InvalidPin("checkout HEAD mismatched: " + item["path"])
    manifest = root / ".repo/manifests/default.xml"
    if manifest.is_file():
        check_manifest(manifest.read_bytes(), pin)
    else:
        raise InvalidPin("missing .repo/manifests/default.xml")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pins", type=Path, default=Path(__file__).with_name("pins.json"))
    parser.add_argument("--manifest", type=Path, help="check downloaded default.xml and its Git blob hash")
    parser.add_argument("--remote", action="store_true", help="check upstream tag objects and manifest live")
    parser.add_argument("--checkout", type=Path, help="check a fully synchronized repo checkout")
    args = parser.parse_args(argv)
    try:
        pin = json.loads(args.pins.read_text(encoding="utf-8"))
        validate_pin(pin)
        result = {"pin_schema": "PASS", "release_tag": pin["tag"]}
        if args.manifest:
            count = check_manifest(args.manifest.read_bytes(), pin)
            result["manifest_project_count"] = count
        if args.remote:
            result["remote_manifest_projects"] = check_remote(pin)
        if args.checkout:
            check_checkout(pin, args.checkout)
            result["checkout"] = "PASS"
        if not (args.manifest or args.remote or args.checkout):
            result["warning"] = "static schema only; no upstream or checkout verified"
        print(json.dumps({"status": "PASS", **result}, sort_keys=True))
        return 0
    except (Unavailable, urllib.error.URLError) as exc:
        print(json.dumps({"status": "UNAVAILABLE", "error": str(exc)}), file=sys.stderr)
        return 2
    except (InvalidPin, ET.ParseError, json.JSONDecodeError, OSError, TypeError, KeyError) as exc:
        print(json.dumps({"status": "FAIL", "error": str(exc)}), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
