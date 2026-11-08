#!/usr/bin/env python3
"""already-taken — is someone already on this issue?

Three different ways an issue can be spoken for, and only the first is obvious:

1. An **open PR** references it. The issue stays open until that PR merges, so
   "the issue is still open" tells you nothing.
2. A **merged PR** references it. The issue may still be open if the PR did not
   close it — or if the merge happened minutes ago and nothing has caught up.
3. A **commit** changed the file the issue names, without ever mentioning the
   issue. No cross-reference exists, so every "has anyone taken this?" check
   that reads GitHub metadata says no. This is the one that costs you a whole
   evening of work.

GitHub's own issue timeline (`cross-referenced` events) answers 1 and 2. Nothing
on GitHub answers 3, so this asks a different question: has any file the issue
names been touched since the issue was opened?

Usage:
    export GITHUB_TOKEN=...
    already-taken check pallets/flask#1234
    already-taken scan --label "good first issue" --since 2026-10-01 --limit 30

Exit codes: 0 free, 1 taken, 2 unsure, 3 error.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.parse
import urllib.request

API = "https://api.github.com"
FILE_RE = re.compile(r"[\w./-]+\.(?:py|ts|tsx|js|jsx|rs|go|md|yml|yaml|toml|json|rb|java|c|h|cpp)\b")

FREE, TAKEN, UNSURE = "free", "taken", "unsure"


def _token() -> str:
    tok = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if not tok:
        sys.exit("set GITHUB_TOKEN (a token with public_repo is enough)")
    return tok


def get(url: str, token: str):
    req = urllib.request.Request(url, headers={
        "Authorization": "Bearer " + token,
        "Accept": "application/vnd.github+json",
        "User-Agent": "already-taken",
    })
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def timeline_refs(repo: str, num: int, token: str) -> list[tuple[str, str, str]]:
    """Everything the issue's timeline says points at it: (kind, label, state)."""
    events = get(f"{API}/repos/{repo}/issues/{num}/timeline?per_page=100", token)
    out = []
    for ev in events:
        if ev.get("event") != "cross-referenced":
            continue
        src = ev.get("source") or {}
        linked = src.get("issue") or {}
        n = linked.get("number")
        title = (linked.get("title") or "")[:60]
        if n is not None and linked.get("pull_request"):
            state = "merged" if linked["pull_request"].get("merged_at") else linked.get("state", "?")
            out.append(("pull", f"#{n} {title}", state))
        elif n is not None:
            out.append(("issue", f"#{n} {title}", linked.get("state", "?")))
        else:
            c = src.get("commit") or {}
            out.append(("commit", f"{(c.get('id') or '')[:8]} {(c.get('message') or '').splitlines()[0][:60]}", "commit"))
    return out


def files_touched(repo: str, num: int, token: str, limit: int = 3) -> list[tuple[str, str, str]]:
    """Files the issue names that changed after it was opened."""
    issue = get(f"{API}/repos/{repo}/issues/{num}", token)
    opened = issue.get("created_at") or ""
    text = (issue.get("title") or "") + "\n" + (issue.get("body") or "")
    paths = {m.group(0) for m in FILE_RE.finditer(text)}
    hits = []
    for path in list(paths)[:limit]:
        commits = get(
            f"{API}/repos/{repo}/commits?path={urllib.parse.quote(path)}&since={opened}&per_page=1",
            token,
        )
        if commits:
            c = commits[0]
            hits.append((path, c["sha"][:8], (c["commit"]["message"] or "").splitlines()[0][:50]))
    return hits


def classify(refs, touched):
    """Pure: turn the two evidence lists into a verdict. Kept separate so it can be tested."""
    for kind, label, state in refs:
        if kind == "pull" and state == "open":
            return TAKEN, f"an open PR is on it: {label}"
        if kind == "pull" and state == "merged":
            return TAKEN, f"a merged PR already did it: {label}"
        if kind == "commit":
            return TAKEN, f"a commit references it: {label}"
    if touched:
        path, sha, msg = touched[0]
        return UNSURE, f"{path} changed after the issue was opened ({sha} {msg})"
    return FREE, "no PR, no commit, and the files it names are untouched"


def check(repo: str, num: int, token: str) -> tuple[str, str, list, list]:
    refs = timeline_refs(repo, num, token)
    touched = files_touched(repo, num, token)
    state, why = classify(refs, touched)
    return state, why, refs, touched


def main() -> int:
    ap = argparse.ArgumentParser(prog="already-taken", description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)

    c = sub.add_parser("check", help="one issue, e.g. owner/repo#123")
    c.add_argument("target")

    s = sub.add_parser("scan", help="walk recent issues carrying a label")
    s.add_argument("--label", default="good first issue")
    s.add_argument("--since", default="2026-10-01")
    s.add_argument("--limit", type=int, default=30)

    args = ap.parse_args()
    token = _token()

    if args.cmd == "check":
        repo, _, num = args.target.partition("#")
        if not num.isdigit():
            sys.exit("expected owner/repo#123")
        state, why, refs, touched = check(repo, int(num), token)
        print(f"{args.target}: {state.upper()} — {why}")
        for kind, label, st in refs:
            print(f"  [{kind} {st}] {label}")
        for path, sha, msg in touched:
            print(f"  [file] {path} ← {sha} {msg}")
        return {FREE: 0, TAKEN: 1, UNSURE: 2}[state]

    q = urllib.parse.quote(f'label:"{args.label}" state:open type:issue created:>{args.since}')
    found = get(f"{API}/search/issues?q={q}&sort=created&order=desc&per_page={args.limit}", token)
    issues = [i for i in found.get("items", []) if "pull_request" not in i]
    buckets = {FREE: [], TAKEN: [], UNSURE: []}
    for i in issues:
        repo = i["repository_url"].split("/repos/")[-1]
        state, why, _, _ = check(repo, i["number"], token)
        buckets[state].append((f"{repo}#{i['number']}", i["title"][:70], why))
    for state, title in ((TAKEN, "already taken"), (UNSURE, "worth a manual look"), (FREE, "free")):
        rows = buckets[state]
        print(f"\n== {title} ({len(rows)}) ==")
        for key, t, why in rows:
            print(f"  {key}  {t}" if state == FREE else f"  {key} ← {why}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
