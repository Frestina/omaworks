# Tickets

The work to build omaworks, one file per ticket. [SPEC.md](../SPEC.md) is the source
of truth; each ticket links the sections it builds. Things left for later are in
[BACKLOG.md](BACKLOG.md).

## How this works

- **Status lives only in the tables below.** Ticket files hold no status, so the
  two can never disagree.
- **Next ticket:** the lowest-numbered `todo` whose dependencies are all `done`.
- **Starting:** set it to `in progress`. **Finishing:** every box under "Done
  when" ticked, `tests/run` passes, set it to `done`.
- **Commits** start with the ticket number: `003: check the plugin field`.
- **Statuses:** `todo`, `in progress`, `done`, `blocked`.
- New work found along the way goes to the backlog or a new ticket, never into
  the current one.
- **Fixtures are fictional.** No real paths, hostnames, usernames or personal
  config. Plugin IDs in tests are made up, such as `example.sky-clock`. The repo is
  public.
- **Nothing is filed on GitHub without the owner.** Opening real issues, labels on
  real reports, or anything else other people can see waits for the owner's yes.
  Test reports go in a fork or are closed and labelled `test` right away.

## M1 Reports

| # | Ticket | Depends on | Status |
| --- | --- | --- | --- |
| 001 | [Project skeleton](001-project-skeleton.md) | | done |
| 002 | [The report form](002-report-form.md) | 001 | done |
| 003 | [Checking reports](003-checking-reports.md) | 002 | done |
| 004 | [Counting and reports.json](004-counting.md) | 003 | done |

## M2 Reading and reporting

| # | Ticket | Depends on | Status |
| --- | --- | --- | --- |
| 005 | [The website](005-website.md) | 004 | done |
| 006 | [The shortcut](006-shortcut.md) | 002 | done |
| 007 | [The agent option](007-agent-option.md) | 006 | done |

## M3 Running it

| # | Ticket | Depends on | Status |
| --- | --- | --- | --- |
| 008 | [Moderation](008-moderation.md) | 003 | done |
| 009 | [Seeding](009-seeding.md) | 004, 008 | done |
