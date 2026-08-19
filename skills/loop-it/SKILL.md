---
name: loop-it
description: >-
  Use when the user runs /loop-it, inits Multica long-running work in this
  repo, continues or closes a Multica parent task (编号如 CAM-17), or runs
  one 巡检 / Loop Patrol round.
  Triggers (EN): loop-it, loop it, long-running task loop, Multica issue,
  Multica Autopilot, Loop Patrol, follow parent task, auto-merge PR.
  (ZH): 长程任务闭环, 任务闭环, 巡检, Multica 巡检, 主任务, 子任务,
  继续跟进, 收尾, 自动合并 PR.
license: MIT
metadata:
  author: fenfenxu
  category: workflow
disable-model-invocation: true
argument-hint: "<新需求 | init | 继续跟进 CAM-17 | 收尾 CAM-17>"
---

# Loop It：长程任务闭环

用 Multica 把一个大需求从计划做到合并代码并关掉。

怎么喊：

- `/loop-it 做某某功能` — 新需求，还没有主任务
- `/loop-it init` — 给当前仓库接上巡检
- `/loop-it 继续跟进 CAM-17` — 只盯这一棵已有主任务
- `/loop-it 收尾 CAM-17` — 子任务都完成后关掉这棵

几个词（正文后头还是这些意思）：

| 词 | 人话 |
|----|------|
| 主任务 / 编号（如 `CAM-17`） | 这棵需求的根任务。Multica CLI 仍叫 `issue` |
| 子任务 | 拆出来的一件件可执行任务 |
| 巡检 / Loop Patrol | 全仓库唯一的定时 Autopilot，按 cron 扫进行中的主任务 |
| Autopilot | Multica 的定时任务；本 skill 全仓库只允许这一个巡检实例 |

把大需求跑成「计划 → 主任务 + 子任务 → 唯一巡检 Autopilot → 提交 MR 并关闭 → 收尾」。

程序源码在 `fenfenxu/fenfenxu-skills` 的 `skills/loop-it/`。安装后运行时读 `~/.agents/skills/loop-it/`。项目里只放事实：`.loop-it/config.yaml`。禁止把本程序全文复制进 autopilot description、任务、或其他 skill。

底层 CLI 一律遵循 `multica-cli` skill（`--output json`、评论用 `--content-file`、mention/status 有副作用）。本 skill 只负责编排。

## 本轮目标

$ARGUMENTS

若 `$ARGUMENTS` 为空：先问用户要启动的新需求、要跟进的主任务编号（如 `CAM-17`）、收尾，还是对当前仓库跑 `init`。

缺关键信息时先问再动手：目标 workspace、指派 agent、是否允许写操作。

## 配置（先读事实，再跑程序）

项目根 `.loop-it/config.yaml` 只放实例事实，不放程序。典型字段：

```yaml
workspace: <multica workspace slug>
project: null
base_branch: <baseline branch>
repo: <owner/name>
executors: [<agent>, ...]
orchestrator: <agent>
patrol:                    # 巡检（Loop Patrol）的节奏与是否自动合 PR
  cron: "*/15 * * * *"
  auto_merge: true
daily_digest:
  enabled: true
  issue_key: <日报主任务编号>
```

- 仓库 / 基线分支 / merge repo / 执行者 / 巡检 cron：**一律读 config**，不要写死。
- 没有 config → 先跑 `init`，不要猜。
- 自动合并：仅当 `patrol.auto_merge: true` 且 DoD + CI 全绿。`gh pr merge` 的 `--repo` 取 `repo` 字段。

## 入口分流（先判定，再开跑）

按用户给出的材料判断起点。**已有可用的设计/计划就直接用，禁止重做 Phase 1。**

| 输入情况 | 起点 |
|----------|------|
| `init` / 新项目接入 | `init` 程序 |
| 巡检者 / Autopilot 触发 /「执行一轮巡检」 | **巡检程序** |
| 已有设计文档 + 计划文档（路径、`@` 引用，或用户说「按已有 plan 执行」） | 跳过 Phase 1；现有计划即验收依据 → Phase 2（主任务已存在则巡检器会接手，不必再建 Autopilot） |
| 只有粗糙需求 / 口头目标，尚无书面设计或计划 | Phase 1 |
| 主任务已存在（如 `继续跟进 MUL-xxx`） | 读 metadata / 计划路径 → 巡检程序（只处理这一棵树） |
| `收尾 MUL-xxx` | Phase 5 |

已有计划时：确认计划路径写入主任务 `plan_path` metadata；可轻量核对「子任务是否覆盖计划」，但不要重写计划、不要再走一轮「先确认计划」。**同样先确认计划/方案改动已 commit + push 到远端**，否则 agent 拉代码时拿不到。

**禁止**为单个任务创建 Autopilot。全 workspace 只允许一个通用巡检 autopilot（由 `init` 创建）。发现 per-task autopilot 视为事故：删除并复盘。

## 开始前

1. `multica auth status` 已登录；否则停下来让用户 `multica login`。
2. 读 `.loop-it/config.yaml`；缺失则转 `init`。
3. `multica agent list --output json` 确认 config 里的 executors / orchestrator 仍存在。
4. 写操作（建任务、改状态、发评论、mention）首次执行前向用户说明口径；用户已明确授权的例行跟进 / 巡检除外。

## init — 新项目接入（幂等）

在**当前仓库根**执行。已存在的文件和实例只修补差异，不覆盖用户改过的事实。输出一份差异报告（新建 / 已存在且一致 / 已修复）。

1. **生成** `.loop-it/config.yaml`（若不存在）。向用户确认 workspace、`base_branch`、`repo`、executors、orchestrator；巡检默认 `*/15`、`auto_merge: true`。
2. **注入** 项目 `AGENTS.md` 的「Agent 工作流不变量」小节（指针原则 / 静默优先 / 唯一决策点 / 状态语义 / 一个系统一个巡检器）。已有则只校对指针仍指向 `~/.agents/skills/loop-it/`，不复制本 skill 正文。
3. **建/修唯一巡检 Autopilot**：
   - title：`Loop Patrol`
   - agent：config 的 `orchestrator`
   - mode：`run_only`（空转不建任务）
   - `--description` **只写指针**，不要贴本文件：

     ```text
     你是工作流巡检者。读项目根 .loop-it/config.yaml，按 ~/.agents/skills/loop-it/SKILL.md 的「巡检程序」执行一轮。静默优先：本轮无动作则无产出。护栏：禁止 push 基线分支；不改生产配置/.env*；反复失败则写 blocked_reason 并升级。
     ```

   - schedule：config `patrol.cron`，时区 `Asia/Shanghai`
   - 已有同名巡检则 `update` 对齐 description / cron / agent，不新建第二个。
4. 列出并建议删除标题含 `Loop It 跟进` 的 per-task autopilot（须用户确认再删）。
5. 三件套齐全（config + AGENTS 小节 + 巡检实例）即开工。

## Phase 1 — 制定计划（Plan）

仅在入口分流判定「尚无可用计划」时执行。

1. 把需求写成计划文档，存 `docs/superpowers/plans/`（或该仓库等价的 plans 目录），含：目标、验收标准、范围边界、拆解思路。
2. 计划先给用户确认，再进入 Phase 2。计划是后续所有任务的验收依据。
3. **派发任务前必须 commit + push 计划文档**（以及本轮产生/修改的任何技术方案、设计文档）。Multica agent 执行时是拉远端代码的——不 push，agent 拿到的代码里没有这些改动，`plan_path` 指向的文件对它来说就是 404。

## Phase 2 — 创建任务树

1. 建主任务：标题即需求名，`--description-file` 指向计划摘要（含计划文档路径、验收标准）。
2. 拆子任务：每个子任务 `--parent <主id>`；**标题必须以主任务的 identifier 为前缀**（`[<主identifier>] <子任务名>`，例如 `[MUL-123] API：live.mjpg`），系统编号仍是流水号，靠标题认亲。有先后顺序的用 `--stage N`，后续阶段先 `--status backlog`：

```bash
multica issue create --title "[MUL-123] ..." --parent <主id> --assignee <executor> --stage 1 --status todo
multica issue create --title "[MUL-123] ..." --parent <主id> --assignee <executor> --stage 2 --status backlog
```

executor 取 config `executors`（用户指定则覆盖）。

3. 在主任务 metadata 记录闭环状态。**不要**写 `autopilot_id`（不再为任务建 Autopilot）：

```bash
multica issue metadata set <主id> --key plan_path --value docs/superpowers/plans/xxx.md
multica issue metadata set <主id> --key loop_it_phase --value executing
```

之后由唯一巡检器发现这棵树。零额外配置。

## 巡检程序

由唯一巡检 Autopilot 按 cron 触发，或用户说「巡检 / 继续跟进」。**静默优先：本轮无动作则无产出。** 不要为「看过了」建任务、不要在全绿时刷评论。

护栏：禁止 push `base_branch`；不改生产配置 / `.env*`；反复失败则写 `blocked_reason` 并升级。

0. **定位仓库**：读项目根 `.loop-it/config.yaml`。工作树没有则从 `repo` checkout 到含 config 的基线分支，不要在空 workdir 里编造。
1. **日报（每天首轮）**：若 `daily_digest.enabled` 且今天尚未写过，把红灯 / 待拍板 / 卡住的主任务汇总到 `daily_digest.issue_key`。全绿可只留一行或跳过。
2. **开场 sweep**：运行任务是日志不是交付物。`multica issue list --status in_review --output json`（必要时再查 `todo` / `in_progress`）中标题含 `Loop It` / `Loop Patrol`、assignee 为自己的**历史**运行任务（本轮新建的除外）一律置 `done`。
3. **找出活跃主任务**：`loop_it_phase=executing`（或用户点名的那一棵）。对每一棵：
   1. `multica issue children <主id> --output json`，再对活跃子任务读 `issue comment list --recent 10`。
   2. 分支处理：
      - **(a) blocked / 报错**：能解就解；需决策则在对应任务评论给方案并 @ agent（谨慎，mention 会触发运行）；解不了升级给用户，主任务 `blocked` + `blocked_reason`。
      - **(b) 标完成但未验证**：对照计划验收标准审 diff / 跑测试。不合格：评论打回 `in_progress`；合格：下一 stage 从 `backlog` → `todo`。
      - **(c) 验收通过且有代码**：确认 PR 标题/正文含任务编号（如 `MUL-123`、`Closes MUL-123`），`multica issue pull-requests <子id>` 核对。若 `patrol.auto_merge: true` 且 DoD 核验通过：`gh pr merge <编号> --repo <config.repo> --merge`；合并冲突/失败不强推，评论升级。合并成功后子任务置 `done`，metadata 写 `pr_number`/`pr_url`，再解锁下一 stage。禁止直接 git push 基线分支，代码只能经 PR 合并进入。
   3. 有动作才在主任务留简短跟进评论（`--content-file`），更新 `loop_it_phase`。全绿不评论。
   4. 子任务全部 `done`/`cancelled` → 转 Phase 5（可当轮做完）。
4. **本轮收尾（必须）**：
   - 本轮正常跟完（含「无需动作」）→ 本运行任务置 `done`（若 mode 建了运行任务）；
   - 需要用户决策 / 升级 → 置 `blocked` 并在主任务评论说明卡点；
   - **禁止**留在 `in_review` / `todo` / `in_progress`——运行记录不走人工 review。
5. 发现 per-task Loop It Autopilot：当作事故记录，删除须用户确认（巡检默默列出即可，不要静默狂删）。

## Phase 5 — 收尾

当 `issue children` 全部为 `done`/`cancelled`：

1. 对照计划验收标准做总验收。
2. 主任务置 `done`；`loop_it_phase` → `completed`。
3. **不要**暂停唯一巡检 Autopilot——它还要看别的树。只把这棵树标 completed。
4. 向用户汇报：产出清单、PR 列表、遗留事项。
