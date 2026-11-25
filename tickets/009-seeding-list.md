# 009 seeding list: the bodies

Each report as it would be filed from the Frestina account, with the labels
`report` and `from-issue`. See [the list](009-seeding.md#the-list) for how
each value was found. Nothing here is filed until the owner says yes.

Each body is checked with `omaworks/check.py` against the catalog fetched on
2026-11-25 and Omarchy's tags, then read with `omaworks/count.py` as a
`from-issue` report. The check's labels are listed under each one.

## 1. omaplug on 4.0.3-1

Title: `omaplug on 4.0.3-1`

Labels: `report`, `from-issue`, then from the check: `plugin:omaplug`, `omarchy:4.0.3`, `result:broken`

Check: passes, and counts once for its source issue

````markdown
### Plugin

omaplug

### Omarchy version

4.0.3-1

### Plugin commit

97cd361

### Result

Broken

### What happens

After updating from Omarchy 4.0.2 to 4.0.3, the plugin manager shows "0 plugins · 0 enabled". The only sign of it is one QML warning in the journal.

Source: https://github.com/omacom/omarchy/issues/10888

### Error lines

_No response_
````

## 2. quickshell.spotify on 4.0.3-1

Title: `quickshell.spotify on 4.0.3-1`

Labels: `report`, `from-issue`, then from the check: `plugin:quickshell.spotify`, `omarchy:4.0.3`, `result:broken`

Check: passes, and counts once for its source issue

````markdown
### Plugin

quickshell.spotify

### Omarchy version

4.0.3-1

### Plugin commit

e6c9f9f

### Result

Broken

### What happens

After updating from Omarchy 4.0.2 to 4.0.3, the plugin's own scripts fail to start because their path is lost. Sign-in, saving the refreshed token, local playback and Connect device control all break.

Source: https://github.com/omacom/omarchy/issues/10863

### Error lines

_No response_
````

## 3. omamail on 4.0.3-1

Title: `omamail on 4.0.3-1`

Labels: `report`, `from-issue`, then from the check: `plugin:omamail`, `omarchy:4.0.3`, `result:broken`

Check: passes, and counts once for its source issue

````markdown
### Plugin

omamail

### Omarchy version

4.0.3-1

### Plugin commit

27c1b4a

### Result

Broken

### What happens

On Omarchy 4.0.3 the plugin's own scripts fail to start because their path is lost. Signing in does nothing, and a refreshed token is never saved.

Source: https://github.com/omacom/omarchy/issues/10863

### Error lines

_No response_
````

## 4. matjam.omajam on 4.0.3-1

Title: `matjam.omajam on 4.0.3-1`

Labels: `report`, `from-issue`, then from the check: `plugin:matjam.omajam`, `omarchy:4.0.3`, `result:problems`

Check: passes, and counts once for its source issue

````markdown
### Plugin

matjam.omajam

### Omarchy version

4.0.3-1

### Plugin commit

8e0b43e

### Result

Works with problems

### What happens

On Omarchy 4.0.3 the plugin can't read its saved settings, so it always connects to 127.0.0.1 whatever host and port are set. No error is shown.

Source: https://github.com/omacom/omarchy/issues/10863

### Error lines

_No response_
````

## 5. io.github.sirjul1337.lock-explorer on 4.0.3-1

Title: `io.github.sirjul1337.lock-explorer on 4.0.3-1`

Labels: `report`, `from-issue`, then from the check: `plugin:io.github.sirjul1337.lock-explorer`, `omarchy:4.0.3`, `result:problems`

Check: passes, and counts once for its source issue

````markdown
### Plugin

io.github.sirjul1337.lock-explorer

### Omarchy version

4.0.3-1

### Plugin commit

9ab294d

### Result

Works with problems

### What happens

On Omarchy 4.0.3 every setting comes up at its default, and changing one setting deletes all the other saved ones.

Source: https://github.com/omacom/omarchy/issues/10907

### Error lines

_No response_
````

## 6. expose.window-overview on 4.0.3

Title: `expose.window-overview on 4.0.3`

Labels: `report`, `from-issue`, then from the check: `plugin:expose.window-overview`, `omarchy:4.0.3`, `result:problems`

Check: passes, and counts once for its source issue

````markdown
### Plugin

expose.window-overview

### Omarchy version

4.0.3

### Plugin commit

7a31c5e

### Result

Works with problems

### What happens

On Omarchy 4.0.3 turning the hot corner off never takes effect, and the first settings change after the update deleted the saved hot-corner setting.

Source: https://github.com/omacom/omarchy/issues/10907

### Error lines

_No response_
````

## 7. io.github.mtolhuys.news-radar on 4.0.3-1

Title: `io.github.mtolhuys.news-radar on 4.0.3-1`

Labels: `report`, `from-issue`, then from the check: `plugin:io.github.mtolhuys.news-radar`, `omarchy:4.0.3`, `result:broken`

Check: passes, and counts once for its source issue

````markdown
### Plugin

io.github.mtolhuys.news-radar

### Omarchy version

4.0.3-1

### Plugin commit

aaa14a9

### Result

Broken

### What happens

After updating from Omarchy 4.0.2 to 4.0.3, the bar widget never appears and the feed stops refreshing. Nothing is logged.

Source: https://github.com/omacom/omarchy/issues/10992

### Error lines

_No response_
````

## 8. themo.nfl on 4.0.3-1

Title: `themo.nfl on 4.0.3-1`

Labels: `report`, `from-issue`, then from the check: `plugin:themo.nfl`, `omarchy:4.0.3`, `result:broken`

Check: passes, and counts once for its source issue

````markdown
### Plugin

themo.nfl

### Omarchy version

4.0.3-1

### Plugin commit

415fc8c

### Result

Broken

### What happens

After updating from Omarchy 4.0.2 to 4.0.3, the panel throws a TypeError ('refresh' is not a function) and "invalid context" errors on every state change.

Source: https://github.com/omacom/omarchy/issues/10992

### Error lines

_No response_
````

## 9. io.github.andressm415.omaprox on 4.0.3-1

Title: `io.github.andressm415.omaprox on 4.0.3-1`

Labels: `report`, `from-issue`, then from the check: `plugin:io.github.andressm415.omaprox`, `omarchy:4.0.3`, `result:broken`

Check: passes, and counts once for its source issue

````markdown
### Plugin

io.github.andressm415.omaprox

### Omarchy version

4.0.3-1

### Plugin commit

a14a336

### Result

Broken

### What happens

After updating from Omarchy 4.0.2 to 4.0.3, the plugin throws a TypeError ('refresh' is not a function) on every state change.

Source: https://github.com/omacom/omarchy/issues/10992

### Error lines

_No response_
````

## 10. othavi0.agent-bar on 4.0.3-1

Title: `othavi0.agent-bar on 4.0.3-1`

Labels: `report`, `from-issue`, then from the check: `plugin:othavi0.agent-bar`, `omarchy:4.0.3`, `result:broken`

Check: passes, and counts once for its source issue

````markdown
### Plugin

othavi0.agent-bar

### Omarchy version

4.0.3-1

### Plugin commit

0e1bd58

### Result

Broken

### What happens

After updating from Omarchy 4.0.2 to 4.0.3, the popup throws a repeating TypeError ('rebuildFocusTargets' is not a function).

Source: https://github.com/omacom/omarchy/issues/10992

### Error lines

_No response_
````

## 11. ericvrp.bar-autohide on 4.0.3-1

Title: `ericvrp.bar-autohide on 4.0.3-1`

Labels: `report`, `from-issue`, then from the check: `plugin:ericvrp.bar-autohide`, `omarchy:4.0.3`, `result:broken`

Check: passes, and counts once for its source issue

````markdown
### Plugin

ericvrp.bar-autohide

### Omarchy version

4.0.3-1

### Plugin commit

514d6fc

### Result

Broken

### What happens

On Omarchy 4.0.3 the bar never hides. The plugin can no longer read whether a popup is open and takes the missing value as an open popup. It also can no longer see the pointer on the bar.

Source: https://github.com/omacom/omarchy/issues/10996

### Error lines

_No response_
````

## 12. costafot.markets on 4.0.3-1

Title: `costafot.markets on 4.0.3-1`

Labels: `report`, `from-issue`, then from the check: `plugin:costafot.markets`, `omarchy:4.0.3`, `result:problems`

Check: passes, and counts once for its source issue

````markdown
### Plugin

costafot.markets

### Omarchy version

4.0.3-1

### Plugin commit

6923f37

### Result

Works with problems

### What happens

On Omarchy 4.0.3 the bar widget can't tell how much room it has, so it always shrinks to a single glyph, whatever the bar's width. Nothing is logged.

Source: https://github.com/omacom/omarchy/issues/11185

### Error lines

_No response_
````

## 13. io.github.tyrichards.tray on 4.0.3-1

Title: `io.github.tyrichards.tray on 4.0.3-1`

Labels: `report`, `from-issue`, then from the check: `plugin:io.github.tyrichards.tray`, `omarchy:4.0.3`, `result:broken`

Check: passes, and counts once for its source issue

````markdown
### Plugin

io.github.tyrichards.tray

### Omarchy version

4.0.3-1

### Plugin commit

c1590d8

### Result

Broken

### What happens

On Omarchy 4.0.3 dragging a widget onto the tray does nothing, so widgets can't be moved into its drawer. A widget added to the drawer by hand never shows. Nothing is logged.

Source: https://github.com/omacom/omarchy/issues/11932

### Error lines

_No response_
````

## 14. blacksheep.sysload on 4.5.0-3

Title: `blacksheep.sysload on 4.5.0-3`

Labels: `report`, `from-issue`, then from the check: `plugin:blacksheep.sysload`, `omarchy:4.5.0`, `result:broken`

Check: passes, and counts once for its source issue

````markdown
### Plugin

blacksheep.sysload

### Omarchy version

4.5.0-3

### Plugin commit

178ec55

### Result

Broken

### What happens

After updating from Omarchy 4.0.6 to 4.5.0, the bar widget is shrunk to about a fifth of its size, so the gauge and temperature can't be read. No error is logged.

Source: https://github.com/omacom/omarchy/issues/17794

### Error lines

_No response_
````
