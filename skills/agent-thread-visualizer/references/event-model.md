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
