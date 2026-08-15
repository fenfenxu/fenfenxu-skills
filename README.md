# fenfenxu-skills

Personal [Agent Skills](https://agentskills.io/) for Cursor, Codex, Claude Code, Workbuddy, kimi-code, and other `npx skills` hosts.

[![skills.sh](https://skills.sh/b/fenfenxu/fenfenxu-skills)](https://skills.sh/fenfenxu/fenfenxu-skills)

## Install

```bash
# Install all skills
npx skills add fenfenxu/fenfenxu-skills

# Install one skill
npx skills add fenfenxu/fenfenxu-skills --skill agent-thread-visualizer

# Global install
npx skills add fenfenxu/fenfenxu-skills -g
```

Browse on skills.sh: [agent-thread-visualizer](https://skills.sh/fenfenxu/fenfenxu-skills/agent-thread-visualizer)

Find via CLI (skills.sh ranks by install count; use `--owner` for a reliable hit while installs are low):

```bash
npx skills find agent-thread-visualizer --owner fenfenxu
```

Local path install:

```bash
npx skills add /Users/liuxu/repo/local/fenfenxu-skills --list
```

## Skills

| Skill | What it does | Find with |
|-------|----------------|-----------|
| [`agent-thread-visualizer`](skills/agent-thread-visualizer) | Host-aware session lookup (ID/name) for Cursor / Codex / Claude Code / Workbuddy / kimi-code; full collect of skills/tools/sub-agents; layered swimlane **execution map** / **agent session timeline** | `agent thread visualizer`, `session timeline`, `session report`, `agent flow`, `execution map`, `subagent timeline`, `conversation visualizer`, `debug agent session`, `Workbuddy session`, `kimi-code session` |

### agent-thread-visualizer

Turns opaque agent runs into readable execution maps:

- **Locate**: Cursor, Codex, Claude Code, Workbuddy, kimi-code sessions by ID or title
- **Collect**: stages, loaded skills, tool calls, sub-agents, retries, forks, waits, worktree context
- **Show**: primary/secondary layered swimlanes; expandable detail; optional session-health tips

Useful when you need a session report, session log walkthrough, agent flow visualization, or transcript inspection — not just a token/context dump.

## Repo layout

```text
skills/
└── <skill-name>/
    ├── SKILL.md          # required
    ├── agents/           # optional host UI metadata
    ├── scripts/          # optional
    └── references/       # optional
```

Source lives under `skills/`. `.agents/` is a local install dir (gitignored).

## Add a skill

1. Create `skills/<skill-name>/SKILL.md`
2. Frontmatter: `name` + trigger-rich `description` (WHAT + WHEN + search synonyms)
3. Register a row in this README
4. Commit and push (skills.sh indexes after publish)

## License

MIT
