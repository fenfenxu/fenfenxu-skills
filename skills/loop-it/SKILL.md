---
name: loop-it
description: >-
  Multica 长程任务闭环：新需求、init、跟进/收尾主任务（编号如 CAM-17）、或跑一轮巡检。
  强制绑定 workspace + Multica profile 后再拆 issue，避免多项目串仓。
license: MIT
metadata:
  author: fenfenxu
  category: workflow
disable-model-invocation: true
argument-hint: "<新需求 | init | 继续跟进 CAM-17 | 收尾 CAM-17>"
---

# Loop It：长程任务闭环

用 Multica 把一个大需求从计划做到合并代码并关掉。底层 CLI 一律遵循 `multica-cli` skill（`--output json`、评论用 `--content-file`、mention/status 有副作用）。本 skill 只负责编排。

| 词 | 含义 |
|----|------|
| 主任务 / 编号（如 `CAM-17`） | 这棵需求的根任务。Multica CLI 仍叫 `issue` |
| 子任务 | 拆出来的一件件可执行任务 |
| 巡检 / Loop Patrol | 全仓库唯一的定时 Autopilot，按 cron 扫进行中的主任务 |

## 本轮目标

$ARGUMENTS

若 `$ARGUMENTS` 为空：先问用户要启动的新需求或者要跟进的任务，还是对当前仓库跑 `init`。

缺关键信息时先问再动手：目标 workspace、指派 agent、是否允许写操作。

## Workspace 绑定（硬门禁）

多项目并行时**禁止**依赖「上次 `workspace switch` 的默认 profile」。每次开跑：

1. 无 `.loop-it/config.yaml` → **只跑 `init`**，禁止建/拆 issue。
2. 读并确认 `workspace`（slug）；与用户冲突则先改 config。
3. 确保 profile：`multica_profile`（默认=slug）存在且 `workspace switch` 到该 workspace；可把 `workspace_id` 写入 config。
4. 之后一律：`MC=(multica --profile "$multica_profile")`，**禁止裸跑** `multica issue …`。  
   建出的 identifier 前缀必须属于本 workspace；不对则停手纠错。

## 配置（先读事实，再跑程序）

项目根 `.loop-it/config.yaml` 只放实例事实。读 `workspace`、`workspace_id`、`multica_profile`、`project`、`base_branch`、`repo`、`executors`、`orchestrator`、`patrol.*`、`daily_digest.*`，不要写死。

- 没有 config → 先跑 `init`，不要猜。
- 自动合并：仅当 `patrol.auto_merge: true` 且 DoD + CI 全绿。`gh pr merge` 的 `--repo` 取 `repo` 字段。

## 入口分流（先判定，再开跑）

按用户给出的材料判断起点。**已有可用的设计/计划就直接用，禁止重做 Phase 1。** 任意入口都先过 Workspace 绑定。

| 输入情况 | 起点 |
|----------|------|
| `init` / 新项目接入 | `init` 程序 |
| 巡检者 / Autopilot 触发 /「执行一轮巡检」 | **巡检程序** |
| 已有设计文档 + 计划文档（路径、`@` 引用，或用户说「按已有 plan 执行」） | 跳过 Phase 1；现有计划即验收依据 → Phase 2（主任务已存在则巡检器会接手，不必再建 Autopilot） |
| 只有粗糙需求 / 口头目标，尚无书面设计或计划 | Phase 1 |
| 主任务已存在（如 `继续跟进 MUL-xxx`） | 读 metadata / 计划路径 → 巡检程序（只处理这一棵树） |
| `收尾 MUL-xxx` | Phase 5 |

已有计划：写入主任务 `plan_path`，确认计划/方案已 commit + push。可轻量核对「子任务是否覆盖计划」，不要重写计划。

**禁止**为单个任务创建 Autopilot。全 workspace 只允许一个通用巡检 autopilot（由 `init` 创建）。发现 per-task autopilot 视为事故：删除并复盘。

## 开始前

1. `multica auth status` 已登录；否则停下来让用户 `multica login`。
2. 读 `.loop-it/config.yaml`；缺失则转 `init`。
3. 做 **Workspace 绑定**；之后只用 `"${MC[@]}"`。
4. `"${MC[@]}" agent list --output json` 确认 executors / orchestrator 仍在**该** workspace。
5. 写操作首次执行前向用户说明口径；已授权的例行跟进 / 巡检除外。

## init — 新项目接入（幂等）

在**当前仓库根**执行。已存在的只修补差异。输出差异报告（新建 / 一致 / 已修复）。

1. **确认 workspace**：`workspace list` 后与用户选定 slug（**禁止**用「当前 CLI 默认」代替确认）。解析 `workspace_id`；`multica_profile` 默认=slug。
2. **对齐 profile**：无则 `multica --profile <p> login`；再 `workspace switch <slug|id>`；校验 `workspace get` 匹配。
3. **生成/补齐** `.loop-it/config.yaml`（含 `workspace` / `workspace_id` / `multica_profile`）。向用户确认 `base_branch`、`repo`、executors、orchestrator；巡检默认 `*/15`、`auto_merge: true`：

   ```yaml
   workspace: <slug>
   workspace_id: <uuid>
   multica_profile: <通常=slug>
   project: null
   base_branch: <baseline branch>
   repo: <owner/name>
   executors: [<agent>, ...]
   orchestrator: <agent>
   patrol:
     cron: "*/15 * * * *"
     auto_merge: true
   daily_digest:
     enabled: true
     issue_key: <日报主任务编号>
   ```

4. **注入** `AGENTS.md`「Agent 工作流不变量」（指针 / 静默优先 / 唯一决策点 / 状态语义 / 一个巡检器；加一句：Multica 必须用本仓库 `multica_profile`）。已有则只校对指针 `~/.agents/skills/loop-it/`。
5. **建/修唯一巡检 Autopilot**（在已绑定 workspace 下）：title `Loop Patrol`；agent=`orchestrator`；mode=`run_only`；description 只写指针：

   ```text
   你是工作流巡检者。读 .loop-it/config.yaml，按 ~/.agents/skills/loop-it/SKILL.md「巡检程序」执行一轮。先 Workspace 绑定（--profile），再巡检。静默优先；不改 .env*；反复失败写 blocked_reason 并升级。
   ```

   schedule=`patrol.cron`，时区 `Asia/Shanghai`；已有同名则 update，不新建第二个。
6. 建议删除标题含 `Loop It 跟进` 的 per-task autopilot（须确认）。三件套齐全即开工。

## Phase 1 — 制定计划（Plan）

仅在尚无可用计划时执行。

1. 计划写入 `docs/superpowers/plans/`（或等价目录）：目标、验收、边界、拆解。
2. 用户确认后再进 Phase 2。
3. **派发前必须 commit + push** 计划/设计文档（agent 拉远端；不 push 则 `plan_path` 对他是 404）。

## Phase 2 — 创建任务树

**一律 `"${MC[@]}"`。**

1. 建主任务；`--description-file` 含计划路径与验收标准。
2. 拆子任务：`--parent`；标题前缀 `[<主identifier>] …`；`--stage`；后续 stage 先 `backlog`。executor 取 config。
3. 核对 identifier 前缀属于本 workspace；不对则停手清理。
4. metadata：`plan_path`、`loop_it_phase=executing`（不要写 `autopilot_id`）。

## 巡检程序

由唯一巡检 Autopilot 或用户「巡检 / 继续跟进」触发。**静默优先：无动作则无产出。**

护栏：不改 `.env*`；反复失败写 `blocked_reason` 并升级。

0. 读 config → **Workspace 绑定** → 后续只用 `"${MC[@]}"`。无工作树则从 `repo` checkout 基线分支。
1. **日报（每天首轮）**：若开启且今日未写，汇总红灯/待拍板/卡住到 `daily_digest.issue_key`。
2. **sweep**：己方历史 `Loop It`/`Loop Patrol` 运行任务置 `done`。
3. **活跃主任务**（`loop_it_phase=executing` 或用户点名）：读 children + 近评；**(a)** blocked 能解就解否则升级；**(b)** 标完成未验证则对照计划打回或放行下一 stage；**(c)** 验收通过则核 PR 编号，`patrol.auto_merge` 且 DoD 过则 `gh pr merge`（不强推），子任务 `done` 并解锁下一 stage。代码只经 PR 进基线。有动作才在主任务留短评。
4. 子任务全 `done`/`cancelled` → Phase 5。本轮运行任务必须收成 `done` 或 `blocked`，禁止留在 review/todo/in_progress。
5. 发现 per-task Loop It Autopilot：记录事故，删前须确认。

## Phase 5 — 收尾

子任务全 `done`/`cancelled` 后：总验收 → 主任务 `done`、`loop_it_phase=completed` → **不**停巡检 Autopilot → 汇报产出与 PR、遗留。
