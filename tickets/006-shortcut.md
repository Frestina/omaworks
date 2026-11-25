---
id: "006"
title: The shortcut
milestone: M2 Reading and reporting
depends_on: ["002"]
---

# 006 The shortcut

## Goal

`omaworks report <plugin>` fills in what the machine knows and opens the form, so a
report takes about 30 seconds.

## Spec

- [The shortcut](../SPEC.md#the-shortcut)
- [A report](../SPEC.md#a-report): where each version comes from
- [What must never happen](../SPEC.md#what-must-never-happen): rules 2, 3 and 5
- [Open questions](../SPEC.md#open-questions): "The shell's log" under Checked

## Scope

- `bin/omaworks report <plugin>`: the Omarchy version from `omarchy version`, the
  plugin's commit from its checkout in `~/.config/omarchy/plugins/<id>`, then the link
  from `omaworks/link.py`, opened with `xdg-open`. It prints the link too.
- A plugin that isn't installed, a checkout that isn't git, or a missing
  `omarchy version` each say so and stop. Nothing is guessed.
- `--logs`: the plugin's lines from `journalctl --user -t omarchy-shell` since the
  last boot, chosen by the plugin's folder, colours stripped, the home path replaced
  by `~`, the hostname and username removed, anything token-like removed. They are
  shown before the browser opens.
- `omaworks/clean.py` for the cleaning, with tests on fictional log lines.
- No network access and no GitHub token.

## Not in this ticket

- `--agent` (007).

## Done when

- [x] The link fills in the real form with this machine's versions.
- [x] Cleaning has tests for each kind of personal detail.
- [x] Every failure case stops with a plain message, with tests.
