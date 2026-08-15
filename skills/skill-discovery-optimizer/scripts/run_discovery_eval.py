#!/usr/bin/env python3
"""Dual-channel find-skills / skills.sh discovery eval."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ANSI = re.compile(r"\x1b\[[0-9;]*m")
SLUG_RE = re.compile(r"([\w.-]+/[\w.-]+)@([\w.-]+)")


def load_queries(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text())
    if "cases" not in data or "target" not in data:
        raise SystemExit(f"invalid queries file: {path}")
    return data


def description_len(skill_md: Path) -> int | None:
    if not skill_md.exists():
        return None
    text = skill_md.read_text()
    parts = text.split("---", 2)
    if len(parts) < 3:
        return None
    fm = parts[1]
    lines = fm.strip().splitlines()
    body: list[str] = []
    started = False
    for line in lines:
        if line.startswith("description:"):
            started = True
            inline = line.split(":", 1)[1].strip()
            if inline and not inline.startswith(">") and not inline.startswith("|"):
                return len(inline.strip("\"'"))
            continue
        if not started:
            continue
        if line.startswith("license:") or line.startswith("metadata:") or (
            line and not line[0].isspace() and ":" in line and not line.startswith(" ")
        ):
            break
        if line.startswith("  "):
            body.append(line[2:].strip())
    return len(" ".join(x for x in body if x))


def api_search(query: str, owner: str | None, limit: int, retries: int = 6) -> dict[str, Any]:
    params: dict[str, str] = {"q": query, "limit": str(limit)}
    if owner:
        params["owner"] = owner
    url = "https://skills.sh/api/search?" + urllib.parse.urlencode(params)
    last_err = ""
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(url, timeout=45) as resp:
                return json.load(resp)
        except urllib.error.HTTPError as e:
            last_err = f"HTTP {e.code}"
            if e.code in (429, 503):
                time.sleep(2.0 * (attempt + 1))
                continue
            return {"_error": last_err}
        except Exception as e:  # noqa: BLE001
            last_err = str(e)
            time.sleep(1.5 * (attempt + 1))
    return {"_error": last_err or "rate limited"}


def cli_find(query: str, owner: str | None) -> tuple[str, int]:
    cmd = ["npx", "skills", "find", query]
    if owner:
        cmd += ["--owner", owner]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        out = ANSI.sub("", (proc.stdout or "") + "\n" + (proc.stderr or ""))
        return out, proc.returncode
    except Exception as e:  # noqa: BLE001
        return f"ERR:{e}", 1


def parse_cli(out: str) -> list[str]:
    hits: list[str] = []
    for line in out.splitlines():
        m = SLUG_RE.search(line)
        if m:
            hits.append(f"{m.group(1)}@{m.group(2)}")
    return hits


def is_hit(ids: list[str], owner: str, skill: str) -> tuple[bool, int | None]:
    for i, item in enumerate(ids):
        low = item.lower()
        if owner.lower() in low and skill.lower() in low:
            return True, i + 1
    return False, None


def eval_case(
    case: dict[str, Any],
    target: dict[str, str],
    modes: list[str],
    api_limit: int,
    delay: float,
) -> dict[str, Any]:
    owner = target["owner"]
    skill = target["skill"]
    q = case["query"]
    row: dict[str, Any] = {
        "lang": case.get("lang"),
        "priority": case.get("priority", "p1"),
        "intent": case.get("intent"),
        "query": q,
        "channels": {},
    }
    for mode in modes:
        if delay:
            time.sleep(delay)
        if mode == "api":
            data = api_search(q, None, api_limit)
            if "_error" in data:
                row["channels"]["api"] = {"error": data["_error"], "hit": False}
                continue
            ids = [s.get("id") or "" for s in (data.get("skills") or [])]
            hit, rank = is_hit(ids, owner, skill)
            row["channels"]["api"] = {
                "hit": hit,
                "rank": rank,
                "n": len(ids),
                "searchType": data.get("searchType"),
                "top": ids[:3],
            }
        elif mode == "cli":
            out, code = cli_find(q, None)
            ids = parse_cli(out)
            hit, rank = is_hit(ids, owner, skill)
            row["channels"]["cli"] = {
                "hit": hit,
                "rank": rank,
                "n": len(ids),
                "exit": code,
                "top": ids[:3],
            }
        elif mode == "cli-owner":
            out, code = cli_find(q, owner)
            ids = parse_cli(out)
            hit, rank = is_hit(ids, owner, skill)
            row["channels"]["cli-owner"] = {
                "hit": hit,
                "rank": rank,
                "n": len(ids),
                "exit": code,
                "top": ids[:3],
            }
        else:
            raise SystemExit(f"unknown mode: {mode}")
    return row


def summarize(rows: list[dict[str, Any]], modes: list[str]) -> dict[str, Any]:
    summary: dict[str, Any] = {"by_channel": {}, "by_lang": {}, "p0": {}}
    for mode in modes:
        hits = misses = errs = 0
        p0_hits = p0_total = 0
        for r in rows:
            ch = r["channels"].get(mode) or {}
            if ch.get("error"):
                errs += 1
            elif ch.get("hit"):
                hits += 1
            else:
                misses += 1
            if r.get("priority") == "p0":
                p0_total += 1
                if ch.get("hit"):
                    p0_hits += 1
        summary["by_channel"][mode] = {
            "hits": hits,
            "misses": misses,
            "errors": errs,
            "hit_rate": round(hits / max(hits + misses, 1), 3),
            "p0_hit_rate": round(p0_hits / max(p0_total, 1), 3) if p0_total else None,
            "p0_hits": p0_hits,
            "p0_total": p0_total,
        }
    lang_c: Counter[str] = Counter()
    for r in rows:
        lang = r.get("lang") or "?"
        cli = (r["channels"].get("cli") or {})
        if cli.get("hit"):
            lang_c[f"{lang}:cli_hit"] += 1
        else:
            lang_c[f"{lang}:cli_miss"] += 1
    summary["by_lang"] = dict(lang_c)
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description="Eval skill discoverability on skills.sh / find-skills")
    parser.add_argument("--queries", required=True, type=Path)
    parser.add_argument("--modes", default="api,cli", help="comma: api,cli,cli-owner")
    parser.add_argument("--owner", default=None, help="override target.owner for cli-owner")
    parser.add_argument("--api-limit", type=int, default=40)
    parser.add_argument("--delay", type=float, default=1.0)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--skill-md", type=Path, default=None, help="optional SKILL.md for description length")
    parser.add_argument("--label", default="")
    parser.add_argument("--check-description", action="store_true")
    args = parser.parse_args()

    data = load_queries(args.queries)
    target = dict(data["target"])
    if args.owner:
        target["owner"] = args.owner
    modes = [m.strip() for m in args.modes.split(",") if m.strip()]

    if args.check_description and args.skill_md:
        n = description_len(args.skill_md)
        print(f"description_chars={n}")
        if n is not None and n > 1024:
            raise SystemExit(f"description too long: {n}")

    rows = []
    for case in data["cases"]:
        rows.append(eval_case(case, target, modes, args.api_limit, args.delay))

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "label": args.label,
        "target": target,
        "modes": modes,
        "api_limit": args.api_limit,
        "description_chars": description_len(args.skill_md) if args.skill_md else None,
        "summary": summarize(rows, modes),
        "results": rows,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")

    # human table
    print("query|lang|pri|" + "|".join(f"{m}_hit|{m}_rank" for m in modes))
    for r in rows:
        parts = [r["query"], r.get("lang") or "", r.get("priority") or ""]
        for m in modes:
            ch = r["channels"].get(m) or {}
            if ch.get("error"):
                parts += ["ERR", "—"]
            else:
                parts += ["Y" if ch.get("hit") else "n", str(ch.get("rank") or "—")]
        print("|".join(parts))
    print(json.dumps(report["summary"], ensure_ascii=False, indent=2))
    print(f"wrote {args.out}")


if __name__ == "__main__":
    main()
