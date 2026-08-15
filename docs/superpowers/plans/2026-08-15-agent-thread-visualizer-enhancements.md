# Agent Thread Visualizer Enhancements Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Update `agent-thread-visualizer` so agents resolve sessions by ID/name in the current host, collect execution events fully (skills, tools, sub-agents), render primary-first collapsible maps, localize output language, and optionally append evidenced session-health tips.

**Architecture:** Keep a slim `SKILL.md` as the always-loaded workflow. Put host probe manuals, event-model extensions, and session-health guidance in `references/` (progressive disclosure). Manuals are ordered heuristics with `last_verified` / `confidence`, never single hard-coded truths. No probe scripts in v1.

**Tech Stack:** Agent Skills markdown (`SKILL.md` + `references/*.md` + `agents/openai.yaml`); no runtime code.

**Spec:** `docs/superpowers/specs/2026-08-15-agent-thread-visualizer-enhancements-design.md`

## Global Constraints

- Unlisted hosts must still work via generic fallback; never refuse solely because a host file is missing.
- Default search scope = current host only; cross-host only when user asks.
- Collect fully; display selectively (primary expanded, secondary collapsed, detail on demand).
- Output-only i18n; do not maintain bilingual SKILL bodies.
- Never invent paths/APIs; mark unknowns `待核实` / `unverified`.
- No multi-host probe scripts in v1.
- Session-health tips only with cited evidence; place at end of output.
- Prefer Chinese instructional prose in SKILL/references to match the existing skill voice, unless a section is intentionally bilingual for field names.

---

## File structure (locked)

| File | Responsibility |
|------|----------------|
| `skills/agent-thread-visualizer/SKILL.md` | Workflow: host detect → resolve → collect → normalize → layered viz → optional health → validate |
| `skills/agent-thread-visualizer/agents/openai.yaml` | Display name / short description / default prompt aligned with new capabilities |
| `skills/agent-thread-visualizer/references/hosts.md` | Host detection cues, lookup order, generic fallback |
| `skills/agent-thread-visualizer/references/host-cursor.md` | Cursor session probe manual |
| `skills/agent-thread-visualizer/references/host-codex.md` | Codex session probe manual |
| `skills/agent-thread-visualizer/references/host-claude-code.md` | Claude Code session probe manual |
| `skills/agent-thread-visualizer/references/host-workbuddy.md` | Workbuddy session probe manual |
| `skills/agent-thread-visualizer/references/host-kimi-code.md` | kimi-code session probe manual |
| `skills/agent-thread-visualizer/references/event-model.md` | Extended fields, kinds, layer mapping |
| `skills/agent-thread-visualizer/references/session-health.md` | Signals + advice patterns |
| `README.md` | One-line skill blurb update if needed |

---

### Task 1: Shared references — `hosts.md` + `event-model.md`

**Files:**
- Create: `skills/agent-thread-visualizer/references/hosts.md`
- Create: `skills/agent-thread-visualizer/references/event-model.md`
- Test: manual checklist below (no automated test suite in this repo)

**Interfaces:**
- Consumes: design §2 lookup order, §3 event extensions
- Produces: canonical lookup order text; field/`kind` lists that later SKILL.md must link to

- [ ] **Step 1: Create `references/` directory**

```bash
mkdir -p skills/agent-thread-visualizer/references
```

- [ ] **Step 2: Write `hosts.md` with this content**

```markdown
# Host detection and session lookup

## Lookup order (anti-staleness)

1. Live signals in the current environment (API / transcript paths / agent metadata)
2. Matching `references/host-<name>.md` probe order (`last_verified` / `confidence`)
3. Generic heuristics below
4. Ask the user for a path or pasted export

Manuals are heuristics. On miss, prefer “manual may be stale” over inventing a match. Note briefly when a host-manual lookup missed.

## Detect current host

Use runtime cues (not user guesswork):

| Host | Typical cues |
|------|----------------|
| Cursor | `CURSOR_*` env, `~/.cursor/`, agent transcripts under project dirs, Cursor UI/tooling in context |
| Codex | `~/.codex/`, Codex CLI/app context, `rollout-*.jsonl` |
| Claude Code | `~/.claude/`, Claude Code CLI/project context |
| Workbuddy | `com.workbuddy.workbuddy` app support / Workbuddy product cues |
| kimi-code | `~/.kimi-code/`, legacy `~/.kimi/` migration markers, kimi-code CLI/product cues |
| other | Anything else → generic fallback only |

Default: search **only** the current host. Cross-host only if the user explicitly names another tool.

## Resolve ID vs name

- Looks like stable ID (UUID, long hex, host-specific prefix) → exact ID first
- Else → title/name exact, then fuzzy/contains
- Multiple hits → short chooser (title, time, path/ID); never silent pick
- Zero hits → report steps tried + manual confidence; ask for path/keywords/paste

## Generic fallback (unlisted or failed host)

Still run the skill:

1. Ask whether the user can point to a session file/dir or paste export
2. Search common patterns under the user’s home if permissioned: `**/agent-transcripts/**`, `**/sessions/**`, `**/rollout-*.jsonl`, `**/*thread*`, `**/*conversation*`
3. If nothing usable: explain unknowns; do not fabricate a timeline

## Host manuals

- [host-cursor.md](host-cursor.md)
- [host-codex.md](host-codex.md)
- [host-claude-code.md](host-claude-code.md)
- [host-workbuddy.md](host-workbuddy.md)
- [host-kimi-code.md](host-kimi-code.md)
```

- [ ] **Step 3: Write `event-model.md` with this content**

```markdown
# Event model extensions

## Core fields (always)

```text
id, kind, actor, parent_id, started_at, ended_at, status,
human_summary, evidence_ref, confidence, environment
```

## Extended fields (when available)

```text
skill_refs[]
tool_refs[]
subagent_type
subagent_name
related_event_ids[]
```

## `kind` set

Existing: `user_goal`, `milestone`, `tool_work`, `subagent_spawn`, `subagent_join`, `retry`, `failure`, `cancel`, `retract`, `fork`, `merge`, `wait`, `file_change`, `environment`

Added: `skill_load`, `tool_call`

Unclassifiable → `other` (keep original type).

## Collection vs display

- **Collect:** every available execution-related event; do not drop skill loads or tool calls to “keep the map clean”.
- **Display layers:**
  - Primary (expanded): goal, main stages, key decisions, failures/retries, sub-agent start/join, environment
  - Secondary (collapsed): per-stage skills list, tool summaries, waits, compaction/context signals
  - Detail (on expand): exact times, evidence, single tool arg summaries, related events
- Redact secrets / huge payloads from visualization body; keep fold counts + evidence refs. Redaction ≠ discard.

## Sub-agent labeling

Swimlane title: `type · name` (show known parts; mark missing as 未知/unknown).
Type/name only from host metadata or spawn parameters.
```

- [ ] **Step 4: Verify files exist and are non-empty**

```bash
test -s skills/agent-thread-visualizer/references/hosts.md && \
test -s skills/agent-thread-visualizer/references/event-model.md && \
wc -l skills/agent-thread-visualizer/references/hosts.md skills/agent-thread-visualizer/references/event-model.md
```

Expected: both files listed with line counts > 30.

- [ ] **Step 5: Commit** (only if the user asked to commit, or during an approved execution pass)

```bash
git add skills/agent-thread-visualizer/references/hosts.md \
        skills/agent-thread-visualizer/references/event-model.md
git commit -m "$(cat <<'EOF'
docs(agent-thread-visualizer): add hosts lookup and event model refs

EOF
)"
```

---

### Task 2: Host manuals — Cursor + Codex

**Files:**
- Create: `skills/agent-thread-visualizer/references/host-cursor.md`
- Create: `skills/agent-thread-visualizer/references/host-codex.md`

**Interfaces:**
- Consumes: header fields required by `hosts.md` (`last_verified`, `confidence`, probe order)
- Produces: probe steps agents follow when host is Cursor or Codex

- [ ] **Step 1: Write `host-cursor.md`**

Use `last_verified: 2026-08` and `confidence: medium`. Include at least:

```markdown
# Cursor

- last_verified: 2026-08
- confidence: medium

## Live signals

- Agent transcript paths mentioned in the current session context / system hooks
- Project mapping under `~/.cursor/projects/<project-slug>/`

## Known locations

- Transcripts: `~/.cursor/projects/<project-slug>/agent-transcripts/`
  - Files often named `<uuid>.jsonl`
- Related: `agent-tools/`, `canvases/`, `terminals/` under the same project slug (supporting evidence, not always the thread itself)

## ID vs name

- ID: transcript UUID / filename stem
- Name: 待核实 — may need scanning jsonl / UI title fields; if absent, match by UUID substring or first user message snippet

## Probe order

1. If user gave UUID, glob `**/agent-transcripts/<uuid>*.jsonl` under `~/.cursor/projects/`
2. Else search transcript filenames and readable titles/snippets for the given name
3. Prefer the project slug matching the current workspace path when multiple hits
4. On miss: report stale risk; ask for transcript path

## Failure / staleness notes

- Project slug encoding changes; workspace renames break path heuristics
- Do not invent transcript content
```

- [ ] **Step 2: Write `host-codex.md`**

```markdown
# Codex

- last_verified: 2026-08
- confidence: medium

## Live signals

- Codex CLI/app session APIs if present in context
- Paths under `~/.codex/`

## Known locations

- Active/archived rollouts: `~/.codex/sessions/` (often `rollout-*.jsonl`)
- Also check: `~/.codex/archived_sessions/` if present
- macOS app support may include `~/Library/Application Support/Codex` or `com.openai.codex` — treat as secondary; mark details 待核实 if layout differs

## ID vs name

- ID: UUID segments inside `rollout-...-<uuid>.jsonl` filenames
- Name: 待核实 — search rollout metadata / first user message if file format allows

## Probe order

1. Exact filename / UUID match under `~/.codex/sessions/`
2. `archived_sessions` if needed
3. Fuzzy name over readable metadata
4. On miss: ask for rollout path

## Failure / staleness notes

- Rollout filename scheme may change across Codex versions
```

- [ ] **Step 3: Verify**

```bash
rg -n "last_verified|confidence|Probe order" \
  skills/agent-thread-visualizer/references/host-cursor.md \
  skills/agent-thread-visualizer/references/host-codex.md
```

Expected: each file shows all three patterns.

- [ ] **Step 4: Commit** (if committing)

```bash
git add skills/agent-thread-visualizer/references/host-cursor.md \
        skills/agent-thread-visualizer/references/host-codex.md
git commit -m "$(cat <<'EOF'
docs(agent-thread-visualizer): add Cursor and Codex host manuals

EOF
)"
```

---

### Task 3: Host manuals — Claude Code + Workbuddy + kimi-code

**Files:**
- Create: `skills/agent-thread-visualizer/references/host-claude-code.md`
- Create: `skills/agent-thread-visualizer/references/host-workbuddy.md`
- Create: `skills/agent-thread-visualizer/references/host-kimi-code.md`

**Interfaces:**
- Same header contract as Task 2
- kimi-code must mention both `~/.kimi-code/` and legacy `~/.kimi/` migration

- [ ] **Step 1: Write `host-claude-code.md`**

```markdown
# Claude Code

- last_verified: 2026-08
- confidence: medium

## Live signals

- Claude Code CLI / project context
- `~/.claude/` trees

## Known locations

- Project data: `~/.claude/projects/<encoded-path>/`
- Session/history artifacts: 待核实 exact filename patterns per version — probe for jsonl/json session files under the project dir
- Do not treat skill caches as sessions

## ID vs name

- ID: session UUID if present in filenames or metadata
- Name: match title/summary fields when present; else first user turn snippet

## Probe order

1. Map current workspace path to `~/.claude/projects/<encoded-path>/`
2. ID match within that project dir
3. Name/fuzzy within that project dir
4. Broader `~/.claude/projects/` only if user asks or local project dir missing
5. On miss: ask for path/export

## Failure / staleness notes

- Path encoding for project dirs changes; prefer live workspace mapping
```

- [ ] **Step 2: Write `host-workbuddy.md`**

```markdown
# Workbuddy

- last_verified: 2026-08
- confidence: low

## Live signals

- Workbuddy product/app context in the session
- macOS: `~/Library/Application Support/com.workbuddy.workbuddy/`

## Known locations

- App support root: `~/Library/Application Support/com.workbuddy.workbuddy/`
- Exact session file layout: 待核实 — probe for `sessions`, `threads`, `conversations`, `*.jsonl`, `*.db` under the app support tree
- Never invent SQLite schemas; if DB found, prefer official export/API or ask user

## ID vs name

- 待核实 field names; try filename stems and any obvious `id`/`title` JSON keys

## Probe order

1. Confirm Workbuddy is current host
2. List likely session containers under app support
3. ID then name match
4. On miss: ask user for export/path; keep skill usable via pasted content

## Failure / staleness notes

- Low confidence until layout verified on a real install
```

- [ ] **Step 3: Write `host-kimi-code.md`**

```markdown
# kimi-code

- last_verified: 2026-08
- confidence: medium

## Live signals

- kimi-code CLI/product context
- `~/.kimi-code/` present; legacy `~/.kimi/.migrated-to-kimi-code` may exist

## Known locations

- Primary: `~/.kimi-code/sessions/`
- Index (if present): `~/.kimi-code/session_index.jsonl`
- Legacy: `~/.kimi/sessions/` (pre-migration); prefer `~/.kimi-code/` when both exist

## ID vs name

- ID: session directory / UUID folder names under `sessions/`
- Name: check `session_index.jsonl` or per-session metadata when available; else fuzzy over known titles

## Probe order

1. Read `session_index.jsonl` if present for ID/title resolution
2. Exact ID under `~/.kimi-code/sessions/`
3. Name match via index / metadata
4. Fall back to legacy `~/.kimi/sessions/` only if needed
5. On miss: ask for path

## Failure / staleness notes

- Migration may leave stale legacy sessions; prefer kimi-code home
```

- [ ] **Step 4: Verify all five host files link from `hosts.md` and exist**

```bash
for f in host-cursor host-codex host-claude-code host-workbuddy host-kimi-code; do
  test -s "skills/agent-thread-visualizer/references/${f}.md" || exit 1
done
rg -n "host-cursor|host-codex|host-claude-code|host-workbuddy|host-kimi-code" \
  skills/agent-thread-visualizer/references/hosts.md
```

Expected: all five files exist; `hosts.md` lists all five.

- [ ] **Step 5: Commit** (if committing)

```bash
git add skills/agent-thread-visualizer/references/host-claude-code.md \
        skills/agent-thread-visualizer/references/host-workbuddy.md \
        skills/agent-thread-visualizer/references/host-kimi-code.md
git commit -m "$(cat <<'EOF'
docs(agent-thread-visualizer): add Claude Code, Workbuddy, kimi-code manuals

EOF
)"
```

---

### Task 4: Session health reference

**Files:**
- Create: `skills/agent-thread-visualizer/references/session-health.md`

**Interfaces:**
- Consumes: design §4 signals table
- Produces: optional end-of-output advice rules linked from SKILL.md

- [ ] **Step 1: Write `session-health.md`**

```markdown
# Session health (optional, end of output)

Show only when evidence exists. Place **after** the visualization. Omit if the user declines advice.

## Signals

| Signal | What to look for | Advice direction |
|--------|------------------|------------------|
| Many compressions / compactions | Compaction/summarization events, repeated “context compressed” markers | Suggest new session or split work to reduce long-thread distortion |
| Context nearly full | Host-reported context/token occupancy high; warnings about limit | Finish current goal, then open a new thread; avoid stuffing new topics |
| Frequent topic switching | Multiple unrelated user goals interleaved without clear phase boundaries | One theme per session; side quests → new sessions with links back |

## Rules

- Every tip must cite concrete observations (counts, quotes, event ids, ratios).
- No host metric → qualitative judgment still requires cited observations.
- No evidence → write nothing (do not speculate).
- Keep the section short (typically 1–3 bullets).
- Match the user’s language (output i18n).
```

- [ ] **Step 2: Verify**

```bash
rg -n "Omit if|No evidence|after" skills/agent-thread-visualizer/references/session-health.md
```

Expected: matches for optional/end placement and no-evidence rule.

- [ ] **Step 3: Commit** (if committing)

```bash
git add skills/agent-thread-visualizer/references/session-health.md
git commit -m "$(cat <<'EOF'
docs(agent-thread-visualizer): add session-health guidance

EOF
)"
```

---

### Task 5: Rewrite `SKILL.md` workflow

**Files:**
- Modify: `skills/agent-thread-visualizer/SKILL.md`
- Test: structure checklist via `rg`

**Interfaces:**
- Consumes: all `references/*` produced above
- Produces: single entry workflow agents follow when the skill loads

- [ ] **Step 1: Update frontmatter `description`** to include new triggers (host/session id/name, skills/tools timeline, session health), stay under 1024 chars, third person, WHAT + WHEN. Use approximately:

```yaml
description: Collect, normalize, summarize, and visualize one or more AI agent threads as human-readable execution maps, with host-aware session lookup (ID or name), full collection of skills/tools/sub-agents, layered primary/secondary display, output-language i18n, and optional session-health tips. Use when a user asks to inspect an agent thread visually, find a Cursor/Codex/Claude Code/Workbuddy/kimi-code session by id or name, understand main-agent and child-agent work, explain timing, retries, detours, failures, cancellations, forks, waits, files, loaded skills, tool calls, or local/worktree execution context.
```

- [ ] **Step 2: Replace the intro + Workflow sections** so the workflow order is:

1. Detect host + resolve session (link `references/hosts.md` + matching host file)
2. Determine scope (single vs multi thread)
3. Collect fully (tasks, actors, times, skills, tools, related events, environment, evidence) — link `event-model.md`
4. Fold/redact for **display only**
5. Normalize with extended fields
6. Visualize layered (primary/secondary/detail); keep existing encoding rules
7. Output order: what-to-see → viz → optional health (`session-health.md`) → sources/unknowns
8. Validation checklist including sub-agent `type · name` and no invented events

Keep Visualization Design substance from the current skill (layout, encoding, human priority), but add an explicit **分层展示** subsection matching the three layers.

Keep Chinese instructional voice. Change the old “默认用中文” line to: follow the user’s language (or explicit request); Chinese is fine when the user writes Chinese.

Critical wording to include verbatim in collection:

- 采集时尽量保留所有可获得的执行相关事件；不要为了“图干净”在采集阶段丢掉 skill 加载或工具调用。
- 未收录宿主不拒绝执行，走通用回退。

- [ ] **Step 3: Ensure progressive disclosure links exist**

```bash
rg -n "references/hosts\.md|event-model\.md|session-health\.md|host-cursor|分层|会话健康|输出语言" \
  skills/agent-thread-visualizer/SKILL.md
```

Expected: hits for hosts, event-model, session-health, layered display, health, i18n.

- [ ] **Step 4: Line-count / size sanity**

```bash
wc -l skills/agent-thread-visualizer/SKILL.md
```

Expected: preferably under ~200 lines; if over 250, move more detail into references rather than growing SKILL further.

- [ ] **Step 5: Commit** (if committing)

```bash
git add skills/agent-thread-visualizer/SKILL.md
git commit -m "$(cat <<'EOF'
feat(agent-thread-visualizer): host-aware workflow, full collect, layered viz

EOF
)"
```

---

### Task 6: Metadata polish + acceptance checklist

**Files:**
- Modify: `skills/agent-thread-visualizer/agents/openai.yaml`
- Modify: `README.md` (skills table blurb only if it still under-describes)

**Interfaces:**
- Consumes: final SKILL capabilities
- Produces: discoverable prompt/description aligned with the skill

- [ ] **Step 1: Update `agents/openai.yaml`**

```yaml
interface:
  display_name: "Agent Thread Visualizer"
  short_description: "按宿主定位会话，整理 skills/工具/子 Agent，输出可展开的执行地图"
  default_prompt: "请在当前 AI 工具内按我给的会话 ID 或名称定位 thread，尽量完整收集阶段、skills、工具调用、子 Agent（含类型/名称）、失败与环境信息，再生成主次分层、细节可展开的执行地图；若有证据，文末可附简短会话健康建议。"
```

- [ ] **Step 2: Update README skills table cell** to mention host-aware lookup + layered map (one line).

- [ ] **Step 3: Run full acceptance checklist**

```bash
# structure
ls skills/agent-thread-visualizer/references/
test -f skills/agent-thread-visualizer/SKILL.md

# required refs present
for f in hosts event-model session-health \
  host-cursor host-codex host-claude-code host-workbuddy host-kimi-code; do
  test -s "skills/agent-thread-visualizer/references/${f}.md" || exit 1
done

# constraints present in SKILL
rg -n "未收录|通用回退|输出语言|分层|会话健康|skill_load|subagent_type" \
  skills/agent-thread-visualizer/SKILL.md
```

Manual review against spec success criteria:

1. Host-aware ID/name resolution documented
2. Unlisted hosts still usable
3. Skills/tools/sub-agent fields documented
4. Primary/secondary/detail layers documented
5. Health tips optional + evidenced + end placement
6. Manuals have `last_verified` / `confidence`

- [ ] **Step 4: Commit** (if committing)

```bash
git add skills/agent-thread-visualizer/agents/openai.yaml README.md
git commit -m "$(cat <<'EOF'
chore(agent-thread-visualizer): align openai.yaml and README blurb

EOF
)"
```

---

## Spec coverage self-check

| Spec requirement | Task |
|------------------|------|
| Slim SKILL + references package | 1–5 |
| Host detect + current-host default | 1, 5 |
| ID or name resolution | 1, 5 |
| Anti-staleness lookup order | 1 |
| Five host manuals + unverified allowed | 2, 3 |
| Unlisted hosts still work | 1, 5 |
| Full collect / selective display | 1 (`event-model`), 5 |
| skill/tool/subagent fields + kinds | 1, 5 |
| Sub-agent type · name | 1, 5 |
| Output-only i18n | 5 |
| Optional health tips at end | 4, 5 |
| No probe scripts v1 | (none added) |
| openai.yaml / discoverability | 6 |

## Placeholder scan

No TBD implementation steps; host unknowns intentionally use `待核实` inside reference content per spec.
