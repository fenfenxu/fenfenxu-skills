# Host detection and session lookup

## Lookup order (anti-staleness)

1. Prefer this skill’s bundled locators — **you choose** which one:
   - `python3 scripts/find-thread-by-id <uuid>` when the user gave a session id
   - `python3 scripts/find-thread-by-name [keywords]` for titles / topic words / recent
   Do not install scripts onto the user’s PATH. Do not use a single auto-detect script.
2. Live signals in the current environment (API / transcript paths / agent metadata)
3. Matching `references/host-<name>.md` probe order (`last_verified` / `confidence`)
4. Generic heuristics below
5. Ask the user for a path or pasted export

Manuals are heuristics. On miss, prefer “manual may be stale” over inventing a match. Note briefly when a host-manual lookup missed.

## Detect current host

Use runtime cues (not user guesswork):

| Host | Typical cues |
|------|----------------|
| Cursor | `CURSOR_*` env, `~/.cursor/`, agent transcripts under project dirs, Cursor UI/tooling in context |
| Codex | `~/.codex/`, Codex CLI/app context, `rollout-*.jsonl` |
| Claude Code | `~/.claude/`, Claude Code CLI/project context |
| Workbuddy | `~/.workbuddy/projects/**/*.jsonl`, `~/.workbuddy/`, Workbuddy product cues (app support alone is not transcripts) |
| kimi-code | `~/.kimi-code/`, legacy `~/.kimi/` migration markers, kimi-code CLI/product cues |
| other | Anything else → generic fallback only |

Default: search **only** the current host. Cross-host only if the user explicitly names another tool.

## Resolve ID vs name

- **Model decides** which script to run; scripts do not guess UUID vs name.
- Session UUID / fragment → `find-thread-by-id` only (path/filename match)
- Title / topic / first-user keywords / “recent” → `find-thread-by-name` (UI title first, then first-user prompt):
  - Cursor: `conversation-search.db` `conversations.title` (Agents sidebar); legacy `composer.composerHeaders`
  - Codex: `state_*.sqlite` `threads.title` / `session_index.thread_name`
  - Workbuddy: `workbuddy.db` `sessions.title`/`custom_title` (UI has no ID — name is primary)
  - Claude: jsonl `type=ai-title` → `aiTitle`
  - kimi: per-session `state.json` → `title`
- Unsure → try the more likely one; on zero hits, try the other
- Multiple hits → short chooser (title, time, path/ID); never silent pick
- Zero hits after both → report steps tried + manual confidence; ask for path/keywords/paste

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
