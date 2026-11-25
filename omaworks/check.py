"""Check a parsed report against the catalog and Omarchy's releases.

See SPEC.md, "Checking reports". The checks take their data from a sources
object, so tests can hand in fixed data and never touch the network:

- sources.catalog() returns the catalog's "plugins" list;
- sources.omarchy_tag_exists(tag) says whether omacom/omarchy has that tag;
- sources.github_repo(owner, name) returns the public repo's "owner/name", or
  None when there is no such public repo.

Any of them may raise SourceError when the data can't be fetched or read.
Then nothing is decided about the report.

What is wrong is said in plain words that never repeat the reporter's text:
the field is named and the rule is given. The only values shown are ones this
module built or took from the catalog, after checking they are plain.
"""

import difflib
import hashlib
import re
from dataclasses import dataclass, field

from omaworks.report import LABELS

# Labels this check adds and removes. It never touches any other label.
NEEDS_FIX = "needs-fix"
PLUGIN_PREFIX = "plugin:"
REPO_PREFIX = "repo:"
VERSION_PREFIX = "omarchy:"
RESULT_PREFIX = "result:"
OWNED_PREFIXES = (PLUGIN_PREFIX, REPO_PREFIX, VERSION_PREFIX, RESULT_PREFIX)

# GitHub refuses label names over 50 characters and descriptions over 100.
MAX_LABEL = 50
MAX_DESCRIPTION = 100

# The result as the form's dropdown writes it, and its key in reports.json.
RESULTS = {
    "works": "works",
    "works with problems": "problems",
    "broken": "broken",
}

RESULT_NAMES = {key: name.capitalize() for name, key in RESULTS.items()}
RESULT_COLORS = {"works": "0e8a16", "problems": "fbca04", "broken": "b60205"}

# Longest value read from a one-line field. Longer is wrong, whatever it is.
MAX_FIELD = 200

# `omarchy version` prints pacman's version of the omarchy package, such as
# 4.5.0-3. Pre-releases attach the suffix: 4.5.0rc2-1, 4.0.0beta3-1. The tags
# in omacom/omarchy are v4.5.0, v4.5.0-rc2, v4.0.0-beta3. Both forms are
# accepted, with an optional v and an optional pacman epoch ("1:").
VERSION_RE = re.compile(
    r"(?:\d{1,3}:)?v?(\d{1,4})\.(\d{1,4})\.(\d{1,4})"
    r"(?:-?(rc|beta)(\d{1,4}))?"
    r"(?:-(\d{1,4}))?",
    re.ASCII,
)
# omarchy-dev's version, such as 4.0.0.r7195.g3ac4365-1, or "dev (3ac4365)"
# from a source checkout.
DEV_RE = re.compile(
    r"dev(?: \([0-9a-f]{4,40}\))?|\d+\.\d+\.\d+\.r\d+\.g[0-9a-f]+(?:-\d+)?",
    re.ASCII,
)

COMMIT_RE = re.compile(r"[0-9a-f]{7,40}", re.ASCII)

ID_RE = re.compile(r"[a-z0-9][a-z0-9._-]{0,99}", re.ASCII)

OWNER = r"[A-Za-z0-9](?:[A-Za-z0-9]|-(?=[A-Za-z0-9])){0,38}"
REPO = r"[A-Za-z0-9._-]{1,100}"
REPO_URL_RE = re.compile(
    rf"(?:https?://)?(?:www\.)?github\.com/({OWNER})/({REPO}?)(?:\.git)?/?",
    re.ASCII,
)
LOOKS_LIKE_URL_RE = re.compile(r"(?:https?://|www\.|github\.com/)", re.ASCII)
CATALOG_REPO_RE = re.compile(
    rf"https://github\.com/({OWNER})/({REPO}?)(?:\.git)?/?", re.ASCII
)


class SourceError(RuntimeError):
    """The catalog or GitHub could not be read. Nothing is decided."""


@dataclass(frozen=True)
class Label:
    name: str
    color: str
    description: str


NEEDS_FIX_LABEL = Label(
    NEEDS_FIX, "e99695", "This report can't be counted until it is fixed."
)


@dataclass
class Checked:
    """The outcome of checking one report."""

    problems: list = field(default_factory=list)
    plugin: str = ""  # catalog ID, or "owner/name" for a repo outside it
    in_catalog: bool = True
    version: str = ""  # as reported, such as 4.5.0-3
    release: str = ""  # its row in reports.json, such as 4.5.0 or 4.5.0-rc2
    commit: str = ""
    result: str = ""  # works, problems or broken

    @property
    def ok(self):
        return not self.problems

    def labels(self):
        """The labels a passing report gets, or needs-fix for a failing one."""
        if not self.ok:
            return [NEEDS_FIX_LABEL]
        if self.in_catalog:
            plugin = label(
                PLUGIN_PREFIX, self.plugin, f"Reports on {self.plugin}", "1d76db"
            )
        else:
            plugin = label(
                REPO_PREFIX,
                self.plugin,
                f"Reports on github.com/{self.plugin}, not in the marketplace",
                "5319e7",
            )
        return [
            plugin,
            label(
                VERSION_PREFIX, self.release, f"Reports on Omarchy {self.release}", "006b75"
            ),
            label(
                RESULT_PREFIX,
                self.result,
                f"Reports that say {RESULT_NAMES[self.result]}",
                RESULT_COLORS[self.result],
            ),
        ]


def label(prefix, value, description, color):
    """A label named prefix + value, at most 50 characters.

    A longer name keeps its first 43 characters, then "~" and the first six
    hex digits of the SHA-256 of the full name, so two long IDs that share a
    beginning still get different labels. The description holds the full value.
    """
    name = f"{prefix}{value}"
    if len(name) > MAX_LABEL:
        digest = hashlib.sha256(name.encode()).hexdigest()[:6]
        name = f"{name[: MAX_LABEL - 7]}~{digest}"
    return Label(name, color, description[:MAX_DESCRIPTION])


def is_owned(name):
    """Whether a label is one this check adds and removes."""
    lowered = name.lower()
    return lowered == NEEDS_FIX or lowered.startswith(OWNED_PREFIXES)


def plan_labels(current, wanted):
    """Return (labels to add, label names to remove).

    current is the issue's label names. Only owned labels are removed. GitHub
    compares label names without case, so this does too.
    """
    have = {name.lower() for name in current}
    want = {item.name.lower() for item in wanted}
    add = [item for item in wanted if item.name.lower() not in have]
    remove = [name for name in current if is_owned(name) and name.lower() not in want]
    return add, remove


def release_of(version):
    """The reports.json row for a version, such as 4.5.0 or 4.5.0-rc2.

    Package revisions, a leading v and an epoch are dropped. None when the
    text isn't an Omarchy release version.
    """
    match = VERSION_RE.fullmatch(version.strip().lower())
    if not match:
        return None
    major, minor, patch, pre, pre_number, _rel = match.groups()
    release = f"{int(major)}.{int(minor)}.{int(patch)}"
    if pre:
        release += f"-{pre}{int(pre_number)}"
    return release


class Catalog:
    """The parts of catalog.json the check needs."""

    def __init__(self, plugins):
        if not isinstance(plugins, list):
            raise SourceError("the catalog's plugins is not a list")
        self.ids = set()
        self.by_repo = {}
        self.repo_of = {}  # catalog ID to its GitHub "owner/name", lowercase
        for plugin in plugins:
            if not isinstance(plugin, dict) or not isinstance(plugin.get("id"), str):
                raise SourceError("a catalog entry has no id")
            plugin_id = plugin["id"].lower()
            self.ids.add(plugin_id)
            match = CATALOG_REPO_RE.fullmatch(str(plugin.get("repo") or ""))
            if match:
                key = f"{match.group(1)}/{match.group(2)}".lower()
                self.by_repo.setdefault(key, []).append(plugin_id)
                self.repo_of[plugin_id] = key
        if not self.ids:
            raise SourceError("the catalog lists no plugins")

    def suggest(self, text):
        """A catalog ID close to text, or None. Only plain IDs are offered."""
        matches = difflib.get_close_matches(text, self.ids, n=1, cutoff=0.85)
        if matches and ID_RE.fullmatch(matches[0]):
            return matches[0]
        return None


def _problem(field_id, text):
    return f"**{LABELS[field_id]}**: {text}"


def _one_line(fields, field_id, problems):
    """The field's value, or None after adding a problem."""
    value = fields.get(field_id)
    if value is None:
        problems.append(_problem(
            field_id,
            "this field is missing. Keep the form's headings when you edit the report.",
        ))
        return None
    if not value:
        problems.append(_problem(field_id, "this field is empty."))
        return None
    if "\n" in value or len(value) > MAX_FIELD:
        problems.append(_problem(field_id, "this must be one short line."))
        return None
    return value


# Most catalog IDs a comment lists for one repo. Omarchy's own repo has 40.
MAX_IDS_SHOWN = 5


def _use_the_id(ids):
    ids = [i for i in sorted(ids) if ID_RE.fullmatch(i)]
    if not ids:
        return "this repo is in the marketplace, so use its plugin ID instead."
    if len(ids) == 1:
        return f"this repo is in the marketplace, so use its plugin ID instead: `{ids[0]}`."
    shown = ", ".join(f"`{i}`" for i in ids[:MAX_IDS_SHOWN])
    more = len(ids) - MAX_IDS_SHOWN
    if more > 0:
        shown += f" and {more} more"
    return (
        "this repo holds several plugins in the marketplace, so use the ID of "
        f"the one you report on: {shown}."
    )


def _check_plugin(value, sources, checked, problems):
    if LOOKS_LIKE_URL_RE.match(value.lower()):
        match = REPO_URL_RE.fullmatch(value)
        if not match or match.group(2) in ("", ".", ".."):
            problems.append(_problem(
                "plugin", "a repo URL must look like `https://github.com/owner/repo`."
            ))
            return
        catalog = Catalog(sources.catalog())
        owner, name = match.group(1), match.group(2)
        in_catalog = catalog.by_repo.get(f"{owner}/{name}".lower())
        if not in_catalog:
            full_name = sources.github_repo(owner, name)
            if full_name is None:
                problems.append(_problem("plugin", "there is no public GitHub repo at this URL."))
                return
            in_catalog = catalog.by_repo.get(full_name.lower())
        if in_catalog:
            problems.append(_problem("plugin", _use_the_id(in_catalog)))
            return
        checked.plugin = full_name.lower()
        checked.in_catalog = False
        return
    plugin_id = value.lower()
    catalog = Catalog(sources.catalog())
    if plugin_id in catalog.ids:
        checked.plugin = plugin_id
        return
    text = (
        "this ID is not in the marketplace catalog. Use the ID the catalog "
        "lists, or the plugin's GitHub repo URL if it isn't in the marketplace."
    )
    suggestion = catalog.suggest(plugin_id) if ID_RE.fullmatch(plugin_id) else None
    if suggestion:
        text += f" Did you mean `{suggestion}`?"
    problems.append(_problem("plugin", text))


def _check_version(value, sources, checked, problems):
    lowered = value.lower()
    if DEV_RE.fullmatch(lowered):
        problems.append(_problem(
            "omarchy",
            "this is a development build. Reports are counted per release, "
            "so report on a release or a release candidate.",
        ))
        return
    release = release_of(lowered)
    if release is None:
        problems.append(_problem(
            "omarchy",
            "this isn't an Omarchy version. Give what `omarchy version` prints, "
            "such as `4.5.0-3`.",
        ))
        return
    tag = f"v{release}"
    if not sources.omarchy_tag_exists(tag):
        problems.append(_problem("omarchy", f"Omarchy has no release `{tag}`."))
        return
    checked.version = value
    checked.release = release


def check_report(fields, sources):
    """Check parsed fields (see omaworks.report). Returns a Checked."""
    checked = Checked()
    problems = checked.problems

    plugin = _one_line(fields, "plugin", problems)
    if plugin is not None:
        _check_plugin(plugin, sources, checked, problems)

    version = _one_line(fields, "omarchy", problems)
    if version is not None:
        _check_version(version, sources, checked, problems)

    commit = _one_line(fields, "commit", problems)
    if commit is not None:
        if COMMIT_RE.fullmatch(commit.lower()):
            checked.commit = commit.lower()
        else:
            problems.append(_problem(
                "commit",
                "a commit is 7 to 40 characters of 0-9 and a-f, as "
                "`git rev-parse --short HEAD` prints it in the plugin's folder.",
            ))

    result = _one_line(fields, "result", problems)
    if result is not None:
        key = RESULTS.get(" ".join(result.lower().split()))
        if key:
            checked.result = key
        else:
            problems.append(_problem("result", "pick Works, Works with problems or Broken."))

    return checked


# The comment is found again by this marker, on a comment the bot wrote.
MARKER = "<!-- omaworks:check -->"

PASS_COMMENT = f"{MARKER}\nThanks, this report passes the check now and will be counted."


def failure_comment(problems):
    lines = [
        MARKER,
        "This report can't be counted yet. Please edit the issue and fix:",
        "",
    ]
    lines += [f"- {problem}" for problem in problems]
    lines += ["", "The check runs again when you save the edit."]
    return "\n".join(lines)
