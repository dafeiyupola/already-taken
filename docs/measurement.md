# How many "good first issues" are already taken? 50 of them, measured

A tool that answers a question should be checked against the question, not against its own output. This is the run where `already-taken` was wrong, how that was caught, and what the corrected number says.

## The question

Take a repository's open `good first issue` backlog. **How many of those issues already have someone on them?**

## The sample

`flisk-sh/flisk`, 50 open issues carrying `good first issue` (numbers 3751–3867, taken 2026-11-12). Chosen because it was the largest such backlog the search returned and the issue numbers are dense, which means an active project rather than a stale one.

## Three rounds

### Round one — 15 "already taken", and wrong

```
total 50   taken 15   unsure 6   free 29
```

Thirty percent. That number would have gone straight into this README as the tool's reason to exist.

**It fell apart on the first spot-check.** The tool said `#3852` was solved by merged PR `#3850`. `#3852` is still open. `#3850`'s body starts with `Fixes #3829` — it mentions `#3852` in passing, nothing more.

The bug: the tool treated *any* cross-reference in the timeline as evidence that the referring PR closed the issue. On GitHub, an issue mentioning another issue produces the same event as a PR that closes it.

### Round two — fixed, and over-corrected

Only PRs whose body uses GitHub's closing syntax now count. But issue-to-issue references were still treated as leads, which pushed everything into `unsure`:

```
total 50   taken 1   unsure 39   free 10
```

A note saying "related to #3859" is not a lead. It is noise wearing the same clothes.

### Round three — the number

```
total 50   taken 0   unsure 21   free 29
```

`unsure` is 21 because the issue bodies name files that changed after the issues were opened — mostly unrelated sweeps through the same files. That is what `unsure` is for: a reason to look, not a verdict.

## What this says, including the part I did not want

**Zero of fifty were already taken.** The honest conclusion is that this particular backlog had nobody competing for it, and the tool found nobody competing for it.

That matters, because the reason I wrote `already-taken` was a run of collisions — three evenings lost to work someone else had already done. It would have been comfortable to say "this is a widespread problem, here is the number". The number does not say that.

What the number *does* support is narrower and duller: **checking is cheap, and the failure mode is expensive.** Three real cases exist (see [case-studies.md](case-studies.md)); the frequency is unknown, and on this sample it is zero.

## What changed in the tool

- A cross-reference is not a fix. `_closes()` reads the referring PR's body for GitHub's closing syntax (`closes`/`fixes`/`resolves` + the issue number) instead of trusting the event.
- Issue-to-issue references no longer count as leads.
- `scan --repo` so a backlog can be walked repository by repository, since the search API cannot be scoped reliably.

Tests were added for the case that broke it: a PR that mentions an issue without closing it must not mark that issue taken.
