"""Controlled positive and negative tests for governance invariants."""
import copy
import unittest

from integration.validate_pr import audit, changed_paths, extract_fields, match_scope, valid_path

SHA = "a" * 40
BASE_BODY = ("Task ID: P0-004\nTests: 14 unit tests passing\n"
             "Rollback: close draft and revert task branch\n"
             "Security: read-only checks, no secrets\n"
             "Compatibility: no Android changes\nBase commit: " + SHA)


def fixtures():
    registry = {"tasks": [
        {"id": "P0-001", "role": "00", "state": "DONE", "depends_on": []},
        {"id": "P0-004", "role": "02", "state": "IN_PROGRESS",
         "depends_on": ["P0-001"], "owned_paths": ["integration/**", ".github/**"]},
    ]}
    ownership = {"role_scopes": {"00": ["tasks/**"], "02": ["integration/**", ".github/**"]}}
    opts = dict(head="task/P0-004-integration-governance", title="[P0-004] Integration governance",
                body=BASE_BODY, changed=["integration/validate_pr.py"], draft=True)
    return registry, ownership, opts


class GovernanceTests(unittest.TestCase):
    def check_error(self, substring, mutate):
        registry, ownership, opts = fixtures()
        mutate(registry, ownership, opts)
        errors, _ = audit(registry, ownership, **opts)
        self.assertTrue(any(substring in e for e in errors), errors)

    def test_valid_draft(self):
        a, b, c = fixtures()
        self.assertEqual(audit(a, b, **c), ([], []))

    def test_wrong_branch(self):
        self.check_error("Branch", lambda a, b, c: c.update(head="feature/no-task"))

    def test_wrong_title(self):
        self.check_error("title", lambda a, b, c: c.update(title="Untracked changes"))

    def test_task_field_mismatch(self):
        self.check_error("Task ID", lambda a, b, c: c.update(body=c["body"].replace("P0-004", "P0-002")))

    def test_missing_evidence(self):
        self.check_error("Security", lambda a, b, c: c.update(body=c["body"].replace("Security:", "Missing:")))

    def test_invalid_base_commit(self):
        self.check_error("Base commit", lambda a, b, c: c.update(body=c["body"].replace(SHA, "xyz")))

    def test_foreign_file(self):
        self.check_error("Out-of-scope", lambda a, b, c: c.update(changed=["framework/base.c"]))

    def test_traversal(self):
        self.check_error("Unsafe", lambda a, b, c: c.update(changed=["integration/../tasks/pilot.json"]))

    def test_dependency_draft_warns(self):
        a, b, c = fixtures()
        a["tasks"][0]["state"] = "IN_PROGRESS"
        errs, warns = audit(a, b, **c)
        self.assertEqual(errs, [])
        self.assertTrue(any("Dependency" in w for w in warns))

    def test_dependency_ready_fails(self):
        def mutate(a, b, c):
            a["tasks"][0]["state"] = "TODO"
            a["tasks"][1]["state"] = "IN_REVIEW"
            c["draft"] = False
        self.check_error("Dependency", mutate)

    def test_ready_requires_review_state(self):
        self.check_error("Ready-to-review", lambda a, b, c: c.update(draft=False))

    def test_unknown_task(self):
        self.check_error("Unknown task", lambda a, b, c: c.update(head="task/P0-099-unknown"))

    def test_duplicate_files(self):
        self.check_error("Duplicate", lambda a, b, c: c.update(changed=["integration/a", "integration/a"]))

    def test_scope_boundaries(self):
        self.assertTrue(match_scope("integration/a.py", "integration/**"))
        self.assertFalse(match_scope("integrations/a.py", "integration/**"))
        self.assertFalse(match_scope("integration", "integration/**"))
        self.assertTrue(valid_path(".github/workflows/ci.yml"))
        self.assertFalse(valid_path("/etc/passwd"))
        self.assertFalse(valid_path("integration\\file.py"))

    def test_extract_fields(self):
        self.assertEqual(extract_fields(BASE_BODY)["Task ID"], "P0-004")


if __name__ == "__main__":
    unittest.main()
