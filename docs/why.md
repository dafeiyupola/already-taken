# Why this tool exists

Three evenings, in order.

**The first two were ordinary.** An issue was open, had no comments, and nothing
referenced it. I started working. By the time I had a patch, someone had opened a pull
request. The issue stays open until the PR merges, so "the issue is open" never meant
"nobody is on it".

**The third was not ordinary.** Same situation: open issue, no PR, no reference. I fixed
it, wrote tests, opened a pull request — and it was closed, because the repository had
already changed the exact file weeks earlier, in a commit that never mentioned the
issue. GitHub had no cross-reference, so every metadata check said nobody was doing it.

That is the case this tool is for. It asks the timeline for PRs and commits that point at
the issue, and then asks a second, dumber question: **has any *source* file the issue
names changed since the issue was opened?** If yes, the verdict is `UNSURE` rather than a
confident `FREE`.

## What it learned the hard way

- **A cross-reference is not a fix.** The first version counted any linked pull request
  as "taken". On a real sample (`flisk-sh/flisk`, 50 issues) that produced 15 `TAKEN`
  where the truth was 0 — `#3852` was still open while the tool reported `#3850` solved
  it, and `#3850`'s body said `Fixes #3829`. Now only GitHub's closing syntax counts.
- **Documentation churn is noise.** Generated indexes and version notes touch `.md`
  files constantly. One commit editing `docs/wsl2.md` marked 49 of those 50 issues as
  worth-a-look. Only source files count now.
- **Issue-to-issue references are not evidence either.** Issues cite each other all the
  time ("also affects #X"); that says nothing about who is working on it.

## What it is not

It does not tell you whether an issue is *worth* doing — only whether someone already
claimed it. `FREE` means "no evidence anyone is on it", not "this is a good use of your
evening".
