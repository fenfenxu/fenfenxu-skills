---
name: skill-discovery-optimizer
description: >-
  Optimizes Agent Skill discoverability (skills SEO / GEO) for find-skills and
  skills.sh: generate multilingual search test cases, run dual evals (API +
  npx skills find), rewrite description/README keywords from misses, version
  each iteration, publish (commit/push + install telemetry), re-validate, and
  loop until hit-rate/rank goals are met. Use when the user wants skill SEO,
  GEO, find-skills ranking, skills.sh discoverability, search keyword coverage
  (zh/en/ja), discovery regression tests, or a publish-and-verify loop for a
  skill — also when they say skill-discovery-optimizer, 会话可视化检索,
  スキル発見, or "make this skill findable".
license: MIT
metadata:
  author: fenfenxu
  category: observability
---

# Skill Discovery Optimizer

把目标 skill 做成 **find-skills / skills.sh 更容易搜到** 的闭环：造用例 → 双通道测 → 按 miss 优化 → 记版本 → 发布 → 再测 → 迭代直到达标。

## Quick start

1. 确认目标 skill 路径（含 `SKILL.md`）与 GitHub `owner/repo`。
2. 生成或加载用例：`discovery/queries.json`（模板见 [assets/queries.template.json](assets/queries.template.json)）。
3. 跑基线：

```bash
python3 scripts/run_discovery_eval.py \
  --queries <skill-or-repo>/discovery/queries.json \
  --modes api,cli \
  --out <skill-or-repo>/discovery/iterations/v0-baseline.json
```

4. 按本 skill 的 Loop 改 description / README，记 `vN`，发布后再跑同一套用例对比。

默认 **API + CLI 都要测**（原理同属 `skills.sh/api/search`，但 CLI=`npx skills find` 才是 find-skills 真实路径，且 `limit=10` + installs 排序会影响首屏）。

## Goals (define before looping)

与用户对齐可测目标，缺省建议：

| Metric | Default goal |
|--------|----------------|
| Primary queries hit@10 (CLI) | ≥ 80% of P0 queries |
| Exact skill id / English name | hit@10 on CLI |
| Multilingual P0 (zh/ja if in scope) | hit@10 on CLI **or** documented `--owner` fallback |
| No description regression | `description` ≤ 1024 chars; still triggers for installed agents |
| Stop condition | 连续 2 轮主要指标无提升，或用户宣布 done |

P0 = 用户明确点名的检索词 + 技能名短语；P1 = 同义词/宿主名；P2 = 口语。

## Workflow checklist

```
Discovery loop:
- [ ] 0. Scope target skill + owner/repo + languages
- [ ] 1. Generate queries.json (zh/en/ja as needed)
- [ ] 2. Baseline eval (api + cli); save v0
- [ ] 3. Analyze misses / competitors / install gap
- [ ] 4. Optimize description + surface copy
- [ ] 5. Record iteration notes + metrics delta
- [ ] 6. Publish (commit/push + telemetry install)
- [ ] 7. Re-eval same queries; compare to previous
- [ ] 8. Loop 3–7 until goals or stop condition
- [ ] 9. Final report + remaining risks (install rank)
```

### 0. Scope

- Target: `skills/<name>/SKILL.md`（或用户指定路径）。
- Publish identity: `owner/repo`（skills.sh 页与 `npx skills add`）。
- Languages: 至少覆盖用户会搜的语言；中文产品默认 **zh+en**，有日文受众再加 **ja**。
- 读 [references/description-geo.md](references/description-geo.md) 再改文案。

### 1. Generate test cases

按意图矩阵生成，不要只堆同义词。每语建议覆盖：

- 核心能力短语（用户原话优先，如 `agent 会话可视化`）
- 短词 / 同义（会话报告、执行地图、session timeline）
- 宿主名（Cursor / Claude Code / Workbuddy / kimi-code…）
- 口语（看看 agent 做了什么 / visualize the run）
- 精确 id（`skill-name`）

写入目标 skill 旁：

```text
skills/<name>/discovery/
├── queries.json
└── iterations/
    ├── v0-baseline.json
    ├── v1-....json
    └── CHANGELOG.md
```

schema 见 [assets/queries.template.json](assets/queries.template.json)。也可从本仓库 `docs/find-skills-geo-queries.json` 复制再改 `target`。

### 2. Run evals (dual channel)

**必须分别跑：**

| Mode | Command / endpoint | 代表 |
|------|-------------------|------|
| `api` | `GET https://skills.sh/api/search?q=&limit=` | 索引本体、可看更深排名 |
| `cli` | `npx skills find "<q>"` | find-skills 真实路径（默认约 top 10） |
| `cli-owner` | `npx skills find "<q>" --owner <owner>` | 低安装量时的可靠命中 |

脚本：

```bash
python3 scripts/run_discovery_eval.py \
  --queries skills/<name>/discovery/queries.json \
  --modes api,cli,cli-owner \
  --owner <owner> \
  --out skills/<name>/discovery/iterations/vN-<label>.json
```

判定：结果 id/slug 同时包含 `owner` 与 skill `name`（或 queries 里配置的 `pass` 规则）。

注意：429 时退避重试；全量矩阵加间隔，避免打爆 API。

评分细则：[references/scoring.md](references/scoring.md)。

### 3. Analyze

对每条 miss 记录：

1. 通道（api / cli）与 rank（若有）
2. Top1–3 竞品（谁吃了语义）
3. 是否缺关键词 / 是否纯 installs 碾压
4. 优化杠杆：description 词、README、skill 名、安装遥测、`--owner` 文档

低 installs（个位数）时：**全局 top10 很难靠文案 alone 赢高安装量竞品**——仍要优化文案召回，同时发布遥测 + README 写明 `--owner`。

### 4. Optimize

优先改 **`SKILL.md` frontmatter `description`**（≤1024，WHAT+WHEN+多语触发词）。其次：正文首段（skills.sh 抓取）、`agents/openai.yaml`、`README` Find-with 列。

规则与反模式：[references/description-geo.md](references/description-geo.md)。

改完本地立刻量 description 长度；超限先砍 P2 口语再砍宿主枚举。

### 5. Record version

每次优化后写一轮：

`skills/<name>/discovery/iterations/CHANGELOG.md` 追加：

```markdown
## vN — YYYY-MM-DD
- Hypothesis: ...
- Changes: (files + keyword adds/removes)
- Metrics: cli P0 hit@10 A→B; api hits ...; description chars ...
- Publish: commit <sha> / install telemetry yes|no
- Decision: continue | stop
```

并把当轮 `run_discovery_eval.py` 输出 JSON 存为 `vN-<label>.json`。

### 6. Publish

仅在用户要求 commit/push 时执行。步骤：[references/publish.md](references/publish.md)。

最小遥测刷新：

```bash
npx skills add <owner>/<repo> --skill <skill-name> -g -y
```

skills.sh **不靠 GitHub crawl 实时同步**。`npx skills add` 往往会刷新 **installs**，但 **listing 上的 description / SKILL.md 正文何时 reindex 未知**（见 [references/publish.md](references/publish.md)「Known unknown」）。发布后必须打开 `https://www.skills.sh/<owner>/<repo>/<skill>` 核对文案，不能只看安装数。

若仍显示旧正文（`index lag`）：

- **暂停** description SEO 迭代（无法验证假设）
- CHANGELOG 记 installs 变化 + 页面仍旧 + `blocked: content reindex unknown`
- 达标暂以 `cli-owner` + GitHub 源文案 + `--owner` 文档为准
- 只能等页面追上后再复测；期间不要继续堆词

### 7–8. Re-validate & loop

- 同一 `queries.json` 复跑；对比 vN vs vN-1。
- 有提升 → 记 changelog → 若未达标继续 3–6。
- 无提升 → 换假设（别只堆词）：竞品差异化短语、缩短 description、加安装、接受 `--owner` 为 P0 达标定义。
- 连续两轮无提升、达目标、或 **listing 内容长期 stale（reindex 未知）** → 出最终报告并停止 / 暂停。

### 9. Final report

向用户交付：

1. 目标与是否达成  
2. 迭代表（版本、假设、cli/api 命中率）  
3. 仍 miss 的 P0 及原因（安装量 / 语义冲突）  
4. 安装与查找命令（含 `--owner`）  
5. `discovery/` 路径，便于下次回归  

## Scripts

| Script | Role |
|--------|------|
| [scripts/run_discovery_eval.py](scripts/run_discovery_eval.py) | 双通道评测，写 JSON 报告 |
| [scripts/init_discovery.py](scripts/init_discovery.py) | 在目标 skill 下初始化 `discovery/` |

脚本相对本 skill 根目录调用；若从别的 cwd 跑，传入本 skill 内脚本的绝对路径。

## Anti-patterns

- 只测 API、不测 `npx skills find`（find-skills 验收不合格）
- 为 SEO 把 description 堆到 >1024 或毁掉 agent 触发语义
- 未发布、或页面正文仍旧（只涨了 installs）就宣称 “skills.sh 已更新”
- 在 `index lag` / content reindex 未知时继续堆 description 并解读 search miss
- 用安装量碾压的竞品排名苛责零安装新 skill，却不记遥测/owner 策略
- 每轮改 queries 导致无法对比（queries 冻结；新词开 vNext 文件）
