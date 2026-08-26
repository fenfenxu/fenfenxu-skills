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

用 Multica 把一个大需求从计划做到合并代码并关掉。本 skill 只负责编排。

| 词 | 含义 |
|----|------|
| 主任务 / 编号（如 `CAM-17`） | 这棵需求的根任务。Multica CLI 仍叫 `issue` |
| 子任务 | 拆出来的一件件可执行任务 |
| 巡检 / Loop Patrol | 全仓库唯一的定时 Autopilot，按 cron 扫进行中的主任务 |

**开跑前先读**项目根 `.loop-it/config.yaml`（workspace、repo、分支、agent 名单等）。没有就 `init`。

**Patrol 分工（B）**：定时 Autopilot 的程序全文写在 **Autopilot description**（`init` 写入）；Autopilot **不**读本 skill。本 skill 供本机 `/loop-it`（init / Phase / 跟进）使用。

## 执行上下文

| 你在哪 | Multica CLI | 程序从哪来 |
|--------|-------------|-----------|
| Multica Autopilot（run_only） | 裸 `multica` | **仅** Autopilot description；禁止找/读 loop-it |
| 本机 Cursor | `MC=(multica --profile "$multica_profile")`；CLI 遵循 `multica-cli` skill | 本 skill |

## 本轮目标

$ARGUMENTS

若 `$ARGUMENTS` 为空：先问用户要启动的新需求或者要跟进的任务，还是对当前仓库跑 `init`。

缺关键信息时先问再动手：目标 workspace、指派 agent、是否允许写操作。

## Workspace 绑定（硬门禁）

多项目并行时**禁止**依赖「上次 `workspace switch` 的默认 profile」。每次开跑：

1. 无 `.loop-it/config.yaml` → **只跑 `init`**，禁止建/拆 issue。（**例外**：Autopilot 已按 description 先 checkout；本机「巡检/跟进」按下方本机巡检步骤 0。）
2. 读并确认 `workspace`（slug）；与用户冲突则先改 config。
3. **本机上下文**：确保 `multica_profile`（默认=slug）存在且 `workspace switch` 到该 workspace；`MC=(multica --profile "$multica_profile")`，之后只用 `"${MC[@]}"`。
4. **Autopilot 上下文**：只跟 description；checkout 后读 `.loop-it/config.yaml` 校验事实；API 一律裸 `multica`。
5. 建出的 identifier 前缀必须属于本 workspace；不对则停手纠错。

## 配置（先读事实，再跑程序）

项目根 `.loop-it/config.yaml` 只放实例事实。读 `workspace`、`workspace_id`、`multica_profile`、`project`、`base_branch`、`repo`、`executors`、`orchestrator`、`patrol.*`、`daily_digest.*`，不要写死在 skill 正文。

- 没有 config → 先跑 `init`，不要猜（巡检入口除外，见上）。
- 自动合并：仅当 `patrol.auto_merge: true` 且 DoD + CI 全绿。`gh pr merge` 的 `--repo` 取 `repo` 字段。

## 入口分流（先判定，再开跑）

按用户给出的材料判断起点。**已有可用的设计/计划就直接用，禁止重做 Phase 1。** 任意入口都先过 Workspace 绑定（巡检则先 checkout 再绑定）。

| 输入情况 | 起点 |
|----------|------|
| `init` / 新项目接入 | `init` 程序 |
| Autopilot 触发 | **只执行 description 内嵌程序**（不读本 skill） |
| 本机「执行一轮巡检」/「继续跟进」 | 下方「巡检程序（本机）」 |
| 已有设计文档 + 计划文档（路径、`@` 引用，或用户说「按已有 plan 执行」） | 跳过 Phase 1；现有计划即验收依据 → Phase 2（主任务已存在则巡检器会接手，不必再建 Autopilot） |
| 只有粗糙需求 / 口头目标，尚无书面设计或计划 | Phase 1 |
| 主任务已存在（如 `继续跟进 MUL-xxx`） | 读 metadata / 计划路径 → 巡检程序（只处理这一棵树） |
| `收尾 MUL-xxx` | Phase 5 |

已有计划：写入主任务 `plan_path`，确认计划/方案已 commit + push。可轻量核对「子任务是否覆盖计划」，不要重写计划。

**禁止**为单个任务创建 Autopilot。全 workspace 只允许一个通用巡检 autopilot（由 `init` 创建）。发现 per-task autopilot 视为事故：删除并复盘。

## 开始前

1. **本机**：`multica auth status` 已登录；否则停下来让用户 `multica login`。（Autopilot task 跳过——已有 task 身份。）
2. 读 `.loop-it/config.yaml`；缺失则转 `init`（巡检入口除外）。
3. 做 **Workspace 绑定**。
4. **本机**：`"${MC[@]}" agent list --output json` 确认 executors / orchestrator 仍在该 workspace。
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
     issue_key: <常驻汇总 issue，如 GAN-372>
   ```

4. **注入** `AGENTS.md`「Agent 工作流不变量」（§4 不变量 + 授权口径；事实指针 `.loop-it/config.yaml`；**Patrol 程序 SSOT = Autopilot description**）。已有则只校对。
5. **建/修唯一巡检 Autopilot**（在已绑定 workspace 下）：title `Loop Patrol`；agent=`orchestrator`；mode=`run_only`。description **必须内嵌完整巡检程序**（由 config 填空；`repo` 为 `owner/name` 时 checkout URL 用 `https://github.com/<repo>.git`；已是 URL 则原样）。改 `base_branch` / `repo` / 巡检规则后必须再 `autopilot update` 同步 description：

   ```text
   你是 Loop Patrol（run_only）。本 description 即本轮编排程序（已注入；禁止 autopilot get 自己）。无动作则静默。只用下列「允许命令」；缺什么也不要 --help / 试 flag。

   ## 允许命令（复制即用；除此以外默认禁止）
   A. multica repo checkout <repo_clone_url> --ref <base_branch>
   B. （Read 工具）读检出目录 .loop-it/config.yaml
   C. multica issue comment list <daily_digest.issue_key> --roots-only --summary --recent 5 --output json --compact
   D. multica issue list --metadata loop_it_phase=executing --limit 20 --output json
   E. multica issue get <ID> --output json
   F. multica issue comment list <ID> --roots-only --summary --recent 3 --output json --compact
   G. multica autopilot runs <本autopilot_id> --limit 2 --output json
   仅当未短路时才允许：
   H. multica issue children <ID> --output json
   I. multica issue pull-requests <ID> --output json
   J. gh pr view / gh pr checks / gh pr merge --repo <repo> …
   K. 写评论 / 改 issue 状态（有实质动作时）
   L. multica autopilot list --output json（仅本轮已确认有实质推进时）

   ## 全程禁止
   - 任何 --help；对 issue list 加 --compact（该子命令无此 flag；--compact 仅用于 comment list）
   - git branch / git log；checkout 成功后勿再验分支
   - 为「确认无变化」调用 H/I/J/L，或全量翻页 issue list
   - 并行乱开未在白名单的探测

   ## 启动
   1. 执行 A → 进入检出目录 → B；校验 repo/base_branch 与上列一致。键名以 config 为准（daily_digest / patrol.auto_merge）。
   2. CLI：裸 multica（不要 --profile）。

   ## 巡检（严格按序；短路后立即收尾）
   护栏：只改 Multica issue/评论（及合规时 J）。不改业务代码/plan/.loop-it；不要 git push <base_branch>；不改 .env*；反复失败写 blocked_reason 并升级。

   1. 常驻汇总：若 daily_digest.enabled，只用 C。看近 5 条 root 摘要的日期（Asia/Shanghai）；今日已有 Patrol 汇总 → 跳过；否则写一条（红灯/待拍板/卡住）。禁止为日报拉全量历史评论。
   2. 活跃主任务轻量探测（必须先于 sweep）：D；若有执行中主任务，再 E +（F 或 G）。禁止本步用 H/I/J/L。
   3. 短路判定：上轮实质结论仍成立（如 hold 某 PR、等人工），且主任务 updated_at/last_activity_at 未新于该结论 → **短路收尾**：跳过步骤 4–7；无评论；进入收尾。
   4. （未短路）深读：H + F；blocked 能解就解否则升级；标完成未验证则对照 plan 打回或放行下一 stage。
   5. （未短路）验收：I；patrol.auto_merge 且 DoD+CI 全绿则 gh pr merge --repo <repo>（不强推）；子任务 done 并解锁下一 stage。否则 hold，不刷屏。
   6. （未短路）sweep：最多一次 `multica issue list --limit 100 --output json`，筛标题含 Loop It/Loop Patrol 且非 done/cancelled → 置 done；没有则停。禁止翻第二页。
   7. （未短路）有实质动作才在主任务留短评。per-task Loop It Autopilot 仅此时才可用 L；paused 忽略；active 的在 daily_digest.issue_key 记一条（每天最多一次），本轮不删。
   8. 子任务全 done/cancelled → 主任务可收尾（done + loop_it_phase=completed）；不停本 Autopilot。

   ## 收尾
   run_only 无关联 issue → 直接结束；有 agent task → done 或 blocked。短路时聊天区也可空。
   ```

   schedule=`patrol.cron`，时区 `Asia/Shanghai`；已有同名则 update，不新建第二个。
6. 建议删除标题含 `Loop It 跟进` 的 per-task autopilot（须确认）。三件套齐全即开工。

## Phase 1 — 制定计划（Plan）

仅在尚无可用计划时执行。

1. 计划写入 `docs/superpowers/plans/`（或等价目录）：目标、验收、边界、拆解。
2. 用户确认后再进 Phase 2。
3. **派发前必须 commit + push** 计划/设计文档（agent 拉远端；不 push 则 `plan_path` 对他是 404）。

## Phase 2 — 创建任务树

**本机**一律 `"${MC[@]}"`；Autopilot 用裸 `multica`。

1. 建主任务；`--description-file` 含计划路径与验收标准。
2. 拆子任务：`--parent`；标题前缀 `[<主identifier>] …`；`--stage`；后续 stage 先 `backlog`。executor 取 config。
3. 核对 identifier 前缀属于本 workspace；不对则停手清理。
4. metadata：`plan_path`、`loop_it_phase=executing`（不要写 `autopilot_id`）。

## 巡检程序（本机 `/loop-it` 跟进用）

**Autopilot Loop Patrol 不读本节**——其程序全文在 Autopilot description（由 `init` 写入）。本机用户说「巡检 / 继续跟进」时按下面做；步骤与 description 模板保持同构。

**静默优先：无动作则无产出。**

护栏：不改业务代码 / plan / `.loop-it`；禁止 `git push` 到 `base_branch`（合入只走 `gh pr merge`）。**不限制** executor 在自己功能分支上 commit/push。不改 `.env*`；反复失败写 `blocked_reason` 并升级。

0. 若尚无本仓 / 无 `.loop-it/config.yaml`：checkout 后读 config（本机通常已在仓库根）。
1. **常驻汇总**：若 `daily_digest.enabled`，用 `comment list --roots-only --summary --recent 5 --compact` 判今日是否已有汇总；没有再写。禁止拉全量历史。
2. **活跃主任务轻量探测（先于 sweep）**：`issue list --metadata loop_it_phase=executing` + `issue get` + 近评摘要（或 `autopilot runs --limit 2`）。结论未变且活动时间未新于结论 → **短路**（跳过 children / `gh` / sweep / autopilot list）。
3. （未短路）读 children + 近评；**(a)** blocked 能解就解否则升级；**(b)** 标完成未验证则对照计划打回或放行；**(c)** 验收通过则核 PR，`patrol.auto_merge` 且 DoD+CI 过则 `gh pr merge`（不强推），子任务 `done` 并解锁下一 stage。有动作才留短评。
4. （未短路）**sweep**：最多一页 limit=100 筛 Loop It/Loop Patrol 运行 issue → done。
5. 子任务全 `done`/`cancelled` → Phase 5。
6. **per-task Autopilot**：默认不 list；仅确认有实质推进时再查。paused 忽略；active 的在 `daily_digest.issue_key` 记一条（每天最多一次），本轮不删。

## Phase 5 — 收尾

子任务全 `done`/`cancelled` 后：总验收 → 主任务 `done`、`loop_it_phase=completed` → **不**停巡检 Autopilot → 汇报产出与 PR、遗留。
