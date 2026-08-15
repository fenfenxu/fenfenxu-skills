# Codex

- last_verified: 2026-08
- confidence: medium

Host manual for locating agent conversation threads stored by OpenAI Codex (CLI and desktop app). Treat paths as heuristics; verify against live signals before relying on a match.

## Live signals

- Codex CLI/app session APIs if present in context (session IDs, rollout references in tool output)
- Paths under `~/.codex/` visible in environment or prior commands
- Active rollout filename or UUID mentioned in the current conversation or terminal history
- macOS: presence of Codex app data directories (secondary signal only)

## Known locations

- **Active/archived rollouts:** `~/.codex/sessions/`
  - Files often named `rollout-*.jsonl` with UUID segments embedded (e.g. `rollout-<timestamp>-<uuid>.jsonl`) — exact pattern 待核实 per installed version
- **Archived sessions:** `~/.codex/archived_sessions/` if present (older or completed rollouts moved here)
- **macOS app support (secondary):** may include `~/Library/Application Support/Codex` or paths under `com.openai.codex` — treat as secondary; mark layout details 待核实 if directory structure differs from CLI layout
- Rollout files are JSONL event streams; metadata fields for display title are version-dependent — inspect first records before assuming a stable title key

## ID vs name

- **ID:** UUID segments inside `rollout-...-<uuid>.jsonl` filenames (match full UUID or distinctive suffix)
- **Name:** 待核实 — search rollout metadata / first user message if file format allows; Codex may not persist a separate human title outside the jsonl content
- Do not conflate rollout filename timestamps with session display names

## Probe order

1. Exact filename / UUID match under `~/.codex/sessions/` (glob `rollout-*<uuid>*.jsonl` or exact basename if user provided path fragment)
2. `~/.codex/archived_sessions/` if needed (same glob patterns)
3. Fuzzy name over readable metadata — scan jsonl headers or first user-role message for contains-match on the given name
4. On miss: ask for rollout path, paste export, or session UUID from Codex UI/CLI

## Failure / staleness notes

- Rollout filename scheme may change across Codex versions; do not hard-code a single prefix/suffix pattern as immutable truth
- CLI vs desktop app may use overlapping but not identical storage roots — if `~/.codex/sessions/` is empty, note app-support paths as 待核实 secondary probe only
- Active sessions may still be writing; partial files or missing final records are possible
- Do not invent transcript content — if no rollout file resolves, report steps tried and manual confidence level before asking the user for a direct path
