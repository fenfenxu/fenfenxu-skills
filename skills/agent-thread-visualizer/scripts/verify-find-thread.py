#!/usr/bin/env python3
"""Verify scripts/find-thread with a 2×2 matrix that actually has teeth.

Coverage (per available host fixture):

  |            | should HIT                         | should MISS                          |
  |------------|------------------------------------|--------------------------------------|
  | by ID      | real session UUID / short UUID     | fabricated UUID never on disk        |
  | by name    | distinctive prompt/title substring | nonsense keyword guaranteed absent   |

Fixtures are discovered from paths in references/host-*.md (live local stores).
Name queries are extracted from each fixture's first user message — not hard-coded
IDs from another machine — so the suite stays portable.

Usage (from this skill root):

  python3 scripts/verify-find-thread.py
  python3 scripts/verify-find-thread.py -v

Exit 0 = all ran checks passed; 1 = failure; 2 = no fixtures on this machine.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import uuid
from dataclasses import dataclass, field
from pathlib import Path

HOME = Path.home()
SKILL_ROOT = Path(__file__).resolve().parent.parent
FIND_THREAD = SKILL_ROOT / "scripts" / "find-thread"
UUID_RE = re.compile(
    r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}",
    re.I,
)

# Guaranteed-absent probes (negative cases)
FAKE_UUID = "deadbeef-dead-4bef-8ead-beefdeadbeef"
FAKE_NAME = "zzznomatch-find-thread-7f3a9c2e-qx"


@dataclass
class Fixture:
    host: str
    path: Path
    session_id: str
    name_query: str = ""
    note: str = ""
    skip_name: str = ""  # reason if name+ cannot be built


@dataclass
class Check:
    name: str
    ok: bool
    detail: str = ""


def uuid_from_path(path: Path) -> str:
    m = UUID_RE.search(path.name) or UUID_RE.search(str(path))
    if m:
        return m.group(0)
    m = re.search(r"session_([0-9a-f-]{36})", str(path), re.I)
    return m.group(1) if m else path.stem


def pick_newest(files: list[Path]) -> Path | None:
    existing = [p for p in files if p.is_file()]
    if not existing:
        return None
    existing.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return existing[0]


def _text_from_content(content) -> str:
    if content is None:
        return ""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for item in content:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, dict):
                for k in ("text", "input_text", "content"):
                    if isinstance(item.get(k), str):
                        parts.append(item[k])
                        break
        return "\n".join(parts)
    if isinstance(content, dict):
        return _text_from_content(content.get("text") or content.get("content"))
    return str(content)


def clean_prompt(text: str) -> str:
    text = text or ""
    text = re.sub(r"<system-reminder[\s\S]*?</system-reminder>", " ", text)
    text = re.sub(r"<user_query>([\s\S]*?)</user_query>", r"\1", text)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


_BOILERPLATE_MARKERS = (
    "<recommended_plugins>",
    "<environment_context>",
    "<system-reminder",
    "plugins that are available but not installed",
)


def _is_boilerplate(text: str) -> bool:
    low = (text or "").lower()
    return any(m.lower() in low for m in _BOILERPLATE_MARKERS)


def extract_prompt(host: str, path: Path, max_lines: int = 400) -> str:
    """First *substantive* user prompt (skip host boilerplate injections)."""
    candidates: list[str] = []
    try:
        with path.open("r", encoding="utf-8", errors="ignore") as f:
            for i, line in enumerate(f):
                if i >= max_lines:
                    break
                try:
                    d = json.loads(line)
                except json.JSONDecodeError:
                    continue
                text = ""
                if host == "codex":
                    pl = d.get("payload") or {}
                    if not (
                        (d.get("type") == "response_item" and pl.get("type") == "message" and pl.get("role") == "user")
                        or (pl.get("role") == "user" and pl.get("content"))
                    ):
                        continue
                    text = clean_prompt(_text_from_content(pl.get("content")))
                elif host == "workbuddy":
                    if not (d.get("type") == "message" and d.get("role") == "user"):
                        continue
                    text = clean_prompt(_text_from_content(d.get("content")))
                else:
                    msg = d.get("message")
                    role = d.get("role")
                    if isinstance(msg, dict):
                        role = role or msg.get("role")
                        content = msg.get("content")
                    else:
                        content = d.get("content")
                    if not (d.get("type") == "user" or role == "user"):
                        continue
                    text = clean_prompt(_text_from_content(content))
                if not text or _is_boilerplate(text):
                    continue
                # Prefer shorter real asks over giant dumps
                if 8 <= len(text) <= 500:
                    return text
                candidates.append(text)
    except OSError:
        return ""
    return candidates[0] if candidates else ""


def pick_name_query(prompt: str) -> str:
    """Choose a distinctive substring suitable for name/title search."""
    prompt = clean_prompt(prompt)
    if not prompt:
        return ""

    # Prefer solid CJK phrases (4–16 chars)
    cjk_runs = re.findall(r"[\u4e00-\u9fff]{4,16}", prompt)
    ban_cjk = {"帮我看看", "帮我看下", "请帮我", "你好啊", "请问下", "帮我这个看一看"}
    for run in sorted(cjk_runs, key=len, reverse=True):
        if run in ban_cjk:
            continue
        if run.startswith("帮我") and len(run) <= 6:
            continue
        return run

    # Prefer quoted skill / product names
    m = re.search(r'@skill:"([^"]+)"', prompt)
    if m:
        return m.group(1)

    # Multi-word Latin phrase beats a single generic token like "plugins"
    m = re.search(r"[A-Za-z][A-Za-z0-9_-]+(?:\s+[A-Za-z][A-Za-z0-9_-]+){1,4}", prompt)
    if m and len(m.group(0)) >= 10:
        return m.group(0)[:40]

    ban_en = {
        "saturday", "sunday", "monday", "tuesday", "wednesday", "thursday", "friday",
        "https", "http", "plugins", "plugin", "available", "installed", "skills",
        "here", "list", "that", "are", "but", "not",
    }
    for m in re.finditer(r"[A-Za-z][A-Za-z0-9_-]{4,}", prompt):
        tok = m.group(0)
        if tok.lower() in ban_en:
            continue
        if re.fullmatch(r"[0-9a-fA-F-]{8,}", tok):
            continue
        return tok

    body = re.sub(
        r"^(Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday).*?UTC[^\)]*\)\s*",
        "",
        prompt,
    )
    body = body.strip() or prompt
    if len(body) >= 8:
        return body[0:24].strip()
    return ""


def discover_fixtures() -> list[Fixture]:
    fixtures: list[Fixture] = []

    def add(host: str, path: Path | None, note: str) -> None:
        if not path or not path.is_file():
            return
        sid = uuid_from_path(path)
        prompt = extract_prompt(host, path)
        name_q = pick_name_query(prompt)
        skip = ""
        if not name_q:
            skip = "no distinctive prompt substring"
        fixtures.append(
            Fixture(
                host=host,
                path=path,
                session_id=sid,
                name_query=name_q,
                note=note,
                skip_name=skip,
            )
        )

    # Cursor — host-cursor.md
    cursor_root = HOME / ".cursor" / "projects"
    cursor_files = list(cursor_root.glob("*/agent-transcripts/**/*.jsonl")) if cursor_root.exists() else []
    preferred = [p for p in cursor_files if "fenfenxu-skills" in str(p)]
    add("cursor", pick_newest(preferred) or pick_newest(cursor_files), "~/.cursor/projects/*/agent-transcripts/**/*.jsonl")

    # Codex — host-codex.md
    codex_files: list[Path] = []
    for root in (HOME / ".codex" / "sessions", HOME / ".codex" / "archived_sessions"):
        if root.exists():
            codex_files.extend(root.rglob("rollout-*.jsonl"))
    add("codex", pick_newest(codex_files), "~/.codex/sessions/**/rollout-*.jsonl")

    # Claude — host-claude-code.md
    claude_root = HOME / ".claude" / "projects"
    claude_files = list(claude_root.glob("*/*.jsonl")) if claude_root.exists() else []
    add("claude", pick_newest(claude_files), "~/.claude/projects/<encoded>/*.jsonl")

    # Workbuddy — host-workbuddy.md
    wb_root = HOME / ".workbuddy" / "projects"
    wb_files = list(wb_root.glob("*/*.jsonl")) if wb_root.exists() else []
    rocket = (
        wb_root
        / "Users-liuxu-WorkBuddy-2026-08-10-20-17-43"
        / "0d2e4064-c980-4fe7-8cee-89cc58d44e97.jsonl"
    )
    add(
        "workbuddy",
        rocket if rocket.is_file() else pick_newest(wb_files),
        "~/.workbuddy/projects/<encoded>/<uuid>.jsonl",
    )

    # kimi — host-kimi-code.md
    kimi_files: list[Path] = []
    for root in (HOME / ".kimi-code" / "sessions", HOME / ".kimi" / "sessions"):
        if root.exists():
            kimi_files.extend(root.rglob("wire.jsonl"))
    add("kimi", pick_newest(kimi_files), "~/.kimi-code/sessions/**/wire.jsonl")

    return fixtures


def run_find(*args: str) -> list[dict]:
    proc = subprocess.run(
        [sys.executable, str(FIND_THREAD), *args, "--json", "-n", "20"],
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
            return True
    return False


def record(results: list[Check], name: str, ok: bool, detail: str = "", verbose: bool = False) -> None:
    results.append(Check(name, ok, detail))
    print(f"{'PASS' if ok else 'FAIL'}  {name}" + (f"  ({detail})" if detail else ""))
    if verbose and detail:
        pass


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
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
        return 2

    print("Matrix: ID×name  ×  hit×miss")
    print("Fixtures:")
    for f in fixtures:
        print(f"  [{f.host}] id={f.session_id}")
        print(f"           path={f.path}")
        print(f"           name_query={f.name_query!r}" + (f"  (skip: {f.skip_name})" if f.skip_name else ""))
    print()

    results: list[Check] = []
    skipped = 0

    for f in fixtures:
        host = f.host

        # ---- ID / HIT (full) ----
        hits = run_find(f.session_id, "-a", host, "--all")
        ok = hit_matches(hits, f) and any(
            (h.get("path") or "") == str(f.path) for h in hits
        )
        record(
            results,
            f"{host} | ID+ | full UUID → hit exact path",
            ok,
            f"hits={len(hits)}",
            args.verbose,
        )
        if args.verbose and hits:
            print(f"         -> {hits[0].get('path')}")

        # ---- ID / HIT (short) ----
        short = f.session_id[:8]
        hits = run_find(short, "-a", host, "--all")
        ok = hit_matches(hits, f)
        record(
            results,
            f"{host} | ID+ | short UUID {short} → hit",
            ok,
            f"hits={len(hits)}",
            args.verbose,
        )

        # ---- ID / MISS ----
        # Use a per-host fake so we don't accidentally collide; still globally unused.
        fake = FAKE_UUID if FAKE_UUID != f.session_id else str(uuid.uuid4())
        hits = run_find(fake, "-a", host, "--all")
        ok = not hit_matches(hits, f) and not any(fake in (h.get("path") or "") for h in hits)
        # Stronger: zero hits preferred; allow unrelated hits only if fake id absent
        ok = len(hits) == 0 or (
            not any(fake[:8].lower() in (h.get("session_id") or "").lower() for h in hits)
            and not any(fake in (h.get("path") or "") for h in hits)
        )
        # For fabricated full UUID, expect empty
        ok = len(hits) == 0
        record(
            results,
            f"{host} | ID− | fake UUID → miss",
            ok,
            f"hits={len(hits)}",
            args.verbose,
        )

        # ---- NAME / HIT ----
        if f.skip_name or not f.name_query:
            print(f"SKIP  {host} | name+ | (no usable prompt name)")
            skipped += 1
        else:
            hits = run_find(f.name_query, "-a", host, "--all")
            ok = hit_matches(hits, f)
            record(
                results,
                f"{host} | name+ | {f.name_query!r} → hit",
                ok,
                f"hits={len(hits)}",
                args.verbose,
            )
            if args.verbose:
                for h in hits[:5]:
                    print(f"         -> {h.get('session_id')} {h.get('prompt','')[:50]}")

        # ---- NAME / MISS ----
        hits = run_find(FAKE_NAME, "-a", host, "--all")
        ok = len(hits) == 0
        record(
            results,
            f"{host} | name− | nonsense → miss",
            ok,
            f"hits={len(hits)}",
            args.verbose,
        )

    passed = sum(1 for c in results if c.ok)
    failed = sum(1 for c in results if not c.ok)
    print()
    print(
        f"Summary: {passed} passed, {failed} failed, {skipped} skipped, "
        f"{len(fixtures)} fixtures × {{ID±, name±}}"
    )
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
