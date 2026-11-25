import html
import json
import posixpath
import re
import shutil
import subprocess
import unittest
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

from omaworks import site
from omaworks.link import build_form_link, build_report_link
from omaworks.site import ISSUES_URL, RULE, SiteError, counts_text, render, version_key
from tests import demo_site
from tests.fixtures import CATALOG

ROOT = Path(__file__).resolve().parent.parent
SPEC = ROOT / "SPEC.md"
ISSUE_RE = re.compile(re.escape(ISSUES_URL) + r"/(\d+)$")


def empty(**groups):
    return {"generated": "2026-12-01T10:00:00Z", "plugins": {}, "repos": {}, **groups}


class Blocks(HTMLParser):
    """Each row of a plugin page and entry of a version page: its statuses and
    the issues it links to. Also every tag, for checks over the whole page."""

    BLOCKS = {"row", "entry"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.blocks = []  # {"id", "kind", "statuses", "issues", "text"}
        self.tags = []  # (tag, attrs)
        self.stack = []  # open tags, with the block each one opened
        self.text = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        self.tags.append((tag, attrs))
        classes = (attrs.get("class") or "").split()
        block = None
        kind = next((c for c in classes if c in self.BLOCKS), None)
        if kind:
            block = {"id": attrs.get("id"), "kind": kind, "statuses": [], "issues": [], "text": []}
            self.blocks.append(block)
        if tag not in ("meta", "link", "input", "br"):
            self.stack.append(block)
        current = self.current()
        if current is None:
            return
        for name in classes:
            if name.startswith("status-"):
                current["statuses"].append(name.removeprefix("status-"))
        match = ISSUE_RE.match(attrs.get("href") or "") if tag == "a" else None
        if match:
            current["issues"].append(int(match.group(1)))

    def handle_endtag(self, tag):
        if self.stack:
            self.stack.pop()

    def handle_data(self, data):
        self.text.append(data)
        current = self.current()
        if current is not None:
            current["text"].append(data)

    def current(self):
        return next((b for b in reversed(self.stack) if b is not None), None)


def parse(text):
    parser = Blocks()
    parser.feed(text)
    parser.close()
    return parser


class Demo(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data, cls.catalog = demo_site.demo()
        cls.files, cls.skipped = render(cls.data, cls.catalog)

    def page(self, path):
        return parse(self.files[path])

    def rows(self, path):
        return {b["id"]: b for b in self.page(path).blocks if b["kind"] == "row"}


class NoReportsTest(Demo):
    """Rule 1: no reports is never shown as working."""

    def test_a_plugin_without_reports_shows_no_reports_yet_and_no_status(self):
        for plugin in ("example.quiet-dock", "example.suite-panel"):
            with self.subTest(plugin=plugin):
                page = self.page(f"plugins/{plugin}/index.html")
                [block] = page.blocks
                self.assertEqual(block["statuses"], ["none"])
                self.assertIn("No reports yet", "".join(block["text"]))
                self.assertIn("doesn't mean it works", "".join(block["text"]))
                statuses = [
                    c for _, a in page.tags for c in (a.get("class") or "").split()
                    if c.startswith("status-")
                ]
                self.assertEqual(statuses, ["status-none"])

    def test_a_version_without_reports_for_the_plugin_is_its_own_row(self):
        row = self.rows("plugins/example.sky-clock/index.html")["v-4.0.3"]
        self.assertEqual(row["statuses"], ["none"])
        self.assertEqual(row["issues"], [])
        self.assertEqual("".join(row["text"]).split().count("Works"), 0)

    def test_a_none_row_shows_no_reports_yet_and_still_lists_its_reports(self):
        row = self.rows("plugins/tidepool/index.html")["v-4.5.0"]
        self.assertEqual(row["statuses"], ["none"])
        self.assertEqual(row["issues"], [150])
        self.assertIn("names no Omarchy issue", "".join(row["text"]))

    def test_every_plugin_page_has_a_row_for_every_known_version(self):
        for path, text in self.files.items():
            if path.startswith(("plugins/", "repos/")):
                ids = {b["id"] for b in parse(text).blocks}
                with self.subTest(path=path):
                    if ids != {"no-reports"}:
                        self.assertEqual(ids, {"v-4.5.0", "v-4.5.0-rc2", "v-4.0.3"})

    def test_version_page_leaves_out_plugins_without_reports_and_says_so(self):
        page = self.files["versions/4.5.0-rc2/index.html"]
        for plugin in ("example.quiet-dock", "example.suite-bar", "tidepool"):
            self.assertNotIn(f"plugins/{plugin}/", page)
        self.assertIn("or has no reports yet on this version", page)

    def test_no_reports_at_all_says_so_on_the_front_page(self):
        files, _ = render(empty(), CATALOG)
        self.assertIn("No reports yet on any Omarchy version.", files["index.html"])
        self.assertNotIn("versions/", "".join(files))

    def test_status_names_never_call_none_working(self):
        self.assertEqual(site.STATUS_NAMES["none"], "No reports yet")
        self.assertEqual(set(site.STATUS_NAMES), set(site.STATUSES))

    def test_none_looks_like_nothing_in_the_stylesheet(self):
        css = (site.SITE / "style.css").read_text()
        self.assertRegex(css, r"\.status-none \{ background: transparent;")


class LinksTest(Demo):
    """Rule 4: every status links to the reports behind it."""

    def test_every_status_on_a_plugin_page_links_its_reports(self):
        checked = 0
        for group in ("plugins", "repos"):
            for key, releases in self.data[group].items():
                path = f"{group}/{key}/index.html"
                rows = self.rows(path)
                for release, row in releases.items():
                    block = rows[f"v-{release}"]
                    with self.subTest(key=key, release=release):
                        self.assertEqual(block["statuses"], [row["status"]])
                        listed = [r["issue"] for r in row["reports"]]
                        self.assertEqual(sorted(set(block["issues"])), sorted(listed))
                        checked += 1
        self.assertEqual(checked, 9)

    def test_every_status_on_a_version_page_links_its_counted_reports(self):
        checked = 0
        for path, text in self.files.items():
            if path.startswith("versions/"):
                for block in parse(text).blocks:
                    with self.subTest(path=path):
                        self.assertEqual(block["kind"], "entry")
                        [status] = block["statuses"]
                        self.assertIn(status, site.LISTED)
                        self.assertTrue(block["issues"])
                    checked += 1
        self.assertEqual(checked, 6)

    def test_version_page_entries_match_the_data(self):
        page = self.files["versions/4.5.0/index.html"]
        entries = re.findall(r'<li class="entry">.*?</li>', page)
        found = {}
        for entry in entries:
            key = re.search(r'href="\.\./\.\./(?:plugins|repos)/([^"#]+)/#v-4\.5\.0"', entry).group(1)
            block = parse(entry).blocks[0]
            found[key] = (block["statuses"], block["issues"])
        expected = {}
        for group in ("plugins", "repos"):
            for key, releases in self.data[group].items():
                row = releases.get("4.5.0")
                if row and row["status"] in site.LISTED:
                    counted = [r["issue"] for r in row["reports"] if r["counted"]]
                    expected[key] = ([row["status"]], counted)
        self.assertEqual(found, expected)
        self.assertNotIn("example.sky-clock", page)  # works on 4.5.0, so not listed

    def test_any_status_anywhere_sits_in_a_block_with_issue_links(self):
        for path, text in self.files.items():
            if not path.endswith(".html"):
                continue
            page = parse(text)
            in_blocks = sum(len(b["statuses"]) for b in page.blocks)
            badges = sum(
                1 for _, a in page.tags if "status" in (a.get("class") or "").split()
            )
            with self.subTest(path=path):
                if path != "index.html":
                    self.assertEqual(badges, in_blocks)
                for block in page.blocks:
                    if set(block["statuses"]) - {"none"}:
                        self.assertTrue(block["issues"])

    def test_fixed_from_and_seeded_and_why(self):
        row = self.rows("plugins/example.sky-clock/index.html")["v-4.5.0"]
        text = " ".join("".join(row["text"]).split())
        self.assertIn("Broken in older versions, reported working from commit 8be04d2.", text)
        self.assertIn("from Omarchy issue #17794", text)
        self.assertIn("the same account has a newer report", text)
        self.assertIn("on an older plugin commit", text)
        self.assertIn("2 works", text)
        page = self.files["plugins/example.sky-clock/index.html"]
        self.assertIn('href="https://github.com/omacom/omarchy/issues/17794"', page)
        self.assertIn('href="https://github.com/example-dev/sky-clock/commit/8be04d2"', page)

    def test_unordered_says_so(self):
        row = self.rows("plugins/example.moon-phase/index.html")["v-4.5.0-rc2"]
        self.assertIn("they all count together", "".join(row["text"]))


class ReportButtonTest(Demo):
    def button(self, path):
        page = self.page(path)
        return [a["href"] for t, a in page.tags if t == "a" and a.get("class") == "button"]

    def test_uses_the_link_format_of_link_py(self):
        self.assertEqual(
            self.button("plugins/example.sky-clock/index.html"),
            [build_report_link("example.sky-clock")],
        )
        self.assertEqual(
            self.button("plugins/example.quiet-dock/index.html"),
            [build_report_link("example.quiet-dock")],
        )

    def test_a_repo_is_reported_by_its_url(self):
        [link] = self.button("repos/example-dev/weather-strip/index.html")
        self.assertEqual(link, build_report_link("https://github.com/example-dev/weather-strip"))
        self.assertEqual(
            parse_qs(urlsplit(link).query)["plugin"], ["https://github.com/example-dev/weather-strip"]
        )

    def test_an_id_no_longer_in_the_catalog_has_no_button(self):
        self.assertEqual(self.button("plugins/example.old-dial/index.html"), [])
        self.assertIn("no longer in the marketplace catalog", self.files["plugins/example.old-dial/index.html"])

    def test_the_hint_names_the_command_and_links_the_install_lines(self):
        for path in ("plugins/example.sky-clock/index.html",
                     "repos/example-dev/weather-strip/index.html"):
            page = self.page(path)
            links = [a["href"] for t, a in page.tags if t == "a"]
            self.assertIn("https://github.com/Frestina/omaworks#install", links)
            self.assertIn("omaworks report &lt;id&gt;", self.files[path])
        # No report button, no hint.
        self.assertNotIn("#install", self.files["plugins/example.old-dial/index.html"])

    def test_front_page_links_the_empty_form(self):
        self.assertIn(html.escape(build_form_link()), self.files["index.html"])


class CountingRuleTest(Demo):
    def test_the_sentence_is_the_specs(self):
        spec = " ".join(SPEC.read_text().split())
        sentence = re.search(r'fit in one sentence on the website: "([^"]+)"', spec).group(1)
        self.assertEqual(RULE, sentence)

    def test_every_page_shows_it(self):
        for path, text in self.files.items():
            if path.endswith(".html"):
                with self.subTest(path=path):
                    self.assertIn(RULE, text)

    def test_counts_text(self):
        def c(works=0, problems=0, broken=0):
            return counts_text({"works": works, "problems": problems, "broken": broken})

        self.assertEqual(c(works=1, broken=3), "3 broken, 1 works")
        self.assertEqual(c(works=2, broken=2), "2 works, 2 broken")
        self.assertEqual(c(broken=1), "1 report")
        self.assertEqual(c(works=2, problems=1), "2 works, 1 with problems")
        self.assertEqual(c(), "no reports count")


class SafetyTest(Demo):
    def test_catalog_text_is_escaped(self):
        page = self.files["plugins/example.moon-phase/index.html"]
        self.assertIn("<h1>Moon &lt;Phase&gt; &amp; Tides</h1>", page)
        self.assertNotIn("<Phase>", page)

    def test_hostile_catalog_text_stays_text(self):
        hostile = '<img src=x onerror=alert(1)>"\' onmouseover=x \x00‮' + "A" * 300
        catalog = [{"id": "example.sky-clock", "name": hostile, "author": hostile,
                    "repo": "javascript:alert(1)"}]
        files, _ = render(empty(), catalog)
        page = files["plugins/example.sky-clock/index.html"]
        self.assertNotIn("<img", page)
        self.assertNotIn("onerror=alert(1)>", page.replace("&lt;img src=x onerror=alert(1)&gt;", ""))
        self.assertNotIn("javascript:", page)
        self.assertNotIn("\x00", page)
        self.assertNotIn("‮", page)
        name = json.loads(files["catalog-index.json"])["plugins"][0][1]
        self.assertLessEqual(len(name), site.MAX_TEXT)

    def test_every_page_has_the_policy_and_no_inline_script(self):
        for path, text in self.files.items():
            if not path.endswith(".html"):
                continue
            page = parse(text)
            with self.subTest(path=path):
                self.assertIn("default-src 'none'; script-src 'self';", text)
                self.assertIn("connect-src 'self'", text)
                for tag, attrs in page.tags:
                    self.assertFalse([a for a in attrs if a.startswith("on")], tag)
                    if tag == "script":
                        self.assertEqual(attrs.get("src"), "search.js")
                    for name in ("href", "src"):
                        value = attrs.get(name) or ""
                        self.assertFalse(value.lower().startswith(("javascript:", "data:")))

    def test_links_go_only_to_the_site_and_github(self):
        for path, text in self.files.items():
            if not path.endswith(".html"):
                continue
            for tag, attrs in parse(text).tags:
                for name in ("href", "src"):
                    value = attrs.get(name)
                    if value and "://" in value:
                        self.assertTrue(value.startswith("https://github.com/"), value)

    def test_search_script_writes_only_text_and_reads_only_the_index(self):
        script = (site.SITE / "search.js").read_text()
        for word in ("innerHTML", "outerHTML", "insertAdjacentHTML", "document.write",
                     "eval(", "Function(", "XMLHttpRequest", "import("):
            self.assertNotIn(word, script)
        self.assertEqual(script.count("fetch("), 1)
        self.assertIn("fetch(input.dataset.index)", script)
        self.assertIn(f'data-index="{site.INDEX}"', self.files["index.html"])

    def test_bad_data_stops_the_build(self):
        good = self.data["plugins"]["example.sky-clock"]["4.5.0"]
        bad_rows = [
            {**good, "status": "fine"},
            {**good, "fixedFrom": '"><script>'},
            {**good, "reports": [{**good["reports"][0], "issue": "1/../../x"}]},
            {**good, "reports": [{**good["reports"][0], "commit": "<b>"}]},
            {**good, "reports": [{**good["reports"][0], "version": "4.5.0<"}]},
            {**good, "counts": {"works": 9, "problems": 0, "broken": 0}},
        ]
        for row in bad_rows:
            with self.subTest(row=row):
                with self.assertRaises(SiteError):
                    render(empty(plugins={"example.sky-clock": {"4.5.0": row}}), CATALOG)
        with self.assertRaises(SiteError):
            render(empty(plugins={"example.sky-clock": {"4.5.0/../x": good}}), CATALOG)
        with self.assertRaises(SiteError):
            render({**empty(), "generated": "<now>"}, CATALOG)

    def test_keys_that_are_not_plain_get_no_page(self):
        good = self.data["plugins"]["example.sky-clock"]["4.5.0"]
        data = empty(
            plugins={"../evil": {"4.5.0": good}, "Example.Upper": {"4.5.0": good}},
            repos={"../x": {"4.5.0": good}, "example-dev/..": {"4.5.0": good}},
        )
        files, skipped = render(data, CATALOG)
        self.assertEqual(sorted(skipped), sorted(["../evil", "Example.Upper", "../x", "example-dev/.."]))
        for path in files:
            self.assertNotIn("..", path)
        self.assertNotIn("versions/4.5.0/index.html", files)


class PagesTest(Demo):
    def test_the_three_kinds_of_page(self):
        self.assertIn("index.html", self.files)
        self.assertIn("plugins/example.sky-clock/index.html", self.files)
        self.assertIn("repos/example-dev/weather-strip/index.html", self.files)
        self.assertEqual(
            sorted(p for p in self.files if p.startswith("versions/")),
            ["versions/4.0.3/index.html", "versions/4.5.0-rc2/index.html", "versions/4.5.0/index.html"],
        )

    def test_a_page_for_every_catalog_plugin(self):
        for item in CATALOG:
            self.assertIn(f"plugins/{item['id']}/index.html", self.files)

    def test_front_page_lists_versions_newest_first(self):
        page = self.files["index.html"]
        order = re.findall(r'href="versions/([^/]+)/"', page)
        self.assertEqual(order, ["4.5.0", "4.5.0-rc2", "4.0.3"])
        self.assertIn("1 reported broken, 6 with reports", page)

    def test_version_order(self):
        releases = ["4.5.0", "4.0.3", "4.5.0-rc2", "4.5.0-beta1", "4.10.0", "4.5.0-rc10"]
        self.assertEqual(
            sorted(releases, key=version_key),
            ["4.0.3", "4.5.0-beta1", "4.5.0-rc2", "4.5.0-rc10", "4.5.0", "4.10.0"],
        )

    def test_relative_links_resolve_to_files_of_the_site(self):
        files = set(self.files) | {"reports.json"}
        for path, text in self.files.items():
            if not path.endswith(".html"):
                continue
            for tag, attrs in parse(text).tags:
                for name in ("href", "src"):
                    value = attrs.get(name)
                    if value is None or "://" in value:
                        continue
                    link = value.split("#")[0]
                    target = posixpath.normpath(posixpath.join(posixpath.dirname(path), link))
                    if link.endswith("/") or link in ("", "."):
                        target = posixpath.normpath(posixpath.join(target, "index.html"))
                    with self.subTest(path=path, link=value):
                        self.assertIn(target, files)

    def test_light_dark_and_phone(self):
        css = (site.SITE / "style.css").read_text()
        self.assertIn("@media (prefers-color-scheme: dark)", css)
        self.assertIn("padding: 0 16px", css)
        self.assertIn("overflow-wrap: anywhere", css)
        for path, text in self.files.items():
            if path.endswith(".html"):
                self.assertIn('<meta name="viewport" content="width=device-width, initial-scale=1">', text)
                self.assertIn('<meta name="color-scheme" content="light dark">', text)

    def test_repo_name_with_a_leading_dot(self):
        good = self.data["repos"]["example-dev/weather-strip"]["4.5.0"]
        files, _ = render(empty(repos={"example-dev/.dotfiles": {"4.5.0": good}}), CATALOG)
        self.assertIn("repos/example-dev/~dotfiles/index.html", files)
        index = json.loads(files["catalog-index.json"])
        self.assertEqual(index["repos"], [["example-dev/.dotfiles", "repos/example-dev/~dotfiles/", ["4.5.0"]]])


class SearchIndexTest(Demo):
    def test_index_holds_every_plugin_and_its_reported_versions(self):
        index = json.loads(self.files["catalog-index.json"])
        plugins = {p[0]: p for p in index["plugins"]}
        self.assertEqual(set(plugins), {p["id"] for p in self.catalog} | {"example.old-dial"})
        self.assertEqual(plugins["example.sky-clock"], ["example.sky-clock", "Sky Clock", "example-dev", ["4.5.0", "4.5.0-rc2"]])
        self.assertEqual(plugins["example.quiet-dock"][3], [])
        self.assertEqual(plugins["example.old-dial"], ["example.old-dial", "", "", ["4.5.0"]])
        self.assertEqual(index["repos"], [["example-dev/weather-strip", "repos/example-dev/weather-strip/", ["4.5.0"]]])

    def test_index_is_compact(self):
        text = self.files["catalog-index.json"]
        self.assertNotIn(", ", text.split('"plugins"')[0])
        self.assertNotIn("\n ", text)


@unittest.skipUnless(shutil.which("node"), "node is not installed")
class SearchScriptTest(Demo):
    """search.js's matching, run with node. The page itself isn't loaded."""

    def search(self, *queries):
        script = (
            "const s = require(process.argv[1]);"
            "const list = s.entries(JSON.parse(process.argv[2]));"
            "console.log(JSON.stringify(JSON.parse(process.argv[3]).map("
            "q => s.search(list, q).map(e => [e.id, e.name, e.path, e.versions]))));"
        )
        out = subprocess.run(
            ["node", "-e", script, str(site.SITE / "search.js"),
             self.files["catalog-index.json"], json.dumps(queries)],
            capture_output=True, text=True, check=True, timeout=60,
        )
        return json.loads(out.stdout)

    def test_matches_by_name_id_and_author(self):
        sky, suite, harbour, nothing, blank = self.search("Sky", "suite", "harbour", "zzz", "  ")
        self.assertEqual(sky, [["example.sky-clock", "Sky Clock", "plugins/example.sky-clock/", ["4.5.0", "4.5.0-rc2"]]])
        self.assertEqual([r[0] for r in suite], ["example.suite-bar", "example.suite-panel"])
        self.assertEqual([r[0] for r in harbour], ["tidepool"])
        self.assertEqual(nothing, [])
        self.assertEqual(blank, [])

    def test_a_github_url_finds_its_repo(self):
        [found] = self.search("https://www.github.com/example-dev/weather-strip.git/")
        self.assertEqual(found, [["example-dev/weather-strip", "example-dev/weather-strip",
                                  "repos/example-dev/weather-strip/", ["4.5.0"]]])

    def test_name_falls_back_to_the_id(self):
        [found] = self.search("old-dial")
        self.assertEqual(found[0][:2], ["example.old-dial", "example.old-dial"])

    def test_reported_plugins_come_first_and_exact_ids_before_them(self):
        [found] = self.search("example")
        ids = [r[0] for r in found]
        reported = [r[0] for r in found if r[3]]
        self.assertEqual(ids[: len(reported)], reported)

    def test_entries_that_are_not_plain_are_left_out(self):
        index = json.dumps({"plugins": [["../x", "X", "", []], ["ok.one", "<b>", "", ["4.5.0", "<i>"]]],
                            "repos": [["a/b", "javascript:alert(1)", []]]})
        script = (
            "const s = require(process.argv[1]);"
            "console.log(JSON.stringify(s.entries(JSON.parse(process.argv[2]))"
            ".map(e => [e.id, e.name, e.path, e.versions])));"
        )
        out = subprocess.run(["node", "-e", script, str(site.SITE / "search.js"), index],
                             capture_output=True, text=True, check=True, timeout=60)
        self.assertEqual(json.loads(out.stdout), [["ok.one", "<b>", "plugins/ok.one/", ["4.5.0"]]])


if __name__ == "__main__":
    unittest.main()
