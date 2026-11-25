---
id: "010"
title: Installing the shortcut
milestone: M4 Getting it to people
depends_on: ["006", "007"]
---

# 010 Installing the shortcut

## Goal

A reporter gets `omaworks` on their PATH with three lines to copy, so they can
report from any folder without knowing where the repo lives.

## Spec

- [The shortcut](../SPEC.md#the-shortcut): "Installing"
- [The agent option](../SPEC.md#the-agent-option): the skill and command paths
- [The website](../SPEC.md#the-website): the Report button's hint
- [Rejected](../SPEC.md#rejected): the AUR package and the plugin

## Scope

- README: an Install section with the spec's three lines, the update line and the
  remove lines, in plain words. Then how to report: `omaworks report <plugin>`,
  `--logs` and `--agent`, one line each. Replace "It is being built" with a link to
  the website, since it is live.
- CONTRIBUTING.md: "How to report" names the installed `omaworks report <plugin>`
  and links the README's Install section, instead of `bin/omaworks` from a clone.
- The website: the hint next to the Report button also says that
  `omaworks report <id>` fills in both versions, and links to the README's Install
  section on GitHub. Only a link, so the Content-Security-Policy is unchanged.
- A test that runs the command through a symlink in another folder, executed
  directly (so the `#!` line is used too), with the faked `omarchy`, `journalctl`
  and `xdg-open` the shortcut tests already use and `HOME` in a temporary folder.
  It prints the link with `--no-open`. A second test checks that `--agent`, run
  through the symlink, names the skill and the command by their real paths in the
  checkout, not the symlink's.
- Tried once: the README's lines run with `HOME` set to a temporary folder,
  cloning this local checkout instead of GitHub, then `omaworks report --no-open`
  on a fictional plugin folder. Recorded in this ticket. Never in the real `$HOME`.

## Not in this ticket

- An AUR package or a plugin (rejected for now, see the spec).
- A bar button (backlog).
- An `omaworks --version` or an update check.

## Done when

- [x] The README has the install, update and remove lines exactly as the spec
      gives them.
- [x] CONTRIBUTING.md and the website's hint point to the installed command, with
      a site test for the hint and its link.
- [x] The symlink tests pass, and fail when `bin/omaworks` uses the symlink's
      folder instead of its real path.
- [x] The README's lines worked in a temporary `HOME`, recorded here.
- [x] `tests/run` passes.

## Tried once

2026-11-25, evening, with `HOME` set to a `mktemp -d` folder and the clone taken
from this local checkout by path instead of GitHub. The real `$HOME` was not
touched.

- The three install lines ran with no error and made the link in
  `~/.local/bin`.
- Running the `ln -s` line again failed with "File exists" and changed nothing.
- A fictional plugin `example.sky-clock` (an empty git commit) with a faked
  `omarchy` printing `4.5.0-3`: from `/`, `omaworks report --no-open
  example.sky-clock` printed `Omarchy 4.5.0-3, example.sky-clock at 26f7633.` and
  the form link with both versions filled in.
- The update line (`git -C ~/.local/share/omaworks pull`) ran with exit 0.
- The two remove lines left both folders empty. The temporary `HOME` was then
  deleted.
