import json
import os
import tempfile
import unittest
from unittest import mock

from omaworks import build
from tests.fixtures import NOW, FakeCountSources, issue

REPO = "example-owner/omaworks"


class FakeGitHub(FakeCountSources):
    def __init__(self, issues, **kw):
        super().__init__(**kw)
        self.issues = issues

    def report_issues(self, repo):
        self.calls.append(("issues", repo))
        if self.fail:
            raise build.SourceError("api down")
        return self.issues


class BuildTest(unittest.TestCase):
    def test_counts_the_repos_report_issues(self):
        gh = FakeGitHub([issue(1, result="Broken")])
        data = build.build(REPO, gh, NOW)
        self.assertEqual(gh.calls[0], ("issues", REPO))
        self.assertEqual(data["plugins"]["example.sky-clock"]["4.5.0"]["status"], "broken")

    def test_file_is_json_with_sorted_keys(self):
        data = build.build(REPO, FakeGitHub([issue(1)]), NOW)
        text = build.dumps(data)
        self.assertEqual(json.loads(text), data)
        self.assertTrue(text.isascii())
        self.assertLess(text.index('"generated"'), text.index('"plugins"'))
        self.assertIn("1 plugins and 0 repos, 1 rows, 1 reports counted", build.summary(data))


class MainTest(unittest.TestCase):
    def main(self, gh, path):
        env = {"GITHUB_TOKEN": "fake-token", "GITHUB_REPOSITORY": REPO}
        with mock.patch.dict(os.environ, env), mock.patch(
            "omaworks.github.GitHub", return_value=gh
        ), mock.patch("sys.stdout"), mock.patch("sys.stderr"):
            return build.main([path])

    def test_writes_the_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "_site", "reports.json")
            self.assertEqual(self.main(FakeGitHub([issue(1)]), path), 0)
            with open(path) as handle:
                data = json.load(handle)
            self.assertEqual(os.listdir(os.path.dirname(path)), ["reports.json"])
        self.assertEqual(data["plugins"]["example.sky-clock"]["4.5.0"]["status"], "works")

    def test_outage_writes_nothing_and_exits_non_zero(self):
        for gh in (FakeGitHub([], fail=True),
                   FakeGitHub([issue(1, user=1), issue(2, user=2, commit="8be04d2")],
                              fail=False)):
            with self.subTest(gh=gh):
                if gh.issues:
                    gh.commit = mock.Mock(side_effect=build.SourceError("api down"))
                with tempfile.TemporaryDirectory() as tmp:
                    path = os.path.join(tmp, "_site", "reports.json")
                    self.assertEqual(self.main(gh, path), 1)
                    self.assertFalse(os.path.exists(path))

    def test_needs_one_path(self):
        with mock.patch("sys.stderr"):
            self.assertEqual(build.main([]), 2)


if __name__ == "__main__":
    unittest.main()
