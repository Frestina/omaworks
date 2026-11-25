# Contributing

omaworks records whether each Omarchy plugin works on each Omarchy version. It
is made of reports by the people who use the plugins.

## How to report

- One report is one issue, made with the Report form. Open it from
  [New issue](https://github.com/Frestina/omaworks/issues/new/choose), from a
  plugin's page on the [website](https://frestina.github.io/omaworks/), or with
  `bin/omaworks report <plugin>` from a clone of this repo, which fills in the
  versions for you.
- One report covers one plugin on one Omarchy version.
- **Plugin** is the plugin's ID from the marketplace, such as `example.sky-clock`.
  For a plugin that isn't in the marketplace, use its GitHub repo URL.
- **Omarchy version** is what `omarchy version` prints.
- **Plugin commit** is what `git rev-parse --short HEAD` prints in the plugin's
  folder, `~/.config/omarchy/plugins/<plugin>`.
- **Result** is Works, Works with problems or Broken. Report when it works, too.
  Those reports count as much as the others.
- **What happens** is what you see, in a sentence or two.
- **Error lines** are optional. Remove your home path, username, hostname and
  anything that looks like a password or token first.
- Your report is public and released as CC0 (public domain).

A check runs on every report. If a field is wrong, it comments with what to fix
and adds `needs-fix`. Edit the issue, and the check runs again. A report with
`needs-fix` isn't counted.

Your newest report on a plugin and Omarchy version is the one that counts. After
you update the plugin, open a new report for the new commit. The old one stays as
history. To withdraw a report, close it.

Questions and ideas go to
[Discussions](https://github.com/Frestina/omaworks/discussions), not issues.

## What gets closed

- **Spam.**
- **Abuse:** insults, harassment, threats.
- **Reports about something other than whether the plugin works:** feature
  requests, questions, help with setup, or reviews of how a plugin looks.

These are closed with the `spam` label, which removes them from the counts. An
account that keeps doing it is blocked. A wave of it can lead to limited
interactions on the repo for a while.

## When you disagree

"Works for me" is just another report. If a report says Broken and the plugin
works for you, open your own report. The counts settle it. Reports aren't
closed because someone disagrees with them.

Plugin authors are welcome to report too, and to comment "fixed in commit X".

## Labels

| Label | What it means |
| --- | --- |
| `report` | The form adds it. Only issues with it are reports. |
| `needs-fix` | The check found a wrong field. Not counted until fixed. |
| `plugin:`, `repo:`, `omarchy:`, `result:` | The check adds these to a report that passes. |
| `needs-look` | For the owner to look at. It changes nothing in the counts. |
| `spam` | Closed as spam, abuse or off topic. Never counted. |
| `from-issue` | Seeded from an issue in Omarchy's tracker. |
| `test` | A test report. Never counted. |

## For maintainers

### The labels

`omaworks/labels.py` creates the fixed labels, or brings back their colour and
description. It never touches the check's labels or any issue. Running it twice
changes nothing. Look first, then run it:

```
GITHUB_TOKEN="$(gh auth token)" python3 -m omaworks.labels --dry-run Frestina/omaworks
GITHUB_TOKEN="$(gh auth token)" python3 -m omaworks.labels Frestina/omaworks
```

The token is read from `GITHUB_TOKEN` and never printed. `--dry-run` only reads.

### The weekly look

A coding agent can read the new reports and suggest what to do, with
[skills/moderate/SKILL.md](skills/moderate/SKILL.md). It lists the reports
opened since the last look, flags likely spam, duplicates and local config
problems, groups reports of the same break, drafts replies, and ends with a
numbered list of proposed actions. The only thing it does alone is add
`needs-look`.

**By hand.** Start your coding agent in a clone of this repo, signed in to `gh`,
and say:

```
Follow skills/moderate/SKILL.md. The last look was 2026-11-18.
```

Without a date it looks back eight days. Read the list. Say yes to an item by
its number and the agent runs that one, or do it yourself.

**On a schedule.** Not set up yet. A scheduled run has nobody to say yes, so it
ends with the list, and nothing but `needs-look` changes. Give it its own token,
never your own:

1. Make a fine-grained personal access token in GitHub's developer settings.
2. Repository access: only select repositories, `Frestina/omaworks`.
3. Repository permissions: Issues, read and write. GitHub adds Metadata, read
   only. Nothing else.
4. Give it an expiry, such as 90 days.
5. Keep it outside the repo, and pass it to the run only, as `GH_TOKEN`.

Run the agent non-interactively in a clone of this repo, with the prompt above,
and keep what it prints.

The token can also close issues and post comments. Only the skill stops the
agent from doing that. If you'd rather it couldn't, choose Issues, read only.
The agent then can't add `needs-look` either, and lists it as a proposal.
