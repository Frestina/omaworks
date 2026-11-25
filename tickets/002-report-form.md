---
id: "002"
title: The report form
milestone: M1 Reports
depends_on: ["001"]
---

# 002 The report form

## Goal

The issue form people fill in, and proof of which of its fields a link can fill in.
Everything that builds a report link (the website, the shortcut, the agent) depends
on this.

## Spec

- [A report](../SPEC.md#a-report): the fields and the CC0 line
- [Open questions](../SPEC.md#open-questions): "Prefilling the form" under Checked

## Scope

- `.github/ISSUE_TEMPLATE/report.yml` with the fields from [A report](../SPEC.md#a-report).
  Stable field IDs: `plugin`, `omarchy`, `commit`, `result`, `what`, `errors`. The
  result is a dropdown with Works, Works with problems and Broken. The form adds the
  `report` label. It ends with the CC0 line.
- `.github/ISSUE_TEMPLATE/config.yml`: blank issues off, and a link for questions
  that aren't reports.
- `omaworks/link.py`: builds the report link from plugin, Omarchy version, commit and
  optional text, URL-encoded, and refuses a link longer than GitHub accepts.
  Unit tests for it.
- **On the real repo**, with the owner's yes: open the link in a browser and check
  which fields fill in. Test the three text fields, the dropdown (by option text),
  and whether `template=report.yml` selects the form. Record the result in the spec's
  "Checked" list, replacing the line about what the docs don't say. Close any test
  issue with a `test` label.

- **Review follow-ups:** `link.py` leaves out the result, sets the title, needs only
  the plugin, strips values, and refuses links over 3500 characters. See the spec's
  "Prefilling the form" and "Link length".

## Not in this ticket

- Checking submitted reports (003).

## Done when

- [x] The form renders on GitHub with every field.
- [x] `omaworks/link.py` builds links the real form fills in, with tests.
- [x] The spec records which fields a link can fill in, checked on the real repo.
- [x] `link.py` no longer takes `result`: the dropdown can't be prefilled.
- [x] `link.py` sets `title` to `<plugin> on <omarchy>`, or `<plugin>` without a
  version.
- [x] Only `plugin` is required; `omarchy` and `commit` are optional.
- [x] Values are stripped of surrounding whitespace before encoding.
- [x] `MAX_LINK_LENGTH` is 3500, with its comment pointing at "Link length".
