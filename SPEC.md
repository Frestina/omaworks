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

### Seeding

An empty site gives nobody a reason to add the first report, so it starts with what
is already known.

- **From Omarchy's issue tracker.** Issues that name a broken plugin and an exact
  version, such as omacom/omarchy #10888, #10929, #10992 and #17794, become reports.
  The owner files them from the Frestina account with a `from-issue` label and a link
  to the issue. The page shows them as "from Omarchy issue #N".
- **They count once per source issue**, not once per account, since one account
  files them all. An issue that names several plugins gives one report per plugin.
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

### reports.json

The Action rebuilds one file on every change and publishes it with the site. Readers
use only this file.

```json
{
  "generated": "2026-12-01T10:00:00Z",
  "plugins": {
    "example.sky-clock": {
      "4.5.0": {
        "status": "broken",
        "counts": {"works": 1, "problems": 0, "broken": 3},
        "fixedFrom": "8be04d2",
        "reports": [101, 104, 107, 112]
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

### The website

A static site on GitHub Pages, built by the same Action. It has:

- a search box over the catalog;
- one page per plugin, with a row per Omarchy version, the reports, and a Report
  button that opens the issue form with the plugin filled in;
- a page per Omarchy version listing the plugins reported broken on it.

### The shortcut

`omaworks report <plugin>` reads the Omarchy version and the plugin's commit, builds
a link to the issue form with those fields filled in, and opens it in the browser. It
posts nothing and needs no GitHub token.

With `--logs` it also adds the plugin's error lines from the shell's log. The shell
logs to the user journal as `omarchy-shell`. Only lines that name the plugin's own
files since the last boot are taken, cleaned as in
[What must never happen](#what-must-never-happen) rule 3, and shown before the form
opens.

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
| `.github/workflows/reports.yml` | checks reports, builds `reports.json` and the site |
| `bin/omaworks` | the shortcut, in Python |
| `omaworks/` | the shared Python module: checking, counting, building the form link |
| `LICENSE` | MIT, for the code |
| `skills/report/SKILL.md` | the agent's method for writing a report |
| `skills/moderate/SKILL.md` | the agent's method for looking at new reports |
| `CONTRIBUTING.md` | what gets closed, and how to report |
| `site/` | the website's source |
| `tests/` | tests for the checker, the counting and the shortcut |

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

No decisions are open.

Checked on 2026-11-25:

- **Prefilling the form.** GitHub's form schema says a field's `id` "is the
  canonical identifier for the field in URL query parameter prefills", and the
  issue docs say URL parameters can "fill custom text fields" in issue forms. So
  the text fields (plugin, versions, commit, what happens) can be prefilled. The docs
  say nothing about dropdowns or checkboxes, or about `template=report.yml`
  selecting a form. Ticket 002 tests both on the real repo. If a dropdown
  can't be prefilled, the reporter picks the result, which they do anyway.
- **The shell's log.** The shell logs to the user journal as `omarchy-shell`. A
  third-party plugin's warnings name its file, such as
  `qs:///home/<user>/.config/omarchy/plugins/<id>/Panel.qml:730:17: …`, with ANSI
  colour codes. So `--logs` can pick a plugin's lines by its folder, and must strip
  the colours and replace the home path, which holds the username.
- **`omarchy-agent-prompt`.** It takes `[--inline] <prompt…>` and runs
  `omarchy-agent --prompt`. Without `--inline` the agent opens in its own window
  (`omarchy-launch-tui`), which is what `omarchy agent crash` does. With `--inline`
  it runs in the current terminal. A bar button uses the window. `omaworks report
  --agent` from a terminal uses `--inline`.
- **Renamed plugins.** The catalog has no rename field. Its registry only has
  `retiredPluginIds`. Omarchy PR #17929 (open) would let a manifest declare
  `"renamedFrom": ["author.old-name"]`. omaworks follows `renamedFrom` when a
  plugin's manifest has it, and otherwise treats a new ID as a new plugin.
