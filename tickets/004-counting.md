---
id: "004"
title: Counting and reports.json
milestone: M1 Reports
depends_on: ["003"]
---

# 004 Counting and reports.json

## Goal

The one file everything else reads: a status for each plugin and Omarchy version,
worked out exactly as the spec says.

## Spec

- [Counting](../SPEC.md#counting)
- [Seeding](../SPEC.md#seeding): seeded reports count once per source issue
- [reports.json](../SPEC.md#reportsjson)
- [What must never happen](../SPEC.md#what-must-never-happen): rules 1 and 4

## Scope

- `omaworks/count.py`: from a list of checked reports to the statuses. One report per
  account, newest wins, except `from-issue` reports, which count per source issue.
  Only the newest reported plugin commit decides. 60% for a result, otherwise
  `mixed`. Package revisions grouped, RCs in their own row. `fixedFrom` when older
  commits are Broken and the newest is Works. Only open reports count: a report
  closed as `spam`, closed as `test`, or closed by its reporter to withdraw it
  doesn't count.
- `.github/workflows/build.yml`: on any change to a `report` issue and once a day,
  reads every report issue, runs the count, and publishes `reports.json` to GitHub
  Pages.
- Tests for every rule, with the spec's examples as test cases: 3 Broken and 1 Works
  is `broken`, 2 and 2 is `mixed`, one report decides alone, a newer commit's Works
  replaces older Broken.

## Not in this ticket

- The website pages (005). The file is published alone for now.

## Done when

- [x] Every rule in [Counting](../SPEC.md#counting) has a test.
- [x] `reports.json` matches the spec's format, and "no reports" is `none`, never
      missing data read as works.
- [ ] The file is live on GitHub Pages after a test report.
