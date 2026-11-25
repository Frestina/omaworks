"""Create the repo's fixed labels, or bring them back to their colour and text.

Run by hand, once for a new repo and again after a label changes here:

    GITHUB_TOKEN=<token> python3 -m omaworks.labels --dry-run <owner>/<repo>
    GITHUB_TOKEN=<token> python3 -m omaworks.labels <owner>/<repo>

The token comes from the environment and is never printed. --dry-run makes
GET requests only and says what it would change. Running it twice changes
nothing the second time. It touches only the six labels below, never the
check's plugin:, repo:, omarchy: and result: labels, and never an issue.
See SPEC.md, "Moderation".
"""

import argparse
import os
import re
import sys
from urllib.parse import quote

from omaworks.check import NEEDS_FIX_LABEL, Label, SourceError
from omaworks.count import FROM_ISSUE, REPORT

LABELS = (
    Label(REPORT, "c5def5", "A report on one plugin and one Omarchy version."),
    NEEDS_FIX_LABEL,
    Label("spam", "3f3f3f", "Spam, abuse, or not about whether a plugin works. Never counted."),
    Label(
        "needs-look",
        "d93f0b",
        "For the owner to look at. The moderation agent may add it, never remove it.",
    ),
    Label(FROM_ISSUE, "bfd4f2", "Seeded from an Omarchy issue. Counts once per source issue."),
    Label("test", "ededed", "A test report. Never counted."),
)

REPO_RE = re.compile(r"[A-Za-z0-9-]{1,39}/[A-Za-z0-9._-]{1,100}", re.ASCII)


def same(have, want):
    """Whether a label from GitHub already matches the wanted one."""
    return (
        have.get("name") == want.name
        and str(have.get("color", "")).lower() == want.color
        and (have.get("description") or "") == want.description
    )


def plan(gh, repo):
    """[(action, label)] for each fixed label: create, update or ok.

    GET requests only. GitHub finds a label by name without case, so a label
    spelled Report is updated to report rather than made twice.
    """
    steps = []
    for want in LABELS:
        status, have = gh.request(
            "GET", f"/repos/{repo}/labels/{quote(want.name, safe='')}", allow=(404,)
        )
        if status == 404:
            steps.append(("create", want, None))
        elif not isinstance(have, dict) or not isinstance(have.get("name"), str):
            raise SourceError(f"GitHub sent no label for {want.name}")
        elif same(have, want):
            steps.append(("ok", want, have["name"]))
        else:
            steps.append(("update", want, have["name"]))
    return steps


def apply(gh, repo, steps):
    for action, want, current in steps:
        fields = {"color": want.color, "description": want.description}
        if action == "create":
            gh.request("POST", f"/repos/{repo}/labels", {"name": want.name, **fields})
        elif action == "update":
            gh.request(
                "PATCH",
                f"/repos/{repo}/labels/{quote(current, safe='')}",
                {"new_name": want.name, **fields},
            )


def run(gh, repo, dry_run=False):
    """Plan, then apply unless dry_run. Returns the lines to print."""
    steps = plan(gh, repo)
    if not dry_run:
        apply(gh, repo, steps)
    lines = []
    for action, want, current in steps:
        if action == "ok":
            verb = "ok"
        elif dry_run:
            verb = f"would {action}"
        else:
            verb = f"{action}d"
        was = f" (was {current})" if current and current != want.name else ""
        lines.append(f"{verb:<14} {want.name}{was}")
    return lines


def main(argv=None, environ=None, out=None, err=None, opener=None):
    from omaworks.github import GitHub

    environ = os.environ if environ is None else environ
    out = sys.stdout if out is None else out
    err = sys.stderr if err is None else err
    parser = argparse.ArgumentParser(
        prog="python3 -m omaworks.labels",
        description="Create or fix the repo's fixed labels. The token is read from GITHUB_TOKEN.",
        allow_abbrev=False,
    )
    parser.add_argument("repo", help="owner/repo, such as Frestina/omaworks")
    parser.add_argument(
        "--dry-run", action="store_true", help="GET requests only; say what would change"
    )
    args = parser.parse_args(argv)
    if not REPO_RE.fullmatch(args.repo):
        print(f"omaworks: {args.repo!r} is not owner/repo", file=err)
        return 2
    token = environ.get("GITHUB_TOKEN", "")
    if not token and not args.dry_run:
        print("omaworks: set GITHUB_TOKEN to a token that can write this repo's issues", file=err)
        return 2
    try:
        lines = run(GitHub(token or None, opener=opener), args.repo, dry_run=args.dry_run)
    except SourceError as error:
        # The message names the method and path, never the token.
        print(f"omaworks: {error}", file=err)
        return 1
    for line in lines:
        print(line, file=out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
