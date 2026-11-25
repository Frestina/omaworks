---
id: "003"
title: Checking reports
milestone: M1 Reports
depends_on: ["002"]
---

# 003 Checking reports

## Goal

A report that can't be counted says so to the reporter right away, and a good one
gets labels that make it easy to find.

## Spec

- [Checking reports](../SPEC.md#checking-reports)
- [Plugins](../SPEC.md#plugins): IDs, repos outside the catalog, `renamedFrom`
- [What must never happen](../SPEC.md#what-must-never-happen)

## Scope

- `omaworks/report.py`: reads an issue body as GitHub renders a form
  (`### Label` then the value) into the six fields. It treats the body as untrusted
  text: no field is ever run or rendered as HTML.
- `omaworks/check.py`: the checks from the spec against the catalog
  (`https://plugins.omarchy.org/catalog.json`) and Omarchy's releases and package
  versions. It returns what is wrong in plain words.
- `.github/workflows/check-report.yml`: on issues opened or edited with the `report`
  label. On failure: one comment saying what to fix (edited, not repeated, on later
  edits) and `needs-fix`. On success: `needs-fix` removed, labels for plugin,
  version and result.
- The Action's token can only write issues. Report text never reaches a shell
  command line.
- Tests with fictional fixtures: good forms, each kind of bad field, a hostile body
  (Markdown, HTML, shell characters, a very long field).

## Not in this ticket

- Counting (004). Spam (008).

## Done when

- [ ] Every check in the spec has a passing and a failing test.
- [ ] A hostile body is handled as text, with a test.
- [ ] The Action labels and comments correctly on the real repo, shown with test
      issues closed as `test`.
