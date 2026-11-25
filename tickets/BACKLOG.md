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
