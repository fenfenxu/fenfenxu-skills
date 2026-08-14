# fenfenxu-skills

我的个人 [Agent Skills](https://agentskills.io/) 仓库。可被 Cursor、Codex、Claude Code 等通过 `npx skills` 安装。

[![skills.sh](https://skills.sh/b/fenfenxu/fenfenxu-skills)](https://skills.sh/fenfenxu/fenfenxu-skills)

## 安装

```bash
# 安装全部 skills
npx skills add fenfenxu/fenfenxu-skills

# 只安装某一个
npx skills add fenfenxu/fenfenxu-skills --skill agent-thread-visualizer

# 全局安装（跨项目可用）
npx skills add fenfenxu/fenfenxu-skills -g
```

本地开发时可直接用路径：

```bash
npx skills add /Users/liuxu/repo/local/fenfenxu-skills --list
```

## Skills

| Skill | 说明 |
|-------|------|
| [`agent-thread-visualizer`](skills/agent-thread-visualizer) | 收集、归一化并可视化一个或多个 AI agent thread，输出易读的执行地图 |

## 仓库结构

```text
skills/
└── <skill-name>/
    ├── SKILL.md          # 必需
    ├── agents/           # 可选：各 agent 的展示元数据
    ├── scripts/          # 可选
    └── references/       # 可选
```

源码放在 `skills/`。`.agents/` 等是本地安装目录，已 gitignore，不要提交。

## 新增 Skill

1. 在 `skills/<skill-name>/` 下创建 `SKILL.md`
2. frontmatter 写好 `name` 与带触发词的 `description`
3. 在本 README 的 Skills 表中登记一行
4. commit & push

## License

MIT
