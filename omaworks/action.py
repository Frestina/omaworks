"""Check the report issue that triggered the workflow, then label and comment.

Run by .github/workflows/check-report.yml as `python3 -m omaworks.action`.
It reads the event from $GITHUB_EVENT_PATH and the token from $GITHUB_TOKEN.
The issue is fetched again, so a run always checks the newest text.

If the catalog or GitHub can't be read, it stops with an error. The check
reads everything before it changes anything, so an outage never marks a
report wrong.
"""

import json
import os
import sys

from omaworks.check import (
    MARKER,
    PASS_COMMENT,
    SourceError,
    check_report,
    failure_comment,
    plan_labels,
)
from omaworks.report import parse_body

BOT_LOGIN = "github-actions[bot]"
REPORT_LABEL = "report"


def find_own_comment(comments):
    """The check's comment: written by the bot and starting with the marker."""
    for comment in comments:
        user = comment.get("user") or {}
        body = comment.get("body") or ""
        if (
            user.get("login") == BOT_LOGIN
            and user.get("type") == "Bot"
            and body.startswith(MARKER)
        ):
            return comment
    return None


def run(event, gh):
    """Check the event's issue. Returns what was done, for the log."""
    repo = event["repository"]["full_name"]
    number = int(event["issue"]["number"])
    issue = gh.get_issue(repo, number)
    names = [item["name"] for item in issue.get("labels") or []]
    if issue.get("pull_request"):
        return "skipped: a pull request"
    if issue.get("state") != "open":
        return "skipped: the issue is closed"
    if REPORT_LABEL not in {name.lower() for name in names}:
        return "skipped: not a report"

    checked = check_report(parse_body(issue.get("body")), gh)

    add, remove = plan_labels(names, checked.labels())
    for item in add:
        gh.ensure_label(repo, item)
    if add:
        gh.add_labels(repo, number, [item.name for item in add])
    for name in remove:
        gh.remove_label(repo, number, name)

    comment = find_own_comment(gh.comments(repo, number))
    if checked.ok:
        wanted = PASS_COMMENT if comment else None
    else:
        wanted = failure_comment(checked.problems)
    if wanted is not None:
        if comment is None:
            gh.create_comment(repo, number, wanted)
        elif comment.get("body") != wanted:
            gh.edit_comment(repo, comment["id"], wanted)

    verdict = "passes" if checked.ok else f"fails {len(checked.problems)} check(s)"
    return (
        f"issue {number} {verdict}; added {[i.name for i in add]}, removed {remove}"
    )


def main():
    from omaworks.github import GitHub

    with open(os.environ["GITHUB_EVENT_PATH"], encoding="utf-8") as handle:
        event = json.load(handle)
    try:
        print(run(event, GitHub(os.environ["GITHUB_TOKEN"])))
    except SourceError as error:
        print(f"check stopped: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
