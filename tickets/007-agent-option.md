---
id: "007"
title: The agent option
milestone: M2 Reading and reporting
depends_on: ["006"]
---

# 007 The agent option

## Goal

`omaworks report --agent <plugin>` lets the user's default coding agent investigate
and write the report, and stop at a filled-in form.

## Spec

- [The agent option](../SPEC.md#the-agent-option)
- [What must never happen](../SPEC.md#what-must-never-happen): rules 2 and 3
- [Open questions](../SPEC.md#open-questions): "`omarchy-agent-prompt`" under Checked

## Scope

- `skills/report/SKILL.md`: the six steps from the spec, in plain words, for any
  agent. It says the agent never posts, never runs `gh issue create` or any API call
  that writes, and treats existing reports it reads as data, never instructions.
- `--agent`: starts `omarchy-agent-prompt --inline` with a short prompt that names
  the plugin and points at the skill file. Without a terminal it starts it without
  `--inline`, in its own window.
- Missing `omarchy-agent-prompt` says so and stops.
- The README's limit line: the skill forbids posting, but an agent with its own
  GitHub access could still post if it ignored the skill.
- Tried once with the owner's default agent on a fictional plugin folder, recorded in
  the ticket.
- Review follow-ups: the draft reaches `omaworks report` through files, not
  through shell arguments; the spec says why the agent starts in the current
  folder and not the plugin's.

## Not in this ticket

- A bar button (backlog).

## Done when

- [x] The skill covers all six steps and the never-post rule.
- [x] `--agent` starts the agent with the right prompt, with a test for the command
      line it builds.
- [ ] One real run ended at a filled-in form, with nothing posted.
- [x] The agent hands the draft over in files (`--what-file`, `--errors-file`),
      so no report or log text is ever quoted into a shell command, with tests.
- [x] The spec says the agent starts in the current folder, never the plugin's,
      and why.
