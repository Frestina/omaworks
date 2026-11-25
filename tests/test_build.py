import json
import os
import tempfile
import unittest
from unittest import mock

from omaworks import build
from tests.fixtures import CATALOG, NOW, FakeCountSources, issue

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
        data, catalog = build.build(REPO, gh, NOW)
        self.assertIn(("issues", REPO), gh.calls)
        self.assertEqual(data["plugins"]["example.sky-clock"]["4.5.0"]["status"], "broken")
        self.assertEqual(catalog, CATALOG)

    def test_fetches_the_catalog_once(self):
        # Two commits on one row, so the count needs the catalog for the repo.
        gh = FakeGitHub([issue(1, user=1), issue(2, user=2, commit="8be04d2")])
        build.build(REPO, gh, NOW)
        self.assertEqual(gh.calls.count(("catalog",)), 1)

    def test_file_is_json_with_sorted_keys(self):
        data, _ = build.build(REPO, FakeGitHub([issue(1)]), NOW)
        text = build.dumps(data)
        self.assertEqual(json.loads(text), data)
        self.assertTrue(text.isascii())
        self.assertLess(text.index('"generated"'), text.index('"plugins"'))
        files, _ = build.site_files(data, CATALOG)
        self.assertEqual(files["reports.json"], text)
        self.assertIn(
            "1 plugins and 0 repos, 1 rows, 1 reports counted, 9 pages",
            build.summary(data, files),
        )


class WriteSiteTest(unittest.TestCase):
    FILES = {"index.html": "a", "plugins/x/index.html": "b", "reports.json": "{}",
             "catalog-index.json": "{}"}

    def test_writes_every_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = os.path.join(tmp, "_site")
            build.write_site(self.FILES, folder)
            with open(os.path.join(folder, "plugins", "x", "index.html")) as handle:
                self.assertEqual(handle.read(), "b")
            self.assertEqual(os.listdir(tmp), ["_site"])

    def test_replaces_an_earlier_build(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = os.path.join(tmp, "_site")
            build.write_site({**self.FILES, "old.html": "x"}, folder)
            build.write_site(self.FILES, folder)
            self.assertNotIn("old.html", os.listdir(folder))

    def test_never_replaces_a_folder_it_did_not_write(self):
        with tempfile.TemporaryDirectory() as tmp:
            with open(os.path.join(tmp, "notes.txt"), "w") as handle:
                handle.write("mine")
            with self.assertRaises(FileExistsError):
                build.write_site(self.FILES, tmp)
            self.assertEqual(os.listdir(tmp), ["notes.txt"])

    def test_refuses_paths_outside_the_folder_and_writes_nothing(self):
        for path in ("../x.html", "/etc/x", "a/../../x", ".hidden/x", ""):
            with self.subTest(path=path):
                with tempfile.TemporaryDirectory() as tmp:
                    folder = os.path.join(tmp, "_site")
                    with self.assertRaises(ValueError):
                        build.write_site({**self.FILES, path: "x"}, folder)
                    self.assertEqual(os.listdir(tmp), [])


class MainTest(unittest.TestCase):
    def main(self, gh, path):
        env = {"GITHUB_TOKEN": "fake-token", "GITHUB_REPOSITORY": REPO}
        with mock.patch.dict(os.environ, env), mock.patch(
            "omaworks.github.GitHub", return_value=gh
        ), mock.patch("sys.stdout"), mock.patch("sys.stderr"):
            return build.main([path])

    def test_writes_the_site_with_reports_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = os.path.join(tmp, "_site")
            self.assertEqual(self.main(FakeGitHub([issue(1)]), folder), 0)
            with open(os.path.join(folder, "reports.json")) as handle:
                data = json.load(handle)
            names = set(os.listdir(folder))
        self.assertEqual(data["plugins"]["example.sky-clock"]["4.5.0"]["status"], "works")
        self.assertLessEqual(
            {"reports.json", "catalog-index.json", "index.html", "plugins", "versions",
             "style.css", "search.js", "favicon.svg"},
            names,
        )

    def test_outage_writes_nothing_and_exits_non_zero(self):
        for gh in (FakeGitHub([], fail=True),
                   FakeGitHub([issue(1, user=1), issue(2, user=2, commit="8be04d2")],
                              fail=False)):
            with self.subTest(gh=gh):
                if gh.issues:
                    gh.commit = mock.Mock(side_effect=build.SourceError("api down"))
                with tempfile.TemporaryDirectory() as tmp:
                    path = os.path.join(tmp, "_site")
                    self.assertEqual(self.main(gh, path), 1)
                    self.assertEqual(os.listdir(tmp), [])

    def test_data_the_site_refuses_writes_nothing(self):
        gh = FakeGitHub([issue(1)])
        with mock.patch("omaworks.build.render", side_effect=build.SiteError("bad")):
            with tempfile.TemporaryDirectory() as tmp:
                self.assertEqual(self.main(gh, os.path.join(tmp, "_site")), 1)
                self.assertEqual(os.listdir(tmp), [])

    def test_needs_one_path(self):
        with mock.patch("sys.stderr"):
            self.assertEqual(build.main([]), 2)


if __name__ == "__main__":
    unittest.main()
