"""Build reports.json from every open report issue.

Run by .github/workflows/build.yml as `python3 -m omaworks.build <path>`. It
reads the repo from $GITHUB_REPOSITORY and the token from $GITHUB_TOKEN, lists
the issues through the REST API, counts them (see omaworks.count) and writes
the file.

If GitHub or the catalog can't be read, it stops with an error and writes
nothing, so the workflow doesn't deploy and the old file stays published.
"""

import json
import os
import sys
from datetime import datetime, timezone

from omaworks.check import SourceError
from omaworks.count import count


def build(repo, gh, now):
    return count(gh.report_issues(repo), gh, now)


def dumps(data):
    return json.dumps(data, indent=2, sort_keys=True, ensure_ascii=True) + "\n"


def write(data, path):
    """Write the file whole, or not at all."""
    folder = os.path.dirname(path)
    if folder:
        os.makedirs(folder, exist_ok=True)
    partial = f"{path}.partial"
    with open(partial, "w", encoding="utf-8") as handle:
        handle.write(dumps(data))
    os.replace(partial, path)


def summary(data):
    rows = [
        row
        for group in ("plugins", "repos")
        for plugin in data[group].values()
        for row in plugin.values()
    ]
    counted = sum(sum(row["counts"].values()) for row in rows)
    return (
        f"{len(data['plugins'])} plugins and {len(data['repos'])} repos, "
        f"{len(rows)} rows, {counted} reports counted"
    )


def main(argv=None):
    from omaworks.github import GitHub

    argv = sys.argv[1:] if argv is None else argv
    if len(argv) != 1:
        print("usage: python3 -m omaworks.build <path to reports.json>", file=sys.stderr)
        return 2
    gh = GitHub(os.environ["GITHUB_TOKEN"])
    try:
        data = build(os.environ["GITHUB_REPOSITORY"], gh, datetime.now(timezone.utc))
    except SourceError as error:
        print(f"build stopped: {error}", file=sys.stderr)
        return 1
    write(data, argv[0])
    print(summary(data))
    return 0


if __name__ == "__main__":
    sys.exit(main())
