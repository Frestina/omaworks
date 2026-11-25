"""Build reports.json and the website from every open report issue.

Run by .github/workflows/build.yml as `python3 -m omaworks.build <folder>`. It
reads the repo from $GITHUB_REPOSITORY and the token from $GITHUB_TOKEN, lists
the issues through the REST API, counts them (see omaworks.count), renders the
site (see omaworks.site) and writes it all into the folder.

If GitHub or the catalog can't be read, it stops with an error and writes
nothing, so the workflow doesn't deploy and the old site stays published.
"""

import json
import os
import shutil
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import PurePosixPath

from omaworks.check import SourceError
from omaworks.count import count
from omaworks.site import INDEX, SiteError, render

REPORTS = "reports.json"


class _Sources:
    """The count's sources, with the catalog fetched once for the whole build."""

    def __init__(self, gh, catalog):
        self._gh = gh
        self._catalog = catalog

    def catalog(self):
        return self._catalog

    def __getattr__(self, name):
        return getattr(self._gh, name)


def build(repo, gh, now):
    """(reports.json's content, the catalog's plugins list)."""
    catalog = gh.catalog()
    return count(gh.report_issues(repo), _Sources(gh, catalog), now), catalog


def dumps(data):
    return json.dumps(data, indent=2, sort_keys=True, ensure_ascii=True) + "\n"


def site_files(data, catalog):
    """(every file of the site, as {path: text}, keys that got no page)."""
    files, skipped = render(data, catalog)
    files[REPORTS] = dumps(data)
    return files, skipped


def _is_build(folder):
    """Whether folder is empty or holds a site this build wrote."""
    names = set(os.listdir(folder))
    return not names or {REPORTS, INDEX} <= names


def write_site(files, folder):
    """Write the site whole into folder, or not at all.

    The files go into a new folder next to it, which then takes its place.
    An existing folder is replaced only when it is empty or an earlier build.
    """
    folder = os.path.abspath(folder)
    if os.path.exists(folder) and not (os.path.isdir(folder) and _is_build(folder)):
        raise FileExistsError(f"{folder} exists and isn't a site this build wrote")
    parent = os.path.dirname(folder)
    os.makedirs(parent, exist_ok=True)
    partial = tempfile.mkdtemp(prefix=".omaworks-site-", dir=parent)
    try:
        for path, text in files.items():
            parts = PurePosixPath(path).parts
            if PurePosixPath(path).is_absolute() or not parts or any(
                p in ("", ".", "..") or p.startswith(".") for p in parts
            ):
                raise ValueError(f"refusing to write {path!r}")
            target = os.path.join(partial, *parts)
            os.makedirs(os.path.dirname(target), exist_ok=True)
            with open(target, "w", encoding="utf-8") as handle:
                handle.write(text)
        os.chmod(partial, 0o755)
        if os.path.exists(folder):
            shutil.rmtree(folder)
        os.replace(partial, folder)
    except BaseException:
        shutil.rmtree(partial, ignore_errors=True)
        raise


def summary(data, files):
    rows = [
        row
        for group in ("plugins", "repos")
        for plugin in data[group].values()
        for row in plugin.values()
    ]
    counted = sum(sum(row["counts"].values()) for row in rows)
    pages = sum(1 for path in files if path.endswith(".html"))
    return (
        f"{len(data['plugins'])} plugins and {len(data['repos'])} repos, "
        f"{len(rows)} rows, {counted} reports counted, {pages} pages"
    )


def main(argv=None):
    from omaworks.github import GitHub

    argv = sys.argv[1:] if argv is None else argv
    if len(argv) != 1:
        print("usage: python3 -m omaworks.build <folder for the site>", file=sys.stderr)
        return 2
    gh = GitHub(os.environ["GITHUB_TOKEN"])
    try:
        data, catalog = build(os.environ["GITHUB_REPOSITORY"], gh, datetime.now(timezone.utc))
        files, skipped = site_files(data, catalog)
    except (SourceError, SiteError) as error:
        print(f"build stopped: {error}", file=sys.stderr)
        return 1
    write_site(files, argv[0])
    print(summary(data, files))
    if skipped:
        print(f"no page for {len(skipped)} keys that aren't plain: {', '.join(map(repr, skipped))}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
