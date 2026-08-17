# fenfenxu-skills

Personal [Agent Skills](https://agentskills.io/) for Cursor, Codex, Claude Code, Workbuddy, kimi-code, and other `npx skills` hosts.

[![skills.sh](https://skills.sh/b/fenfenxu/fenfenxu-skills)](https://skills.sh/fenfenxu/fenfenxu-skills)

## Install

```bash
# Install all skills
npx skills add fenfenxu/fenfenxu-skills

# Install one skill
npx skills add fenfenxu/fenfenxu-skills --skill agent-thread-visualizer
npx skills add fenfenxu/fenfenxu-skills --skill loop-it

# Global install
npx skills add fenfenxu/fenfenxu-skills -g
```

Browse on skills.sh: [agent-thread-visualizer](https://skills.sh/fenfenxu/fenfenxu-skills/agent-thread-visualizer) · [loop-it](https://skills.sh/fenfenxu/fenfenxu-skills/loop-it)

Find via CLI (skills.sh ranks by install count; use `--owner` for a reliable hit while installs are low):

```bash
# English
npx skills find "agent thread visualizer" --owner fenfenxu
# Chinese
npx skills find "agent 会话可视化" --owner fenfenxu
# Japanese
npx skills find "セッション可視化" --owner fenfenxu

npx skills find agent-thread-visualizer --owner fenfenxu
```

Local path install:

```bash
npx skills add /Users/liuxu/repo/local/fenfenxu-skills --list
```

## Skills

| Skill | What it does | Find with |
|-------|----------------|-----------|
| [`agent-thread-visualizer`](skills/agent-thread-visualizer) | Host-aware session lookup (ID/name) for Cursor / Codex / Claude Code / Workbuddy / kimi-code; full collect of skills/tools/sub-agents; layered swimlane **execution map** / **agent session timeline** | EN: `agent thread visualizer`, `session timeline`, `session report`, `agent flow`, `execution map`; ZH: `agent 会话可视化`, `会话可视化`, `执行地图`, `会话报告`; JA: `セッション可視化`, `実行マップ`, `エージェント タイムライン` |
| [`skill-discovery-optimizer`](skills/skill-discovery-optimizer) | Skills SEO / GEO loop: generate multilingual find-skills tests, dual eval (API + `npx skills find`), optimize description, version, publish, re-validate | `skill SEO`, `skill GEO`, `find-skills`, `skills.sh discoverability`, `技能检索优化` |
| [`loop-it`](skills/loop-it) | Long-running Multica loop: plan → issue tree → one patrol Autopilot → MR closeout. Project facts stay in `.loop-it/config.yaml` | EN: `loop-it`, `Multica patrol`, `issue tree`, `epic follow-up`; ZH: `长程任务闭环`, `巡检程序`, `Issue 树` |

### agent-thread-visualizer

Turns opaque agent runs into readable execution maps:

- **Locate**: Cursor, Codex, Claude Code, Workbuddy, kimi-code sessions by ID or title
- **Collect**: stages, loaded skills, tool calls, sub-agents, retries, forks, waits, worktree context
- **Show**: primary/secondary layered swimlanes; expandable detail; optional session-health tips

Useful when you need a session report, session log walkthrough, agent flow visualization, or transcript inspection — not just a token/context dump.

### skill-discovery-optimizer

Skills SEO / GEO closed loop for find-skills:

1. Generate multilingual queries → 2. Dual eval (API + `npx skills find`) → 3. Optimize description → 4. Version → 5. Publish + telemetry → 6. Re-validate → loop

```bash
npx skills add fenfenxu/fenfenxu-skills --skill skill-discovery-optimizer
```

### loop-it

Turns an open-ended coding objective into a bounded Multica loop:

- **Plan** only when no design/plan exists
- **Issue tree** with staged children and `loop_it_phase=executing`
- **One patrol Autopilot** for the whole workspace (`run_only`, pointer-only description)
- **Closeout** after DoD + optional auto-merge from `.loop-it/config.yaml`

```bash
npx skills add fenfenxu/fenfenxu-skills --skill loop-it -g
```

Then in a project: `/loop-it init`.

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
