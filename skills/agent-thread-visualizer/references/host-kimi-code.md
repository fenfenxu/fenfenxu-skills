# kimi-code

- last_verified: 2026-08
- confidence: medium

Host manual for locating agent conversation threads stored by kimi-code (CLI/product). Treat paths as heuristics; verify against live signals before relying on a match.

## Live signals

- kimi-code CLI/product context visible in the session (commands, tool output, or product references)
- `~/.kimi-code/` present on disk
- Legacy migration marker: `~/.kimi/.migrated-to-kimi-code` may exist when the user upgraded from the older kimi home layout
- Session UUID or title references in kimi-code UI/CLI output

## Known locations

- **Primary home:** `~/.kimi-code/`
- **Sessions:** `~/.kimi-code/sessions/` — session directories often named by UUID or session ID (exact naming 待核实 per version)
- **Index (if present):** `~/.kimi-code/session_index.jsonl` — may map IDs to titles/metadata for faster lookup
- **Legacy (pre-migration):** `~/.kimi/sessions/` — use only when primary kimi-code home is missing or user indicates pre-migration data; prefer `~/.kimi-code/` when both exist

## ID vs name

- **ID:** session directory / UUID folder names under `sessions/` (often `session_<uuid>/`)
- **Name:** each session dir has `state.json` with `title` (and `lastPrompt`, which may diverge). Prefer `title` for name search; `session_index.jsonl` only maps id→dir/cwd and does **not** store titles.
- Do not assume folder name equals display title when `state.json` is available — prefer `state.json.title` first

## Probe order

1. Read `session_index.jsonl` if present for ID/title resolution
2. Exact ID under `~/.kimi-code/sessions/` (match directory name or UUID stem)
3. Name match via index / per-session metadata
4. Fall back to legacy `~/.kimi/sessions/` only if needed (primary home empty or user points to legacy data)
5. On miss: report steps tried + manual confidence; ask for path

## Failure / staleness notes

- Migration may leave stale legacy sessions under `~/.kimi/` — always prefer `~/.kimi-code/` when both trees exist
- Index file format and metadata keys are version-dependent — 待核实 field names if parsing fails
- Active sessions may still be writing; partial index entries or missing session dirs are possible
- Do not invent transcript content — if no session resolves, say so and ask the user to paste or point to the file
