# Workbuddy

- last_verified: 2026-08-15 (client 2.115.0, macOS arm64)
- confidence: medium (transcripts under `~/.workbuddy/projects/` verified)

Host manual for locating agent conversation threads stored by Workbuddy. Treat paths as heuristics; verify against live signals before relying on a match.

## Live signals

- Workbuddy product/app context in the session (UI references, app name, or rules mentioning Workbuddy)
- Presence of `~/.workbuddy/` (especially `projects/` with `*.jsonl` transcripts)
- macOS: presence of `~/Library/Application Support/com.workbuddy.workbuddy/` (app support only — not where transcripts live)
- Session or thread UUID mentioned in Workbuddy UI or export output

## Known locations

- **Transcripts (primary):** `~/.workbuddy/projects/<encoded-workspace>/<uuid>.jsonl`
  - Layout mirrors Claude Code-style project trees: one encoded workspace dir, one jsonl per thread
  - Encoding is path-like with `/` → `-` (e.g. `/Users/liuxu/repo/local/foo` → `Users-liuxu-repo-local-foo`) — exact rules 待核实 if mapping fails
  - Same stem often has a sibling dir `<uuid>/tool-results/` for tool artifacts (supporting evidence, not the thread itself)
  - Format: JSONL with `type`/`role`/`content`/`timestamp` message records (schema may vary by version)
- **Process heartbeats (NOT transcripts):** `~/.workbuddy/sessions/<pid>.json`
  - Fields like `pid`, `sessionId` (`interactive-<pid>` / `prewarm-...`), `cwd`, `startedAt`, `kind` — use only as live-process signals
- **App support root:** `~/Library/Application Support/com.workbuddy.workbuddy/` — verified 2026-08-15: contains only `Documents/`; no session/thread/conversation files here
- **Other under `~/.workbuddy/`:**
  - `workspace/sessions/<uuid>/` — observed empty for active sessions; do not expect transcript files here
  - `workbuddy.db` (+wal/shm) — SQLite for automations/tasks etc.; **do not guess conversation table schemas** — prefer `projects/*.jsonl` over DB spelunking
- **Never invent SQLite schemas** — if a DB is found and jsonl is missing, prefer official export/API or ask the user for a known-good export path

## ID vs name

- **ID:** transcript UUID / filename stem (e.g. `6b01c691-e361-4e08-9ad6-cb21353d858a` from `*.jsonl`)
- **Name (primary for users):** Workbuddy UI **does not expose session IDs** — users search by sidebar title only. Titles live in `~/.workbuddy/workbuddy.db` table `sessions` (`title`, optional `custom_title`; prefer `custom_title` when set). Join `sessions.id` to `~/.workbuddy/projects/**/<id>.jsonl`.
- Do not conflate `~/.workbuddy/sessions/<pid>.json` sessionIds (`interactive-2001`) with conversation thread UUIDs

## Probe order

1. Confirm Workbuddy is the current host (`~/.workbuddy/` or product cues)
2. If user gave UUID (full or partial), glob `~/.workbuddy/projects/**/<uuid>*.jsonl`
3. Else map current workspace path to `~/.workbuddy/projects/<encoded-workspace>/` and search there first (ID, then name/first-user-message fuzzy)
4. Broader scan under `~/.workbuddy/projects/` if workspace mapping misses or user asks
5. On miss: report steps tried + manual confidence; ask for path/export/paste — do not fall back to inventing content from `sessions/` heartbeats or guessed DB tables

## Failure / staleness notes

- Project path encoding may change across Workbuddy versions; workspace renames/moves break slug heuristics
- Active sessions may still be writing; partial jsonl or missing final records are possible
- `~/.workbuddy/sessions/` is easy to confuse with conversation storage — it is process state only
- Other platforms beyond macOS home-layout 待核实
- Do not invent transcript content — if no `projects/**/*.jsonl` resolves, say so and ask the user to paste or point to the file
