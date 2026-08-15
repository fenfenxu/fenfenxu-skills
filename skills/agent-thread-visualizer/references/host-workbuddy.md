# Workbuddy

- last_verified: 2026-08-15 (client 2.115.0, macOS arm64)
- confidence: medium (layout verified; current-session transcript NOT locally readable)

Host manual for locating agent conversation threads stored by Workbuddy. Treat paths as heuristics; verify against live signals before relying on a match. Layout details are largely unverified — mark unknowns as 待核实.

## Live signals

- Workbuddy product/app context in the session (UI references, app name, or rules mentioning Workbuddy)
- macOS: presence of `~/Library/Application Support/com.workbuddy.workbuddy/`
- Session or thread identifiers mentioned in Workbuddy UI or export output — field names 待核实

## Known locations

- **App support root:** `~/Library/Application Support/com.workbuddy.workbuddy/` — verified 2026-08-15: contains only `Documents/`; no session/thread/conversation files here
- **Verified 2026-08-15, root `~/.workbuddy/`:**
  - `~/.workbuddy/sessions/<pid>.json` — live process heartbeats only (pid, sessionId like `interactive-2001`, cwd, startedAt); NOT transcripts
  - `~/.workbuddy/workspace/sessions/<uuid>/` — one dir per workspace session, exists but observed empty for an active session; do not expect transcript files
  - `~/.workbuddy/workbuddy.db` (+wal/shm) — SQLite; automations/tasks etc.; **do not guess conversation table schemas** — conversation history appears server-side (use the host's conversation search API if exposed), not reliably in local files
- **Practical fallback (verified):** for the *current* session, the running agent has the conversation itself in context — use in-conversation timestamps as the evidence source and mark per-turn end times as estimated; for *past* sessions, prefer the host's conversation-search tool over local file probing
- **Never invent SQLite schemas** — if a DB is found, prefer official export/API or ask the user for a known-good export path rather than guessing table/column names

## ID vs name

- **ID:** 待核实 field names; try filename stems and any obvious `id`/`title` JSON keys when readable files are found
- **Name:** 待核实 — match title/summary keys if present in JSON/JSONL; else fuzzy over filename stems or first user message snippet
- Do not assume Workbuddy persists a separate human title outside session file content

## Probe order

1. Confirm Workbuddy is the current host (app support dir exists or product cues in context)
2. List likely session containers under app support (`sessions`, `threads`, `conversations`, or similar — names 待核实)
3. ID then name match within discovered containers
4. On miss: ask user for export/path; keep skill usable via pasted content

## Failure / staleness notes

- **Low confidence** until layout is verified on a real install — directory structure and file formats may differ from expectations
- macOS-only app support path is the primary known root; other platforms 待核实
- Do not invent transcript content or DB queries — if no session file resolves, report steps tried and manual confidence level before asking the user for a direct path or paste
