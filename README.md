# already-taken

Ask GitHub whether someone is already working on an issue — and get an answer that is sometimes *no, but check anyway*.

```
$ already-taken check elviskahoro/buridan-ui#313
elviskahoro/buridan-ui#313: UNSURE — scripts/generate_registry.py changed after the issue was opened (a1819f22 ...)
```

## Why this exists

I wrote this after losing the same evening three times.

The first two were ordinary: the issue was open, no comments, so I started. By the time I had a patch, someone had opened a PR. **An open issue does not mean nobody is on it** — GitHub keeps the issue open until the pull request merges.

The third was not ordinary. The issue was open, there was no PR anywhere, and nothing referenced it. I fixed it, wrote tests, opened a PR — and it was closed, because the repository had already changed the exact file weeks earlier, by a commit that never mentioned the issue. GitHub had no cross-reference, so every metadata check I ran said "nobody is doing this".

That is the case this tool is actually for. It asks GitHub's timeline for PRs and commits that point at the issue, and then asks a second, dumber question: **has any file the issue names been modified since the issue was opened?** If the answer is yes, you get `UNSURE` rather than a false `FREE`.

## Three real cases

`docs/case-studies.md` walks through three issues that all looked unclaimed, with the command output and the links: one with an open PR underneath it, one already merged while the issue stayed open, and one with no reference anywhere that a commit had already changed.

## Verdicts

| verdict | meaning | exit |
|---|---|---|
| `FREE` | no open PR, no merged PR, no commit, and the files it names are untouched | 0 |
| `TAKEN` | the issue is closed, or an open PR, a merged PR, or a commit already references it | 1 |
| `UNSURE` | a file the issue names changed after it was opened — look before you type | 2 |

`UNSURE` is a soft signal on purpose. A file can change for reasons unrelated to the issue. Skipping everything that touches a file is too strict; ignoring it is how you waste an evening. Look, then decide.

## Usage

```bash
export GITHUB_TOKEN=...        # public_repo is enough

already-taken check pallets/flask#1234
already-taken scan --label "good first issue" --since 2026-10-01 --limit 30
```

`scan` prints three buckets: taken, worth a manual look, and free.

## Machine-readable output

`--json` on either subcommand, for scripts and for anything else that is going to read this instead of a person:

```json
{
  "target": "eyalgolan/statecraft-israel#2771",
  "verdict": "taken",
  "reason": "a merged PR already did it: #2781 ...",
  "references": [{"kind": "pull", "label": "#2781 ...", "state": "merged"}],
  "touched_files": [{"path": "docs/mvp-checklist.md", "commit": "fd59f274", "message": "..."}]
}
```

`scan --json` returns three arrays (`free`, `taken`, `unsure`) instead of the printed sections.

Exit codes stay the same either way: `0` free, `1` taken, `2` unsure, so `already-taken check x#1 || true` still branches the way you expect.

## What it does not do

- **It does not tell you whether the issue is worth doing.** Only whether someone else got there first.
- **It is not a crawler.** One timeline request plus at most three commit lookups per issue, against the rate limit of your own token.
- **`UNSURE` is not a verdict.** It is the place where your judgment starts.

## Tests

```bash
python3 -m pytest tests/
```

The classification is a pure function (`classify`), so the tests need no network.
