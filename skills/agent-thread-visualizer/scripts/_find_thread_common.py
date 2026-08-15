#!/usr/bin/env python3
"""Shared helpers for find-thread-by-id / find-thread-by-name.

Callers choose the mode — this module does not guess UUID vs name.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable, Iterator, Literal, Optional

SearchMode = Literal["id", "name", "recent"]

HOME = Path.home()
CACHE_DIR = HOME / ".cache" / "agent-thread-find"
CACHE_FILE = CACHE_DIR / "snippets.json"
UUID_RE = re.compile(
    r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}",
    re.I,
)
HOSTS = ("cursor", "codex", "claude", "workbuddy", "kimi")


@dataclass
class NameMatch:
    """How a name query hit a title and/or first-user prompt."""

    score: float = 0.0
    # title-exact | title-substr | title-tokens | prompt-phrase | prompt-tokens | ""
    kind: str = ""
    tokens: tuple[str, ...] = ()

    @property
    def via(self) -> str:
        """Short label for tables / LLM disambiguation when multiple hits."""
        if not self.kind:
            return ""
        if self.tokens:
            return f"{self.kind}[{','.join(self.tokens)}]"
        return self.kind


@dataclass
class Hit:
    host: str
    session_id: str
    path: str
    mtime: float
    project: str
    prompt: str
    # Coarse bucket for sort/filter: id | title | prompt | rg | recent
    match: str
    title: str = ""
    score: float = 0.0
    # Fine-grained how: title-exact | title-tokens | prompt-tokens | id | rg | …
    match_via: str = ""
    match_tokens: tuple[str, ...] = ()

    def age(self) -> str:
        return _fmt_age(self.mtime)


def _fmt_age(mtime: float) -> str:
    sec = max(0, time.time() - mtime)
    if sec < 60:
        return f"{int(sec)}s"
    if sec < 3600:
        return f"{int(sec // 60)}m"
    if sec < 86400:
        return f"{int(sec // 3600)}h"
    return f"{int(sec // 86400)}d"


def _fmt_time(mtime: float) -> str:
    return datetime.fromtimestamp(mtime).strftime("%m-%d %H:%M")


def encode_workspace(path: Path) -> str:
    """Best-effort slug used by Cursor / Workbuddy / Claude-ish layouts."""
    s = str(path.resolve())
    if s.startswith(str(HOME)):
        s = s[len(str(HOME)) :].lstrip("/")
        # Claude often prefixes with -Users-...
        claude = "-" + s.replace("/", "-")
        cursorish = s.replace("/", "-")
        return cursorish  # primary; callers may also try claude form
    return s.replace("/", "-").lstrip("-")


def workspace_slugs(cwd: Path) -> list[str]:
    raw = str(cwd.resolve())
    under_home = raw.startswith(str(HOME) + "/") or raw == str(HOME)
    rel = raw[len(str(HOME)) :].lstrip("/") if under_home else raw.lstrip("/")
    dashed = rel.replace("/", "-")
    variants = [
        dashed,
        "Users-" + dashed if not dashed.startswith("Users-") and under_home else dashed,
        "-" + dashed,
        "-Users-" + dashed if not dashed.startswith("Users-") else "-" + dashed,
    ]
    # also leaf-only fuzzy token for glob
    leaf = cwd.name
    out: list[str] = []
    for v in variants + [leaf]:
        if v and v not in out:
            out.append(v)
    return out


_STOPWORDS = {
    "a", "an", "the", "and", "or", "of", "to", "for", "in", "on", "at", "by", "with",
    "is", "are", "was", "be", "this", "that", "from", "into", "about", "如何", "怎么",
    "一个", "什么", "这个",
}

_WEAK_NAME_TOKENS = {
    "install", "installation", "installed", "error", "issue", "problem", "test",
    "chat", "general", "help", "please", "new", "session",
}

# Cross-language / morphological soft matches for name tokens
_TOKEN_SYNONYMS: dict[str, tuple[str, ...]] = {
    "installation": ("install", "installed", "安装", "安裝"),
    "install": ("installation", "installed", "安装", "安裝"),
    "installed": ("install", "installation", "安装"),
    "visualizer": ("visualization", "visualisation", "可视化", "可視化"),
    "visualization": ("visualizer", "可视化"),
    "skill": ("skills",),
    "skills": ("skill",),
}


def normalize_name_text(text: str) -> str:
    text = (text or "").lower()
    text = text.replace("_", " ").replace("-", " ")
    text = re.sub(r"[^\w\u4e00-\u9fff]+", " ", text, flags=re.UNICODE)
    return re.sub(r"\s+", " ", text).strip()


def name_tokens(query: str) -> list[str]:
    norm = normalize_name_text(query)
    toks = []
    for t in norm.split():
        if t in _STOPWORDS:
            continue
        if len(t) < 2:
            continue
        # keep CJK bigrams+ and latin tokens len>=3
        if re.search(r"[\u4e00-\u9fff]", t):
            if len(t) >= 2:
                toks.append(t)
        elif len(t) >= 3:
            toks.append(t)
    # de-dupe preserving order
    out: list[str] = []
    for t in toks:
        if t not in out:
            out.append(t)
    return out


def _levenshtein(a: str, b: str) -> int:
    """Classic edit distance; swap so we keep the shorter row in memory."""
    if a == b:
        return 0
    if not a:
        return len(b)
    if not b:
        return len(a)
    if len(a) < len(b):
        a, b = b, a
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            ins = cur[j - 1] + 1
            delete = prev[j] + 1
            sub = prev[j - 1] + (0 if ca == cb else 1)
            cur.append(min(ins, delete, sub))
        prev = cur
    return prev[-1]


def _string_similarity(a: str, b: str) -> float:
    """1 - edit_distance / max(len); 1.0 = identical."""
    if not a and not b:
        return 1.0
    if not a or not b:
        return 0.0
    return 1.0 - (_levenshtein(a, b) / max(len(a), len(b)))


# Token / title fuzzy threshold (edit-distance similarity)
_FUZZY_TOKEN_MIN = 0.68
_FUZZY_TITLE_MIN = 0.68


def _best_window_similarity(token: str, blob: str) -> float:
    """Best edit-similarity of token against near-length windows in blob."""
    n = len(token)
    if n < 2 or not blob:
        return 0.0
    if len(blob) > 160:
        blob = blob[:160]
    best = 0.0
    lengths = {n, max(2, n - 1), n + 1, max(2, n - 2), n + 2, max(2, (n * 3) // 4)}
    for wlen in sorted(lengths):
        if wlen > len(blob):
            continue
        step = 1 if len(blob) <= 64 else max(1, wlen // 4)
        for i in range(0, len(blob) - wlen + 1, step):
            sim = _string_similarity(token, blob[i : i + wlen])
            if sim > best:
                best = sim
                if best >= 0.95:
                    return best
    if len(blob) <= 64:
        best = max(best, _string_similarity(token, blob))
    return best


def _token_match_quality(token: str, blob: str) -> float:
    """0..1 how well a query token aligns with title/prompt text.

    Edit-distance windows are only used on short blobs (UI titles). Long first-user
    prompts stay exact/synonym/prefix — sliding Levenshtein over ~2k prompts is too slow.
    """
    if not token or not blob:
        return 0.0
    if token in blob:
        return 1.0
    for syn in _TOKEN_SYNONYMS.get(token, ()):
        if syn in blob:
            return 1.0
    # CJK: long query token may extend past a shorter title fragment
    if re.search(r"[\u4e00-\u9fff]", token) and len(token) >= 4:
        for n in range(len(token) - 1, 3, -1):
            if token[:n] in blob or token[-n:] in blob:
                return n / len(token)
    # Fuzzy edit distance: short titles only (typo tolerance without scanning prompts)
    if len(blob) <= 64:
        return _best_window_similarity(token, blob)
    return 0.0


def _token_in_blob(token: str, blob: str) -> bool:
    return _token_match_quality(token, blob) >= _FUZZY_TOKEN_MIN


def name_match_detail(query: str, title: str = "", prompt: str = "") -> NameMatch:
    """Score + explain how a UI title / first-user prompt matches a name query.

    Prefer short real UI titles over huge dumped transcripts that merely mention
    the same tokens. Full-phrase substring wins; else token coverage on
    normalized title+prompt (so "Agent thread visualizer installation" can hit
    a prompt containing `agent-thread-visualizer` + `安装`).

    Fuzzy fallback uses Levenshtein similarity (typos / extra CJK chars).

    `kind` tells the caller (and LLM) what evidence was used:
      title-exact / title-substr / title-fuzzy / title-tokens — sidebar/UI name
      prompt-phrase / prompt-tokens — first user message text
    """
    q = (query or "").strip()
    if not q:
        return NameMatch()
    title_n = normalize_name_text(title)
    prompt_n = normalize_name_text(prompt)
    blob = f"{title_n} {prompt_n}".strip()
    if not blob:
        return NameMatch()

    qn = normalize_name_text(q)
    # Exact / near-exact UI title (Codex/Workbuddy/Claude/Kimi short labels)
    if qn and title_n:
        if qn == title_n:
            return NameMatch(1.0, "title-exact")
        if qn in title_n and len(title_n) <= max(len(qn) * 3, 96):
            return NameMatch(0.99, "title-substr")
        # title ⊆ query only when title is substantial (avoid "ls" ⊂ long garbage)
        if (
            len(title_n) >= 4
            and title_n in qn
            and len(qn) <= max(len(title_n) * 3, 96)
        ):
            return NameMatch(0.98, "title-substr")
    if qn and qn in prompt_n and len(prompt_n) <= max(len(qn) * 4, 160):
        return NameMatch(0.95, "prompt-phrase")

    toks = name_tokens(q)
    if not toks:
        if qn in title_n:
            return NameMatch(1.0, "title-substr")
        if qn in prompt_n:
            return NameMatch(0.95, "prompt-phrase")
        fuzzy = _title_fuzzy_match(qn, title_n)
        if fuzzy.score > 0:
            return fuzzy
        return NameMatch()

    # When scoring a title alone, ignore absurdly long "titles" (approval dumps).
    title_blob = title_n
    if title_n and len(title_n) > 180:
        title_blob = ""
    use_blob = f"{title_blob} {prompt_n}".strip() if title_blob or prompt_n else blob
    if title_n and not title_blob and not prompt_n:
        return _title_fuzzy_match(qn, title_n)

    qualities = [(t, _token_match_quality(t, use_blob)) for t in toks]
    matched = [t for t, qual in qualities if qual >= _FUZZY_TOKEN_MIN]
    if not matched:
        return _title_fuzzy_match(qn, title_n)

    # Distinctive tokens gate false positives like bare find+thread.
    distinctive = [t for t in toks if len(t) >= 8 or (t not in _WEAK_NAME_TOKENS and len(t) >= 6)]
    if distinctive and not any(
        _token_match_quality(t, use_blob) >= _FUZZY_TOKEN_MIN for t in distinctive
    ):
        return _title_fuzzy_match(qn, title_n)

    strong = [t for t in matched if t not in _WEAK_NAME_TOKENS]
    if not strong and len(matched) < 2:
        return _title_fuzzy_match(qn, title_n)

    # Partial credit: average per-token quality (unmatched ≈ 0)
    coverage = sum(qual for _, qual in qualities) / len(toks)
    if len(matched) < 2 and coverage < 0.6:
        return _title_fuzzy_match(qn, title_n)

    score = coverage
    on_title = bool(
        title_blob
        and any(
            _token_match_quality(t, title_blob) >= _FUZZY_TOKEN_MIN
            for t in (strong or matched)
        )
    )
    if on_title:
        # Full-credit tokens get the title boost; fuzzy/partial get less
        exact_frac = sum(1 for _, qual in qualities if qual >= 0.999) / len(toks)
        score += 0.15 * exact_frac
    # Prefer short user asks over huge subagent task dumps that merely mention the skill
    if prompt and len(prompt) > 350 and not title_blob:
        score *= 0.55
    # Reserve 1.0 for clean exact coverage — typos/fuzzy stay visibly below
    if any(qual < 0.999 for _, qual in qualities):
        score = min(0.97, score)
    kind = "title-tokens" if on_title else "prompt-tokens"
    # If caller scored title-only vs prompt-only, force kind to that field.
    if title_blob and not prompt_n:
        kind = "title-tokens"
    elif prompt_n and not title_blob:
        kind = "prompt-tokens"
    token_hit = NameMatch(min(1.0, round(score, 3)), kind, tuple(matched))
    # If tokens are weak, whole-title edit-distance may still be better signal
    fuzzy = _title_fuzzy_match(qn, title_n)
    if fuzzy.score > token_hit.score:
        return fuzzy
    return token_hit


def _title_fuzzy_match(qn: str, title_n: str) -> NameMatch:
    """Compact Levenshtein match of query vs UI title (spaces ignored)."""
    if not qn or not title_n:
        return NameMatch()
    qc = qn.replace(" ", "")
    tc = title_n.replace(" ", "")
    if not qc or not tc:
        return NameMatch()
    if abs(len(qc) - len(tc)) > max(3, len(tc) // 3):
        return NameMatch()
    if max(len(qc), len(tc)) > 64:
        return NameMatch()
    sim = _string_similarity(qc, tc)
    if sim < _FUZZY_TITLE_MIN:
        return NameMatch()
    return NameMatch(round(min(0.97, sim), 3), "title-fuzzy")


def name_match_score(query: str, title: str = "", prompt: str = "") -> float:
    """Backward-compatible score-only wrapper around name_match_detail."""
    return name_match_detail(query, title=title, prompt=prompt).score

# host -> session_id -> UI/sidebar title
HostTitles = dict[str, dict[str, str]]


def load_cursor_titles() -> dict[str, str]:
    """Map agent/composer UUID -> UI sidebar title.

    Prefer `conversation-search.db` (Agents sidebar / Today list titles).
    Fall back to legacy `composer.composerHeaders` name/subtitle for older chats.
    """
    out: dict[str, str] = {}
    try:
        import sqlite3
    except ImportError:
        return {}

    # Primary: conversation search index (includes Agents window titles)
    search_db = (
        HOME
        / "Library"
        / "Application Support"
        / "Cursor"
        / "User"
        / "globalStorage"
        / "conversation-search.db"
    )
    if search_db.is_file():
        try:
            con = sqlite3.connect(f"file:{search_db}?mode=ro", uri=True)
            for sid, title in con.execute(
                "SELECT id, title FROM conversations WHERE title IS NOT NULL AND title != ''"
            ):
                if sid and title:
                    out[str(sid)] = str(title).strip()
            con.close()
        except Exception:
            pass

    # Legacy: composerHeaders (Pinned / older composer chats)
    db = (
        HOME
        / "Library"
        / "Application Support"
        / "Cursor"
        / "User"
        / "globalStorage"
        / "state.vscdb"
    )
    if db.is_file():
        try:
            con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
            row = con.execute(
                "SELECT value FROM ItemTable WHERE key='composer.composerHeaders'"
            ).fetchone()
            con.close()
            if row:
                raw = row[0].decode("utf-8") if isinstance(row[0], bytes) else row[0]
                data = json.loads(raw)
                for c in data.get("allComposers") or []:
                    if not isinstance(c, dict):
                        continue
                    cid = c.get("composerId")
                    if not cid or cid == "empty-state-draft":
                        continue
                    if str(cid) in out:
                        continue  # conversation-search title wins
                    name = (c.get("name") or "").strip()
                    sub = (c.get("subtitle") or "").strip()
                    label = name or sub
                    if label:
                        out[str(cid)] = label
        except Exception:
            pass
    return out


def load_codex_titles() -> dict[str, str]:
    """Map thread UUID -> title from Codex state DB / session_index."""
    out: dict[str, str] = {}
    try:
        import sqlite3
    except ImportError:
        sqlite3 = None  # type: ignore

    if sqlite3 is not None:
        # Prefer newest state_*.sqlite that has a threads.title column.
        dbs = sorted(
            (HOME / ".codex").glob("state_*.sqlite"),
            key=lambda p: p.stat().st_mtime if p.exists() else 0,
            reverse=True,
        )
        for db in dbs:
            if not db.is_file():
                continue
            try:
                con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
                cols = {
                    r[1]
                    for r in con.execute("PRAGMA table_info(threads)").fetchall()
                }
                if "id" not in cols or "title" not in cols:
                    con.close()
                    continue
                for sid, title in con.execute(
                    "SELECT id, title FROM threads WHERE title IS NOT NULL AND title != ''"
                ):
                    if not sid or not title:
                        continue
                    label = str(title).strip()
                    # Approval/transcript dumps occasionally land in title — skip.
                    if len(label) > 180:
                        continue
                    out[str(sid)] = label
                con.close()
                if out:
                    break
            except Exception:
                continue

    idx = HOME / ".codex" / "session_index.jsonl"
    if idx.is_file():
        try:
            for line in idx.open(encoding="utf-8", errors="replace"):
                line = line.strip()
                if not line:
                    continue
                try:
                    o = json.loads(line)
                except json.JSONDecodeError:
                    continue
                sid = o.get("id")
                name = (o.get("thread_name") or o.get("title") or "").strip()
                if sid and name and len(name) <= 180 and str(sid) not in out:
                    out[str(sid)] = name
        except OSError:
            pass
    return out


def load_workbuddy_titles() -> dict[str, str]:
    """Map session UUID -> title from Workbuddy SQLite (UI does not expose IDs)."""
    db = HOME / ".workbuddy" / "workbuddy.db"
    if not db.is_file():
        return {}
    try:
        import sqlite3

        con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
        out: dict[str, str] = {}
        for sid, title, custom in con.execute(
            "SELECT id, title, custom_title FROM sessions"
        ):
            if not sid:
                continue
            label = (custom or title or "").strip()
            if label:
                out[str(sid)] = label
        con.close()
        return out
    except Exception:
        return {}


def load_kimi_titles() -> dict[str, str]:
    """Map session UUID -> title from each session's state.json."""
    out: dict[str, str] = {}
    for root in (HOME / ".kimi-code" / "sessions", HOME / ".kimi" / "sessions"):
        if not root.exists():
            continue
        for state in root.rglob("state.json"):
            try:
                o = json.loads(state.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            if not isinstance(o, dict):
                continue
            title = (o.get("title") or "").strip()
            if not title:
                continue
            raw_id = str(o.get("id") or state.parent.name or "")
            if raw_id.startswith("session_"):
                bare = raw_id[len("session_") :]
            else:
                bare = raw_id
            m = UUID_RE.search(bare) or UUID_RE.search(raw_id)
            if m:
                out[m.group(0)] = title
            if bare:
                out[bare] = title
            if raw_id:
                out[raw_id] = title
    return out


def _extract_claude_ai_title(path: Path) -> str:
    """Latest ai-title.aiTitle in a Claude Code session jsonl."""
    last = ""
    try:
        with path.open(encoding="utf-8", errors="replace") as f:
            for line in f:
                if "aiTitle" not in line and "ai-title" not in line:
                    continue
                try:
                    o = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if o.get("type") == "ai-title":
                    t = (o.get("aiTitle") or "").strip()
                    if t:
                        last = t
    except OSError:
        return ""
    return last


def load_claude_titles(files: list[Path]) -> dict[str, str]:
    """Map session UUID -> aiTitle; cache by path+mtime under ~/.cache."""
    cache_path = CACHE_DIR / "claude-titles.json"
    disk: dict[str, dict] = {}
    if cache_path.exists():
        try:
            disk = json.loads(cache_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            disk = {}

    out: dict[str, str] = {}
    dirty = False
    for path in files:
        if path.suffix != ".jsonl":
            continue
        try:
            mtime = path.stat().st_mtime
        except OSError:
            continue
        key = str(path)
        ent = disk.get(key)
        if ent and abs(ent.get("mtime", 0) - mtime) < 0.01:
            title = (ent.get("title") or "").strip()
        else:
            title = _extract_claude_ai_title(path)
            disk[key] = {"mtime": mtime, "title": title}
            dirty = True
        if not title:
            continue
        sid = session_id_of("claude", path)
        if sid:
            out[sid] = title

    if dirty:
        try:
            CACHE_DIR.mkdir(parents=True, exist_ok=True)
            tmp = cache_path.with_suffix(".tmp")
            tmp.write_text(json.dumps(disk, ensure_ascii=False), encoding="utf-8")
            tmp.replace(cache_path)
        except OSError:
            pass
    return out


def load_host_titles(hosts: Iterable[str], discovered: dict[str, list[Path]]) -> HostTitles:
    """Load UI/sidebar titles for the requested hosts (best-effort per host)."""
    out: HostTitles = {}
    host_set = set(hosts)
    if "cursor" in host_set:
        out["cursor"] = load_cursor_titles()
    if "codex" in host_set:
        out["codex"] = load_codex_titles()
    if "workbuddy" in host_set:
        out["workbuddy"] = load_workbuddy_titles()
    if "kimi" in host_set:
        out["kimi"] = load_kimi_titles()
    if "claude" in host_set:
        out["claude"] = load_claude_titles(discovered.get("claude") or [])
    return out


def lookup_title(titles: Optional[HostTitles], host: str, sid: str) -> str:
    if not titles or not sid:
        return ""
    by_host = titles.get(host) or {}
    if sid in by_host:
        return by_host[sid]
    if sid.startswith("session_"):
        bare = sid[len("session_") :]
        if bare in by_host:
            return by_host[bare]
    else:
        alt = f"session_{sid}"
        if alt in by_host:
            return by_host[alt]
    return ""


# ---------- discovery (path only; no content) ----------


def discover_cursor(scoped: Optional[list[str]], all_projects: bool) -> list[Path]:
    root = HOME / ".cursor" / "projects"
    if not root.exists():
        return []
    files: list[Path] = []
    if not all_projects and scoped:
        for slug in scoped:
            for d in root.glob(f"*{slug}*"):
                at = d / "agent-transcripts"
                if at.is_dir():
                    files.extend(at.rglob("*.jsonl"))
        if files:
            return files
    # broad: only under agent-transcripts dirs
    for at in root.glob("*/agent-transcripts"):
        files.extend(at.rglob("*.jsonl"))
    return files


def discover_codex(all_projects: bool, cwd: Optional[Path] = None) -> list[Path]:
    roots = [HOME / ".codex" / "sessions", HOME / ".codex" / "archived_sessions"]
    files: list[Path] = []
    for root in roots:
        if not root.exists():
            continue
        files.extend(root.rglob("rollout-*.jsonl"))
    # No project slug tree — keep a recent window unless --all (cwd filter would need opening files).
    if all_projects:
        return files
    files.sort(key=lambda p: p.stat().st_mtime if p.exists() else 0, reverse=True)
    return files[:120]


def discover_claude(scoped: Optional[list[str]], all_projects: bool) -> list[Path]:
    root = HOME / ".claude" / "projects"
    if not root.exists():
        return []
    files: list[Path] = []
    if not all_projects and scoped:
        for slug in scoped:
            for d in root.glob(f"*{slug}*"):
                if d.is_dir():
                    files.extend(d.glob("*.jsonl"))
        if files:
            return files
    for d in root.iterdir():
        if d.is_dir():
            files.extend(d.glob("*.jsonl"))
    return files


def discover_workbuddy(scoped: Optional[list[str]], all_projects: bool) -> list[Path]:
    root = HOME / ".workbuddy" / "projects"
    if not root.exists():
        return []
    files: list[Path] = []
    if not all_projects and scoped:
        for slug in scoped:
            for d in root.glob(f"*{slug}*"):
                if d.is_dir():
                    files.extend(d.glob("*.jsonl"))
        if files:
            return files
    for d in root.iterdir():
        if d.is_dir():
            files.extend(d.glob("*.jsonl"))
    return files


def discover_kimi(all_projects: bool = True) -> list[Path]:
    files: list[Path] = []
    for root in (HOME / ".kimi-code" / "sessions", HOME / ".kimi" / "sessions"):
        if not root.exists():
            continue
        # Prefer transcript-like files; skip noisy state/index sidecars.
        for p in root.rglob("*"):
            if not p.is_file():
                continue
            name = p.name.lower()
            if name in {"state.json", "config.json", "meta.json"}:
                continue
            if p.suffix == ".jsonl" or name in {"wire.jsonl", "transcript.jsonl", "messages.jsonl"}:
                files.append(p)
            elif p.suffix == ".json" and "session" in name:
                files.append(p)
    files.sort(key=lambda p: p.stat().st_mtime if p.exists() else 0, reverse=True)
    return files if all_projects else files[:80]


def discover(
    hosts: Iterable[str],
    cwd: Path,
    all_projects: bool,
) -> dict[str, list[Path]]:
    scoped = None if all_projects else workspace_slugs(cwd)
    out: dict[str, list[Path]] = {}

    def one(host: str) -> tuple[str, list[Path]]:
        if host == "cursor":
            return host, discover_cursor(scoped, all_projects)
        if host == "codex":
            return host, discover_codex(all_projects, cwd)
        if host == "claude":
            return host, discover_claude(scoped, all_projects)
        if host == "workbuddy":
            return host, discover_workbuddy(scoped, all_projects)
        if host == "kimi":
            return host, discover_kimi(all_projects)
        return host, []

    with ThreadPoolExecutor(max_workers=5) as ex:
        futs = [ex.submit(one, h) for h in hosts]
        for fut in as_completed(futs):
            host, files = fut.result()
            out[host] = files
    return out


# ---------- snippet extraction + cache ----------


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
                    if k in item and isinstance(item[k], str):
                        parts.append(item[k])
                        break
        return "\n".join(parts)
    if isinstance(content, dict):
        return _text_from_content(content.get("text") or content.get("content"))
    return str(content)


def _clean_prompt(text: str, limit: int = 240) -> str:
    text = text or ""
    # strip common wrappers
    text = re.sub(r"<system-reminder[\s\S]*?</system-reminder>", " ", text)
    text = re.sub(r"<user_query>([\s\S]*?)</user_query>", r"\1", text)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) > limit:
        return text[: limit - 1] + "…"
    return text


_BOILERPLATE_MARKERS = (
    "<recommended_plugins>",
    "<environment_context>",
    "plugins that are available but not installed",
)


def _is_boilerplate(text: str) -> bool:
    low = (text or "").lower()
    return any(m.lower() in low for m in _BOILERPLATE_MARKERS)


def extract_prompt(host: str, path: Path, max_lines: int = 400) -> str:
    """First substantive user prompt (skip host boilerplate injections)."""
    if path.is_dir():
        return ""
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
                        (
                            d.get("type") == "response_item"
                            and pl.get("type") == "message"
                            and pl.get("role") == "user"
                        )
                        or (pl.get("role") == "user" and pl.get("content"))
                    ):
                        continue
                    text = _clean_prompt(_text_from_content(pl.get("content")), limit=500)
                elif host == "workbuddy":
                    if not (d.get("type") == "message" and d.get("role") == "user"):
                        continue
                    text = _clean_prompt(_text_from_content(d.get("content")), limit=500)
                else:
                    role = d.get("role")
                    msg = d.get("message")
                    if isinstance(msg, dict):
                        role = role or msg.get("role")
                        content = msg.get("content")
                    else:
                        content = d.get("content")
                    if not (d.get("type") == "user" or role == "user"):
                        continue
                    text = _clean_prompt(_text_from_content(content), limit=500)
                if not text or _is_boilerplate(text):
                    continue
                if 8 <= len(text) <= 500:
                    return text
                candidates.append(text)
    except OSError:
        return ""
    return candidates[0] if candidates else ""


def session_id_of(host: str, path: Path) -> str:
    name = path.stem if path.is_file() else path.name
    m = UUID_RE.search(path.name) or UUID_RE.search(str(path))
    if m:
        return m.group(0)
    if host == "codex":
        # rollout-...-<uuid>
        parts = name.split("-")
        for i, p in enumerate(parts):
            if len(p) == 8 and i + 4 < len(parts):
                cand = "-".join(parts[i : i + 5])
                if UUID_RE.fullmatch(cand):
                    return cand
    return name


def project_of(host: str, path: Path) -> str:
    parts = path.parts
    try:
        if host == "cursor":
            i = parts.index("projects")
            return parts[i + 1]
        if host == "claude":
            i = parts.index("projects")
            return parts[i + 1]
        if host == "workbuddy":
            i = parts.index("projects")
            return parts[i + 1]
        if host == "codex":
            # YYYY/MM/DD under sessions
            return "codex"
        if host == "kimi":
            return "kimi"
    except (ValueError, IndexError):
        pass
    return path.parent.name


class SnippetCache:
    def __init__(self, path: Path = CACHE_FILE):
        self.path = path
        self.data: dict[str, dict] = {}
        self._dirty = False
        self.load()

    def load(self) -> None:
        if not self.path.exists():
            return
        try:
            self.data = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            self.data = {}

    def save(self) -> None:
        if not self._dirty:
            return
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps(self.data, ensure_ascii=False), encoding="utf-8")
        tmp.replace(self.path)
        self._dirty = False

    def get(self, host: str, path: Path) -> str:
        try:
            mtime = path.stat().st_mtime
        except OSError:
            return ""
        key = str(path)
        ent = self.data.get(key)
        if ent and abs(ent.get("mtime", 0) - mtime) < 0.01:
            return ent.get("prompt") or ""
        prompt = extract_prompt(host, path)
        self.data[key] = {"mtime": mtime, "prompt": prompt, "host": host}
        self._dirty = True
        return prompt


# ---------- matching ----------


def path_id_match(path: Path, query: str) -> bool:
    q = query.lower().strip()
    return q in path.name.lower() or q in str(path).lower()


def to_hit(
    host: str,
    path: Path,
    match: str,
    cache: SnippetCache,
    need_prompt: bool,
    titles: Optional[HostTitles] = None,
    score: float = 0.0,
    match_via: str = "",
    match_tokens: tuple[str, ...] = (),
) -> Hit:
    try:
        mtime = path.stat().st_mtime
    except OSError:
        mtime = 0.0
    prompt = cache.get(host, path) if need_prompt else ""
    sid = session_id_of(host, path)
    title = lookup_title(titles, host, sid)
    via = match_via or match
    return Hit(
        host=host,
        session_id=sid,
        path=str(path),
        mtime=mtime,
        project=project_of(host, path),
        prompt=prompt,
        match=match,
        title=title,
        score=score,
        match_via=via,
        match_tokens=match_tokens,
    )


def is_subagent_path(path: Path) -> bool:
    """Cursor subagent jsonl or non-main kimi worker agents."""
    s = str(path).replace("\\", "/")
    if "/subagents/" in s:
        return True
    if "/agents/agent-" in s:  # keep .../agents/main/
        return True
    return False


def rg_search(roots: list[Path], query: str, limit: int) -> list[Path]:
    if not roots or not shutil.which("rg"):
        return []
    existing = [str(r) for r in roots if r.exists()]
    if not existing:
        return []
    cmd = [
        "rg",
        "-l",
        "-i",
        "--max-count",
        "1",
        "-g",
        "*.jsonl",
        "-g",
        "*.json",
        query,
        *existing,
    ]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=20)
    except (OSError, subprocess.TimeoutExpired):
        return []
    paths = []
    for line in proc.stdout.splitlines():
        line = line.strip()
        if line:
            paths.append(Path(line))
        if len(paths) >= limit * 3:
            break
    return paths


def find_threads(
    query: Optional[str],
    hosts: list[str],
    cwd: Path,
    limit: int,
    all_projects: bool,
    deep: bool,
    include_subagents: bool = False,
    mode: SearchMode = "name",
) -> list[Hit]:
    """Locate threads. `mode` is chosen by the caller (LLM), never auto-detected.

    - id: path/filename UUID (or fragment) match only
    - name: UI title / first-user prompt tokens (optional --deep rg)
    - recent: newest parent threads when query is empty (used by by-name CLI)
    """
    if mode not in {"id", "name", "recent"}:
        raise ValueError(f"unknown mode: {mode!r}")

    cache = SnippetCache()
    t0 = time.perf_counter()
    discovered = discover(hosts, cwd, all_projects=all_projects)
    discover_ms = (time.perf_counter() - t0) * 1000

    hits: list[Hit] = []
    seen_path: set[str] = set()
    seen_sid: set[str] = set()

    def add(h: Hit) -> None:
        if h.path in seen_path:
            return
        sid_key = f"{h.host}:{h.session_id}"
        if h.session_id and sid_key in seen_sid:
            return
        seen_path.add(h.path)
        if h.session_id:
            seen_sid.add(sid_key)
        hits.append(h)

    def allow_for_name(p: Path) -> bool:
        return include_subagents or not is_subagent_path(p)

    q = (query or "").strip()
    titles: HostTitles = {}
    if mode in {"name", "recent", "id"}:
        titles = load_host_titles(hosts, discovered)

    # ---- ID mode: path / filename only ----
    if mode == "id":
        if not q:
            find_threads.last_stats = {  # type: ignore[attr-defined]
                "discover_ms": round(discover_ms, 1),
                "files": sum(len(v) for v in discovered.values()),
                "hits": 0,
            }
            return []
        for host, files in discovered.items():
            for p in files:
                if path_id_match(p, q):
                    add(
                        to_hit(
                            host,
                            p,
                            "id",
                            cache,
                            need_prompt=True,
                            titles=titles,
                            score=1.0,
                            match_via="id",
                        )
                    )
        if not hits and not all_projects:
            discovered = discover(hosts, cwd, all_projects=True)
            titles = load_host_titles(hosts, discovered)
            for host, files in discovered.items():
                for p in files:
                    if path_id_match(p, q):
                        add(
                            to_hit(
                                host,
                                p,
                                "id",
                                cache,
                                need_prompt=True,
                                titles=titles,
                                score=1.0,
                                match_via="id",
                            )
                        )

    # ---- NAME mode: host UI title first, then first-user prompt ----
    elif mode == "name" and q:
        candidates: list[tuple[str, Path]] = []
        for host, files in discovered.items():
            for p in files:
                if allow_for_name(p):
                    candidates.append((host, p))
        candidates.sort(
            key=lambda hp: hp[1].stat().st_mtime if hp[1].exists() else 0,
            reverse=True,
        )
        window = (
            candidates[: max(2000, limit * 80)]
            if all_projects
            else candidates[: max(400, limit * 40)]
        )

        scored: list[tuple[int, float, Hit]] = []  # title_tier, score, hit
        for host, p in window:
            if str(p) in seen_path:
                continue
            sid = session_id_of(host, p)
            title = lookup_title(titles, host, sid)

            title_m = name_match_detail(q, title=title, prompt="") if title else NameMatch()
            if title_m.score > 0:
                h = to_hit(
                    host,
                    p,
                    "title",
                    cache,
                    need_prompt=True,
                    titles=titles,
                    score=title_m.score,
                    match_via=title_m.via,
                    match_tokens=title_m.tokens,
                )
                scored.append((1, title_m.score, h))
                continue

            # Prompt only when title missed (avoid ~2k× Levenshtein on first-user text)
            prompt = cache.get(host, p)
            prompt_m = (
                name_match_detail(q, title="", prompt=prompt) if prompt else NameMatch()
            )
            if prompt_m.score > 0:
                h = to_hit(
                    host,
                    p,
                    "prompt",
                    cache,
                    need_prompt=True,
                    titles=titles,
                    score=prompt_m.score,
                    match_via=prompt_m.via,
                    match_tokens=prompt_m.tokens,
                )
                scored.append((0, prompt_m.score, h))

        scored.sort(key=lambda x: (x[0], x[1], x[2].mtime), reverse=True)
        # Near-exact UI title hit → drop weak prompt-only noise
        best_title = max((s for tier, s, _ in scored if tier == 1), default=0.0)
        if best_title >= 0.98:
            scored = [
                x for x in scored if x[0] == 1 or x[1] >= 0.85
            ]
        for _tier, _score, h in scored:
            add(h)
            if len(hits) >= limit * 2:
                break

        if deep and len(hits) < limit:
            roots: list[Path] = []
            if "cursor" in hosts:
                roots.append(HOME / ".cursor" / "projects")
            if "codex" in hosts:
                roots.extend(
                    [HOME / ".codex" / "sessions", HOME / ".codex" / "archived_sessions"]
                )
            if "claude" in hosts:
                roots.append(HOME / ".claude" / "projects")
            if "workbuddy" in hosts:
                roots.append(HOME / ".workbuddy" / "projects")
            if "kimi" in hosts:
                roots.extend(
                    [HOME / ".kimi-code" / "sessions", HOME / ".kimi" / "sessions"]
                )
            for p in rg_search(roots, q, limit):
                if not allow_for_name(p):
                    continue
                host = infer_host(p)
                if host in hosts:
                    add(
                        to_hit(
                            host,
                            p,
                            "rg",
                            cache,
                            need_prompt=True,
                            titles=titles,
                            score=0.2,
                            match_via="rg-fulltext",
                        )
                    )

    # ---- RECENT (by-name with no query) ----
    elif mode == "recent" or (mode == "name" and not q):
        candidates = []
        for host, files in discovered.items():
            for p in files:
                if not allow_for_name(p):
                    continue
                try:
                    candidates.append((host, p, p.stat().st_mtime))
                except OSError:
                    continue
        if not candidates and not all_projects:
            discovered = discover(hosts, cwd, all_projects=True)
            for host, files in discovered.items():
                for p in files:
                    if not allow_for_name(p):
                        continue
                    try:
                        candidates.append((host, p, p.stat().st_mtime))
                    except OSError:
                        continue
        candidates.sort(key=lambda x: x[2], reverse=True)
        for host, p, _ in candidates[:limit]:
            add(
                to_hit(
                    host,
                    p,
                    "recent",
                    cache,
                    need_prompt=True,
                    titles=titles,
                    score=0.0,
                    match_via="recent",
                )
            )

    cache.save()

    def sort_key(h: Hit):
        # Prefer high score overall. Only give title a small bump when it is strong,
        # so weak title token hits cannot outrank near-exact first-user matches.
        title_boost = 0.05 if h.match == "title" and h.score >= 0.85 else 0.0
        if h.match in {"id", "path"}:
            tier = 3
        elif h.match == "title" and h.score >= 0.85:
            tier = 2
        elif h.match in {"title", "prompt", "name"}:
            tier = 1
        else:
            tier = 0
        return (tier, h.score + title_boost, h.mtime)

    hits.sort(key=sort_key, reverse=True)
    find_threads.last_stats = {  # type: ignore[attr-defined]
        "discover_ms": round(discover_ms, 1),
        "files": sum(len(v) for v in discovered.values()),
        "hits": len(hits),
        "mode": mode,
    }
    return hits[:limit]


def infer_host(path: Path) -> str:
    s = str(path)
    if "/.cursor/" in s:
        return "cursor"
    if "/.codex/" in s:
        return "codex"
    if "/.claude/" in s:
        return "claude"
    if "/.workbuddy/" in s:
        return "workbuddy"
    if "/.kimi-code/" in s or "/.kimi/" in s:
        return "kimi"
    return "other"


# ---------- CLI helpers (used by find-thread-by-id / find-thread-by-name) ----------


def print_table(hits: list[Hit], stats: dict) -> None:
    if not hits:
        print("No threads found.")
        mode = stats.get("mode", "?")
        print(
            f"(mode={mode}; scanned {stats.get('files', 0)} files in "
            f"{stats.get('discover_ms', '?')}ms; try --all or another query)",
            file=sys.stderr,
        )
        return
    rows = []
    for h in hits:
        label = h.title or h.prompt or ""
        score_s = f"{h.score:.2f}" if h.score else ("—" if h.match == "recent" else "0.00")
        rows.append(
            (
                h.host[:7],
                h.session_id[:8],
                h.age(),
                _fmt_time(h.mtime),
                (h.match_via or h.match)[:28],
                score_s,
                h.project[:24],
                label[:56],
                h.path,
            )
        )
    headers = ("HOST", "ID", "AGE", "WHEN", "MATCH_VIA", "SCORE", "PROJECT", "NAME/PROMPT")
    widths = [max(len(headers[i]), max(len(r[i]) for r in rows)) for i in range(8)]

    def fmt_row(cols):
        return "  ".join(str(cols[i]).ljust(widths[i]) for i in range(8))

    print(fmt_row(headers))
    print(fmt_row(tuple("-" * w for w in widths)))
    for r in rows:
        print(fmt_row(r[:8]))
        print(f"    {r[8]}")
    sys.stdout.flush()
    print(
        f"\n{len(hits)} shown · mode={stats.get('mode', '?')} · "
        f"scanned {stats.get('files', 0)} files · "
        f"discover {stats.get('discover_ms', '?')}ms",
        file=sys.stderr,
    )
    print(
        "MATCH_VIA legend: title-exact/substr/fuzzy/tokens = UI sidebar title "
        "(fuzzy = edit-distance); "
        "prompt-phrase/tokens = first-user message keywords; "
        "rg-fulltext = --deep transcript search; id = UUID/path; recent = no query. "
        "Prefer title-exact > title-substr > title-fuzzy > title-tokens > prompt-* "
        "when disambiguating.",
        file=sys.stderr,
    )


def hit_as_dict(h: Hit) -> dict:
    """JSON-friendly hit; match_via is the field LLMs should use for multi-hit choice."""
    d = asdict(h)
    d["match_tokens"] = list(h.match_tokens)
    return d


def build_common_parser(prog: str, description: str, *, query_required: bool) -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(prog=prog, description=description)
    if query_required:
        ap.add_argument("query", help="Session UUID or path fragment")
    else:
        ap.add_argument(
            "query",
            nargs="?",
            help="Title / first-user keywords (omit = recent threads for cwd)",
        )
    ap.add_argument("-a", "--agent", action="append", choices=HOSTS, help="Limit host (repeatable)")
    ap.add_argument("-n", "--limit", type=int, default=15, help="Max results (default 15)")
    ap.add_argument("--all", action="store_true", help="Do not scope to current workspace")
    ap.add_argument(
        "--deep",
        action="store_true",
        help="Also ripgrep transcript content (name search only; ignored for id)",
    )
    ap.add_argument(
        "--include-subagents",
        action="store_true",
        help="Include Cursor /subagents/ and kimi worker agent paths in name/recent results",
    )
    ap.add_argument("--json", action="store_true", help="JSON output")
    ap.add_argument("-C", "--cwd", default=None, help="Workspace path (default: $PWD)")
    ap.add_argument("--clear-cache", action="store_true", help="Drop snippet cache and exit")
    return ap


def run_cli(mode: SearchMode, argv: Optional[list[str]] = None) -> int:
    if mode == "id":
        ap = build_common_parser(
            "find-thread-by-id",
            "Locate agent threads by session UUID / path fragment (no name guessing)",
            query_required=True,
        )
    else:
        ap = build_common_parser(
            "find-thread-by-name",
            "Locate agent threads by UI title / first-user keywords (or list recent)",
            query_required=False,
        )
    args = ap.parse_args(argv)

    if args.clear_cache:
        if CACHE_FILE.exists():
            CACHE_FILE.unlink()
            print(f"Cleared {CACHE_FILE}")
        else:
            print("No cache to clear")
        return 0

    cwd = Path(args.cwd).resolve() if args.cwd else Path.cwd().resolve()
    hosts = list(args.agent) if args.agent else list(HOSTS)
    query = getattr(args, "query", None)
    effective_mode: SearchMode = mode
    if mode == "name" and not (query or "").strip():
        effective_mode = "recent"

    hits = find_threads(
        query=query,
        hosts=hosts,
        cwd=cwd,
        limit=args.limit,
        all_projects=args.all,
        deep=args.deep if mode == "name" else False,
        include_subagents=args.include_subagents,
        mode=effective_mode,
    )
    stats = getattr(find_threads, "last_stats", {})

    if args.json:
        print(json.dumps([hit_as_dict(h) for h in hits], ensure_ascii=False, indent=2))
        return 0 if hits else 1

    print_table(hits, stats)
    return 0 if hits else 1


if __name__ == "__main__":
    print(
        "Use find-thread-by-id or find-thread-by-name — do not call _find_thread_common.py directly.",
        file=sys.stderr,
    )
    raise SystemExit(2)
