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
import urllib.error
import urllib.parse
import urllib.request

API = "https://api.github.com"
# Messages that mean "a machine moved a version around", not "a person worked
# on this". They touch the same files an issue names often enough to swamp the
# unsure bucket: on one real backlog, 7 of 30 issues landed there only because a
# dependency bump had touched .github/workflows.
BUMP_RE = re.compile(
    r"(^|\b)(chore\(deps\)|build\(deps\)|deps\b|bump\b|release\b|version\b|dependabot|renovate)",
    re.IGNORECASE,
)


def _is_bump(message: str) -> bool:
    """True for automated version churn. A judgement call, and the detail stays visible."""
    return bool(BUMP_RE.search(message or ""))


FILE_RE = re.compile(r"[\w./-]+\.(?:py|ts|tsx|js|jsx|rs|go|md|yml|yaml|toml|json|rb|java|c|h|cpp)\b")

FREE, TAKEN, UNSURE = "free", "taken", "unsure"


def _token() -> str:
    tok = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if not tok:
        sys.exit("set GITHUB_TOKEN (a token with public_repo is enough)")
    return tok


class ApiError(RuntimeError):
    """A GitHub call failed; the caller decides whether that is fatal."""


def get(url: str, token: str):
    req = urllib.request.Request(url, headers={
        "Authorization": "Bearer " + token,
        "Accept": "application/vnd.github+json",
        "User-Agent": "already-taken",
    })
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        # GitHub's timeline endpoint answers 500 for some issues. Without this the
        # whole check dies with a traceback instead of saying what went wrong.
        raise ApiError(_explain(e, url)) from e
    except urllib.error.URLError as e:
        raise ApiError(f"network error: {e.reason} — {url}") from e


def _explain(e, url: str) -> str:
    """A status code is not an error message. Say what to do about it."""
    if e.code == 401:
        return "GITHUB_TOKEN was rejected — check it is valid and not expired"
    if e.code in (403, 429):
        headers = getattr(e, "headers", None) or {}
        if str(headers.get("X-RateLimit-Remaining")) == "0":
            reset = headers.get("X-RateLimit-Reset")
            when = ""
            if reset and str(reset).isdigit():
                import datetime
                when = " (resets " + datetime.datetime.fromtimestamp(
                    int(reset), datetime.timezone.utc).strftime("%H:%M UTC") + ")"
            return f"rate limited by GitHub{when} — wait for the reset, or use a token with more quota"
        return f"GitHub refused this request (403) for {url}"
    if e.code == 404:
        return f"not found — check the owner/repo and the issue number ({url})"
    return f"GitHub answered {e.code} {e.reason} for {url}"


CLOSING_RE = re.compile(r"\b(?:close[sd]?|fix(?:e[sd])?|resolve[sd]?)\b[^\n]{0,60}?#(\d+)\b", re.I)


def closes_issue(body: str | None, num: int) -> bool:
    """Does this PR body say, in GitHub's closing syntax, that it closes THIS issue?

    A cross-reference alone means someone mentioned the issue, not that they fixed it.
    """
    if not body:
        return False
    return any(int(m) == num for m in CLOSING_RE.findall(body))


def timeline_refs(repo: str, num: int, token: str) -> list[tuple[str, str, str, bool]]:
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
            closes = False
            try:
                pr = get(f"{API}/repos/{repo}/pulls/{n}", token)
                closes = closes_issue(pr.get("body"), num)
            except ApiError:
                closes = False
            out.append(("pull", f"#{n} {title}", state, closes))
        elif n is not None:
            out.append(("issue", f"#{n} {title}", linked.get("state", "?"), False))
        else:
            c = src.get("commit") or {}
            out.append(("commit", f"{(c.get('id') or '')[:8]} {(c.get('message') or '').splitlines()[0][:60]}", "commit", False))
    return out


def _named_paths(issue: dict) -> list[str]:
    """Paths the issue names, in the order they appear, deduplicated.

    Empty means the issue names no file at all — which is not the same as
    "no file changed", and the caller has to say so.
    """
    text = (issue.get("title") or "") + "\n" + (issue.get("body") or "")
    seen, out = set(), []
    for m in FILE_RE.finditer(text):
        path = m.group(0)
        # An issue can name a path outside the repo ("../hi/QUICKSTART.md").
        # Asking GitHub for its history answers 500 and takes the whole check down.
        if path in seen or ".." in path.split("/") or path.startswith("/"):
            continue
        seen.add(path)
        out.append(path)
    return out


def files_touched(repo: str, num: int, token: str, issue: dict | None = None,
                  limit: int = 3) -> list[tuple[str, str, str]]:
    """Files the issue names that changed after it was opened."""
    issue = issue if issue is not None else get(f"{API}/repos/{repo}/issues/{num}", token)
    opened = issue.get("created_at") or ""
    paths = _named_paths(issue)
    hits = []
    for path in list(paths)[:limit]:
        commits = get(
            f"{API}/repos/{repo}/commits?path={urllib.parse.quote(path)}&since={opened}&per_page=1",
            token,
        )
        if commits:
            c = commits[0]
            msg = (c["commit"]["message"] or "").splitlines()[0]
            if _is_bump(msg):
                continue
            hits.append((path, c["sha"][:8], msg[:50]))
    return hits


def refs_as_dicts(refs) -> list[dict]:
    """The evidence as JSON. Unpacks the real 4-tuple; the tests only ever
    exercised classify(), so the printing path went out unpinned once."""
    return [{"kind": k, "label": lbl, "state": st, "closes": cl} for k, lbl, st, cl in refs]


def refs_as_lines(refs) -> list[str]:
    return [f"[{k} {st}{' closes' if cl else ''}] {lbl}" for k, lbl, st, cl in refs]


def classify(refs, touched, closed: bool = False, files_named: int | None = None):
    """Pure: turn the evidence into a verdict. Kept separate so it can be tested."""
    mentioned = []
    for kind, label, state, closes in refs:
        if kind == "pull" and state == "open" and closes:
            return TAKEN, f"an open PR says it closes this: {label}"
        if kind == "pull" and state == "merged" and closes:
            return TAKEN, f"a merged PR says it closed this: {label}"
        if kind == "commit":
            return TAKEN, f"a commit references it: {label}"
        if kind == "pull":
            # Issues cross-reference each other constantly ("also affects #X"); that is not
            # evidence anyone is working on this one. Only a pull request counts.
            mentioned.append(f"{label} ({state})")
    if closed:
        # Closed means someone settled it, even when nothing cross-references it.
        # Reporting FREE here would send the reader to work on a dead issue.
        return TAKEN, "the issue is closed"
    if touched:
        path, sha, msg = touched[0]
        return UNSURE, f"{path} changed after the issue was opened ({sha} {msg})"
    if mentioned:
        return UNSURE, f"mentioned but never claimed closed: {'; '.join(mentioned[:2])}"
    if files_named == 0:
        # Saying FREE here would claim the third check passed when it never ran.
        return FREE, ("no PR and no commit, but the issue names no file — "
                      "a silent commit change could not be ruled out")
    return FREE, "no PR, no commit, and the files it names are untouched"


def check(repo: str, num: int, token: str) -> tuple[str, str, list, list]:
    refs = timeline_refs(repo, num, token)
    issue = get(f"{API}/repos/{repo}/issues/{num}", token)
    touched = files_touched(repo, num, token, issue)
    state, why = classify(refs, touched, closed=issue.get("state") == "closed",
                          files_named=len(_named_paths(issue)))
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
    s.add_argument("--repo", help="only this owner/repo, e.g. pallets/flask")

    c.add_argument("--json", action="store_true", help="machine-readable output")
    s.add_argument("--json", action="store_true", help="machine-readable output")

    args = ap.parse_args()
    token = _token()

    try:
        return run(args, token)
    except ApiError as e:
        print(f"already-taken: {e}", file=sys.stderr)
        return 3


def run(args, token: str) -> int:
    if args.cmd == "check":
        repo, _, num = args.target.partition("#")
        if not num.isdigit():
            sys.exit("expected owner/repo#123")
        state, why, refs, touched = check(repo, int(num), token)
        if args.json:
            print(json.dumps({
                "target": args.target,
                "verdict": state,
                "reason": why,
                "references": refs_as_dicts(refs),
                "touched_files": [{"path": p, "commit": c, "message": m} for p, c, m in touched],
            }, ensure_ascii=False, indent=2))
            return {FREE: 0, TAKEN: 1, UNSURE: 2}[state]
        print(f"{args.target}: {state.upper()} — {why}")
        for line in refs_as_lines(refs):
            print(f"  {line}")
        for path, sha, msg in touched:
            print(f"  [file] {path} ← {sha} {msg}")
        return {FREE: 0, TAKEN: 1, UNSURE: 2}[state]

    if getattr(args, "repo", None):
        # GitHub's search API cannot be scoped to one repo reliably enough to
        # page through a backlog, so ask the repo directly.
        q = urllib.parse.quote(args.label)
        found = get(f"{API}/repos/{args.repo}/issues?state=open&labels={q}&per_page={args.limit}", token)
        issues = [i for i in found if "pull_request" not in i]
    else:
        q = urllib.parse.quote(f'label:"{args.label}" state:open type:issue created:>{args.since}')
        found = get(f"{API}/search/issues?q={q}&sort=created&order=desc&per_page={args.limit}", token)
        issues = [i for i in found.get("items", []) if "pull_request" not in i]
    buckets = {FREE: [], TAKEN: [], UNSURE: []}
    for i in issues:
        repo = i["repository_url"].split("/repos/")[-1]
        state, why, _, _ = check(repo, i["number"], token)
        buckets[state].append((f"{repo}#{i['number']}", i["title"][:70], why))
    if getattr(args, "json", False):
        print(json.dumps({
            "free": [{"target": k, "title": t} for k, t, _ in buckets[FREE]],
            "taken": [{"target": k, "title": t, "reason": w} for k, t, w in buckets[TAKEN]],
            "unsure": [{"target": k, "title": t, "reason": w} for k, t, w in buckets[UNSURE]],
        }, ensure_ascii=False, indent=2))
        return 0

    for state, title in ((TAKEN, "already taken"), (UNSURE, "worth a manual look"), (FREE, "free")):
        rows = buckets[state]
        print(f"\n== {title} ({len(rows)}) ==")
        for key, t, why in rows:
            print(f"  {key}  {t}" if state == FREE else f"  {key} ← {why}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
