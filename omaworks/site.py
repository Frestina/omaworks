"""Render the website from reports.json's data and the catalog.

See SPEC.md, "The website". The build calls render() and writes what it
returns next to reports.json. Every page is static HTML written here, so the
rules about what a page may say are tested with unittest:

- a plugin, or a version of it, without reports shows "No reports yet",
  never a status;
- every status sits next to links to the reports behind it.

Only the search runs in the browser, in site/search.js. It reads
catalog-index.json, a small index the build writes from the catalog, and
makes no other request.

Names and authors come from the catalog, which is someone else's text. Each
one, and every value from reports.json, is escaped before it goes into a page.
reports.json holds no free text from a report, and its values are checked
against their patterns again here, so a link never holds anything else.
"""

import html
import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from string import Template

from omaworks.check import CATALOG_REPO_RE, ID_RE, OWNER, REPO, VERSION_RE
from omaworks.count import RESULTS, STATUSES
from omaworks.link import BASE_URL, build_form_link, build_report_link

SITE = Path(__file__).resolve().parent.parent / "site"
TEMPLATE = "page.html"
ASSETS = ("style.css", "search.js", "favicon.svg")
INDEX = "catalog-index.json"

REPO_URL = BASE_URL.removesuffix("/issues/new")
ISSUES_URL = f"{REPO_URL}/issues"
INSTALL_URL = f"{REPO_URL}#install"
OMARCHY_ISSUES_URL = "https://github.com/omacom/omarchy/issues"

# The counting rule in one sentence. See SPEC.md, "Counting".
RULE = (
    "The newest plugin version that has reports decides, and a result needs "
    "at least 60% of those reports."
)

STATUS_NAMES = {
    "none": "No reports yet",
    "works": "Works",
    "problems": "Works with problems",
    "broken": "Broken",
    "mixed": "Mixed reports",
}
RESULT_NAMES = {"works": "Works", "problems": "Works with problems", "broken": "Broken"}
COUNT_WORDS = {"works": "works", "problems": "with problems", "broken": "broken"}
WHY = {
    "older-commit": "doesn't count: on an older plugin commit",
    "commit-not-found": "doesn't count: the plugin's repo has no such commit",
    "no-source": "doesn't count: it names no Omarchy issue as its source",
}
WHY_NEWER = {
    False: "doesn't count: the same account has a newer report",
    True: "doesn't count: there is a newer report from the same Omarchy issue",
}

# A version page lists these, in this order. See SPEC.md, "The website".
LISTED = ("broken", "mixed", "problems")
LISTED_TITLES = {
    "broken": "Broken",
    "mixed": "Mixed reports",
    "problems": "Works with problems",
}

RELEASE_RE = re.compile(r"(\d{1,4})\.(\d{1,4})\.(\d{1,4})(?:-(beta|rc)(\d{1,4}))?", re.ASCII)
COMMIT_RE = re.compile(r"[0-9a-f]{7,40}", re.ASCII)
REPO_KEY_RE = re.compile(rf"({OWNER})/({REPO})", re.ASCII)
GENERATED_RE = re.compile(r"\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ", re.ASCII)

MAX_TEXT = 100  # longest name or author taken from the catalog


class SiteError(ValueError):
    """reports.json's data isn't what the count writes. Nothing is built."""


def e(value):
    return html.escape(str(value), quote=True)


def version_key(release):
    """Sorts releases oldest first: 4.0.3, 4.5.0-beta1, 4.5.0-rc2, 4.5.0."""
    major, minor, patch, pre, number = RELEASE_RE.fullmatch(release).groups()
    rank = {"beta": 0, "rc": 1, None: 2}[pre]
    return (int(major), int(minor), int(patch), rank, int(number or 0))


def counts_text(counts):
    """ "3 broken, 1 works", or "1 report" when one report decides alone."""
    total = sum(counts.values())
    if total == 0:
        return "no reports count"
    if total == 1:
        return "1 report"
    order = sorted((r for r in RESULTS if counts[r]), key=lambda r: -counts[r])
    return ", ".join(f"{counts[r]} {COUNT_WORDS[r]}" for r in order)


def _text(value):
    """Catalog text on one line, printable, at most MAX_TEXT characters."""
    if not isinstance(value, str):
        return ""
    value = " ".join("".join(c if c.isprintable() else " " for c in value).split())
    return value if len(value) <= MAX_TEXT else value[: MAX_TEXT - 1] + "…"


def _repo_segment(name):
    """A repo name as a folder. A leading dot becomes "~", which no repo name has,
    since Pages leaves out folders that start with a dot."""
    return "~" + name[1:] if name.startswith(".") else name


@dataclass
class Plugin:
    group: str  # "plugins" for a catalog ID, "repos" for a repo outside it
    key: str  # the catalog ID, or "owner/name" in lowercase
    name: str
    author: str = ""
    repo: str | None = None  # "owner/name" on GitHub, for links to commits
    in_catalog: bool = True
    rows: dict = field(default_factory=dict)  # release to its row

    @property
    def path(self):
        if self.group == "plugins":
            return f"plugins/{self.key}/"
        owner, name = self.key.split("/", 1)
        return f"repos/{owner}/{_repo_segment(name)}/"

    @property
    def report_link(self):
        """The Report button's link, or None when a report on it can't pass."""
        if self.group == "repos":
            return build_report_link(f"https://github.com/{self.key}")
        return build_report_link(self.key) if self.in_catalog else None


def catalog_plugins(plugins):
    """{id: Plugin} for the catalog's plain IDs. The first of an ID wins."""
    found = {}
    for item in plugins:
        if not isinstance(item, dict) or not isinstance(item.get("id"), str):
            continue
        plugin_id = item["id"].lower()
        if not ID_RE.fullmatch(plugin_id) or plugin_id in found:
            continue
        match = CATALOG_REPO_RE.fullmatch(str(item.get("repo") or ""))
        found[plugin_id] = Plugin(
            group="plugins",
            key=plugin_id,
            name=_text(item.get("name")) or plugin_id,
            author=_text(item.get("author")),
            repo=f"{match.group(1)}/{match.group(2)}" if match else None,
        )
    return found


def _check_row(release, row):
    """Raise SiteError unless the row is one the count could have written."""
    if not RELEASE_RE.fullmatch(release):
        raise SiteError(f"bad release {release!r}")
    if not isinstance(row, dict) or row.get("status") not in STATUSES:
        raise SiteError(f"bad status on {release}")
    counts = row.get("counts")
    if not isinstance(counts, dict) or set(counts) != set(RESULTS):
        raise SiteError(f"bad counts on {release}")
    for value in counts.values():
        if not isinstance(value, int) or isinstance(value, bool) or value < 0:
            raise SiteError(f"bad counts on {release}")
    if "fixedFrom" in row and not COMMIT_RE.fullmatch(str(row["fixedFrom"])):
        raise SiteError(f"bad fixedFrom on {release}")
    reports = row.get("reports")
    if not isinstance(reports, list):
        raise SiteError(f"bad reports on {release}")
    for entry in reports:
        if not isinstance(entry, dict):
            raise SiteError(f"bad report on {release}")
        number = entry.get("issue")
        if not isinstance(number, int) or isinstance(number, bool) or number < 1:
            raise SiteError(f"bad issue on {release}")
        if not VERSION_RE.fullmatch(str(entry.get("version")).lower()):
            raise SiteError(f"bad version on #{number}")
        if not COMMIT_RE.fullmatch(str(entry.get("commit"))):
            raise SiteError(f"bad commit on #{number}")
        if entry.get("result") not in RESULTS or not isinstance(entry.get("counted"), bool):
            raise SiteError(f"bad result on #{number}")
        if entry.get("why", "older-commit") not in set(WHY) | {"newer-report"}:
            raise SiteError(f"bad why on #{number}")
        source = entry.get("fromIssue", 1)
        if not isinstance(source, int) or isinstance(source, bool) or source < 1:
            raise SiteError(f"bad fromIssue on #{number}")
    if sum(counts.values()) != sum(1 for r in reports if r["counted"]):
        raise SiteError(f"counts and counted reports differ on {release}")


class Site:
    def __init__(self, data, plugins):
        if not isinstance(data, dict) or not GENERATED_RE.fullmatch(str(data.get("generated"))):
            raise SiteError("reports.json has no generated time")
        self.generated = data["generated"]
        self.template = Template((SITE / TEMPLATE).read_text(encoding="utf-8"))
        self.catalog = catalog_plugins(plugins)
        self.plugins = dict(self.catalog)
        self.repos = {}
        self.skipped = []  # keys in reports.json that get no page
        for group, target in (("plugins", self.plugins), ("repos", self.repos)):
            rows = data.get(group)
            if not isinstance(rows, dict):
                raise SiteError(f"reports.json has no {group}")
            for key, releases in rows.items():
                if not isinstance(releases, dict):
                    raise SiteError(f"bad rows for {key!r}")
                for release, row in releases.items():
                    _check_row(release, row)
                plugin = self._plugin(group, key, target)
                if plugin is None:
                    self.skipped.append(key)
                    continue
                plugin.rows = dict(releases)
        reported = [p for p in self._all() if p.rows]
        self.releases = sorted(
            {release for p in reported for release in p.rows}, key=version_key, reverse=True
        )

    def _plugin(self, group, key, target):
        if not isinstance(key, str):
            return None
        if group == "plugins":
            if not ID_RE.fullmatch(key):
                return None
            if key not in target:
                # Reported, but no longer in the catalog.
                target[key] = Plugin("plugins", key, key, in_catalog=False)
            return target[key]
        match = REPO_KEY_RE.fullmatch(key)
        if not match or key != key.lower() or match.group(2) in (".", ".."):
            return None
        target[key] = Plugin("repos", key, key, repo=key, in_catalog=False)
        return target[key]

    def _all(self):
        return list(self.plugins.values()) + list(self.repos.values())

    # Pieces.

    def page(self, root, title, description, main, scripts=""):
        generated_text = self.generated.replace("T", " ")[:16] + " UTC"
        return self.template.substitute(
            root=root,
            title=e(title),
            description=e(description),
            main=main,
            rule=e(RULE),
            repo_url=e(REPO_URL),
            generated=e(self.generated),
            generated_text=e(generated_text),
            scripts=scripts,
        )

    @staticmethod
    def badge(status):
        return f'<span class="status status-{status}">{e(STATUS_NAMES[status])}</span>'

    @staticmethod
    def issue_link(number):
        return f'<a href="{e(ISSUES_URL)}/{number}">#{number}</a>'

    @staticmethod
    def commit_html(plugin, commit):
        if plugin.repo:
            return f'<a href="https://github.com/{e(plugin.repo)}/commit/{e(commit)}"><code>{e(commit)}</code></a>'
        return f"<code>{e(commit)}</code>"

    def report_item(self, plugin, entry):
        parts = [
            self.issue_link(entry["issue"]),
            e(RESULT_NAMES[entry["result"]]),
            f"Omarchy {e(entry['version'])}",
            "commit " + self.commit_html(plugin, entry["commit"]),
        ]
        if "fromIssue" in entry:
            source = entry["fromIssue"]
            parts.append(
                f'from Omarchy issue <a href="{OMARCHY_ISSUES_URL}/{source}">#{source}</a>'
            )
        if not entry["counted"]:
            why = entry.get("why")
            text = WHY_NEWER["fromIssue" in entry] if why == "newer-report" else WHY.get(why)
            if text:
                parts.append(f'<span class="why">{e(text)}</span>')
        return f'<li class="report">{" · ".join(parts)}</li>'

    # Pages.

    def plugin_row(self, plugin, release, root):
        row = plugin.rows.get(release)
        status = row["status"] if row else "none"
        out = [
            f'<section class="row" id="v-{e(release)}">',
            f'<h2><a href="{root}versions/{e(release)}/">Omarchy {e(release)}</a></h2>',
        ]
        verdict = self.badge(status)
        if status != "none":
            verdict += f' <span class="counts">{e(counts_text(row["counts"]))}</span>'
        out.append(f'<p class="verdict">{verdict}</p>')
        if row is None:
            out.append("</section>")
            return "\n".join(out)
        if "fixedFrom" in row:
            out.append(
                '<p class="history">Broken in older versions, reported working from commit '
                f"{self.commit_html(plugin, row['fixedFrom'])}.</p>"
            )
        if row.get("unordered"):
            out.append(
                '<p class="history">These reports name more than one plugin commit, and '
                "their order couldn't be found, so they all count together.</p>"
            )
        counted = [r for r in row["reports"] if r["counted"]]
        others = [r for r in row["reports"] if not r["counted"]]
        if counted:
            out.append("<h3>Reports that count</h3>")
            out.append('<ul class="reports counted">')
            out += [self.report_item(plugin, r) for r in counted]
            out.append("</ul>")
        if others:
            word = "report that doesn't" if len(others) == 1 else "reports that don't"
            # With nothing counted, the reports are the whole story: show them.
            opened = "" if counted else " open"
            out.append(f'<details class="others"{opened}>')
            out.append(f"<summary>{len(others)} {word} count</summary>")
            out.append('<ul class="reports">')
            out += [self.report_item(plugin, r) for r in others]
            out.append("</ul></details>")
        out.append("</section>")
        return "\n".join(out)

    def plugin_page(self, plugin):
        root = "../../../" if plugin.group == "repos" else "../../"
        out = ['<nav class="crumbs"><a href="' + root + '">All plugins</a></nav>']
        out.append(f"<h1>{e(plugin.name)}</h1>")
        meta = []
        if plugin.group == "plugins":
            meta.append(f"<code>{e(plugin.key)}</code>")
        if plugin.author:
            meta.append(f"by {e(plugin.author)}")
        if plugin.repo:
            meta.append(f'<a href="https://github.com/{e(plugin.repo)}">source on GitHub</a>')
        if plugin.group == "repos":
            meta.append('<span class="tag">not in the marketplace</span>')
        out.append(f'<p class="meta">{" · ".join(meta)}</p>')

        link = plugin.report_link
        if link:
            out.append(
                f'<p><a class="button" href="{e(link)}">Report how it works for you</a></p>'
            )
            out.append(
                '<p class="hint">The form asks for your Omarchy version '
                "(<code>omarchy version</code> prints it) and the plugin's commit "
                "(<code>git rev-parse --short HEAD</code> in the plugin's folder). "
                "<code>omaworks report &lt;id&gt;</code> fills in both. "
                f'<a href="{INSTALL_URL}">How to install it</a>.</p>'
            )
        else:
            out.append(
                '<p class="note">This ID is no longer in the marketplace catalog, '
                "so new reports on it can't be counted. The reports below stay.</p>"
            )

        if plugin.rows:
            out.append(f'<p class="rule">{e(RULE)}</p>')
            for release in self.releases:
                out.append(self.plugin_row(plugin, release, root))
        else:
            out.append('<section class="row" id="no-reports">')
            out.append(f'<p class="verdict">{self.badge("none")}</p>')
            out.append(
                "<p>Nobody has reported on this plugin yet, on any Omarchy version. "
                "That doesn't mean it works, or that it's broken. If you use it, "
                "your report is the first.</p>"
            )
            out.append("</section>")
        title = f"{plugin.name} on Omarchy · omaworks"
        description = f"Whether {plugin.name} works on each Omarchy version, from the people who use it."
        return self.page(root, title, description, "\n".join(out))

    def version_entry(self, plugin, release):
        row = plugin.rows[release]
        anchor = f"{plugin.path}#v-{release}"
        parts = [f'<a class="name" href="../../{e(anchor)}">{e(plugin.name)}</a>']
        if plugin.group == "plugins" and plugin.name != plugin.key:
            parts.append(f"<code>{e(plugin.key)}</code>")
        if plugin.group == "repos":
            parts.append('<span class="tag">not in the marketplace</span>')
        parts.append(self.badge(row["status"]))
        parts.append(f'<span class="counts">{e(counts_text(row["counts"]))}</span>')
        links = ", ".join(self.issue_link(r["issue"]) for r in row["reports"] if r["counted"])
        parts.append(f'<span class="links">Reports: {links}</span>')
        return f'<li class="entry">{" ".join(parts)}</li>'

    def version_page(self, release):
        root = "../../"
        reported = sorted(
            (p for p in self._all() if release in p.rows), key=lambda p: (p.group, p.key)
        )
        out = [f'<nav class="crumbs"><a href="{root}">All plugins</a></nav>']
        out.append(f"<h1>Omarchy {e(release)}</h1>")
        word = "plugin has" if len(reported) == 1 else "plugins have"
        out.append(f'<p class="meta">{len(reported)} {word} reports on Omarchy {e(release)}.</p>')
        for status in LISTED:
            listed = [p for p in reported if p.rows[release]["status"] == status]
            out.append(f"<h2>{e(LISTED_TITLES[status])}</h2>")
            if listed:
                out.append('<ul class="entries">')
                out += [self.version_entry(p, release) for p in listed]
                out.append("</ul>")
            else:
                out.append(f'<p class="muted">No plugin is reported {e(LISTED_TITLES[status].lower())} here.</p>')
        out.append(
            '<p class="note">A plugin missing from these lists is reported working, '
            "or has no reports yet on this version. Look at its own page before you update.</p>"
        )
        title = f"Omarchy {release}: plugins reported broken · omaworks"
        description = f"Plugins reported broken on Omarchy {release}, from the people who use them."
        return self.page(root, title, description, "\n".join(out))

    def index_page(self):
        root = "./"
        out = ["<h1>Does this Omarchy plugin still work?</h1>"]
        out.append(
            "<p>See what the people who use a plugin report about it, on each Omarchy "
            "version. Search for it by name, ID or author.</p>"
        )
        out.append('<div class="search">')
        out.append('<label for="q">Plugin</label>')
        out.append(
            f'<input id="q" type="search" placeholder="Name, ID or author" '
            f'autocomplete="off" spellcheck="false" data-index="{INDEX}">'
        )
        out.append("</div>")
        out.append(
            '<p id="search-status" class="muted" aria-live="polite">'
            "<noscript>The search needs JavaScript. A plugin's page is at "
            "plugins/&lt;its ID&gt;/.</noscript></p>"
        )
        out.append('<ul id="results" class="results"></ul>')
        out.append(
            '<p id="not-found" class="hint" hidden>A plugin that isn\'t in the marketplace '
            f'can be reported by its GitHub URL in the <a href="{e(build_form_link())}">report form</a>.</p>'
        )
        out.append("<h2>Omarchy versions</h2>")
        if self.releases:
            out.append('<ul class="versions">')
            for release in self.releases:
                rows = [p.rows[release] for p in self._all() if release in p.rows]
                broken = sum(1 for r in rows if r["status"] == "broken")
                out.append(
                    f'<li><a href="versions/{e(release)}/">Omarchy {e(release)}</a> '
                    f'<span class="muted">{broken} reported broken, '
                    f"{len(rows)} with reports</span></li>"
                )
            out.append("</ul>")
        else:
            out.append(f'<p>{self.badge("none")} No reports yet on any Omarchy version.</p>')
        out.append("<h2>How a status is decided</h2>")
        out.append(f'<p class="rule">{e(RULE)}</p>')
        out.append(
            "<p>Only each account's newest report counts. When no result has 60%, the "
            "status is Mixed reports. Every status links to the reports behind it. "
            "No reports yet means nobody has reported: it never means the plugin works.</p>"
        )
        title = "omaworks: does this Omarchy plugin still work?"
        description = "Whether each Omarchy plugin works on each Omarchy version, reported by the people who use it."
        return self.page(root, title, description, "\n".join(out), '<script src="search.js"></script>')

    def search_index(self):
        """catalog-index.json: every plugin's ID, name, author and reported releases."""

        def releases(plugin):
            return sorted(plugin.rows, key=version_key, reverse=True)

        plugins = [
            # A name that is just the ID is left out, and search.js shows the ID.
            [p.key, p.name if p.name != p.key else "", p.author, releases(p)]
            for p in sorted(self.plugins.values(), key=lambda p: p.key)
        ]
        repos = [[p.key, p.path, releases(p)] for p in sorted(self.repos.values(), key=lambda p: p.key)]
        data = {"generated": self.generated, "plugins": plugins, "repos": repos}
        return json.dumps(data, separators=(",", ":"), ensure_ascii=False) + "\n"

    def files(self):
        files = {name: (SITE / name).read_text(encoding="utf-8") for name in ASSETS}
        files["index.html"] = self.index_page()
        files[INDEX] = self.search_index()
        for plugin in self._all():
            files[f"{plugin.path}index.html"] = self.plugin_page(plugin)
        for release in self.releases:
            files[f"versions/{release}/index.html"] = self.version_page(release)
        return files


def render(data, plugins):
    """(every file of the site except reports.json as {path: text}, skipped keys).

    data is reports.json's content, plugins the catalog's plugins list.
    """
    site = Site(data, plugins)
    return site.files(), site.skipped
