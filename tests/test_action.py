import json
import os
import subprocess
import tempfile
import unittest
from unittest import mock

from omaworks import action
from omaworks.check import MARKER, PASS_COMMENT
from tests.fixtures import HOSTILE, FakeSources, body

REPO = "example-owner/omaworks"
BOT = {"login": "github-actions[bot]", "type": "Bot"}


class FakeGitHub(FakeSources):
    """GitHub for one issue, in memory. Records every write."""

    def __init__(self, text, labels=("report",), state="open", comments=(), **kw):
        super().__init__(**kw)
        self.issue = {
            "number": 7,
            "state": state,
            "body": text,
            "labels": [{"name": n} for n in labels],
        }
        self.comment_list = [dict(c) for c in comments]
        self.writes = []
        self.created_labels = []

    def label_names(self):
        return [item["name"] for item in self.issue["labels"]]

    def get_issue(self, repo, number):
        assert (repo, number) == (REPO, 7)
        return json.loads(json.dumps(self.issue))

    def comments(self, repo, number):
        return [dict(c) for c in self.comment_list]

    def create_comment(self, repo, number, text):
        self.writes.append(("create_comment",))
        self.comment_list.append({"id": 100 + len(self.comment_list), "user": BOT, "body": text})

    def edit_comment(self, repo, comment_id, text):
        self.writes.append(("edit_comment", comment_id))
        for comment in self.comment_list:
            if comment["id"] == comment_id:
                comment["body"] = text

    def ensure_label(self, repo, item):
        self.created_labels.append(item)

    def add_labels(self, repo, number, names):
        self.writes.append(("add_labels", tuple(names)))
        self.issue["labels"] += [{"name": n} for n in names]

    def remove_label(self, repo, number, name):
        self.writes.append(("remove_label", name))
        self.issue["labels"] = [i for i in self.issue["labels"] if i["name"] != name]


EVENT = {"repository": {"full_name": REPO}, "issue": {"number": 7, "body": "stale"}}


class RunTest(unittest.TestCase):
    def test_good_report_is_labelled_without_a_comment(self):
        gh = FakeGitHub(body())
        action.run(EVENT, gh)
        self.assertEqual(
            gh.label_names(),
            ["report", "plugin:example.sky-clock", "omarchy:4.5.0", "result:works"],
        )
        self.assertEqual(gh.comment_list, [])
        self.assertEqual([i.name for i in gh.created_labels], gh.label_names()[1:])

    def test_bad_report_gets_needs_fix_and_one_comment(self):
        gh = FakeGitHub(body(commit="nope"))
        action.run(EVENT, gh)
        self.assertEqual(gh.label_names(), ["report", "needs-fix"])
        self.assertEqual(len(gh.comment_list), 1)
        self.assertTrue(gh.comment_list[0]["body"].startswith(MARKER))
        self.assertIn("**Plugin commit**", gh.comment_list[0]["body"])

    def test_the_issue_is_fetched_not_taken_from_the_event(self):
        gh = FakeGitHub(body())
        action.run(EVENT, gh)
        self.assertIn("result:works", gh.label_names())

    def test_later_edits_edit_the_comment_never_add_one(self):
        gh = FakeGitHub(body(commit="nope"))
        action.run(EVENT, gh)
        gh.issue["body"] = body(commit="nope", result="Meh")
        action.run(EVENT, gh)
        self.assertEqual(len(gh.comment_list), 1)
        self.assertIn("**Result**", gh.comment_list[0]["body"])
        self.assertEqual([w for w in gh.writes if w[0] == "create_comment"], [("create_comment",)])

    def test_same_problems_again_writes_nothing(self):
        gh = FakeGitHub(body(commit="nope"))
        action.run(EVENT, gh)
        gh.writes.clear()
        action.run(EVENT, gh)
        self.assertEqual(gh.writes, [])

    def test_fixed_report_loses_needs_fix_and_the_comment_says_so(self):
        gh = FakeGitHub(body(commit="nope"))
        action.run(EVENT, gh)
        gh.issue["body"] = body()
        action.run(EVENT, gh)
        self.assertNotIn("needs-fix", gh.label_names())
        self.assertIn("plugin:example.sky-clock", gh.label_names())
        self.assertEqual(len(gh.comment_list), 1)
        self.assertEqual(gh.comment_list[0]["body"], PASS_COMMENT)

    def test_edit_that_changes_fields_swaps_labels(self):
        gh = FakeGitHub(body())
        action.run(EVENT, gh)
        gh.issue["body"] = body(plugin="example.moon-phase", omarchy="4.5.0rc2-1", result="Broken")
        action.run(EVENT, gh)
        self.assertEqual(
            sorted(gh.label_names()),
            ["omarchy:4.5.0-rc2", "plugin:example.moon-phase", "report", "result:broken"],
        )

    def test_edit_that_breaks_a_good_report_takes_its_labels_off(self):
        gh = FakeGitHub(body())
        action.run(EVENT, gh)
        gh.issue["body"] = body(omarchy="soon")
        action.run(EVENT, gh)
        self.assertEqual(gh.label_names(), ["report", "needs-fix"])

    def test_other_labels_stay(self):
        labels = ("report", "spam", "test", "needs-look", "from-issue")
        for text in (body(), body(commit="nope")):
            gh = FakeGitHub(text, labels=labels)
            action.run(EVENT, gh)
            for name in labels:
                self.assertIn(name, gh.label_names())
            self.assertFalse(any(w == ("remove_label", n) for w in gh.writes for n in labels))

    def test_only_the_bots_marked_comment_is_edited(self):
        others = [
            {"id": 1, "user": {"login": "someone", "type": "User"}, "body": MARKER + "\nfake"},
            {"id": 2, "user": BOT, "body": "a bot comment without the marker"},
            {"id": 3, "user": {"login": "github-actions[bot]", "type": "User"}, "body": MARKER},
        ]
        gh = FakeGitHub(body(commit="nope"), comments=others)
        action.run(EVENT, gh)
        self.assertEqual(len(gh.comment_list), 4)
        self.assertEqual([c["body"] for c in gh.comment_list[:3]], [c["body"] for c in others])

    def test_existing_bot_comment_is_found(self):
        mine = {"id": 9, "user": BOT, "body": MARKER + "\nold"}
        gh = FakeGitHub(body(commit="nope"), comments=[mine])
        action.run(EVENT, gh)
        self.assertEqual(len(gh.comment_list), 1)
        self.assertIn(("edit_comment", 9), gh.writes)

    def test_skips_closed_issues_pull_requests_and_non_reports(self):
        cases = [
            FakeGitHub(body(commit="nope"), state="closed"),
            FakeGitHub(body(commit="nope"), labels=("question",)),
        ]
        pr = FakeGitHub(body(commit="nope"))
        pr.issue["pull_request"] = {"url": "x"}
        cases.append(pr)
        for gh in cases:
            self.assertTrue(action.run(EVENT, gh).startswith("skipped"))
            self.assertEqual(gh.writes, [])

    def test_outage_changes_nothing(self):
        gh = FakeGitHub(body(), labels=("report", "plugin:example.sky-clock"), fail=True)
        with self.assertRaises(action.SourceError):
            action.run(EVENT, gh)
        self.assertEqual(gh.writes, [])

    def test_hostile_body_runs_nothing(self):
        gh = FakeGitHub(body(**HOSTILE))
        boom = AssertionError("a subprocess was started")
        with mock.patch.object(subprocess, "Popen", side_effect=boom), mock.patch.object(
            os, "system", side_effect=boom
        ), mock.patch("builtins.eval", side_effect=boom), mock.patch(
            "builtins.exec", side_effect=boom
        ):
            action.run(EVENT, gh)
        self.assertEqual(gh.label_names(), ["report", "needs-fix"])
        text = gh.comment_list[0]["body"]
        for piece in ("@octo-team", "<img", "$(rm", "<script>", "@someone", "#99"):
            self.assertNotIn(piece, text)


class MainTest(unittest.TestCase):
    def test_outage_exits_non_zero(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "event.json")
            with open(path, "w") as handle:
                json.dump(EVENT, handle)
            gh = FakeGitHub(body(), fail=True)
            env = {"GITHUB_EVENT_PATH": path, "GITHUB_TOKEN": "fake-token"}
            with mock.patch.dict(os.environ, env), mock.patch(
                "omaworks.github.GitHub", return_value=gh
            ), mock.patch("sys.stderr"):
                self.assertEqual(action.main(), 1)
        self.assertEqual(gh.writes, [])


if __name__ == "__main__":
    unittest.main()
