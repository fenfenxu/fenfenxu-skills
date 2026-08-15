# Claude Code

- last_verified: 2026-08
- confidence: medium

Host manual for locating agent conversation threads stored by Claude Code (CLI and project context). Treat paths as heuristics; verify against live signals before relying on a match.

## Live signals

- Claude Code CLI / project context visible in the session (commands, tool output, or rules referencing Claude Code)
- Paths under `~/.claude/` mentioned in environment or prior commands
- Active workspace path — used to map to the encoded project directory under `~/.claude/projects/`
- Session UUID or history references in Claude Code UI/CLI output

## Known locations

- **Project data:** `~/.claude/projects/<encoded-path>/`
  - `<encoded-path>` is derived from the workspace path; encoding rules may change — 待核实 if mapping fails
- **Session/history artifacts:** 待核实 exact filename patterns per version — probe for jsonl/json session files under the project dir
- **Do not treat skill caches as sessions** — skill/plugin cache trees under `~/.claude/` are supporting data, not conversation threads

## ID vs name

- **ID:** session UUID if present in filenames or metadata (match full UUID or distinctive suffix)
- **Name:** Claude Code persists sidebar titles as jsonl events `type=ai-title` with field `aiTitle` (may appear multiple times; use the latest). Coverage is partial — older/short sessions may lack `ai-title`; then fall back to first user turn / `last-prompt`.
- Display titles in Claude Code UI are not guaranteed in filenames; do not assume filename equals display name

## Probe order

1. Map current workspace path to `~/.claude/projects/<encoded-path>/`
2. ID match within that project dir (glob for UUID stems in session filenames)
3. Name/fuzzy within that project dir — scan metadata or first user message for contains-match
4. Broader `~/.claude/projects/` only if user asks or local project dir missing
5. On miss: report steps tried + manual confidence; ask for path/export

## Failure / staleness notes

- Path encoding for project dirs changes across Claude Code versions; prefer live workspace mapping over hard-coded slug guesses
- Active sessions may still be writing; partial files or missing final records are possible
- Do not invent transcript content — if no session file resolves, say so and ask the user to paste or point to the file
- Cross-project UUID collisions are unlikely but multiple workspaces each have their own project tree; always note which path was chosen and why
