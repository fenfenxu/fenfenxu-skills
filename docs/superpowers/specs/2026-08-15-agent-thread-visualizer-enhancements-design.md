# Agent Thread Visualizer Enhancements — Design

Date: 2026-08-15  
Status: approved for spec review  
Skill: `skills/agent-thread-visualizer`

## 1. Goal and scope

### Goal

Enhance `agent-thread-visualizer` so that, inside the current AI coding host, the agent can resolve a thread by session ID or name, collect execution facts as completely as sources allow (including skills, tools, sub-agents, and related events), and render a primary-first, collapsible execution map. Output language follows the user. When evidence is sufficient, optionally append session-health advice at the end.

### In scope

- Host-aware session lookup with per-host reference manuals and anti-staleness rules
- Priority hosts: Cursor, Codex, Claude Code, Workbuddy, kimi-code
- Unlisted hosts remain usable via generic probe + user-provided path/paste (never refuse solely because the host is missing from manuals)
- Session input: ID or name; default search only within the current host
- Full collection of available execution-related events; layered visualization (primary expanded, secondary collapsed, details on demand)
- Sub-agent type and/or name made explicit when available
- Output-only i18n (no bilingual SKILL maintenance)
- Optional session-health section at the end when evidence supports it

### Out of scope

- Default cross-host merge of same-named sessions (unless the user explicitly asks)
- Executable multi-host probe scripts in v1
- Full bilingual SKILL / reference documentation

### Chosen package structure

**Slim SKILL.md + `references/`** (not a single fat SKILL, not probe scripts in v1).

## 2. Session resolution and host adaptation

### Host detection

1. Infer the current host from runtime context (Cursor / Codex / Claude Code / Workbuddy / kimi-code / other).
2. Default: search only inside that host. Cross-host search only when the user explicitly requests another tool.
3. If the host has no dedicated manual: do not exit; use the generic probe path in `references/hosts.md`.

### Input: ID or name

- Values that look like stable IDs (UUID, long hex, host-specific prefixes) → exact ID match first.
- Otherwise → match by session name/title (exact, then fuzzy/contains).
- Multiple candidates → present a short chooser (title, time, path/ID); do not pick silently.
- Zero hits → report attempted steps and manual confidence; ask for path, different keywords, or pasted export content.

### Lookup order (anti-staleness)

```text
1. Live signals in the current environment (API / transcript paths / agent metadata)
2. Probe order in references/host-<name>.md (with last_verified / confidence)
3. Generic heuristics (common dirs, naming patterns)
4. Ask the user for a path or raw content
```

Manuals are heuristics, not ground truth. On failure, prefer “manual may be stale” over inventing a match. Note briefly in output when a host manual lookup missed.

### Reference layout

```text
skills/agent-thread-visualizer/
├── SKILL.md
├── agents/openai.yaml
└── references/
    ├── hosts.md                 # overview + generic fallback
    ├── host-cursor.md
    ├── host-codex.md
    ├── host-claude-code.md
    ├── host-workbuddy.md
    ├── host-kimi-code.md
    ├── event-model.md
    └── session-health.md
```

Unverified sections are marked `待核实` / `unverified`; never invent paths or APIs.

Each host file should include:

- `last_verified` (date or month)
- `confidence` (`high` | `medium` | `low` | `unverified`)
- Known session locations / APIs (if any)
- ID vs title field names (if known)
- Ordered probe steps
- Failure notes (what “stale” looks like)

## 3. Collection, sub-agents, layered visualization

### Collection principles

- Collect as completely as sources allow: every available execution-related event (messages, status, sub-agents, file changes, times, rollout/event logs, correlated fields). Do not drop skill loads or tool calls at collection time to “keep the map clean”—cleaning is a display concern only.
- Always retain, by stage when possible:
  - loaded **skills** (name, approximate window, trigger if present)
  - invoked **tools** (name/category, success/failure, link to surrounding decisions)
- Privacy and bulk: secrets, tokens, huge base64, and raw oversized tool dumps stay out of visualization body; record fold/redaction counts with evidence refs. Redaction is not the same as discarding the event record.
- Missing fields stay unknown; no fabrication.

### Normalized event extensions

Keep existing core fields:

```text
id, kind, actor, parent_id, started_at, ended_at, status,
human_summary, evidence_ref, confidence, environment
```

Add when available:

```text
skill_refs[]
tool_refs[]
subagent_type
subagent_name
related_event_ids[]
```

Additional `kind` values: `skill_load`, `tool_call`. Unclassifiable events remain `other` with original type preserved.

### Sub-agent clarity

- Swimlane title preference: `type · name` (show what exists; mark missing parts unknown).
- Spawn/join edges keep parent linkage.
- Type/name come from host metadata or spawn parameters; do not invent from narrative alone.

### Visualization layers

| Layer | Default | Content |
|-------|---------|---------|
| Primary | Expanded | Goal, main-agent stages, key decisions, failures/retries, sub-agent start/join, environment tags |
| Secondary | Collapsed | Per-stage skills list, tool-call summaries, waits, compaction/context signals |
| Detail | On expand/click | Exact times, evidence refs, single tool arg summaries, related events |

Timeline segment length still follows real duration. Secondary info must not fake duration on the main axis. Use Mermaid when a static map is enough; use HTML when branching/expandable detail is needed (existing visualize skill contract if available).

**Collect fully; display selectively.** Full event retention in the normalized model does not require painting every event on the primary timeline.

## 4. i18n, session health, output

### i18n (output only)

- Summaries, legends, stage labels, and advice follow the user’s language (or an explicitly requested language).
- Do not maintain parallel EN/ZH SKILL bodies in v1.
- `agents/openai.yaml` may stay Chinese-first; adjust later if needed.

### Session health (optional, end of output)

When evidence is sufficient, append a short “会话健康” / “Session health” section **after** the visualization. Omit if the user declines advice.

| Signal | Advice direction |
|--------|------------------|
| Many compressions / compactions | Prefer a new session or split work to reduce long-thread distortion |
| Context nearly full | Finish current goal, then new thread; avoid stuffing new topics |
| Frequent topic switching in one session | One theme per session; side quests get new sessions with links back |

Every tip must cite observed facts (counts, ratios, stage-switch evidence). No evidence → no tip. Numeric thresholds are not hard-coded in v1: prefer host-reported metrics when present; otherwise use qualitative judgment and still cite the concrete observations.

### Output order

1. One or two sentences: what the visualization helps the user see
2. Visualization (primary open, secondary collapsed by default)
3. Optional session-health section
4. Brief sources and notable unknowns

## 5. SKILL.md workflow changes (implementation intent)

Update the skill workflow to include, in order:

1. Detect host + resolve session (ID/name) via lookup order above; read `references/hosts.md` and the matching host file when needed
2. Collect fully (including skills, tools, related events, sub-agent type/name)
3. Normalize with extended fields
4. Fold low-value bulk for display only (data still collected where safe)
5. Render layered visualization in the user’s language
6. Optionally append session-health tips from `references/session-health.md`
7. Validate: no invented events, clear main/sub grouping, duration fidelity, collapsed secondary readable on expand

## 6. Success criteria

- In Cursor (and other documented hosts when manuals are filled), resolve by ID or name, or fail clearly with fallback
- Unlisted hosts can still use the skill via generic probe / user input
- When data exists, output includes stage-linked skills/tools and sub-agent type or name
- Primary view stays uncluttered; details expand on demand
- Health tips appear at the end only with evidence; otherwise absent
- Host manuals carry `last_verified` / `confidence` and degrade gracefully when stale

## 7. Decisions log

| Topic | Decision |
|-------|----------|
| Host manuals | Per-host references + anti-staleness; not hard single paths |
| Unlisted hosts | Still supported via generic fallback |
| Hosts in v1 manuals | Cursor, Codex, Claude Code, Workbuddy, kimi-code |
| i18n | Output language only |
| Skills/tools | Collect all valuable events; visualize primary-first with collapse |
| Practice tips | Optional; default when evidenced; place at end |
| Scripts | None in v1 |
| Package shape | Slim SKILL + references |
| Output order (final) | what-to-see → visualization → sources/unknowns → optional session-health (absolute last). Overrides §4 numbered list which placed health before sources. |
