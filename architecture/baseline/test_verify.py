#!/usr/bin/env python3
"""Deterministic standard-library tests for P0-002 pin verification."""
import copy
import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import verify

PIN = json.loads(Path(__file__).with_name("pins.json").read_text())


def fixture_xml(tag=PIN["tag"], override=""):
    lines = ['<?xml version="1.0"?><manifest>',
             f'<default remote="aosp" revision="refs/tags/{tag}"/>']
    for item in PIN["projects"]:
        revision = (' revision="other"' if item["path"] == override else '')
        lines.append(f'<project name="{item["repository"]}" path="{item["path"]}"{revision}/>')
    return ("\n".join(lines) + "\n</manifest>").encode()


class VerifyTests(unittest.TestCase):
    def test_pins_are_well_formed(self):
        verify.validate_pin(PIN)

    def test_pin_missing_project_rejected(self):
        bad = copy.deepcopy(PIN)
        bad["projects"].pop()
        with self.assertRaises(verify.InvalidPin):
            verify.validate_pin(bad)

    def test_pin_duplicate_checkout_rejected(self):
        bad = copy.deepcopy(PIN)
        bad["projects"][1]["path"] = bad["projects"][0]["path"]
        with self.assertRaises(verify.InvalidPin):
            verify.validate_pin(bad)

    def test_pin_traversal_rejected(self):
        bad = copy.deepcopy(PIN)
        bad["projects"][0]["path"] = "../external"
        with self.assertRaises(verify.InvalidPin):
            verify.validate_pin(bad)

    def test_git_blob_hash_known_fixture(self):
        # Published Git blob calculation: blob header + content, not raw SHA1.
        self.assertEqual(verify.blob_sha(b"test content\n"),
                         "d670460b4b4aece5915caf5c68d12f560a9fe3e4")

    def test_manifest_valid_fixture(self):
        self.assertEqual(verify.check_manifest(fixture_xml(), PIN, verify_blob=False), 5)

    def test_manifest_wrong_release(self):
        with self.assertRaises(verify.InvalidPin):
            verify.check_manifest(fixture_xml("android-16.0.0_r1"), PIN, verify_blob=False)

    def test_manifest_override_rejected(self):
        with self.assertRaises(verify.InvalidPin):
            verify.check_manifest(fixture_xml(override="art"), PIN, verify_blob=False)

    def test_manifest_hash_rejected(self):
        with self.assertRaises(verify.InvalidPin):
            verify.check_manifest(fixture_xml(), PIN)

    def test_manifest_missing_project(self):
        data = fixture_xml().replace(b'<project name="platform/art" path="art"/>', b'')
        with self.assertRaises(verify.InvalidPin):
            verify.check_manifest(data, PIN, verify_blob=False)

    def test_remote_tag_git_fixture(self):
        with tempfile.TemporaryDirectory() as temp:
            repo = Path(temp) / "fixture"
            repo.mkdir()
            subprocess.run(["git", "init", "-q", str(repo)], check=True)
            (repo / "content").write_text("fixture")
            subprocess.run(["git", "-C", str(repo), "add", "content"], check=True)
            subprocess.run(["git", "-C", str(repo), "-c", "user.name=Fixture",
                            "-c", "user.email=fixture@example.invalid", "commit", "-qm", "base"], check=True)
            subprocess.run(["git", "-C", str(repo), "-c", "user.name=Fixture",
                            "-c", "user.email=fixture@example.invalid", "tag", "-am", "test", PIN["tag"]], check=True)
            actual_tag, actual_commit = verify.ls_remote(str(repo), PIN["tag"])
            self.assertEqual(actual_tag, subprocess.check_output(
                ["git", "-C", str(repo), "rev-parse", PIN["tag"]], text=True).strip())
            self.assertEqual(actual_commit, subprocess.check_output(
                ["git", "-C", str(repo), "rev-parse", "HEAD"], text=True).strip())

    def test_remote_unavailable_exposed(self):
        with mock.patch.object(verify.subprocess, "run", side_effect=FileNotFoundError("git")):
            with self.assertRaises(verify.Unavailable):
                verify.ls_remote("https://example.invalid/repo", PIN["tag"])

    def test_cli_schema_only_has_warning(self):
        self.assertEqual(verify.main(["--pins", str(Path(__file__).with_name("pins.json"))]), 0)

    def test_cli_rejects_corruption(self):
        with tempfile.TemporaryDirectory() as temp:
            file = Path(temp) / "pins.json"
            bad = copy.deepcopy(PIN)
            bad["manifest"]["tag_object"] = "invalid"
            file.write_text(json.dumps(bad))
            self.assertEqual(verify.main(["--pins", str(file)]), 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
