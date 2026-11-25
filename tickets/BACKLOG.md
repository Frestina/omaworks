# Backlog

Work that waits, and why.

- **omaupdateimpact reads reports.json.** Waits until omaupdateimpact's current
  marketplace review is finished, and is built in that repo, not this one. See
  [omaupdateimpact](../SPEC.md#omaupdateimpact).
- **Telling others.** Waits for about one Omarchy release cycle of data. See
  [Telling others](../SPEC.md#telling-others).
- **A bar button for reporting.** An Omarchy plugin that opens the shortcut or the
  agent option. Waits until 006 and 007 are in use.
- **Fading old reports.** Rejected for now in [Counting](../SPEC.md#counting).
  Revisit only if real data shows a need.
- **Error lines from Nejcc/omarchy-safe-update.** Its log reading may be reusable for
  `--logs`. Read its license and code before borrowing anything.
- **Reports from the edge channel.** `omarchy-dev` versions such as
  `4.0.0.r7195.g3ac4365-1` fail the check, because they belong to no release row.
  Edge users could be the earliest warning. Needs a decision on how to group them.
  See [Checking reports](../SPEC.md#checking-reports).
- **Old IDs of renamed plugins.** A report on an ID the catalog no longer lists
  fails the check, since the catalog has no rename field. Accepting it would mean
  reading `renamedFrom` from every plugin's manifest. See
  [Plugins](../SPEC.md#plugins).
- **Labels left by spam.** The check creates a `plugin:` or `repo:` label for any
  report that passes, and a spammer can pass with any public repo URL. Closing the
  report as `spam` leaves the label. Moderation (008) could delete Action-made
  labels that no open report uses. Waits until spam is seen.
- **Caching commit dates between builds.** Each build asks GitHub for the date of
  every commit on a row with reports on more than one commit. The Action's token
  allows 1000 requests an hour. A commit's date never changes, so they could be
  kept between builds. Waits until a build comes near the limit. See
  [Counting](../SPEC.md#counting).
- **A 404 page.** A link to a plugin page that doesn't exist, such as an ID never
  in the catalog, gets GitHub's own 404. Ours could point to the search. Its links
  would need the site's full path, since it is served at any depth. See
  [The website](../SPEC.md#the-website).
- **Working plugins on a version's page.** It lists Broken, Mixed reports and
  Works with problems. A list of plugins reported working there could help people
  about to update. Waits until there are enough reports to make it worth reading.
- **Fewer pages per build.** Every build writes a page for each of the catalog's
  7054 plugins, 17 MB in all. If deploys get slow, plugins without reports could
  share one page that the search links to. See [The website](../SPEC.md#the-website).
- **Installing the shortcut.** `bin/omaworks` runs from a clone of this repo. How
  a reporter gets `omaworks` on their PATH, and what the README tells them, is not
  decided: an AUR package, a plugin, or a line to copy. See
  [The shortcut](../SPEC.md#the-shortcut).
- **Local changes in a plugin's checkout.** The shortcut reports `HEAD`, but a
  checkout with local edits is not running that commit. It could warn, or add a
  note to the draft. Waits until a report shows the need.
- **Warnings over several lines.** The shell logs some warnings as one line and
  then indented lines that don't name the file, such as a list of properties.
  `--logs` takes only the line that names the plugin's file. Taking the lines
  that follow would need care not to take another plugin's.
- **Installed plugins outside the marketplace.** The shortcut puts the plugin's
  folder name in the Plugin field. For a plugin the catalog doesn't list, the
  check fails it, since such a plugin is reported by repo URL. The shortcut has
  no network to ask the catalog, but it could offer the checkout's `origin` URL.
  Waits until someone reports one this way.
- **Reports edited after a look.** The moderation agent lists reports opened
  since the last look. A report that passed a look and was later edited into
  spam waits until someone sees it. The check runs again on the edit, but only
  for the form's fields. The look could also list reports updated since then,
  which includes every new comment. Waits until it happens. See
  [Moderation](../SPEC.md#moderation).
