"""Count the open report issues into the statuses of reports.json.

See SPEC.md, "Counting" and "reports.json". count() takes the issues as the
REST API lists them and a sources object, so tests can hand in fixed data and
never touch the network:

- sources.catalog() returns the catalog's "plugins" list;
- sources.github_repo(owner, name) as in omaworks.check;
- sources.commit(owner, name, sha) returns (full sha, committer date as an
  aware datetime) for a commit in that GitHub repo, or None when the repo has
  no such commit.

Any of them may raise SourceError. Then nothing is counted and the old file
stays published.

Report text is untrusted. It is read with omaworks.report and checked with
omaworks.check. Only values the check built go into the file: plugin IDs,
repos, versions, commits and results that matched strict patterns, and issue
numbers. No free text from a report is ever written.
"""

import re
from dataclasses import dataclass
from datetime import timezone

from omaworks.check import (
    REPO_PREFIX,
    VERSION_PREFIX,
    Catalog,
    check_report,
    is_owned,
    label,
)
from omaworks.report import parse_body

REPORT = "report"
FROM_ISSUE = "from-issue"
# An open issue with one of these is on its way out and never counts.
SKIP = {"spam", "test"}

THRESHOLD = 60  # percent of the reports that count
RESULTS = ("works", "problems", "broken")
STATUSES = ("none",) + RESULTS + ("mixed",)

# Why a listed report doesn't count.
NEWER_REPORT = "newer-report"  # the same account, or source issue, has a newer one
OLDER_COMMIT = "older-commit"  # a newer plugin commit has reports
COMMIT_NOT_FOUND = "commit-not-found"  # the plugin's repo has no such commit
NO_SOURCE = "no-source"  # a from-issue report that names no one source issue

# A seeded report names its source issue in "What happens" by this URL.
SOURCE_RE = re.compile(
    r"https://github\.com/omacom/omarchy/issues/([1-9][0-9]{0,6})(?![0-9])", re.ASCII
)


@dataclass(frozen=True)
class Report:
    """One open report that passes the check, as the count sees it."""

    issue: int
    group: str  # "plugins" for a catalog ID, "repos" for a repo outside it
    plugin: str  # catalog ID, or "owner/name"
    release: str  # its row, such as 4.5.0 or 4.5.0-rc2
    version: str  # as reported, such as 4.5.0-3
    commit: str  # as reported, lowercase
    result: str  # works, problems or broken
    voter: tuple | None  # ("account", id) or ("issue", n); None when unknown
    source: int | None = None  # the Omarchy issue a seeded report comes from


class _FromLabels:
    """Answers the check's network questions from the labels the check left.

    The check fetched the catalog and asked GitHub when it last ran, and its
    labels record what it found. The count re-reads the body and runs the same
    check, but takes those answers from the labels instead of the network.
    Then the labels the check would give the current text must be exactly the
    ones on the issue, so a report edited since its last check stops counting
    until the check has run on the new text.
    """

    def __init__(self, plugin, names, sources):
        self._plugin = plugin
        self._names = names
        self._sources = sources

    def catalog(self):
        # Any ID passes here. The comparison with the labels decides.
        return [{"id": self._plugin.lower() or "-"}]

    def omarchy_tag_exists(self, tag):
        return _name(VERSION_PREFIX, tag.removeprefix("v")) in self._names

    def github_repo(self, owner, name):
        given = f"{owner}/{name}".lower()
        if _name(REPO_PREFIX, given) in self._names:
            return given
        if not any(n.startswith(REPO_PREFIX) for n in self._names):
            return None
        # The URL may name a repo since renamed. GitHub says what it is now.
        return self._sources.github_repo(owner, name)


def _name(prefix, value):
    return label(prefix, value, "", "").name.lower()


def _label_names(issue):
    names = set()
    for item in issue.get("labels") or []:
        name = item.get("name") if isinstance(item, dict) else item
        if isinstance(name, str):
            names.add(name.lower())
    return names


def read_report(issue, sources):
    """The issue as a Report, or None when it doesn't count at all.

    It counts only when it is an open issue, not a pull request, labelled
    report, not labelled spam or test, and its text passes the check with
    exactly the check's labels on it (so no needs-fix).
    """
    if not isinstance(issue, dict) or issue.get("pull_request"):
        return None
    if issue.get("state") != "open":
        return None
    number = issue.get("number")
    if not isinstance(number, int) or isinstance(number, bool) or number < 1:
        return None
    names = _label_names(issue)
    if REPORT not in names or names & SKIP:
        return None

    fields = parse_body(issue.get("body"))
    checked = check_report(fields, _FromLabels(fields["plugin"] or "", names, sources))
    if not checked.ok:
        return None
    wanted = {item.name.lower() for item in checked.labels()}
    if wanted != {name for name in names if is_owned(name)}:
        return None

    source = None
    if FROM_ISSUE in names:
        found = set(SOURCE_RE.findall(fields["what"] or ""))
        if len(found) == 1:
            source = int(found.pop())
        voter = ("issue", source) if source else None
    else:
        user = issue.get("user") or {}
        account = user.get("id") if isinstance(user, dict) else None
        if not isinstance(account, int) or isinstance(account, bool):
            return None
        voter = ("account", account)

    return Report(
        issue=number,
        group="plugins" if checked.in_catalog else "repos",
        plugin=checked.plugin,
        release=checked.release,
        version=checked.version,
        commit=checked.commit,
        result=checked.result,
        voter=voter,
        source=source,
    )


def status_of(counts):
    """none, a result that has at least 60% of the counts, or mixed."""
    total = sum(counts.values())
    if total == 0:
        return "none"
    for result in RESULTS:
        if counts[result] * 100 >= THRESHOLD * total:
            return result
    return "mixed"


def count_row(reports, find):
    """The row for one plugin and Omarchy release.

    find(commit) returns (full sha, date) for a commit as reported, or None
    when the plugin's repo doesn't have it. It is called only when the row's
    reports name more than one commit.
    """
    reports = sorted(reports, key=lambda r: r.issue)
    why = {}

    # 1. One report per account, or per source issue: the newest opened.
    newest = {}
    for report in reports:
        if report.voter is None:
            why[report.issue] = NO_SOURCE
        else:
            newest[report.voter] = report
    voting = [r for r in reports if r.voter is not None]
    candidates = [r for r in voting if newest[r.voter] is r]
    for report in voting:
        if newest[report.voter] is not report:
            why[report.issue] = NEWER_REPORT

    # 2. Only the newest plugin commit that has reports.
    counted = candidates
    placed = {}
    top = None
    newest_commits = set()
    unordered = False
    if len({r.commit for r in voting}) > 1:
        for commit in sorted({r.commit for r in voting}):
            found = find(commit)
            if found is not None:
                placed[commit] = found
        dated = [r for r in candidates if r.commit in placed]
        if dated:
            top = max(placed[r.commit][1] for r in dated)
            newest_commits = {placed[r.commit][0] for r in dated if placed[r.commit][1] == top}
            counted = [r for r in dated if placed[r.commit][0] in newest_commits]
            kept = {r.issue for r in counted}
            for report in candidates:
                if report.issue not in kept:
                    if report.commit in placed:
                        why[report.issue] = OLDER_COMMIT
                    else:
                        why[report.issue] = COMMIT_NOT_FOUND
        else:
            # None of the commits that count could be found, so nothing says
            # which is newest. They all count, and the row says so.
            unordered = len({r.commit for r in candidates}) > 1

    counts = {result: 0 for result in RESULTS}
    for report in counted:
        counts[report.result] += 1
    row = {"status": status_of(counts), "counts": counts}

    if row["status"] == "works" and len(newest_commits) == 1:
        if any(
            r.result == "broken" and r.commit in placed and placed[r.commit][1] < top
            for r in voting
        ):
            row["fixedFrom"] = min((r.commit for r in counted), key=lambda c: (len(c), c))
    if unordered:
        row["unordered"] = True

    counted_issues = {r.issue for r in counted}
    entries = []
    for report in reports:
        entry = {
            "issue": report.issue,
            "version": report.version,
            "commit": report.commit,
            "result": report.result,
            "counted": report.issue in counted_issues,
        }
        if report.issue in why:
            entry["why"] = why[report.issue]
        if report.source is not None:
            entry["fromIssue"] = report.source
        entries.append(entry)
    row["reports"] = entries
    return row


class _Commits:
    """Finds commits in a plugin's repo, each one once per build."""

    def __init__(self, sources):
        self._sources = sources
        self._catalog = None
        self._found = {}

    def repo(self, group, plugin):
        if group == "repos":
            return plugin
        if self._catalog is None:
            self._catalog = Catalog(self._sources.catalog())
        return self._catalog.repo_of.get(plugin)

    def finder(self, group, plugin):
        def find(commit):
            repo = self.repo(group, plugin)
            if repo is None:
                return None
            key = (repo, commit)
            if key not in self._found:
                owner, name = repo.split("/", 1)
                self._found[key] = self._sources.commit(owner, name, commit)
            return self._found[key]

        return find


def count(issues, sources, now):
    """reports.json's content from the open report issues."""
    rows = {}
    for issue in issues:
        report = read_report(issue, sources)
        if report is not None:
            rows.setdefault((report.group, report.plugin, report.release), []).append(report)
    data = {
        "generated": now.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "plugins": {},
        "repos": {},
    }
    commits = _Commits(sources)
    for (group, plugin, release), reports in sorted(rows.items()):
        row = count_row(reports, commits.finder(group, plugin))
        data[group].setdefault(plugin, {})[release] = row
    return data
