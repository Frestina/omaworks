---
id: "005"
title: The website
milestone: M2 Reading and reporting
depends_on: ["004"]
---

# 005 The website

## Goal

What most people will see: search a plugin, see whether it works on each Omarchy
version and why, and report in one click.

## Spec

- [The website](../SPEC.md#the-website)
- [Counting](../SPEC.md#counting): the one-sentence rule shown on the site
- [What must never happen](../SPEC.md#what-must-never-happen): rules 1 and 4

## Scope

- A static site in `site/`, built by `build.yml` next to `reports.json`. No
  framework and no runtime requests except reading `reports.json` and the catalog.
- A search over the catalog, a page per plugin (a row per Omarchy version with its
  status, counts, history, and links to the reports), and a page per Omarchy version
  listing plugins reported broken.
- A Report button on each plugin page using `omaworks/link.py`'s link format.
- The counting rule in one sentence, and "No reports yet" shown as its own state.
- Works in light and dark, and at phone width.

## Not in this ticket

- A bar widget (backlog).

## Done when

- [x] The three kinds of page work on the live site with test data.
- [x] No plugin without reports is shown as working.
- [x] Every status links to its reports.
