#!/usr/bin/env python3
"""Verify scripts/find-thread against real local host stores.

Discovers one existing transcript per host from the paths documented in
references/host-*.md, then checks that find-thread returns the same file
(by UUID and, for Workbuddy, by a known keyword).

Usage (from this skill root, or via absolute path):

  python3 scripts/verify-find-thread.py
  python3 scripts/verify-find-thread.py --verbose

Exit 0 = all checks passed; 1 = failure; 2 = not enough fixtures on this machine.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

HOME = Path.home()
SKILL_ROOT = Path(__file__).resolve().parent.parent
FIND_THREAD = SKILL_ROOT / "scripts" / "find-thread"
UUID_RE = re.compile(
    r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}",
    re.I,
)


@dataclass
class Fixture:
    host: str
    path: Path
    session_id: str
    note: str = ""


def uuid_from_path(path: Path) -> str:
    m = UUID_RE.search(path.name) or UUID_RE.search(str(path))
    if m:
        return m.group(0)
    # kimi: .../session_<uuid>/...
    m = re.search(r"session_([0-9a-f-]{36})", str(path), re.I)
    return m.group(1) if m else path.stem


def pick_newest(files: list[Path]) -> Path | None:
    existing = [p for p in files if p.is_file()]
    if not existing:
        return None
    existing.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return existing[0]


def discover_fixtures() -> list[Fixture]:
    fixtures: list[Fixture] = []

    # Cursor — host-cursor.md
    cursor_root = HOME / ".cursor" / "projects"
    cursor_files = list(cursor_root.glob("*/agent-transcripts/**/*.jsonl")) if cursor_root.exists() else []
    # Prefer fenfenxu-skills project when present (stable for this repo)
    preferred = [
        p
        for p in cursor_files
        if "fenfenxu-skills" in str(p)
    ]
    c = pick_newest(preferred) or pick_newest(cursor_files)
    if c:
        fixtures.append(Fixture("cursor", c, uuid_from_path(c), "~/.cursor/projects/*/agent-transcripts/**/*.jsonl"))

    # Codex — host-codex.md
    codex_files: list[Path] = []
    for root in (HOME / ".codex" / "sessions", HOME / ".codex" / "archived_sessions"):
        if root.exists():
            codex_files.extend(root.rglob("rollout-*.jsonl"))
    x = pick_newest(codex_files)
    if x:
        fixtures.append(Fixture("codex", x, uuid_from_path(x), "~/.codex/sessions/**/rollout-*.jsonl"))

    # Claude — host-claude-code.md
    claude_root = HOME / ".claude" / "projects"
    claude_files = list(claude_root.glob("*/*.jsonl")) if claude_root.exists() else []
    cl = pick_newest(claude_files)
    if cl:
        fixtures.append(Fixture("claude", cl, uuid_from_path(cl), "~/.claude/projects/<encoded>/*.jsonl"))

    # Workbuddy — host-workbuddy.md
    wb_root = HOME / ".workbuddy" / "projects"
    wb_files = list(wb_root.glob("*/*.jsonl")) if wb_root.exists() else []
    # Prefer known 水火箭 session if present
    rocket = wb_root / "Users-liuxu-WorkBuddy-2026-08-10-20-17-43" / "0d2e4064-c980-4fe7-8cee-89cc58d44e97.jsonl"
    w = rocket if rocket.is_file() else pick_newest(wb_files)
    if w:
        fixtures.append(Fixture("workbuddy", w, uuid_from_path(w), "~/.workbuddy/projects/<encoded>/<uuid>.jsonl"))

    # kimi — host-kimi-code.md
    kimi_files: list[Path] = []
    for root in (HOME / ".kimi-code" / "sessions", HOME / ".kimi" / "sessions"):
        if root.exists():
            kimi_files.extend(root.rglob("wire.jsonl"))
    k = pick_newest(kimi_files)
    if k:
        fixtures.append(Fixture("kimi", k, uuid_from_path(k), "~/.kimi-code/sessions/**/wire.jsonl"))

    return fixtures


def run_find(*args: str) -> list[dict]:
    proc = subprocess.run(
        [sys.executable, str(FIND_THREAD), *args, "--json", "-n", "15"],
        capture_output=True,
        text=True,
        cwd=str(SKILL_ROOT),
    )
    raw = (proc.stdout or "").strip()
    if not raw:
        return []
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return []


def hit_matches(hits: list[dict], fixture: Fixture) -> bool:
    expect = str(fixture.path)
    for h in hits:
        path = h.get("path") or ""
        sid = h.get("session_id") or ""
        if path == expect:
            return True
        if fixture.session_id and (
            fixture.session_id == sid or fixture.session_id in path
        ):
            # same id under documented tree
            if fixture.host in path.replace("\\", "/"):
                return True
            # host folder names differ slightly (workbuddy vs .workbuddy)
            if fixture.session_id in path:
                return True
    return False


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--verbose", "-v", action="store_true")
    ap.add_argument(
        "--hosts",
        default="cursor,codex,claude,workbuddy,kimi",
        help="Comma-separated hosts to check",
    )
    args = ap.parse_args()
    want = {h.strip() for h in args.hosts.split(",") if h.strip()}

    if not FIND_THREAD.is_file():
        print(f"FAIL: missing {FIND_THREAD}", file=sys.stderr)
        return 1

    fixtures = [f for f in discover_fixtures() if f.host in want]
    if not fixtures:
        print("No local fixtures found under documented host paths.", file=sys.stderr)
        print("Install/use Cursor, Codex, Claude Code, Workbuddy, or kimi-code first.", file=sys.stderr)
        return 2

    print("Fixtures (from documented paths):")
    for f in fixtures:
        print(f"  [{f.host}] id={f.session_id}")
        print(f"           path={f.path}")
        print(f"           manual={f.note}")
    print()

    results: list[tuple[str, bool, str]] = []

    # --- Case A: full UUID per host ---
    for f in fixtures:
        name = f"{f.host} / full UUID"
        hits = run_find(f.session_id, "-a", f.host, "--all")
        ok = hit_matches(hits, f)
        detail = f"hits={len(hits)}"
        if hits and args.verbose:
            detail += f" top={hits[0].get('path')}"
        elif hits:
            detail += f" got={hits[0].get('path')}"
        results.append((name, ok, detail))
        print(f"{'PASS' if ok else 'FAIL'}  {name}  ({detail})")
        if args.verbose and hits:
            for h in hits[:3]:
                print(f"         -> {h.get('path')}")

    # --- Case B: short UUID (first 8) for each ---
    for f in fixtures:
        short = f.session_id[:8]
        name = f"{f.host} / short UUID {short}"
        hits = run_find(short, "-a", f.host, "--all")
        ok = hit_matches(hits, f)
        results.append((name, ok, f"hits={len(hits)}"))
        print(f"{'PASS' if ok else 'FAIL'}  {name}  (hits={len(hits)})")

    # --- Case C: Workbuddy keyword (only if rocket fixture present) ---
    rocket_id = "0d2e4064-c980-4fe7-8cee-89cc58d44e97"
    rocket = next((f for f in fixtures if f.host == "workbuddy" and f.session_id == rocket_id), None)
    if rocket:
        name = "workbuddy / keyword 水火箭"
        hits = run_find("水火箭", "-a", "workbuddy", "--all")
        ok = hit_matches(hits, rocket)
        results.append((name, ok, f"hits={len(hits)}"))
        print(f"{'PASS' if ok else 'FAIL'}  {name}  (hits={len(hits)})")
        if args.verbose:
            for h in hits:
                print(f"         -> {h.get('session_id')} {h.get('path')}")
    else:
        print("SKIP  workbuddy / keyword 水火箭  (fixture session not on this machine)")

    # --- Case D: path equality (full UUID must return exact path) ---
    for f in fixtures:
        name = f"{f.host} / path equality"
        hits = run_find(f.session_id, "-a", f.host, "--all")
        got = Path(hits[0]["path"]) if hits else None
        ok = got == f.path
        results.append((name, ok, f"got={got}"))
        print(f"{'PASS' if ok else 'FAIL'}  {name}")
        if not ok:
            print(f"         expect {f.path}")
            print(f"         got    {got}")

    passed = sum(1 for _, ok, _ in results if ok)
    failed = sum(1 for _, ok, _ in results if not ok)
    print()
    print(f"Summary: {passed} passed, {failed} failed, {len(fixtures)} fixtures")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
