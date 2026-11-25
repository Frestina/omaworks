import unittest

from omaworks.check import (
    MARKER,
    MAX_LABEL,
    NEEDS_FIX,
    PASS_COMMENT,
    Catalog,
    SourceError,
    check_report,
    failure_comment,
    is_owned,
    label,
    plan_labels,
    release_of,
)
from omaworks.report import parse_body
from tests.fixtures import HOSTILE, LONG_ID, FakeSources, body


def check(sources=None, **fields):
    return check_report(parse_body(body(**fields)), sources or FakeSources())


class GoodReportTest(unittest.TestCase):
    def test_good_report_passes(self):
        checked = check()
        self.assertEqual(checked.problems, [])
        self.assertTrue(checked.ok)
        self.assertEqual(checked.plugin, "example.sky-clock")
        self.assertTrue(checked.in_catalog)
        self.assertEqual(checked.version, "4.5.0-3")
        self.assertEqual(checked.release, "4.5.0")
        self.assertEqual(checked.commit, "3f2a91c")
        self.assertEqual(checked.result, "works")
        self.assertEqual(
            [item.name for item in checked.labels()],
            ["plugin:example.sky-clock", "omarchy:4.5.0", "result:works"],
        )

    def test_one_problem_per_bad_field(self):
        checked = check(plugin="example.nope", omarchy="soon", commit="xyz", result="Meh")
        self.assertEqual(len(checked.problems), 4)
        for name in ("Plugin", "Omarchy version", "Plugin commit", "Result"):
            self.assertTrue(any(p.startswith(f"**{name}**") for p in checked.problems), name)
        self.assertEqual([item.name for item in checked.labels()], [NEEDS_FIX])


class PluginCheckTest(unittest.TestCase):
    def test_catalog_id_passes(self):
        self.assertTrue(check(plugin="example.moon-phase").ok)

    def test_catalog_id_without_a_dot_passes(self):
        self.assertTrue(check(plugin="tidepool").ok)

    def test_catalog_id_any_case_passes(self):
        checked = check(plugin="Example.Sky-Clock")
        self.assertTrue(checked.ok)
        self.assertEqual(checked.plugin, "example.sky-clock")

    def test_unknown_id_fails(self):
        checked = check(plugin="example.star-chart")
        self.assertFalse(checked.ok)
        self.assertIn("not in the marketplace catalog", checked.problems[0])
        self.assertNotIn("Did you mean", checked.problems[0])

    def test_unknown_id_suggests_a_close_catalog_id(self):
        checked = check(plugin="example.sky-clok")
        self.assertIn("Did you mean `example.sky-clock`?", checked.problems[0])

    def test_suggestion_is_only_a_plain_catalog_id(self):
        sources = FakeSources(catalog=[{"id": "example.sky-clock`@x"}])
        checked = check(sources, plugin="example.sky-clock`@")
        self.assertFalse(checked.ok)
        self.assertNotIn("Did you mean", checked.problems[0])

    def test_missing_field_fails(self):
        text = body().replace("### Plugin\n\nexample.sky-clock\n\n", "")
        checked = check_report(parse_body(text), FakeSources())
        self.assertIn("**Plugin**: this field is missing", checked.problems[0])

    def test_empty_field_fails(self):
        self.assertIn("this field is empty", check(plugin="_No response_").problems[0])

    def test_two_lines_fail(self):
        checked = check(plugin="example.sky-clock\nexample.moon-phase")
        self.assertIn("one short line", checked.problems[0])

    def test_very_long_field_fails(self):
        checked = check(plugin="example." + "a" * 5000)
        self.assertIn("one short line", checked.problems[0])


class RepoUrlTest(unittest.TestCase):
    def test_repo_outside_the_catalog_passes(self):
        for url in (
            "https://github.com/example-dev/weather-strip",
            "https://github.com/Example-Dev/Weather-Strip/",
            "http://github.com/example-dev/weather-strip.git",
            "github.com/example-dev/weather-strip",
            "https://www.github.com/example-dev/weather-strip",
        ):
            with self.subTest(url=url):
                checked = check(plugin=url)
                self.assertEqual(checked.problems, [])
                self.assertFalse(checked.in_catalog)
                self.assertEqual(checked.plugin, "example-dev/weather-strip")
                self.assertEqual(
                    checked.labels()[0].name, "repo:example-dev/weather-strip"
                )

    def test_repo_that_does_not_exist_fails(self):
        sources = FakeSources()
        checked = check(sources, plugin="https://github.com/example-dev/ghost")
        self.assertIn("no public GitHub repo", checked.problems[0])
        self.assertIn(("repo", "example-dev", "ghost"), sources.calls)

    def test_repo_in_the_catalog_names_its_id(self):
        sources = FakeSources()
        checked = check(sources, plugin="https://github.com/example-dev/sky-clock")
        self.assertIn("use its plugin ID instead: `example.sky-clock`.", checked.problems[0])
        self.assertFalse(any(call[0] == "repo" for call in sources.calls))

    def test_repo_with_several_catalog_ids_names_them_all(self):
        checked = check(plugin="https://github.com/example-dev/suite")
        self.assertIn("several plugins", checked.problems[0])
        self.assertIn("`example.suite-bar`, `example.suite-panel`.", checked.problems[0])

    def test_repo_with_many_catalog_ids_lists_five(self):
        plugins = [
            {"id": f"example.part-{n:02}", "repo": "https://github.com/example-dev/big"}
            for n in range(12)
        ]
        checked = check(FakeSources(catalog=plugins), plugin="https://github.com/example-dev/big")
        self.assertIn("`example.part-04` and 7 more.", checked.problems[0])
        self.assertNotIn("example.part-05", checked.problems[0])

    def test_moved_repo_found_in_the_catalog_by_its_new_name(self):
        sources = FakeSources(repos={"old-name/sky": "example-dev/sky-clock"})
        checked = check(sources, plugin="https://github.com/old-name/sky")
        self.assertIn("`example.sky-clock`", checked.problems[0])

    def test_badly_shaped_url_fails_without_a_lookup(self):
        for url in (
            "https://github.com/example-dev",
            "https://github.com/example-dev/weather-strip/tree/main",
            "https://gitlab.com/example-dev/weather-strip",
            "https://github.com/-bad/weather-strip",
            "https://github.com/example-dev/..",
            "https://github.com/example-dev/weather strip",
        ):
            with self.subTest(url=url):
                sources = FakeSources()
                checked = check(sources, plugin=url)
                self.assertFalse(checked.ok)
                self.assertFalse(any(call[0] == "repo" for call in sources.calls))


class VersionCheckTest(unittest.TestCase):
    def test_versions_that_pass(self):
        cases = {
            "4.5.0-3": "4.5.0",
            "4.5.0-1": "4.5.0",
            "4.5.0": "4.5.0",
            "v4.5.0": "4.5.0",
            "1:4.5.0-1": "4.5.0",
            "4.5.0rc2-1": "4.5.0-rc2",
            "4.5.0-rc2": "4.5.0-rc2",
            "v4.5.0-rc2": "4.5.0-rc2",
            "4.0.0beta3-1": "4.0.0-beta3",
            "4.0.3-1": "4.0.3",
        }
        for version, release in cases.items():
            with self.subTest(version=version):
                checked = check(omarchy=version)
                self.assertEqual(checked.problems, [])
                self.assertEqual(checked.release, release)
                self.assertEqual(checked.version, version)
                self.assertEqual(checked.labels()[1].name, f"omarchy:{release}")

    def test_release_that_does_not_exist_fails(self):
        checked = check(omarchy="4.5.9-1")
        self.assertEqual(checked.problems, ["**Omarchy version**: Omarchy has no release `v4.5.9`."])

    def test_untagged_release_candidate_fails(self):
        self.assertIn("`v4.5.0-rc3`", check(omarchy="4.5.0rc3-1").problems[0])

    def test_not_a_version_fails_without_a_lookup(self):
        for version in ("soon", "4.5", "4.5.0.1", "4.5.0-", "4.5.0 -3", "latest", "4.5.0-alpha1"):
            with self.subTest(version=version):
                sources = FakeSources()
                checked = check(sources, omarchy=version)
                self.assertIn("isn't an Omarchy version", checked.problems[0])
                self.assertFalse(any(call[0] == "tag" for call in sources.calls))

    def test_development_build_fails(self):
        for version in ("4.0.0.r7195.g3ac4365-1", "dev (3ac4365)", "dev"):
            with self.subTest(version=version):
                self.assertIn("development build", check(omarchy=version).problems[0])

    def test_release_of(self):
        self.assertEqual(release_of("4.5.0-3"), "4.5.0")
        self.assertEqual(release_of("4.5.0rc2-1"), "4.5.0-rc2")
        self.assertIsNone(release_of("nope"))


class CommitCheckTest(unittest.TestCase):
    def test_commits_that_pass(self):
        for commit in ("3f2a91c", "3F2A91C", "a" * 40, "0123456789ab"):
            with self.subTest(commit=commit):
                checked = check(commit=commit)
                self.assertEqual(checked.problems, [])
                self.assertEqual(checked.commit, commit.lower())

    def test_commits_that_fail(self):
        for commit in ("3f2a91", "a" * 41, "3f2a91g", "main", "v1.2.0"):
            with self.subTest(commit=commit):
                self.assertIn("**Plugin commit**", check(commit=commit).problems[0])


class ResultCheckTest(unittest.TestCase):
    def test_the_three_results_pass(self):
        cases = {"Works": "works", "Works with problems": "problems", "Broken": "broken"}
        for text, key in cases.items():
            with self.subTest(text=text):
                checked = check(result=text)
                self.assertEqual(checked.result, key)
                self.assertEqual(checked.labels()[2].name, f"result:{key}")

    def test_other_results_fail(self):
        for text in ("Mostly works", "works?", "Broken!", "_No response_"):
            with self.subTest(text=text):
                self.assertIn("**Result**", check(result=text).problems[0])


class LabelTest(unittest.TestCase):
    def test_short_name_kept(self):
        self.assertEqual(label("plugin:", "example.sky-clock", "d", "ffffff").name,
                         "plugin:example.sky-clock")

    def test_long_name_cut_to_fifty_with_a_hash(self):
        name = label("plugin:", LONG_ID, "d", "ffffff").name
        self.assertEqual(len(name), MAX_LABEL)
        self.assertTrue(name.startswith(f"plugin:{LONG_ID[:36]}"))
        self.assertRegex(name, r"~[0-9a-f]{6}$")

    def test_long_names_sharing_a_start_differ(self):
        one = label("plugin:", LONG_ID, "d", "ffffff").name
        two = label("plugin:", LONG_ID[:-1] + "x", "d", "ffffff").name
        self.assertNotEqual(one, two)

    def test_long_id_report_gets_a_valid_label_with_the_full_id(self):
        plugin = check(plugin=LONG_ID).labels()[0]
        self.assertLessEqual(len(plugin.name), MAX_LABEL)
        self.assertIn(LONG_ID, plugin.description)
        self.assertLessEqual(len(plugin.description), 100)

    def test_long_repo_label_fits(self):
        repo = "example-dev/" + "w" * 90
        sources = FakeSources(repos={repo: repo})
        checked = check(sources, plugin=f"https://github.com/{repo}")
        for item in checked.labels():
            self.assertLessEqual(len(item.name), MAX_LABEL)
            self.assertLessEqual(len(item.description), 100)

    def test_every_label_has_a_colour(self):
        for item in check().labels() + check(result="Broken").labels() + check(result="nope").labels():
            self.assertRegex(item.color, r"^[0-9a-f]{6}$")


class PlanLabelsTest(unittest.TestCase):
    def test_new_report_gets_its_labels(self):
        wanted = check().labels()
        add, remove = plan_labels(["report"], wanted)
        self.assertEqual(add, wanted)
        self.assertEqual(remove, [])

    def test_edit_swaps_the_changed_labels(self):
        current = ["report", "plugin:example.sky-clock", "omarchy:4.5.0", "result:works"]
        wanted = check(plugin="example.moon-phase", result="Broken").labels()
        add, remove = plan_labels(current, wanted)
        self.assertEqual([i.name for i in add], ["plugin:example.moon-phase", "result:broken"])
        self.assertEqual(remove, ["plugin:example.sky-clock", "result:works"])

    def test_failing_edit_takes_off_the_old_labels(self):
        current = ["report", "plugin:example.sky-clock", "omarchy:4.5.0", "result:works"]
        add, remove = plan_labels(current, check(commit="nope").labels())
        self.assertEqual([i.name for i in add], [NEEDS_FIX])
        self.assertEqual(remove, current[1:])

    def test_fixed_report_loses_needs_fix(self):
        add, remove = plan_labels(["report", "needs-fix"], check().labels())
        self.assertEqual(remove, ["needs-fix"])
        self.assertEqual(len(add), 3)

    def test_labels_it_did_not_create_are_never_removed(self):
        current = ["report", "spam", "test", "needs-look", "from-issue", "good first issue"]
        for wanted in (check().labels(), check(result="nope").labels()):
            _, remove = plan_labels(current, wanted)
            self.assertEqual(remove, [])

    def test_names_compare_without_case(self):
        add, remove = plan_labels(["Plugin:Example.Sky-Clock"], check().labels()[:1])
        self.assertEqual((add, remove), ([], []))

    def test_owned_labels(self):
        for name in ("needs-fix", "plugin:x", "repo:x/y", "omarchy:4.5.0", "result:works"):
            self.assertTrue(is_owned(name), name)
        for name in ("report", "spam", "test", "needs-look", "from-issue", "plugins"):
            self.assertFalse(is_owned(name), name)


class CommentTest(unittest.TestCase):
    def test_failure_comment_lists_each_problem(self):
        checked = check(commit="nope", result="Meh")
        text = failure_comment(checked.problems)
        self.assertTrue(text.startswith(MARKER + "\n"))
        self.assertIn("- **Plugin commit**:", text)
        self.assertIn("- **Result**:", text)

    def test_pass_comment_has_the_marker(self):
        self.assertTrue(PASS_COMMENT.startswith(MARKER + "\n"))


class HostileBodyTest(unittest.TestCase):
    def setUp(self):
        self.checked = check_report(parse_body(body(**HOSTILE)), FakeSources())
        self.comment = failure_comment(self.checked.problems)

    def test_every_hostile_field_fails(self):
        self.assertEqual(len(self.checked.problems), 4)

    def test_comment_repeats_none_of_the_reporters_text(self):
        for piece in (
            "@octo-team", "#1", "<img", "onerror", "$(rm", "`id`", "github.token",
            "curl", "example.invalid", "<script>", "**Works**", "pwned", "<details",
            "@someone", "#99", "AAAA", "whoami", "$HOME",
        ):
            self.assertTrue(any(piece in value for value in HOSTILE.values()), piece)
            self.assertNotIn(piece, self.comment)

    def test_comment_cannot_mention_link_or_render(self):
        text = self.comment.replace(MARKER, "")
        self.assertNotIn("@", text)
        self.assertNotRegex(text, r"#\d")
        self.assertNotIn("<", text)
        self.assertNotIn("](", text)
        self.assertNotIn("${{", text)

    def test_hostile_text_close_to_an_id_is_not_suggested(self):
        checked = check(plugin="example.sky-clock<b>")
        self.assertNotIn("<b>", failure_comment(checked.problems))

    def test_long_body_is_checked_quickly(self):
        import time

        start = time.monotonic()
        check(what="x" * 65536, errors="y\n" * 30000, plugin="a" * 65536)
        self.assertLess(time.monotonic() - start, 2)


class SourceErrorTest(unittest.TestCase):
    def test_outage_raises_rather_than_failing_the_report(self):
        with self.assertRaises(SourceError):
            check(FakeSources(fail=True))

    def test_catalog_without_ids_raises(self):
        for plugins in ({}, [], [{"name": "x"}], ["x"]):
            with self.subTest(plugins=plugins):
                with self.assertRaises(SourceError):
                    Catalog(plugins)


if __name__ == "__main__":
    unittest.main()
