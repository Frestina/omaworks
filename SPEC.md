# omaworks spec

The source of truth for what this project is and how it behaves. When a decision
changes, change this file in the same commit. The repo is github.com/Frestina/omaworks.

## The problem

Omarchy updates sometimes break third-party plugins. Often nothing says so: a widget
is gone, a panel won't close, a popup stays stuck. 4.0.3 broke about ten known
plugins (omacom/omarchy #10888, #10863, #10929, #10992 and others) and 4.5.0 broke
more (#17794, #18194).

These breaks can't be found by reading the code. A backtest on 2026-11-25 ran
omaupdateimpact v0.3.7's qmllint check over 308 plugins at their pre-release commits,
for 4.0.2 → 4.0.3 and 4.0.6 → 4.5.0. It caught 0 of 11 known breaks and 0 of 9
plugins whose authors pushed a fix after the release. Plugins reach the shell through
loosely typed properties such as `property var bar`, so qmllint sees the same thing
in both versions. The breaks only show when the plugin runs.

So the people who use a plugin are the only ones who find out. Today what they find
is lost in scattered issues, or nowhere.

## What it is

A public record of whether each Omarchy plugin works on each Omarchy version, written
by the people who use it. ProtonDB does the same for Steam games on Linux.

- **Reported by people.** Nothing runs anyone's plugin for them.
- **Per version.** Every report names the Omarchy version and the plugin's commit.
- **Public.** Anyone can read every report and how the status was worked out.
- **Honest.** "No reports" is never shown as "works".
- **No server.** It runs on GitHub: issues, Actions and Pages.

### Who it is for

- People about to update Omarchy who want to know if their plugins survive.
- People whose plugin just broke and who want to tell others.
- Plugin authors, who learn about breaks without waiting for an issue.
- Tools such as omaupdateimpact and marketplace browsers, which read the summary.

## Where it stops

- It doesn't test plugins. That needs a runtime harness in a VM, a different project.
- It doesn't rate plugins. No stars, no reviews of features or looks.
- It isn't a security check. The marketplace's verification stays separate.
- It doesn't fix plugins. It can point at a newer commit that reportedly works.
- It isn't part of Omarchy or the marketplace and needs nothing from them.

## What must never happen

1. **"No reports" shown as working.** Missing data is always shown as missing.
2. **A report sent without the reporter pressing Submit.** The shortcut and the agent
   only ever open a filled-in form in the browser.
3. **Personal details in a draft.** Home paths, usernames, hostnames and anything
   that looks like a token are removed before the form opens.
4. **A status without its reports.** Every status links to the reports behind it.
5. **Anything leaving the machine unasked.** The shortcut reads local facts and opens
   a browser. It sends nothing. Readers of the summary make GET requests only.

## Product shape

One public repository holds everything, built in this order:

1. **The reports repo**: an issue form, and a GitHub Action that checks each report
   and builds `reports.json`. This alone is useful: people can report, and anyone can
   read the issues.
2. **The website**: a static site on GitHub Pages that shows each plugin's status per
   Omarchy version, its reports, and a Report button.
3. **The shortcut**: a command, `omaworks report <plugin>`, that fills in the versions
   and opens the form. Later maybe a bar button.
4. **The agent option**: `omaworks report --agent <plugin>` hands the investigation
   to the user's default coding agent. See [The agent option](#the-agent-option).
5. **Readers**: omaupdateimpact reads `reports.json` before an update. This waits
   until omaupdateimpact's current marketplace review is finished.

## How it works

### Plugins

A plugin is named by its marketplace ID, such as `example.sky-clock`, taken from
`https://plugins.omarchy.org/catalog.json`. The ID is stable when a repo moves. A
plugin that isn't in the catalog can still be reported by repo URL, and is shown
apart as "not in the marketplace".

When the catalog renames an ID, the old reports follow it.

### A report

One report is one GitHub issue, made from the issue form. Its fields:

| Field | Filled in by | Example |
| --- | --- | --- |
| Plugin | the shortcut, or the user | `example.sky-clock` |
| Omarchy version | the shortcut, from `omarchy version` | `4.5.0-3` |
| Plugin commit | the shortcut, from the plugin's git checkout | `3f2a91c` |
| Result | the user | Works / Works with problems / Broken |
| What happens | the user | "Clock disappears from the bar after updating." |
| Error lines | optional, the shortcut or the agent | `BarWidget.qml:41: TypeError: …` |

The form ends with one line: "Your report is public and released as CC0 (public
domain)." That lets any tool reuse `reports.json`.

The issue form is the only way to open an issue. Blank issues are for maintainers
only. Questions and ideas go to the repo's GitHub Discussions, linked from the
form chooser, so the issues hold only reports.

On this machine `omarchy version` printed `4.5.0-3`, while
`/usr/share/omarchy/version` still said `4.0.0.alpha`, so the command is the source.
Plugins in `~/.config/omarchy/plugins/` are git checkouts, so the commit is
`git rev-parse --short HEAD` there.

### Checking reports

The Action runs when an issue is opened or edited. It checks that:

- the plugin ID is in the catalog, or the repo URL is a real GitHub repo;
- the Omarchy version matches a real tag or package version;
- the commit looks like a commit;
- the result is one of the three choices.

A report that fails gets a comment saying what to fix and a `needs-fix` label. It
isn't counted until it passes. A report that passes gets labels for its plugin,
version and result.

A maintainer closing an issue as spam removes it from the counts. A reporter closing
their own issue withdraws it.

The details, decided in ticket 003 (2026-11-25):

**When.** `.github/workflows/check-report.yml` runs on `issues` opened or edited
with the `report` label. It fetches the issue again, so a run always checks the
newest text, and it skips closed issues. The report's fields are read by the
form's headings (`### Plugin` and so on). A missing heading is a missing field.

**Plugin.** Either a catalog ID or a GitHub repo URL.

- An ID passes when `catalog.json` lists it, in any case. The catalog is fetched on
  every run. On 2026-11-25 it listed 7054 IDs, up to 63 characters long. Most have
  a dot, but 281 have none, so the check doesn't require one.
  An unknown ID gets a "did you mean" with the closest catalog ID, if one is close.
- A repo URL is `https://github.com/<owner>/<repo>`. `http://`, no scheme, `www.`, a
  trailing `/` or `.git` are fine. It is real when a GET to
  `api.github.com/repos/<owner>/<repo>`, with the Action's token, answers with a
  public repo. A redirect from a renamed repo is followed.
- A repo URL that the catalog lists fails, and the comment names its ID. Reports on
  a catalog plugin all go under its ID, which stays stable when the repo moves. One
  repo can hold several plugins (Omarchy's own repo holds 40), so the comment lists
  up to five IDs and says how many more there are.

**Omarchy version.** `omarchy version` prints the pacman version of the `omarchy`
package. Releases are `4.5.0-3`. Pre-releases attach the suffix, `4.5.0rc2-1` or
`4.0.0beta3-1`, a convention set in omacom/omarchy-pkgs' PKGBUILD so pacman sorts
them before the release. The tags are in omacom/omarchy: `v4.5.0`, `v4.5.0-rc2`,
`v4.0.0-beta3`.

- The check accepts both forms: the package form, and the tag form with or without
  the `v` (`4.5.0`, `4.5.0-rc2`). A pacman epoch (`1:`) is dropped.
- The version is real when its release names a tag in omacom/omarchy, checked with a
  GET to `git/ref/tags/<tag>`. `4.5.0-3` needs `v4.5.0`. `4.5.0rc2-1` needs
  `v4.5.0-rc2`.
- The package revision isn't checked: the package repo only holds the current
  package, and revisions are grouped anyway. An untagged pre-release fails. Some
  4.0.x RCs were never tagged.
- Development builds fail, since they belong to no release: `omarchy-dev`'s
  `4.0.0.r7195.g3ac4365-1`, and `dev (<hash>)` from a source checkout.
- A report's row is its release: `4.5.0` for `4.5.0-1` and `4.5.0-3`, `4.5.0-rc2` for
  `4.5.0rc2-1`. See [reports.json](#reportsjson). The report keeps the full version.

**Commit.** 7 to 40 hex digits, in any case.

**Result.** Works, Works with problems or Broken, in any case.

What happens and Error lines aren't checked.

**Labels.** A passing report gets three:

| Label | Example |
| --- | --- |
| `plugin:<id>` | `plugin:example.sky-clock` |
| `repo:<owner>/<repo>` for a repo URL, lowercase | `repo:example-dev/weather-strip` |
| `omarchy:<release>` | `omarchy:4.5.0`, `omarchy:4.5.0-rc2` |
| `result:<result>` | `result:works`, `result:problems`, `result:broken` |

- GitHub allows 50 characters in a label name. A longer name keeps its first 43
  characters, then `~` and the first six hex digits of the full name's SHA-256. The
  label's description holds the full ID.
- The Action creates a label the first time it needs it.
- The Action owns only `needs-fix` and labels starting `plugin:`, `repo:`,
  `omarchy:` and `result:`. On each run it removes its own labels that no longer
  fit, so an edit swaps them, and a failing report keeps only `needs-fix`. It never
  touches any other label, such as `report`, `spam`, `test` or `needs-look`.

**The comment.** One comment from `github-actions[bot]` that starts with the hidden
marker `<!-- omaworks:check -->`. Later runs edit it and never add a second. When a
report that failed passes, the comment says so. A report that passes the first time
gets no comment.

- The comment names each field and the rule it breaks. It never repeats the
  reporter's text, so nothing in it can mention, link or render. The only values in
  it are ones the check built, such as the tag `v4.5.9`, or plain catalog IDs.

**Safety.**

- The workflow's token has `issues: write` and `contents: read`, nothing else.
- The report's text never goes into the workflow file through an expression and
  never reaches a shell. The Python code reads the event file and talks to the REST
  API with `urllib`.
- The check reads with GET requests only: the catalog, Omarchy's tags and repo
  lookups. The token goes only to `api.github.com`, never to the catalog's host,
  and a redirect to another host is refused.
- If the catalog or GitHub can't be read, the run fails before it changes anything,
  so an outage never marks a report wrong. Re-running it from the Actions tab
  checks the report again.

### Counting

The rule has to fit in one sentence on the website: "The newest plugin version that
has reports decides, and a result needs at least 60% of those reports."

**Which reports count.** For each plugin and Omarchy version:

1. Only one report per GitHub account counts: that account's newest. Seeded reports
   are the exception: they count once per source issue. See [Seeding](#seeding).
2. Only reports on the newest plugin commit that has any reports count. Reports on
   older commits stay visible as history. Without this, a plugin its author fixed
   would keep showing Broken.

**The status**, from the reports that count:

| Status | When |
| --- | --- |
| No reports yet | no reports count |
| Works | at least 60% say Works |
| Works with problems | at least 60% say Works with problems |
| Broken | at least 60% say Broken |
| Mixed reports | no result reaches 60%, such as 2 Works and 2 Broken |

Examples: 3 Broken and 1 Works is Broken (75%). 2 Works and 2 Broken is Mixed
reports. A single report decides alone, and shows as "1 report".

The counts are always shown beside the status ("3 broken, 1 works"), so one report
never looks like a settled verdict.

**History.** When older commits were reported Broken and the newest is reported
Works, the page says "broken in older versions, reported working from commit
8be04d2".

**No fading over time.** Reports are tied to an Omarchy version, and each new
release starts its own row, so old reports never decide a new version. omadb fades
old reports because hardware reports have no version. These do.

The details, decided in ticket 004 (2026-11-25), built in `omaworks/count.py`:

**Which issues are reports.** An issue counts only when it is open, not a pull
request, labelled `report`, and not labelled `spam` or `test`. So a report closed
as spam, closed as test, or closed by its reporter never counts, and neither does
an open one a maintainer has marked `spam` or `test`.

**It must pass the check, now.** The count reads the body again with the same
code as the check, and runs the same check. What needs the network (is the ID in
the catalog, is the tag real, is the repo public) it takes from the labels the
check left, since they record what the check found. Then the check's labels for
the current text must be exactly the ones on the issue. So:

- a report with `needs-fix`, or not yet checked, doesn't count;
- a report edited into failing stops counting at the next build, even before the
  check has run on the edit, because its text no longer fits its labels;
- the commit comes from the body, since no label holds it.

Why not trust the labels alone: no label holds the commit, and a label shortened
to 50 characters can't give back a long ID. Why not run the whole check again:
that fetches the 18 MB catalog and asks GitHub about every report on every build,
and could disagree with the labels people see on the issue. Labels can only be set
by the Action and maintainers, so trusting them for the network answers is safe.

**One report per account.** The account is the GitHub user's ID, so a renamed
account is still one account. Its newest report is the one opened last, the
highest issue number. Not the last updated: anyone's comment changes that time.

**The newest commit.** Commit hashes have no order, so the count asks the plugin's
repo, with a GET to `api.github.com/repos/<owner>/<repo>/commits/<commit>`, and
takes the committer date.

- The repo is the catalog's `repo` for a catalog ID, or the reported repo itself.
- Commits are looked up only when a row's reports name more than one commit, and
  each one once per build. A row on one commit needs no order.
- A short and a long spelling of one commit are one commit.
- A commit the repo doesn't have, such as a local one never pushed, can't be put in
  order. While any commit that counts was found, reports on commits that weren't
  don't count. So a made-up commit can neither take over a row nor block it.
- If none of them was found, for example when the repo isn't on GitHub or is gone,
  nothing says which is newest. Then they all count together, and the row says
  `"unordered": true`. Nothing is guessed.
- Commits with the same date count together.
- If GitHub can't be read, the build stops and the last file stays published.

**History.** `fixedFrom` is set when the status is `works`, one commit is newest,
and some report on an older commit says Broken, including a reporter's own report
that their newer one replaced. It holds the newest commit as its reports spell it,
the shortest spelling if they differ.

**When it runs.** `.github/workflows/build.yml` builds and publishes the file,
with the website (see [The website](#the-website)):

- on `issues` opened, edited, closed, reopened, labeled, unlabeled or deleted,
  when the issue has, or just lost, the `report` label;
- each time "Check report" finishes, since the check's own label changes start no
  workflow (GitHub starts none for changes made with the Action's token);
- once a day, and by hand from the Actions tab.

It lists every open `report` issue through the REST API, all pages, with a token
that can only read issues and contents. Builds run one at a time, and each reads
every report afresh. The deploy job alone has `pages: write` and `id-token: write`,
as GitHub's Pages deploy needs. No report text reaches the workflow file or a
shell.

### Seeding

An empty site gives nobody a reason to add the first report, so it starts with what
is already known.

- **From Omarchy's issue tracker.** Issues that name a broken plugin and an exact
  version, such as omacom/omarchy #10888, #10929, #10992 and #17794, become reports.
  The owner files them from the Frestina account with a `from-issue` label and a link
  to the issue. The page shows them as "from Omarchy issue #N".
- **They count once per source issue**, not once per account, since one account
  files them all. An issue that names several plugins gives one report per plugin.
- **How the count finds the source** (decided in ticket 004, for 009 to follow):
  the report carries the `from-issue` label, and its "What happens" field holds the
  line from the issue about what happens, followed by the source issue's link,
  `https://github.com/omacom/omarchy/issues/<N>`, exactly in that form. The same link twice is fine. No link, or links to two different
  issues, and the report doesn't count, listed with `"why": "no-source"`. For each
  plugin and Omarchy version, one report counts per source issue: the newest
  opened. The owner's own first-hand reports have no `from-issue` label and count
  as the owner's account, apart from the seeded ones.
- **Only what the issue says.** The result and the line about what happens come
  from the issue. Nothing is guessed. If the issue doesn't name a plugin commit, the
  report uses the newest plugin commit from before the release that broke it.
- **The owner's own plugins.** Reports on plugins the owner runs are ordinary
  first-hand reports, not seeding.

The 4.0.3 breaks are mostly history now. The 4.5.0 ones are the useful part, and
together they show visitors how the site works.

### Moderation

The owner moderates alone, with the Action doing most of the work.

- **The Action** handles bad forms: a comment saying what to fix, a `needs-fix`
  label, and no count until it passes. One report per account stops one person
  stuffing the count.
- **The owner** handles spam and abuse: closing with a `spam` label removes the
  report from the counts, and GitHub's block and "limit interactions" (24 hours to 6
  months) handle people and waves.
- **Disagreements aren't moderation.** "Works for me" from a plugin author is just
  another report, and the counts settle it. Authors may comment "fixed in commit X".
- **CONTRIBUTING.md** says what gets closed: spam, abuse, and reports about
  something other than whether the plugin works.
- **A second maintainer** only later, for example past about 50 reports a week, or
  for long absences.

**An agent as helper.** A coding agent can read new reports and suggest what to do.
It works through a skill in the repo, `skills/moderate/SKILL.md`, started by hand
("look at new omaworks reports") or on a weekly schedule. It:

- lists reports opened since the last look;
- flags likely spam, duplicates, and reports that look like a local config problem
  rather than the plugin;
- groups reports that seem to describe the same break, and links the Omarchy change
  when it is clear;
- drafts replies, such as asking for error lines;
- ends with a short list of proposed actions.

The owner approves each action. The agent may add only a reversible
`needs-look` label on its own. It never closes issues, applies `spam`, edits
reports, blocks anyone or posts a reply without the owner's yes.

Two reasons. Closing or labelling changes public counts. And reports are written by
strangers, so an agent reading them is reading untrusted text that could try to steer
it. It treats every report as data, never as instructions. If it runs on a schedule,
its GitHub token is fine-grained: this one repo, issues only.

The details, decided in ticket 008 (2026-11-25):

**The labels.** `omaworks/labels.py` makes the six fixed labels, run by hand as
`python3 -m omaworks.labels [--dry-run] <owner>/<repo>` with the token in
`GITHUB_TOKEN`. A script, not a workflow: it is needed once per repo and again
only when a label changes here, and run by hand it stays the owner's step.

| Label | Colour | Description |
| --- | --- | --- |
| `report` | `c5def5` | A report on one plugin and one Omarchy version. |
| `needs-fix` | `e99695` | This report can't be counted until it is fixed. |
| `spam` | `3f3f3f` | Spam, abuse, or not about whether a plugin works. Never counted. |
| `needs-look` | `d93f0b` | For the owner to look at. The moderation agent may add it, never remove it. |
| `from-issue` | `bfd4f2` | Seeded from an Omarchy issue. Counts once per source issue. |
| `test` | `ededed` | A test report. Never counted. |

- `needs-fix` is the check's own label, with the same colour and description.
- For each label it sends a GET. A missing one is created. One with another
  colour, description or case is changed back, so running it twice changes
  nothing. `--dry-run` sends only the GETs and says what it would change.
- It touches no other label and no issue. The token is never printed, and goes
  only to `api.github.com`, as everywhere else.

**The last look.** Nothing stores when the agent last looked: not a file, a
comment or a label. State that others can write could be changed to hide
reports. The owner names the date in the prompt. Without one the agent looks back
eight days, so weekly looks overlap by a day. Seeing a report twice is harmless,
since the agent only suggests. Open reports that still carry `needs-look` are
listed again.

**What the agent runs.** It reads with `gh issue list`, `gh issue view`,
`gh release list`, `gh release view` and `gh api` with no option that turns it
into a write. Its only write alone is `gh issue edit <n> --add-label needs-look`,
for likely spam, abuse, text that talks to the agent, and reports not about
whether the plugin works. Values from GitHub reach a command only as issue
numbers, plugin IDs, account names and tags that match strict patterns, never as
words from a report. Each proposed action comes with its command. The agent runs
one only when the owner says yes to that numbered item in the same conversation.
A run nobody watches ends with the list.

**The weekly look** is documented in CONTRIBUTING.md, by hand or on a schedule.
The scheduled token is fine-grained: this repo only, Issues read and write, so it
can add `needs-look`. It could also close and comment, and only the skill stops
that. Issues read only is the stricter choice, and then `needs-look` becomes a
proposal too. No schedule is set up.

### reports.json

The Action rebuilds one file on every change and publishes it with the site, at
`https://frestina.github.io/omaworks/reports.json`. Readers use only this file.

```json
{
  "generated": "2026-12-01T10:00:00Z",
  "plugins": {
    "example.sky-clock": {
      "4.5.0": {
        "status": "works",
        "counts": {"works": 2, "problems": 0, "broken": 0},
        "fixedFrom": "8be04d2",
        "reports": [
          {"issue": 101, "version": "4.5.0-1", "commit": "3f2a91c", "result": "broken",
           "counted": false, "why": "older-commit"},
          {"issue": 104, "version": "4.5.0-3", "commit": "3f2a91c", "result": "broken",
           "counted": false, "why": "older-commit", "fromIssue": 17794},
          {"issue": 107, "version": "4.5.0-3", "commit": "3f2a91c", "result": "broken",
           "counted": false, "why": "newer-report"},
          {"issue": 112, "version": "4.5.0-3", "commit": "8be04d2", "result": "works",
           "counted": true},
          {"issue": 115, "version": "4.5.0-3", "commit": "8be04d2", "result": "works",
           "counted": true}
        ]
      },
      "4.5.0-rc2": {
        "status": "broken",
        "counts": {"works": 0, "problems": 0, "broken": 1},
        "reports": [
          {"issue": 120, "version": "4.5.0rc2-1", "commit": "3f2a91c", "result": "broken",
           "counted": true}
        ]
      }
    }
  },
  "repos": {
    "example-dev/weather-strip": {
      "4.5.0": {
        "status": "problems",
        "counts": {"works": 0, "problems": 1, "broken": 0},
        "reports": [
          {"issue": 123, "version": "4.5.0-3", "commit": "5c0ffee", "result": "problems",
           "counted": true}
        ]
      }
    }
  }
}
```

Versions are grouped by Omarchy release (`4.5.0`), not package revision: `4.5.0-1`
and `4.5.0-3` both count as `4.5.0`. Release candidates get their own row
(`4.5.0-rc2`), because RC reports are the early warning for everyone else. Reports
keep the full version. `status` is one of `none`, `works`, `problems`, `broken` and
`mixed`.

The fields, decided in ticket 004 (2026-11-25):

- `generated` is UTC.
- `plugins` holds catalog IDs, lowercase. `repos` holds plugins reported by repo
  URL, as `owner/repo` in lowercase: these are "not in the marketplace". The two
  never mix.
- `counts` always has all three results. Its numbers are the reports that count.
- `reports` lists every open report on the row that passes the check, oldest
  first: the ones that count (`"counted": true`) and the history (`false`). So
  every status links to the reports behind it, and to the older ones. `why` says
  why one doesn't count: `newer-report` (the same account, or source issue, has a
  newer one), `older-commit`, `commit-not-found` or `no-source` (see
  [Seeding](#seeding)). `fromIssue` is the Omarchy issue a seeded report comes
  from. `version` is as reported, and `commit` as reported in lowercase.
- `fixedFrom` and `unordered` appear only when they apply. See
  [Counting](#counting).
- Closed reports, failing reports and their text never appear. The file holds no
  free text from any report: only IDs, versions, commits and results that passed
  the check's patterns, and issue numbers.

**A missing plugin or version is `none`.** A row appears only when an open report
that passes the check is on it. A reader treats a plugin, or a version of it, that
isn't in the file as `none`, "No reports yet". Never as works, and never as "no
known problems". A plugin whose reports are all withdrawn or closed as spam
disappears the same way. `none` is written only for a row whose reports all don't
count, such as a seeded report without its source link, so its reports are still
listed.

### The website

A static site on GitHub Pages, built by the same Action. It has:

- a search box over the catalog;
- one page per plugin, with a row per Omarchy version, the reports, and a Report
  button that opens the issue form with the plugin filled in;
- a page per Omarchy version listing the plugins reported broken on it.

The details, decided in ticket 005 (2026-11-25), built in `omaworks/site.py` with
the page shell, stylesheet and search script in `site/`:

**Built, not fetched.** `build.yml` runs `python3 -m omaworks.build _site`. It
writes `reports.json` and every page as static HTML into `_site`, then deploys it.
So the rules about what a page may say are Python, tested with `unittest`, and
the pages work without JavaScript. Only the search needs it.

**The catalog stays on the server.** The catalog is 18 MB, too much for a phone
to fetch for a search. The build fetches it once and writes `catalog-index.json`:
each plugin's ID, name, author and the Omarchy versions it has reports on. On
2026-11-25 that was 423 KB, or 136 KB as sent gzipped. The search reads only
this file. It makes no other request, and no page makes any. A
Content-Security-Policy on every page allows nothing else.

**The pages.**

| Page | Path | What |
| --- | --- | --- |
| Front page | `/` | the search, the Omarchy versions with reports, the counting rule |
| A catalog plugin | `plugins/<id>/` | one for every catalog ID, reported or not |
| A plugin outside the marketplace | `repos/<owner>/<repo>/` | one for every repo in `reports.json`, marked "not in the marketplace" |
| An Omarchy version | `versions/<release>/` | one for every release with reports |

On 2026-11-25 that was 7060 files and 17 MB. A repo name that starts with a dot
gets `~` instead in its path, since Pages leaves out such folders and no repo name
has a `~`. A key in `reports.json` that isn't plain (letters, digits, `.`, `_`,
`-`) gets no page, and the build log names it. No catalog ID was like that on
2026-11-25.

**A plugin's page.** A row for every Omarchy version that has any report, newest
first. Each row shows the status, the counts beside it ("3 broken, 1 works", or
"1 report"), the reports that count, and the ones that don't in a fold, with why.
Each report links to its issue, to its commit in the plugin's repo, and to its
Omarchy issue when seeded. A version the plugin has no reports on is its own row,
"No reports yet". A plugin with no reports at all says so in one box, and that
this doesn't mean it works. The counting rule is shown above the rows and at the
foot of every page.

**The Report button** opens `omaworks/link.py`'s link with only the plugin filled
in: the ID, or the repo's URL for a plugin outside the marketplace. The site
doesn't know the reporter's versions, so it says how to find them. An ID that has
left the catalog keeps its page and reports but has no button, since a new
report on it fails the check.

**A version's page** lists the plugins whose status there is Broken, then Mixed
reports, then Works with problems, each with its counts and its counted reports'
links. It says that a plugin missing from the lists is reported working or has
no reports yet.

**The search** matches the ID, name and author, and a pasted GitHub URL finds a
repo outside the marketplace. A result shows "No reports yet", or the versions it
has reports on. It shows no status, so a status is only ever shown next to its
reports.

**Safety.** Names and authors come from the catalog, which is someone else's
text. They are cut to one line of 100 characters and escaped, and the search
puts them in the page as text, never as HTML. Every value from `reports.json` is
checked against its pattern again before it goes into a page or a link. If one
doesn't fit, the build stops and the old site stays published.

**Looks.** Light and dark follow the system. One column, 16 px side margins,
long IDs wrap, so it fits a phone. A status is always a word, never only a
colour, and "No reports yet" has a dashed outline so it never looks like a
result.

To look at the site on this machine with made-up reports:
`python3 -m tests.demo_site <folder>`, then
`python3 -m http.server --directory <folder>`.

### The shortcut

`omaworks report <plugin>` reads the Omarchy version and the plugin's commit, builds
a link to the issue form with those fields filled in, and opens it in the browser. It
posts nothing and needs no GitHub token.

With `--logs` it also adds the plugin's error lines from the shell's log. The shell
logs to the user journal as `omarchy-shell`. Only lines that name the plugin's own
files since the last boot are taken, cleaned as in
[What must never happen](#what-must-never-happen) rule 3, and shown before the form
opens.

How it decides (ticket 006):

- **The plugin.** The argument must be a plugin ID, such as `example.sky-clock`,
  and `~/.config/omarchy/plugins/<id>` must be a folder. A symlink to a folder
  counts.
- **The commit.** The plugin's folder must be the top of its own git checkout.
  `omarchy plugin add` clones each plugin that way. A folder inside some other
  checkout, such as a dotfiles repo holding `~/.config`, counts as not git, so
  that checkout's commit is never taken. `GIT_DIR` and other `GIT_` variables are
  not passed to git.
- **The version.** A development build (`dev`, `dev (3ac4365)`,
  `4.0.0.r7195.g3ac4365-1`) stops the shortcut, since the check would not count
  the report. So does anything that isn't one release version.
- **Stopping.** Each of these, and a missing `omarchy`, `git` or `journalctl`,
  prints one plain line starting `omaworks:` and exits with 1. The form is not
  opened.
- **`--no-open`** prints the link without opening the browser.
- **`--what-file` and `--errors-file`** fill What happens and Error lines with
  the text in a file, cleaned as below. The agent option uses them. See
  [The agent option](#the-agent-option).
- **The browser.** The link is printed before `xdg-open` runs. If `xdg-open`
  fails, the shortcut says so and the reporter opens the printed link.
- **A plugin's lines.** A line is the plugin's when it names a path under
  `~/.config/omarchy/plugins/<id>/`. The closing slash keeps
  `example.sky-clock-pro` out. Every plugin in that folder gets the shell's
  `Module path "…" is outside of the config folder.` warning, so that line is
  left out. A line repeated in the log is shown once. No lines means the shortcut
  says so and opens the form without them.
- **Cleaning** is in `omaworks/clean.py`. Colour codes go. The home path becomes
  `~`, and any other `/home/<name>` becomes `/home/<user>`. Email addresses become
  `<email>`. The hostname becomes `<host>` and the username `<user>`, as whole
  words in any case. The hostname comes from the kernel only, never from DNS.
  Tokens become `<removed>`: known prefixes such as `ghp_`, values after names
  such as `token=` or `password:`, `Bearer` values, and long runs of letters and
  digits such as hashes. Removing too much is safe, so the rules are broad.
- **What cleaning keeps.** The plugin's ID and the paths of files inside its
  folder are left as they are. `omarchy plugin clone` names a clone
  `<username>.<id>`, and the ID is in the Plugin field anyway.
- **Too long.** When the lines make the link longer than 3500 characters, the
  link leaves them out and the shortcut asks the reporter to paste them. They are
  already shown above it.

### The agent option

`omaworks report --agent <plugin>` starts the user's default coding agent through
Omarchy's `omarchy-agent-prompt`, the way `omarchy agent crash` hands a crash to it.
The prompt points at one skill file, so the method lives in one place and works with
any default agent. The skill tells the agent to:

1. collect the Omarchy version, the plugin's commit, and whether a newer commit
   exists upstream;
2. read the plugin's error lines from the journal since the update;
3. compare them with what changed in the Omarchy release, when the change is clear;
4. look for existing reports of the same thing, and suggest adding to one instead of
   opening a duplicate;
5. write the draft and remove personal details;
6. open the filled-in form with `omaworks report` and stop.

How it works (ticket 007):

- **The plugin first.** `--agent` checks the plugin ID and its folder as the
  shortcut does, so a typo stops before an agent starts. It reads nothing else.
  The agent reads the versions itself, with `omaworks report --no-open`.
- **The command line.** `omarchy-agent-prompt --inline <prompt>` when both input
  and output are a terminal, `omarchy-agent-prompt <prompt>` otherwise. The prompt
  is one argument. It names the plugin, the full path of `skills/report/SKILL.md`
  and the full path of `bin/omaworks` in the same checkout, since `omaworks` may
  not be on the PATH. `omaworks` replaces itself with `omarchy-agent-prompt`.
- **The folder.** The agent starts in the current folder, never in the plugin's
  checkout. A checkout can hold an `AGENTS.md` or `CLAUDE.md` by the plugin's
  author, and many agents load those as instructions. A bar button keeps to this.
- **Missing.** No `omarchy-agent-prompt` on the PATH prints one `omaworks:` line
  and exits with 1, before anything else is printed.
- **Alone.** `--agent` can't be combined with `--logs`, `--what-file`,
  `--errors-file` or `--no-open`. That is a usage error.
- **The draft.** The agent fills the form through two options of the shortcut:
  `--what-file <path>` for What happens and `--errors-file <path>` for Error
  lines. They take files, not text, because the draft is built from untrusted
  text: log lines plugins write, reports by strangers, release notes. Text quoted
  into a shell command breaks at an apostrophe, which QML errors and plain
  sentences hold, and in double quotes `$(…)` and backticks run. So report text
  never reaches a shell. The skill has the agent write the files with its own
  file tool into a `mktemp -d` folder, pass only the paths, and remove the folder.
- **Reading the files.** Each is read as UTF-8 and cleaned by
  `omaworks/clean.py`, line by line, before it goes into the link, so rule 3
  holds even when the agent misses something. A missing, unreadable, non-UTF-8
  or bigger than 64 KB file prints one `omaworks:` line and exits with 1.
  `--errors-file` and `--logs` both fill Error lines, so they can't be combined.
  Options can't be shortened, so `--what` is not taken for `--what-file`. When
  the link would be too long, the error lines are left out first and then What
  happens, each printed for the reporter to paste.

**Limit.** Omarchy starts agents with their approval prompts off. The skill forbids
posting and omaworks gives the agent no command that posts, but an agent with its own
GitHub access could still post if it ignored the skill. The README says so plainly.

### omaupdateimpact

A later omaupdateimpact version downloads `reports.json` before an update. For each
installed plugin it reports Broken or Works with problems on the target version as
findings, naming the reports. A plugin with no reports is listed under "no reports
yet", never as clear. This fits its rule that only GET requests to GitHub leave the
machine.

### Telling others

Other places should show the status, in this order:

1. **Wait for data.** About one full Omarchy release cycle with reports for the 50
   or so most-used plugins. Asking with an empty site gets a polite no.
2. **Third-party marketplace browsers first**, such as Bazaar, Plugin Marketplace,
   OmaSift and PlugBrug. Each is one person, and reading one JSON file is a small
   change for them.
3. **Then the official marketplace.** Its plan says engagement data must never
   influence verification, and it avoids new backends. A static JSON shown beside a
   listing fits both, but they may still say no, so the site stands on its own.
4. **Kept apart from omaupdateimpact's listing.** omaworks isn't mentioned in
   omaupdateimpact's marketplace review while that review is open.

## Files

| Path | What |
| --- | --- |
| `.github/ISSUE_TEMPLATE/report.yml` | the issue form |
| `.github/workflows/check-report.yml` | checks each report as it is opened or edited |
| `.github/workflows/build.yml` | builds `reports.json` and the site |
| `bin/omaworks` | the shortcut, in Python |
| `omaworks/` | the shared Python module: checking, counting, building the form link, the shortcut and its cleaning, the agent option, the label script |
| `LICENSE` | MIT, for the code |
| `skills/report/SKILL.md` | the agent's method for writing a report |
| `skills/moderate/SKILL.md` | the agent's method for looking at new reports |
| `CONTRIBUTING.md` | what gets closed, how to report, the labels, and the weekly look |
| `site/` | the website's page shell, stylesheet and search script; `omaworks/site.py` writes the pages |
| `tests/` | tests for the checker, the counting, the shortcut, the label script and the skills |

## Neighbours

- [ponzgpt/omadb](https://github.com/ponzgpt/omadb): the ProtonDB idea for Omarchy
  hardware, not plugins. Worth reading for its tiers and report decay.
- The marketplace (omacom/omarchy-plugin-marketplace): listings, verification and
  hearts. Its "Compatibility failed" only checks the manifest and entry points.
- Nejcc/omarchy-safe-update: checks your own plugins after an update, by validation
  and QML errors in the log. Its log reading is close to what `--logs` needs.
- omaupdateimpact: the first reader. Its qmllint check is a hint, not a verdict.

## Rejected

- **qmllint across the catalog.** The 2026-11-25 backtest caught none of the real
  breaks. See [The problem](#the-problem).
- **Our own server.** It would need hosting, accounts and moderation. GitHub issues
  give accounts, history and moderation for free.
- **Ratings and stars.** The marketplace already has hearts, and opinions about a
  plugin's features aren't what this records.
- **The agent posting reports.** A report is public and carries the reporter's
  GitHub name, so the reporter always presses Submit.

## Open questions

Decided:

1. **Name.** omaworks (2026-11-25). On that day no GitHub repo, marketplace plugin,
   Arch package or AUR package used it.
2. **Account.** Frestina owns the repo and the site (2026-11-25).
3. **Moderation.** The owner alone, with an agent that suggests and the owner
   approving (2026-11-25). See [Moderation](#moderation).
4. **Status rule.** Newest reported plugin commit decides, 60% for a result,
   otherwise Mixed reports, no fading, RCs in their own row (2026-11-25). See
   [Counting](#counting).

5. **Starting data.** Seed from Omarchy's issue tracker, labelled as second-hand
   (2026-11-25). See [Seeding](#seeding).
6. **Language.** Python with only the standard library, tests with `unittest`
   (2026-11-25). The Action's checker and counting and the `omaworks` command share
   one module, so both run the same code and the same tests. Python 3 is on every
   Omarchy machine because many default packages need it. omaupdateimpact relies on
   it the same way. CI tests on 3.11 and 3.15 (2026-11-25): the oldest and newest
   that both Arch (core has 3.14, the AUR has 3.9 to 3.15) and the Ubuntu runner
   (3.11 to 3.15) have. So the code uses nothing newer than 3.11.
7. **License.** MIT for the code. Reports are released as CC0, said on the form, so
   any tool can reuse `reports.json` (2026-11-25).
8. **Telling the marketplace.** Later, in steps (2026-11-25). See
   [Telling others](#telling-others).
9. **Questions.** They go to GitHub Discussions, not issues, so the issues and the
   counts hold only reports (2026-11-25).

No decisions are open.

Checked on 2026-11-25:

- **Prefilling the form.** Checked on the real repo, signed in, with ticket 002's
  form. `template=report.yml` selects the form and adds the `report` label. The
  text fields `plugin`, `omarchy`, `commit`, `what` and `errors` fill in, with
  `&`, `#`, newlines and non-ASCII intact. `title` fills the issue title and
  replaces the form's `[report] ` prefix. The `result` dropdown does not fill in,
  by option text (`Works with problems`, `Broken`) or by number, so the link leaves
  it out and the reporter picks the result, which they do anyway.
- **Link length.** A reporter who isn't signed in to GitHub is sent through
  `github.com/login?return_to=<the link>`, which encodes the link again. Measured
  with links where every character of the text is escaped, the worst case: a
  3973-character link reached the login page, a 4273-character one gave a server
  error, and from about 6000 the login drops the link. Signed-in links work up to
  about 8000. So `omaworks/link.py` refuses links over 3500 characters, counted
  after encoding. A longer link means the caller drops the error lines and tells
  the user to paste them.
- **The shell's log.** The shell logs to the user journal as `omarchy-shell`. A
  third-party plugin's warnings name its file, such as
  `qs:///home/<user>/.config/omarchy/plugins/<id>/Panel.qml:730:17: …`, with ANSI
  colour codes. So `--logs` can pick a plugin's lines by its folder, and must strip
  the colours and replace the home path, which holds the username.
- **`omarchy-agent-prompt`.** It takes `[--inline] <prompt…>` and runs
  `omarchy-agent --prompt`. Without `--inline` the agent opens in its own window
  (`omarchy-launch-tui`), which is what `omarchy agent crash` does. With `--inline`
  it runs in the current terminal. A bar button uses the window. `omaworks report
  --agent` from a terminal uses `--inline`. Rechecked in ticket 007: it joins all
  its arguments into one prompt with spaces, and takes `--inline` only as its
  first argument. `omarchy-agent` moves to `~/Work` when started in the home
  folder and that folder exists. `omarchy agent crash` points its prompt at the
  skill file by full path, the same way.
- **Renamed plugins.** The catalog has no rename field. Its registry only has
  `retiredPluginIds`. Omarchy PR #17929 (open) would let a manifest declare
  `"renamedFrom": ["author.old-name"]`. omaworks follows `renamedFrom` when a
  plugin's manifest has it, and otherwise treats a new ID as a new plugin.
