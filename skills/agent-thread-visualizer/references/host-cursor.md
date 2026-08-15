# Cursor

- last_verified: 2026-08
- confidence: medium

Host manual for locating agent conversation threads stored by Cursor IDE. Treat paths as heuristics; verify against live signals before relying on a match.

## Live signals

- Agent transcript paths mentioned in the current session context / system hooks (e.g. `<agent_transcripts>` blocks, rules referencing `~/.cursor/projects/.../agent-transcripts/`)
- Project mapping under `~/.cursor/projects/<project-slug>/` derived from the active workspace path
- `CURSOR_*` environment variables or Cursor-specific tooling visible in the runtime context
- Open workspace root path — used to narrow which project slug to prefer when multiple projects exist

## Known locations

- **Transcripts:** `~/.cursor/projects/<project-slug>/agent-transcripts/`
  - Files often named `<uuid>.jsonl` (one file per parent chat transcript)
  - Format: JSONL with message/tool/event records; exact schema varies by Cursor version — 待核实 per file if parsing metadata
- **Related (supporting evidence, not always the thread itself):**
  - `agent-tools/` — tool invocation artifacts tied to the session
  - `canvases/` — Canvas outputs when the agent produced standalone artifacts
  - `terminals/` — terminal session logs referenced during the run
- **Project slug:** typically derived from workspace path (e.g. `/Users/foo/repo/bar` → a slug like `Users-foo-repo-bar` or similar encoding) — encoding rules may change; 待核实 if slug does not match expectations

## ID vs name

- **ID:** transcript UUID / filename stem (e.g. `a1b2c3d4-e5f6-...` from `a1b2c3d4-e5f6-....jsonl`)
- **Name:** 待核实 — may need scanning jsonl for UI title fields, first user message snippet, or parent-agent link text; if absent, match by UUID substring or first user message snippet
- User-facing chat titles in Cursor UI are not guaranteed to appear in transcript filenames; do not assume filename equals display name

## Probe order

1. If user gave UUID (full or partial), glob `**/agent-transcripts/<uuid>*.jsonl` under `~/.cursor/projects/`
2. Else search transcript filenames and readable titles/snippets inside jsonl for the given name (case-insensitive contains)
3. Prefer the project slug matching the current workspace path when multiple hits; if workspace unknown, list candidates with path + mtime
4. On miss: report stale risk (manual may be outdated or slug encoding changed); ask for transcript path or UUID

## Failure / staleness notes

- Project slug encoding changes across Cursor versions; workspace renames or moves break path heuristics
- Transcripts may lag behind the live chat; very recent turns might not yet be flushed to disk
- Do not invent transcript content — if the file is missing or unreadable, say so and ask the user to paste or point to the file
- Cross-project UUID collisions are unlikely but multiple workspaces can each have their own `agent-transcripts/` tree; always note which path was chosen and why
