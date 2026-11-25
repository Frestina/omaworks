import json
import os
import re
import subprocess
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest import mock

from omaworks.check import SourceError
from omaworks.count import STATUSES, count, read_report, status_of
from tests.fixtures import (
    HOSTILE,
    NEW,
    NOW,
    OLD,
    FakeCountSources,
    body,
    issue,
    source_line,
)

SPEC = Path(__file__).resolve().parent.parent / "SPEC.md"
LATER = datetime(2026, 11, 21, 9, 30, tzinfo=timezone.utc)


def run(issues, sources=None):
    return count(issues, sources or FakeCountSources(), NOW)


def row(issues, plugin="example.sky-clock", release="4.5.0", sources=None):
    return run(issues, sources)["plugins"][plugin][release]


def counted(r):
    return [entry["issue"] for entry in r["reports"] if entry["counted"]]


def why(r):
    return {entry["issue"]: entry.get("why") for entry in r["reports"]}


def results(*names, commit="3f2a91c"):
    """One report per account with these results, on one commit."""
    return [issue(n + 1, user=n + 1, result=name, commit=commit) for n, name in enumerate(names)]


class StatusTest(unittest.TestCase):
    """The spec's examples and the 60% rule."""

    def test_three_broken_one_works_is_broken(self):
        r = row(results("Broken", "Broken", "Broken", "Works"))
        self.assertEqual(r["status"], "broken")
        self.assertEqual(r["counts"], {"works": 1, "problems": 0, "broken": 3})

    def test_two_works_two_broken_is_mixed(self):
        r = row(results("Works", "Broken", "Works", "Broken"))
        self.assertEqual(r["status"], "mixed")
        self.assertEqual(r["counts"], {"works": 2, "problems": 0, "broken": 2})

    def test_one_report_decides_alone(self):
        for name, status in (("Works", "works"), ("Works with problems", "problems"),
                             ("Broken", "broken")):
            with self.subTest(name=name):
                r = row(results(name))
                self.assertEqual(r["status"], status)
                self.assertEqual(sum(r["counts"].values()), 1)

    def test_sixty_percent_is_enough(self):
        r = row(results("Works", "Broken", "Works", "Broken", "Works"))
        self.assertEqual(r["status"], "works")

    def test_below_sixty_percent_is_mixed(self):
        r = row(results("Works", "Works with problems", "Broken", "Works"))
        self.assertEqual(r["status"], "mixed")
        self.assertEqual(status_of({"works": 59, "problems": 41, "broken": 0}), "mixed")
        self.assertEqual(status_of({"works": 60, "problems": 40, "broken": 0}), "works")

    def test_no_reports_is_none_never_works(self):
        self.assertEqual(status_of({"works": 0, "problems": 0, "broken": 0}), "none")

    def test_no_reports_means_no_row(self):
        data = run([])
        self.assertEqual(data["plugins"], {})
        self.assertEqual(data["repos"], {})
        data = run(results("Broken"))
        self.assertNotIn("example.moon-phase", data["plugins"])
        self.assertNotIn("4.0.3", data["plugins"]["example.sky-clock"])


class OnePerAccountTest(unittest.TestCase):
    def test_the_accounts_newest_report_counts(self):
        r = row([
            issue(5, user=1, result="Broken"),
            issue(9, user=1, result="Works"),
            issue(7, user=2, result="Works"),
        ])
        self.assertEqual(r["counts"], {"works": 2, "problems": 0, "broken": 0})
        self.assertEqual(counted(r), [7, 9])
        self.assertEqual(why(r)[5], "newer-report")

    def test_account_is_its_id_not_its_login(self):
        renamed = issue(9, user=1, result="Works")
        renamed["user"]["login"] = "a-new-name"
        r = row([issue(5, user=1, result="Broken"), renamed])
        self.assertEqual(counted(r), [9])

    def test_each_omarchy_version_has_its_own_newest(self):
        data = run([
            issue(5, user=1, result="Broken", omarchy="4.0.3-1"),
            issue(9, user=1, result="Works", omarchy="4.5.0-3"),
        ])
        rows = data["plugins"]["example.sky-clock"]
        self.assertEqual(rows["4.0.3"]["status"], "broken")
        self.assertEqual(rows["4.5.0"]["status"], "works")

    def test_a_report_without_an_account_does_not_count(self):
        ghost = issue(5)
        del ghost["user"]
        self.assertEqual(run([ghost])["plugins"], {})


class SeededTest(unittest.TestCase):
    def seeded(self, number, source, **kw):
        what = source_line(source) if isinstance(source, int) else source
        return issue(number, user=9, extra=("from-issue",), what=what, **kw)

    def test_seeded_reports_count_once_per_source_issue(self):
        r = row([
            self.seeded(1, 10888, result="Broken"),
            self.seeded(2, 10929, result="Broken"),
            self.seeded(3, 10888, result="Broken"),
            issue(4, user=9, result="Works"),  # the owner's own report
        ])
        self.assertEqual(counted(r), [2, 3, 4])
        self.assertEqual(why(r)[1], "newer-report")
        self.assertEqual(r["counts"], {"works": 1, "problems": 0, "broken": 2})
        self.assertEqual([e.get("fromIssue") for e in r["reports"]], [10888, 10929, 10888, None])

    def test_seeded_report_without_one_source_does_not_count(self):
        both = source_line(10888) + " " + source_line(10929)
        for what in ("The clock is gone.", both, "https://github.com/someone/else/issues/12"):
            with self.subTest(what=what):
                data = run([self.seeded(1, what, result="Broken"), issue(2, result="Works")])
                r = data["plugins"]["example.sky-clock"]["4.5.0"]
                self.assertEqual(counted(r), [2])
                self.assertEqual(why(r)[1], "no-source")
                self.assertNotIn("fromIssue", r["reports"][0])

    def test_a_row_where_nothing_counts_is_none_and_lists_its_reports(self):
        r = row([self.seeded(1, "The clock is gone.", result="Works")])
        self.assertEqual(r["status"], "none")
        self.assertEqual(r["counts"], {"works": 0, "problems": 0, "broken": 0})
        self.assertEqual(why(r), {1: "no-source"})

    def test_the_same_link_twice_is_one_source(self):
        r = row([self.seeded(1, source_line(10888) + "\n" + source_line(10888))])
        self.assertEqual(counted(r), [1])
        self.assertEqual(r["reports"][0]["fromIssue"], 10888)

    def test_source_link_in_backticks_is_found(self):
        # Seeded reports put the link in a code span, so the Omarchy issue
        # gets no back-link. See SPEC.md, "Seeding".
        what = "The clock is gone.\n\nSource: `https://github.com/omacom/omarchy/issues/10888`"
        r = row([self.seeded(1, what, result="Broken")])
        self.assertEqual(counted(r), [1])
        self.assertEqual(r["reports"][0]["fromIssue"], 10888)

    def test_source_is_read_only_from_what_happens(self):
        text = body(what="The clock is gone.", errors=source_line(10888))
        r = row([issue(1, user=9, extra=("from-issue",), text=text)])
        self.assertEqual(why(r)[1], "no-source")

    def test_source_link_without_from_issue_label_is_an_ordinary_report(self):
        r = row([issue(1, user=9, what=source_line(10888)), issue(2, user=9, what=source_line(10929))])
        self.assertEqual(counted(r), [2])
        self.assertNotIn("fromIssue", r["reports"][1])


class NewestCommitTest(unittest.TestCase):
    def test_newer_commits_works_replaces_older_broken(self):
        r = row([
            issue(1, user=1, commit="3f2a91c", result="Broken"),
            issue(2, user=2, commit="3f2a91c", result="Broken"),
            issue(3, user=3, commit="3f2a91c", result="Broken"),
            issue(4, user=4, commit="8be04d2", result="Works"),
        ])
        self.assertEqual(r["status"], "works")
        self.assertEqual(r["counts"], {"works": 1, "problems": 0, "broken": 0})
        self.assertEqual(r["fixedFrom"], "8be04d2")
        self.assertEqual(counted(r), [4])
        self.assertEqual(why(r), {1: "older-commit", 2: "older-commit", 3: "older-commit", 4: None})

    def test_newest_is_by_commit_date_not_by_report(self):
        r = row([
            issue(1, user=1, commit="8be04d2", result="Broken"),
            issue(2, user=2, commit="3f2a91c", result="Works"),
        ])
        self.assertEqual(r["status"], "broken")
        self.assertEqual(counted(r), [1])
        self.assertNotIn("fixedFrom", r)

    def test_fixed_from_needs_broken_before_and_works_now(self):
        cases = [
            (("Works with problems", "Works"), None),
            (("Broken", "Works with problems"), None),
            (("Broken", "Works"), "8be04d2"),
        ]
        for (old, new), fixed in cases:
            with self.subTest(old=old, new=new):
                r = row([
                    issue(1, user=1, commit="3f2a91c", result=old),
                    issue(2, user=2, commit="8be04d2", result=new),
                ])
                self.assertEqual(r.get("fixedFrom"), fixed)

    def test_fixed_from_counts_a_reporters_own_older_broken(self):
        r = row([
            issue(1, user=1, commit="3f2a91c", result="Broken"),
            issue(2, user=1, commit="8be04d2", result="Works"),
        ])
        self.assertEqual(why(r)[1], "newer-report")
        self.assertEqual(r["fixedFrom"], "8be04d2")

    def test_fixed_from_is_the_shortest_spelling(self):
        r = row([
            issue(1, user=1, commit="3f2a91c", result="Broken"),
            issue(2, user=2, commit=NEW, result="Works"),
            issue(3, user=3, commit="8be04d2b", result="Works"),
        ])
        self.assertEqual(r["fixedFrom"], "8be04d2b")

    def test_short_and_long_spellings_are_one_commit(self):
        r = row([
            issue(1, user=1, commit="3f2a91c", result="Broken"),
            issue(2, user=2, commit=OLD.upper(), result="Broken"),
        ])
        self.assertEqual(counted(r), [1, 2])
        self.assertEqual(r["reports"][1]["commit"], OLD)

    def test_one_commit_needs_no_lookup(self):
        sources = FakeCountSources()
        row(results("Broken", "Works"), sources=sources)
        self.assertEqual(sources.calls, [])

    def test_each_commit_is_looked_up_once(self):
        sources = FakeCountSources()
        run([
            issue(1, user=1, commit="3f2a91c"),
            issue(2, user=2, commit="8be04d2"),
            issue(3, user=3, commit="8be04d2", omarchy="4.5.0rc2-1"),
            issue(4, user=4, commit="3f2a91c", omarchy="4.5.0rc2-1"),
        ], sources)
        lookups = [call for call in sources.calls if call[0] == "commit"]
        self.assertEqual(sorted(lookups), [
            ("commit", "example-dev/sky-clock", "3f2a91c"),
            ("commit", "example-dev/sky-clock", "8be04d2"),
        ])
        self.assertEqual(sources.calls.count(("catalog",)), 1)

    def test_commit_not_in_the_repo_does_not_count(self):
        r = row([
            issue(1, user=1, commit="3f2a91c", result="Works"),
            issue(2, user=2, commit="fffffff", result="Broken"),
        ])
        self.assertEqual(r["status"], "works")
        self.assertEqual(why(r)[2], "commit-not-found")
        self.assertNotIn("unordered", r)

    def test_no_commit_found_counts_all_and_says_so(self):
        catalog = [{"id": "example.sky-clock", "repo": "https://example.invalid/sky-clock"}]
        sources = FakeCountSources(catalog=catalog)
        r = row([
            issue(1, user=1, commit="3f2a91c", result="Broken"),
            issue(2, user=2, commit="8be04d2", result="Works"),
        ], sources=sources)
        self.assertEqual(r["status"], "mixed")
        self.assertTrue(r["unordered"])
        self.assertEqual(counted(r), [1, 2])
        self.assertFalse([c for c in sources.calls if c[0] == "commit"])

    def test_commits_with_the_same_date_count_together(self):
        commits = {"example-dev/sky-clock": {OLD: LATER, NEW: LATER}}
        r = row([
            issue(1, user=1, commit="3f2a91c", result="Works"),
            issue(2, user=2, commit="8be04d2", result="Works"),
        ], sources=FakeCountSources(commits=commits))
        self.assertEqual(counted(r), [1, 2])
        self.assertNotIn("fixedFrom", r)

    def test_outage_stops_the_count(self):
        with self.assertRaises(SourceError):
            run([issue(1, user=1, commit="3f2a91c"), issue(2, user=2, commit="8be04d2")],
                FakeCountSources(fail=True))


class WhichReportsCountTest(unittest.TestCase):
    def test_a_good_report_counts(self):
        self.assertIsNotNone(read_report(issue(1), FakeCountSources()))

    def test_closed_reports_do_not_count(self):
        # Closed as spam, as test, or by the reporter to withdraw it.
        for extra in (("spam",), ("test",), ()):
            with self.subTest(extra=extra):
                self.assertIsNone(read_report(issue(1, state="closed", extra=extra),
                                              FakeCountSources()))

    def test_open_spam_or_test_does_not_count(self):
        for extra in (("spam",), ("Test",)):
            with self.subTest(extra=extra):
                self.assertIsNone(read_report(issue(1, extra=extra), FakeCountSources()))

    def test_pull_requests_and_non_reports_do_not_count(self):
        pr = issue(1)
        pr["pull_request"] = {"url": "x"}
        unlabelled = issue(2)
        unlabelled["labels"] = unlabelled["labels"][1:]
        for item in (pr, unlabelled, None, "text", {"number": "3", "state": "open"}):
            with self.subTest(item=item):
                self.assertIsNone(read_report(item, FakeCountSources()))

    def test_needs_fix_does_not_count(self):
        self.assertIsNone(read_report(issue(1, commit="nope"), FakeCountSources()))
        with_old_labels = issue(1, extra=("needs-fix",))
        self.assertIsNone(read_report(with_old_labels, FakeCountSources()))

    def test_not_yet_checked_does_not_count(self):
        self.assertIsNone(read_report(issue(1, labels=()), FakeCountSources()))

    def test_edited_into_failing_stops_counting_at_once(self):
        labels = ["plugin:example.sky-clock", "omarchy:4.5.0", "result:works"]
        edits = [
            {"commit": "nope"},
            {"result": "Maybe"},
            {"omarchy": "4.0.0.r7195.g3ac4365-1"},
            {"plugin": "example.unknown"},
            {"omarchy": "4.0.3-1"},
            {"result": "Broken"},
        ]
        for edit in edits:
            with self.subTest(edit=edit):
                stale = issue(1, labels=labels, **edit)
                self.assertIsNone(read_report(stale, FakeCountSources()))

    def test_edited_to_another_commit_counts_the_new_commit(self):
        labels = ["plugin:example.sky-clock", "omarchy:4.5.0", "result:works"]
        report = read_report(issue(1, labels=labels, commit="8be04d2"), FakeCountSources())
        self.assertEqual(report.commit, "8be04d2")

    def test_a_stale_extra_check_label_does_not_count(self):
        self.assertIsNone(read_report(issue(1, extra=("result:broken",)), FakeCountSources()))

    def test_other_labels_do_not_matter(self):
        self.assertIsNotNone(read_report(issue(1, extra=("needs-look", "good first")),
                                         FakeCountSources()))

    def test_label_case_does_not_matter(self):
        item = issue(1)
        for label in item["labels"]:
            label["name"] = label["name"].upper()
        self.assertIsNotNone(read_report(item, FakeCountSources()))

    def test_the_check_needs_no_network_here(self):
        sources = FakeCountSources(fail=True)
        self.assertIsNotNone(read_report(issue(1), sources))
        self.assertEqual(sources.calls, [])


class RowsTest(unittest.TestCase):
    def test_package_revisions_share_a_row_and_keep_their_version(self):
        r = row([issue(1, user=1, omarchy="4.5.0-1"), issue(2, user=2, omarchy="4.5.0-3")])
        self.assertEqual([e["version"] for e in r["reports"]], ["4.5.0-1", "4.5.0-3"])
        self.assertEqual(r["counts"]["works"], 2)

    def test_release_candidates_get_their_own_row(self):
        data = run([
            issue(1, user=1, omarchy="4.5.0rc2-1", result="Broken"),
            issue(2, user=1, omarchy="4.5.0-3", result="Works"),
        ])
        rows = data["plugins"]["example.sky-clock"]
        self.assertEqual(sorted(rows), ["4.5.0", "4.5.0-rc2"])
        self.assertEqual(rows["4.5.0-rc2"]["status"], "broken")
        self.assertEqual(rows["4.5.0-rc2"]["reports"][0]["version"], "4.5.0rc2-1")

    def test_repo_url_plugins_are_kept_apart(self):
        data = run([issue(1, plugin="https://github.com/Example-Dev/weather-strip")])
        self.assertEqual(data["plugins"], {})
        self.assertEqual(data["repos"]["example-dev/weather-strip"]["4.5.0"]["status"], "works")

    def test_renamed_repo_counts_under_its_new_name(self):
        labels = ["repo:example-dev/weather-strip", "omarchy:4.5.0", "result:works"]
        item = issue(1, labels=labels, plugin="https://github.com/example-dev/old-strip")
        sources = FakeCountSources(repos={"example-dev/old-strip": "example-dev/weather-strip"})
        data = run([item], sources)
        self.assertIn("example-dev/weather-strip", data["repos"])
        self.assertIn(("repo", "example-dev", "old-strip"), sources.calls)

    def test_repo_url_commits_are_looked_up_in_that_repo(self):
        url = "https://github.com/example-dev/weather-strip"
        commits = {"example-dev/weather-strip": {OLD: LATER}}
        r = run([
            issue(1, user=1, plugin=url, commit="3f2a91c"),
            issue(2, user=2, plugin=url, commit="8be04d2"),
        ], FakeCountSources(commits=commits))["repos"]["example-dev/weather-strip"]["4.5.0"]
        self.assertEqual(counted(r), [1])
        self.assertEqual(why(r)[2], "commit-not-found")


class FileTest(unittest.TestCase):
    def test_generated_is_utc(self):
        self.assertEqual(run([])["generated"], "2026-12-01T10:00:00Z")

    def test_every_status_links_to_its_reports(self):
        data = run([
            issue(1, user=1, commit="3f2a91c", result="Broken"),
            issue(2, user=2, commit="8be04d2", result="Works"),
            issue(3, user=2, omarchy="4.5.0rc2-1", result="Broken"),
            issue(4, user=3, plugin="https://github.com/example-dev/weather-strip"),
        ])
        for group in ("plugins", "repos"):
            for rows in data[group].values():
                for r in rows.values():
                    self.assertIn(r["status"], STATUSES)
                    self.assertNotEqual(r["status"], "none")
                    self.assertEqual(sorted(r["counts"]), ["broken", "problems", "works"])
                    self.assertEqual(len(counted(r)), sum(r["counts"].values()))
                    self.assertGreater(len(counted(r)), 0)

    def test_spec_example_is_what_the_count_gives(self):
        text = SPEC.read_text()
        section = text[text.index("### reports.json"):]
        example = json.loads(re.search(r"```json\n(.*?)```", section, re.S).group(1))
        issues = [
            issue(101, user=1, omarchy="4.5.0-1", commit="3f2a91c", result="Broken"),
            issue(104, user=9, extra=("from-issue",), what=source_line(17794),
                  commit="3f2a91c", result="Broken"),
            issue(107, user=3, commit="3f2a91c", result="Broken"),
            issue(112, user=4, commit="8be04d2", result="Works"),
            issue(115, user=3, commit="8be04d2", result="Works"),
            issue(120, user=5, omarchy="4.5.0rc2-1", commit="3f2a91c", result="Broken"),
            issue(123, user=6, plugin="https://github.com/example-dev/weather-strip",
                  commit="5c0ffee", result="Works with problems"),
        ]
        self.assertEqual(run(issues), example)

    def test_no_report_text_reaches_the_file(self):
        hostile = dict(HOSTILE, plugin="example.sky-clock", omarchy="4.5.0-3",
                       commit="3f2a91c", result="Works")
        item = issue(1, **hostile)
        boom = AssertionError("a subprocess was started")
        with mock.patch.object(subprocess, "Popen", side_effect=boom), mock.patch.object(
            os, "system", side_effect=boom
        ), mock.patch("builtins.eval", side_effect=boom), mock.patch(
            "builtins.exec", side_effect=boom
        ):
            data = run([item, issue(2, **HOSTILE, labels=())])
        self.assertEqual(counted(data["plugins"]["example.sky-clock"]["4.5.0"]), [1])
        text = json.dumps(data)
        for piece in ("details", "@someone", "whoami", "AAAA", "<", "$"):
            self.assertNotIn(piece, text)


if __name__ == "__main__":
    unittest.main()
