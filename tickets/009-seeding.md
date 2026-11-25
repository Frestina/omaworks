---
id: "009"
title: Seeding
milestone: M3 Running it
depends_on: ["004", "008"]
---

# 009 Seeding

## Goal

The site opens with the breaks people already reported in Omarchy's issue tracker,
clearly marked as second-hand, plus the owner's own first-hand reports.

## Spec

- [Seeding](../SPEC.md#seeding)
- [Counting](../SPEC.md#counting): seeded reports count once per source issue

## Scope

- A list, in this ticket, of each seeded report before anything is filed: plugin ID,
  Omarchy version, result, the line about what happens, the plugin commit, and the
  source issue. Start from omacom/omarchy #10888, #10863, #10907, #10929, #10992,
  #10996, #11185, #11932 and #17794. Read each issue again: only what it says goes in.
  A plugin no longer in the catalog is reported by repo URL.
- The owner reads the list and says yes before any issue is filed.
- Filed from the Frestina account with `report` and `from-issue`, each linking its
  source issue.
- The owner's own reports on the plugins they run, as ordinary reports, if they want.

## Not in this ticket

- Asking anyone outside to report. See the backlog.

## Done when

- [ ] The list is in this ticket and the owner approved it.
- [ ] Every seeded report links its source issue and passed the checks.
- [ ] The site shows them as "from Omarchy issue #N".
