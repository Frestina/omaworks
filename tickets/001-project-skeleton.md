---
id: "001"
title: Project skeleton
milestone: M1 Reports
depends_on: []
---

# 001 Project skeleton

## Goal

A repo every later ticket can build on: the shared Python module, a test runner, CI,
and the files a public repo needs.

## Spec

- [Product shape](../SPEC.md#product-shape)
- [Files](../SPEC.md#files)
- [Open questions](../SPEC.md#open-questions): decisions 6 and 7 (Python, licenses)

## Scope

- `omaworks/__init__.py`, an empty package the later tickets fill.
- `tests/run`, which runs every `unittest` test under `tests/` with the system
  Python, and one placeholder test so the runner has something to run.
- `.github/workflows/ci.yml`: `tests/run` on the oldest and newest Python 3 that
  Arch and GitHub's Ubuntu runner both have, on push and pull request.
- `README.md`: what omaworks is, in a few plain lines, that it is being built, and a
  link to the spec. No install steps yet.
- `LICENSE` (MIT, Frestina, 2026). The README says reports are CC0.

## Not in this ticket

- The issue form (002), any Action beyond CI.

## Done when

- [x] `tests/run` passes locally and in CI.
- [x] CI runs on the two Python versions.
- [x] README and LICENSE are in place, with no personal details.
