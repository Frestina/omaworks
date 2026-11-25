"""Build the website from fictional reports, to look at it on this machine.

    python3 -m tests.demo_site <folder>
    python3 -m http.server --directory <folder> 8000

Then open http://localhost:8000/. Every plugin, account and report here is made
up. The reports cover each state a row can be in, and test_site uses the same
data.
"""

import sys

from omaworks.build import site_files, write_site
from omaworks.count import count
from tests.fixtures import CATALOG, NOW, FakeCountSources, issue, source_line

NAMES = {
    "example.sky-clock": ("Sky Clock", "example-dev"),
    "example.moon-phase": ("Moon <Phase> & Tides", "example-dev"),
    "example.suite-bar": ("Suite Bar", "suite-folks"),
    "example.suite-panel": ("Suite Panel", "suite-folks"),
    "tidepool": ("Tidepool", "harbour-lab"),
}

# A plugin with reports that has since left the catalog.
RETIRED = "example.old-dial"


def catalog():
    plugins = []
    for item in CATALOG:
        name, author = NAMES.get(item["id"], ("", ""))
        plugins.append({**item, "name": name or item["id"], "author": author or "example-dev"})
    plugins.append({
        "id": "example.quiet-dock",
        "name": "Quiet Dock",
        "author": "example-dev",
        "repo": "https://github.com/example-dev/quiet-dock",
    })
    return plugins


def issues():
    retired = ["plugin:example.old-dial", "omarchy:4.5.0", "result:broken"]
    return [
        # Sky Clock on 4.5.0: broken on the old commit, fixed on the new one.
        issue(101, user=1, result="Broken", omarchy="4.5.0-1"),
        issue(104, user=1001, result="Broken", extra=["from-issue"], what=source_line(17794)),
        issue(107, user=2, result="Broken"),
        issue(112, user=2, result="Works", commit="8be04d2"),
        issue(115, user=3, result="Works", commit="8be04d2"),
        # Sky Clock on the release candidate: one report decides alone.
        issue(120, user=4, result="Broken", omarchy="4.5.0rc2-1"),
        # Moon Phase on 4.5.0: no result reaches 60%.
        issue(130, user=5, result="Works", plugin="example.moon-phase", commit="1a2b3c4"),
        issue(131, user=6, result="Broken", plugin="example.moon-phase", commit="1a2b3c4"),
        issue(132, user=7, result="Works", plugin="example.moon-phase", commit="1a2b3c4"),
        issue(133, user=8, result="Broken", plugin="example.moon-phase", commit="1a2b3c4"),
        # Moon Phase on the release candidate: two commits GitHub doesn't know.
        issue(134, user=5, result="Broken", plugin="example.moon-phase",
              omarchy="4.5.0rc2-1", commit="1a2b3c4"),
        issue(135, user=6, result="Broken", plugin="example.moon-phase",
              omarchy="4.5.0rc2-1", commit="5d6e7f8"),
        # Suite Bar: problems now, worked on an older Omarchy.
        issue(140, user=9, result="Works with problems", plugin="example.suite-bar"),
        issue(141, user=9, result="Works", plugin="example.suite-bar", omarchy="4.0.3-1"),
        # Tidepool: a seeded report without its source link counts for nothing.
        issue(150, user=1001, result="Broken", plugin="tidepool", extra=["from-issue"],
              what="The pool is empty."),
        # A plugin outside the marketplace, reported by its repo.
        issue(160, user=10, result="Works with problems",
              plugin="https://github.com/example-dev/weather-strip", commit="5c0ffee"),
        # A plugin that has left the catalog.
        issue(170, user=11, result="Broken", plugin=RETIRED, labels=retired),
    ]


def demo():
    """(reports.json's content, the catalog's plugins list)."""
    return count(issues(), FakeCountSources(), NOW), catalog()


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) != 1:
        print("usage: python3 -m tests.demo_site <folder>", file=sys.stderr)
        return 2
    data, plugins = demo()
    files, _ = site_files(data, plugins)
    write_site(files, argv[0])
    print(f"wrote {len(files)} files to {argv[0]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
