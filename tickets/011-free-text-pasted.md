---
id: "011"
title: Free text is pasted, not linked
milestone: M4 Getting it to people
depends_on: ["006", "007"]
---

# 011 Free text is pasted, not linked

## Goal

The reporter can change every word of What happens and Error lines before
Submit. GitHub locks any field the form link fills in, so free text leaves the
link and the shortcut prints it for the reporter to paste.

## Spec

- [The shortcut](../SPEC.md#the-shortcut): "Only the fixed fields go in the link",
  "What it prints", "Link length"
- [The agent option](../SPEC.md#the-agent-option): "The draft", "Reading the files"
- [Open questions](../SPEC.md#open-questions): "A field the link fills in is
  locked" and "GitHub keeps a draft per tab" under Checked
- [What must never happen](../SPEC.md#what-must-never-happen): rules 2 and 3

## Scope

- `omaworks/link.py`: `build_report_link` takes only the plugin, the Omarchy
  version and the commit. `what` and `errors` are gone from it, so nothing can
  put free text in the link by mistake. The 3500 limit stays.
- `omaworks/shortcut.py`: `--logs`, `--what-file` and `--errors-file` print
  their text, cleaned, as the spec's "What it prints" says, and never add it to
  the link. The old "too long, paste it" path goes, since the link can no longer
  get long from free text. The checks on the files (UTF-8, 64 KB, missing)
  stay as they are.
- `skills/report/SKILL.md` step 6: the shortcut prints the draft, and the agent
  tells the user to paste What happens and any Error lines from the terminal into
  the form, change anything they want, pick the Result and press Submit.
- README's Report lines and CONTRIBUTING.md: say that `--logs` and `--agent`
  print text to paste, not that they fill it in.
- Tests: the link never holds `what` or `errors`, with any input. The printed
  output for each of `--logs`, `--what-file` and `--errors-file`, in order and
  cleaned. A test that fails if free text goes back in the link. Remove or
  rewrite the tests of the old too-long path.
- Tried once in the browser by the reviewer, not by you: the link from
  `omaworks report --no-open` on a fictional plugin opens a form where only the
  fixed fields are filled, and pasted text can be deleted. Leave a box for it.
- Review follow-ups: with `--agent`, the printed draft lands in the agent's
  tool output, which many agents fold away. The skill has the agent show the
  cleaned text from the command's output in its last message, one code block per
  field, so the user can copy it.

## Not in this ticket

- Copying the text to the clipboard. Printing is enough to start.
- Anything about the title (GitHub's per-tab draft can override it, but
  `xdg-open` opens a new tab).

## Done when

- [x] No code path puts What happens or Error lines in the link, with tests.
- [x] `--logs`, `--what-file` and `--errors-file` print the cleaned text under
      its heading, before the link, with tests.
- [x] The skill, README and CONTRIBUTING.md say to paste the printed text.
- [x] `tests/run` passes.
- [x] Checked in the browser by the reviewer: only the fixed fields are filled,
      and pasted text can be deleted.
- [x] The skill's step 6 has the agent show the cleaned draft from the
      command's output in its last message, one code block per field, with a
      skill test.

## Checked in the browser (2026-11-25)

By the reviewer, in Chromium on the desktop, signed in as Frestina. The link
from `omaworks report --no-open --what-file … --errors-file …` on a fictional
`example.sky-clock` filled the title, Plugin, Omarchy version and Plugin commit,
and left What happens and Error lines empty. Text typed into What happens could
be shortened and then deleted entirely, and stayed that way. Nothing was
submitted, and no label or issue was created.
