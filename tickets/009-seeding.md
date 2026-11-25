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

## The list

Read again on 2026-11-25: omacom/omarchy #10888, #10863, #10907, #10929, #10992,
#10996, #11185, #11932 and #17794, with their comments. Every plugin ID was found
in the catalog fetched that day. The exact bodies, as the form writes them, are
in [009-seeding-list.md](009-seeding-list.md).

Approved by the owner on 2026-11-25, with the source link in backticks.

All 14 pass `omaworks/check.py` against that catalog and Omarchy's tags, and
`omaworks/count.py` reads each one as a `from-issue` report that counts once for
its source issue. Each commit was found in the plugin's repo with a GET request.

The release dates used, from the tags in omacom/omarchy: `v4.0.3` 2026-09-08
16:49 UTC (a lightweight tag, so its commit's date), `v4.5.0` 2026-11-05 03:02 UTC
(the tagger date). "Newest commit before the release" means the newest commit on
the plugin's default branch before that time.

| # | Plugin | Omarchy | Result | What happens | Commit | Source |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | `omaplug` | `4.0.3-1` | Broken | After updating from Omarchy 4.0.2 to 4.0.3, the plugin manager shows "0 plugins · 0 enabled". The only sign of it is one QML warning in the journal. | `97cd361` | #10888 |
| 2 | `quickshell.spotify` | `4.0.3-1` | Broken | After updating from Omarchy 4.0.2 to 4.0.3, the plugin's own scripts fail to start because their path is lost. Sign-in, saving the refreshed token, local playback and Connect device control all break. | `e6c9f9f` | #10863 |
| 3 | `omamail` | `4.0.3-1` | Broken | On Omarchy 4.0.3 the plugin's own scripts fail to start because their path is lost. Signing in does nothing, and a refreshed token is never saved. | `27c1b4a` | #10863 (a comment) |
| 4 | `matjam.omajam` | `4.0.3-1` | Works with problems | On Omarchy 4.0.3 the plugin can't read its saved settings, so it always connects to 127.0.0.1 whatever host and port are set. No error is shown. | `8e0b43e` | #10863 (a comment) |
| 5 | `io.github.sirjul1337.lock-explorer` | `4.0.3-1` | Works with problems | On Omarchy 4.0.3 every setting comes up at its default, and changing one setting deletes all the other saved ones. | `9ab294d` | #10907 |
| 6 | `expose.window-overview` | `4.0.3` | Works with problems | On Omarchy 4.0.3 turning the hot corner off never takes effect, and the first settings change after the update deleted the saved hot-corner setting. | `7a31c5e` | #10907 (a comment) |
| 7 | `io.github.mtolhuys.news-radar` | `4.0.3-1` | Broken | After updating from Omarchy 4.0.2 to 4.0.3, the bar widget never appears and the feed stops refreshing. Nothing is logged. | `aaa14a9` | #10992 |
| 8 | `themo.nfl` | `4.0.3-1` | Broken | After updating from Omarchy 4.0.2 to 4.0.3, the panel throws a TypeError ('refresh' is not a function) and "invalid context" errors on every state change. | `415fc8c` | #10992 |
| 9 | `io.github.andressm415.omaprox` | `4.0.3-1` | Broken | After updating from Omarchy 4.0.2 to 4.0.3, the plugin throws a TypeError ('refresh' is not a function) on every state change. | `a14a336` | #10992 |
| 10 | `othavi0.agent-bar` | `4.0.3-1` | Broken | After updating from Omarchy 4.0.2 to 4.0.3, the popup throws a repeating TypeError ('rebuildFocusTargets' is not a function). | `0e1bd58` | #10992 |
| 11 | `ericvrp.bar-autohide` | `4.0.3-1` | Broken | On Omarchy 4.0.3 the bar never hides. The plugin can no longer read whether a popup is open and takes the missing value as an open popup. It also can no longer see the pointer on the bar. | `514d6fc` | #10996 |
| 12 | `costafot.markets` | `4.0.3-1` | Works with problems | On Omarchy 4.0.3 the bar widget can't tell how much room it has, so it always shrinks to a single glyph, whatever the bar's width. Nothing is logged. | `6923f37` | #11185 |
| 13 | `io.github.tyrichards.tray` | `4.0.3-1` | Broken | On Omarchy 4.0.3 dragging a widget onto the tray does nothing, so widgets can't be moved into its drawer. A widget added to the drawer by hand never shows. Nothing is logged. | `c1590d8` | #11932 |
| 14 | `blacksheep.sysload` | `4.5.0-3` | Broken | After updating from Omarchy 4.0.6 to 4.5.0, the bar widget is shrunk to about a fifth of its size, so the gauge and temperature can't be read. No error is logged. | `178ec55` | #17794 |

How each row's commit and result were found:

1. Commit: Not named. The issue names v1.3.0. Newest commit before the v4.0.3 tag; its manifest says 1.3.0. The v1.3.0 tag itself is c8c53ec, also 1.3.0. Result: The title says it "silently" breaks the plugin, which now lists no plugins at all.
2. Commit: Named in the issue (e6c9f9f, manifest 1.0.4). It is also the newest commit before the v4.0.3 tag. Result: The issue says the update "broke" the plugin.
3. Commit: Not named for 4.0.3 (another comment names one, on a development build). Newest commit before the v4.0.3 tag (manifest 0.8.2). One more commit, 7f7c1f0, landed after the tag and before the release was published. Result: The comment says "fully broken rather than degraded".
4. Commit: Not named. Newest commit before the v4.0.3 tag (manifest 1.2.0). Result: It still connects, but ignores its settings.
5. Commit: Not named. The issue names v1.6.1. Newest commit before the v4.0.3 tag; its manifest says 1.6.1. The v1.6.1 tag itself is 62e855d, also 1.6.1. Result: The issue says its settings are lost, not that it stops working.
6. Commit: Not named. Newest commit before the v4.0.3 tag (manifest 4.1.0). Result: A setting is ignored and lost; the overview itself is not said to fail.
7. Commit: Not named. The issue names 0.5.5. Newest commit before the v4.0.3 tag, which is also the v0.5.5 tag (manifest 0.5.5). Result: The widget is gone; the title says the plugins "break".
8. Commit: Not named. Newest commit before the v4.0.3 tag (manifest 1.3.1). Result: The issue says the update "broke every" plugin it lists, and going back to 4.0.2 fixed them; it describes only the errors.
9. Commit: Not named. Newest commit before the v4.0.3 tag (manifest 0.3.1). Result: As for themo.nfl.
10. Commit: Not named. Newest commit before the v4.0.3 tag (manifest 10.3.22). Result: As for themo.nfl.
11. Commit: Not named. The issue names 1.3.0. Newest commit before the v4.0.3 tag; its manifest says 1.3.0. The repo has no tags. Result: Hiding the bar is what the plugin does, and it never happens.
12. Commit: Not named. Newest commit before the v4.0.3 tag (manifest 1.0.1). Two more commits, cb42cde and 772f0fc, landed after the tag and before the release was published; the issue was opened two days later. Result: It still shows, only in its smallest form.
13. Commit: Not named. The issue names 1.9.3. Newest commit before the v4.0.3 tag; its manifest says 1.9.3. The repo has no tags. Result: The issue says its headline feature "no longer" works.
14. Commit: Named in the issue (178ec55). The newest commit before the v4.5.0 tag is 7e5be88, two days newer; the issue's own commit is used. Result: The issue says such widgets "silently break"; they can't be read.

### Left out

- **#10929**, `io.github.tyrichards.tray`: the reporter ran an edge build
  (`omarchy-dev 4.0.0.r2083.gd504061-1`), not a release, and development builds
  fail the check. The title names the 4.0.3 sandbox, but not the version they ran.
  The same plugin on 4.0.3-1 is row 13, from #11932.
- **#10863, the comment on a development build**: `omamail` on `omarchy-dev`
  builds, for the same reason. `omamail` on 4.0.3-1 is row 3, from another comment.
- **#10907, the comment's other plugins**: `b.okomart` and `quickshell.spotify` are
  named as "also affected", with no result and nothing about what happens.

### Before filing

- The source link is in backticks, so filing adds nothing to the Omarchy issue's
  timeline. A plain link would add "Frestina mentioned this issue" there. Editing a
  report to a plain link later adds it then. See [Seeding](../SPEC.md#seeding).
- Rows 4, 5, 6 and 12 are Works with problems and rows 8 to 10 Broken, though the
  issue describes only errors for those three. The notes above say which words
  decided. The owner may change any result before filing.
- Row 1 and row 5 name a plugin version that has a tag on an older commit. The rule
  takes the newest commit before the release instead, which has the same version.

## Filed on 2026-11-25

- The 14 bodies from [009-seeding-list.md](009-seeding-list.md) were filed from
  Frestina with `report` and `from-issue`. They are issues #15 to #28, in list
  order: row 1 is #15, row 14 is #28.
- "Check report" passed all 14. Each got its `plugin:`, `omarchy:` and `result:`
  labels. None got `needs-fix` or a comment.
- The published reports.json (generated 2026-11-25T18:21:24Z) has all 14 rows.
  Each report is counted, with `fromIssue` set to its source issue. 13 rows are on
  4.0.3. One, `blacksheep.sysload`, is on 4.5.0.
- Plugin pages show "from Omarchy issue #N" with a link. Checked on
  `blacksheep.sysload`: "from Omarchy issue #17794".
- None of the eight source issues (#10888, #10863, #10907, #10992, #10996, #11185,
  #11932, #17794) has a cross-reference from Frestina/omaworks in its timeline. So
  the backticks worked.

## Done when

- [x] The list is in this ticket and the owner approved it.
- [x] Every seeded report links its source issue and passed the checks.
- [x] The site shows them as "from Omarchy issue #N".
