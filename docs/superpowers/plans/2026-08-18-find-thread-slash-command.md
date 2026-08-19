# Find Thread Slash Command Implementation Plan

> **Superseded 2026-08-18:** `/find-thread` is **not** a top-level skill. It lives at `skills/agent-thread-visualizer/find-thread/SKILL.md`. Ignore sibling-skill / `resolve_locator_root` steps below.

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans (inline; user asked to implement immediately) or superpowers:subagent-driven-development. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship `/find-thread` as a sibling skill that finds past agent sessions from recall (“project + what we did + optional host”), ranked as 最相关 / 可能相关, without auto-visualizing.

**Architecture:** Thin `skills/find-thread/SKILL.md` tells the agent how to parse, cascade, reject, and present. Locator binaries stay in `agent-thread-visualizer`. A small `resolve_locator_root.py` finds those scripts. No new scoring engine.

**Tech Stack:** Python 3 stdlib (resolver + unittest), Agent Skills markdown, existing `find-thread-by-name` / `find-thread-by-id`.

## Global Constraints

- Do not copy locator scripts; do not install them on PATH; do not `find ~`.
- Do not invent `cursor://` or unverified resume URLs; do not auto-visualize.
- Find-thread default: all five hosts; named host is a hard filter. Visualizer host default stays “current host first”.
- Always `--json` on locator calls. Never call deprecated `scripts/find-thread`.
- User-facing output is two-bucket markdown cards, not the CLI table.
- Do not commit unless the user asks (repo git rule). Work on branch `feat/find-thread`, not `main`.

## File map

| File | Role |
|------|------|
| `skills/find-thread/scripts/resolve_locator_root.py` | Print visualizer `scripts/` dir or exit 2 |
| `skills/find-thread/scripts/test_resolve_locator_root.py` | Unittest for sibling / home / cwd / miss |
| `skills/find-thread/SKILL.md` | Slash command + cascade + presentation contract |
| `skills/find-thread/agents/openai.yaml` | Codex UI sidecar |
| `skills/agent-thread-visualizer/SKILL.md` | Point recall-search at `/find-thread` |
| `README.md` | Register the skill |
| `docs/superpowers/specs/2026-08-18-find-thread-slash-command-design.md` | Status → approved |

---

### Task 1: Locator root resolver

**Files:**
- Create: `skills/find-thread/scripts/resolve_locator_root.py`
- Test: `skills/find-thread/scripts/test_resolve_locator_root.py`

**Interfaces:**
- Produces: `resolve_locator_root(*, cwd: Path \| None = None, skill_file: Path \| None = None, home: Path \| None = None) -> Path`
- CLI: stdout = scripts dir path; exit 0 on hit, 2 on miss (stderr explains install `agent-thread-visualizer`)

- [ ] **Step 1: Write the failing test**

Create `skills/find-thread/scripts/test_resolve_locator_root.py` as unittest: sibling `skills/agent-thread-visualizer/scripts/find-thread-by-name` wins; `home/.agents/skills/...` wins when no sibling; `{cwd}/.agents/skills/...` wins; miss raises `FileNotFoundError`.

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m unittest skills/find-thread/scripts/test_resolve_locator_root.py -v`

Expected: FAIL (module not found or function missing)

- [ ] **Step 3: Write minimal implementation**

`candidate_roots` order must match the spec exactly:

1. `<skill_dir>/../agent-thread-visualizer/scripts/`
2. `{home}/.agents/skills/agent-thread-visualizer/scripts/`
3. `{home}/.cursor/skills/agent-thread-visualizer/scripts/`
4. `{home}/.claude/skills/agent-thread-visualizer/scripts/`
5. `{cwd}/.agents/skills/agent-thread-visualizer/scripts/`
6. `{cwd}/.cursor/skills/agent-thread-visualizer/scripts/`
7. `{cwd}/.claude/skills/agent-thread-visualizer/scripts/`

First directory containing file `find-thread-by-name` wins. `if __name__` prints that path.

- [ ] **Step 4: Run tests and make sure they pass**

Run: `python3 -m unittest skills/find-thread/scripts/test_resolve_locator_root.py -v`

Expected: OK

- [ ] **Step 5: Commit** — skip unless user asks

---

### Task 2: `skills/find-thread/SKILL.md`

**Files:**
- Create: `skills/find-thread/SKILL.md`

**Interfaces:**
- Consumes: Task 1 CLI; visualizer `find-thread-by-id` / `find-thread-by-name`
- Produces: `/find-thread` behavior contract

- [ ] **Step 1: Contract grep fixtures (failing before SKILL exists)**

Required strings after SKILL.md exists (run as a shell check in Task 2 step 4):

- `argument-hint`
- `$ARGUMENTS`
- `resolve_locator_root`
- `find-thread-by-name`
- `find-thread-by-id`
- `--json`
- `--deep`
- `最相关`
- `可能相关`
- `file://`
- `都不是`
- `cursor://` must **not** appear except inside a prohibition (“Do not invent `cursor://`”)
- `find ~` must appear only as forbidden
- no auto-visualize instruction that starts visualization without user asking

- [ ] **Step 2: Write SKILL.md** (full file in implementation; required sections below)

Frontmatter:

```yaml
name: find-thread
description: >-
  Use when the user wants to find a past agent session/conversation by what
  it did, which project, or which host, especially when they do not remember
  the exact title or UUID. Triggers (EN): /find-thread, find thread, find
  session, find conversation, search agent history, find that chat where,
  recall session. (ZH): 查找会话, 找会话, 找上次那个会话, 会话搜索,
  按做过的事找会话, 回忆会话.
license: MIT
metadata:
  author: fenfenxu
  category: observability
argument-hint: "<项目 / 做了什么 / 可选宿主>"
```

Body must include, in order:

1. `$ARGUMENTS` as the recall string; empty = recent, all hosts, cwd
2. Run `python3 scripts/resolve_locator_root.py` first; on exit 2, stop and tell user to install `agent-thread-visualizer`
3. Facet table (keywords, host, project, time, UUID vs name)
4. Named host = `-a`; unnamed = do not pass `-a`
5. Cascade: UUID → by-id; empty → recent; else name → `--deep` if zero/weak/activity-shaped → `-C`/`--all` if other project; max 3 script calls; at most one synonym retry
6. Rank: match_via order, named host, recency, current project; 最相关 usually 1 (tie: same via + score Δ≤0.05, cap 3); 可能相关 cap 5; cross-host expansion never 最相关
7. **Positive card recipe** (required fields): title, 2–4 sentence summary, host·project·time, `file://` path, full id, why, honest open line
8. Reject loop: exclude `host:session_id`; escalate deep → new keywords → widen project → widen host into 可能相关 only
9. Error table from spec
10. Red flags: dump CLI table as the answer; UUID-only; title-only; auto-visualize; invent deeplinks; `find ~`; deprecated `find-thread`; current-host-only when user did not name a host

Open lines (honest, no resume until host manuals verify):

- cursor: 在 Agents 侧边栏搜标题，或把路径/ID 交给 `/agent-thread-visualizer`
- others: 打开方式未在 host 手册核实 — 给路径和 ID；需要执行地图时用 `/agent-thread-visualizer`

- [ ] **Step 3: agents/openai.yaml**

```yaml
interface:
  display_name: "Find Thread"
  short_description: "Find a past agent session by project, what you did, and optional host — ranked 最相关 / 可能相关."
  default_prompt: "Parse the user's recall into keywords/host/project. Resolve locator scripts, then find-thread-by-id or find-thread-by-name --json (all hosts unless named). Cascade to --deep for activity-shaped queries. Present 最相关 and 可能相关 cards with summary, file:// path, full id, and honest open method. Do not auto-visualize or invent deeplinks."
```

- [ ] **Step 4: Grep contract**

```bash
python3 - <<'PY'
from pathlib import Path
p = Path("skills/find-thread/SKILL.md").read_text()
need = ["argument-hint", "$ARGUMENTS", "resolve_locator_root", "find-thread-by-name",
        "find-thread-by-id", "--json", "--deep", "最相关", "可能相关", "file://", "都不是"]
missing = [s for s in need if s not in p]
assert not missing, missing
assert "Do not invent" in p or "禁止" in p
print("contract ok")
PY
```

Expected: `contract ok`

- [ ] **Step 5: Commit** — skip unless user asks

---

### Task 3: Cross-links

**Files:**
- Modify: `skills/agent-thread-visualizer/SKILL.md` (Workflow §1, after the locate table)
- Modify: `README.md` (install list, skills table, new subsection)
- Modify: spec status line to `approved`

- [ ] **Step 1: Visualizer** — after locate table, add: if the user remembers what they did but not title/id, use sibling **find-thread** (`/find-thread`). This skill still defaults to current host and visualizes after a session is chosen.

- [ ] **Step 2: README** — add `npx skills add ... --skill find-thread`; table row; subsection describing recall search + two-bucket cards; skills.sh browse link.

- [ ] **Step 3: Spec status** `Status: approved`

- [ ] **Step 4: Commit** — skip unless user asks

---

### Task 4: Verify

- [ ] Run resolver unittest
- [ ] Run SKILL contract grep
- [ ] `python3 skills/find-thread/scripts/resolve_locator_root.py` from repo → prints `.../agent-thread-visualizer/scripts`
- [ ] Confirm visualizer still says current-host-first for *its* lookup
