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
