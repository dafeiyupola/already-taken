# Does this problem exist? Four repositories, 71 issues

The tool answers "is someone already on this issue?". Before claiming that question matters, it should be measured — and the first two attempts to measure it were wrong in opposite directions.

## Round one: one repository, and a number I wanted

`flisk-sh/flisk`, 50 open `good first issue`s, 2026-11-12. First run:

```
total 50   taken 15   unsure 6   free 29
```

Thirty percent taken. That number would have gone straight into this README.

**A spot-check killed it.** The tool said `#3852` was solved by merged PR `#3850`. `#3852` is still open; `#3850`'s body opens with `Fixes #3829` and mentions `#3852` in passing. The tool had been treating *any* cross-reference as a fix. On GitHub, an issue mentioning another issue looks exactly like a PR that closes it.

## Round two: the fix, and an over-correction

Only PRs using GitHub's closing syntax count. Issue-to-issue references stop being leads. Rerun:

```
total 50   taken 0   unsure 21   free 29
```

I wrote down that the data did not support the premise. That was also premature: one repository is one observation.

## Round three: four repositories

| repository | sampled | taken | unsure | free |
|---|---|---|---|---|
| `vercel/next.js` | 11 | **11** | 0 | 0 |
| `lingdojo/kana-dojo` | 30 | 9 | 4 | 17 |
| `flisk-sh/flisk` | 30 | 2 | 22 | 6 |
| `shadcn-ui/ui` | 0 | — | — | — |

**71 issues in total: 22 already taken (31%)**, 26 worth a manual look, 23 free.

## What the number actually says

Not "everyone is competing" and not "nobody is". **It is unevenly distributed, and the distribution is the whole point:**

- **`vercel/next.js`: 11 of 11 taken.** In a large, popular repository, there is no such thing as an unclaimed easy issue.
- **`kana-dojo`: 30%.**
- **`flisk`: 7%.**

People crowd where the repo is famous. So the tool is worth nothing on a random repository and worth a lot on the one you actually want to contribute to — which is, by definition, the crowded one.

## The part that is uncomfortable

Three separate times in this project, a number has said what I wanted it to say:

1. The 15-of-50 that was a bug.
2. The 0-of-50 that let me write "my premise is unsupported".
3. This table, which is better — and which I would not have run if the second number had not embarrassed me.

The pattern underneath: **one sample is an observation, not a rate.** The first two rounds differed only in which way the sample happened to lean.

## What changed in the tool

- A cross-reference is not a fix: `_closes()` reads the referring PR's body for closing syntax instead of trusting the event.
- Issue-to-issue references are no longer leads.
- `scan --repo`, so a backlog can be walked one repository at a time.
- `FREE` now says so when the issue names no file and the third check therefore never ran.

See [case-studies.md](case-studies.md) for the three original incidents this came out of.
