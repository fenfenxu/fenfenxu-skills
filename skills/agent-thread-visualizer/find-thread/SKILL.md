---
name: find-thread
description: >-
  Use when the user wants to find a past agent session or conversation by what
  it did, which project, or which host, especially when they do not remember
  the exact title or UUID. Slash command of agent-thread-visualizer.
  Triggers (EN): /find-thread, find thread, find session, find conversation,
  search agent history, find that chat where, recall session. (ZH): 查找会话,
  找会话, 找上次那个会话, 会话搜索, 按做过的事找会话, 回忆会话.
license: MIT
metadata:
  author: fenfenxu
  category: observability
argument-hint: "<项目 / 做了什么 / 可选宿主>"
disable-model-invocation: true
---

# Find Thread

本文件是 **agent-thread-visualizer 包内的 slash 命令** `/find-thread`，不是独立 skill。按回忆找过去的 agent 会话（项目 / 做了啥 / 可选宿主），给出排序后的候选。不画执行地图。

本轮回忆：

$ARGUMENTS

空参数 = 当前工作区、全部宿主的最近会话。

## 1. 脚本（与主 skill 共用）

本命令目录是 `agent-thread-visualizer/find-thread/`。Locator 在**上一级** `scripts/`，不要手搓 `find ~`，不要装进 PATH。

先定位 visualizer 根目录（含主 `SKILL.md` 与 `scripts/` 的那一层），然后：

```bash
python3 "<visualizer-root>/scripts/find-thread-by-id" --json <uuid>
python3 "<visualizer-root>/scripts/find-thread-by-name" --json
python3 "<visualizer-root>/scripts/find-thread-by-name" --json "关键词"
python3 "<visualizer-root>/scripts/find-thread-by-name" --json --deep "关键词"
python3 "<visualizer-root>/scripts/find-thread-by-name" --json -a cursor "关键词"
```

始终 `--json`。禁止调用已废弃的 `scripts/find-thread`。找不到 `scripts/find-thread-by-name` 就停，不要自己扫家目录。

## 2. 拆字段

从 `$ARGUMENTS` 抽出：

| 字段 | 规则 | 默认 |
|------|------|------|
| 关键词 | 「做了啥」里的实质词，去掉口语虚词；不要把整句当 query | 空参数则无 |
| 宿主 | cursor / Cursor；codex / Codex；claude / Claude Code / claude-code；workbuddy / Workbuddy；kimi / kimi-code / kimi code | 不点名 = **五个都搜**（不要传 `-a`） |
| 项目 | 说出的仓库名/路径 | 当前 cwd |
| 时间 | 「昨天」「上周」 | 只影响排序，不硬过滤 |
| 形态 | 像 UUID / 路径片段 → `find-thread-by-id` | 否则 `find-thread-by-name` |

点名宿主 = 硬过滤（`-a`）。没点名 ≠ 项目也不确定。用户点了别的项目才 `-C` 或 `--all`。

## 3. Cascade（本轮最多 3 次脚本调用）

```text
像 UUID？     → find-thread-by-id
无参数？      → find-thread-by-name（recent）
否则：
  1. by-name + 压缩后的关键词
  2. 零命中 / 全是弱命中 / 查询是「做了啥」而非标题
       → 同一过滤条件加 --deep
  3. 仍没有，且用户提了别的项目 → -C 该项目或 --all
```

**做了啥**（「加过 slash command」「修过登录」）：即使第 1 跳已有标题命中，也要 `--deep`，把额外命中放进「可能相关」。

**弱命中**：只有 `prompt-tokens` / 低分 fuzzy，且没有 `title-*`、没有 deep 片段。

第一组关键词零命中时，最多换一组同义再跑一次，计入 3 次上限。

点名宿主零命中：先报告该宿主没有。再搜其他宿主时，结果只能进「可能相关」，并写「你说是 \<host\>，但这些在别的宿主」。禁止把扩搜结果当成最相关。

## 4. 排序

`match_via`：`title-exact` > `title-substr` > `title-fuzzy` > `title-tokens` > `prompt-*` > `rg` / `rg-fulltext`，然后：用户点名的宿主 → 越新越好 → 当前项目。

| 档 | 数量 |
|----|------|
| **最相关** | 通常 1；同 via 且 score 差 ≤ 0.05 可并列，最多 3，多的进可能相关 |
| **可能相关** | 其余有信号的，默认最多 5 |

跨宿主扩搜不得进入最相关。

## 5. 呈现（必须用卡片，禁止把 CLI 表当答案）

只给 UID 或只给标题 = 不合格。每条都要有：

1. 标题（没有则截断首条用户消息）
2. 摘要 2–4 句：标题 + 首条目标 + deep 命中片段。最相关若仍认不出，再读几轮用户消息补一句「后来做了什么」。不要贴全文。
3. 宿主 · 项目 · 相对时间 + 时钟时间
4. 绝对路径，markdown：`[basename](file://绝对路径)`
5. 完整 session id（等宽）
6. 理由：一句话 + `match_via`
7. 打开（禁止编造 `cursor://` 或其他未核实 deeplink；不要暗示点击能回到当时的聊天 UI）：
   - Cursor：在 Agents 侧边栏搜标题，或让用户对这条说「画这个」（走本包主 SKILL 的可视化）
   - 其他宿主：打开方式未在 host 手册核实 — 给路径和 ID；要执行地图时走本包可视化流程

```markdown
## 最相关
**{title}** · {host} · {project} · {relative time}
{2–4 sentence summary}
- 路径: [{basename}](file://{absolute-path})
- ID: `{full-session-id}`
- 打开: {honest open method}
- 理由: {match_via} — {one sentence}

## 可能相关
1. **{title}** · {host} · {project} · {relative time}
   {one-line summary}
   - 路径: …  · ID: `{…}`  · 理由: …
2. …

如果都不是，直接说「都不是」或补一句更具体的「做了啥」。
```

语言跟随用户。不要自动可视化；用户说「画出这个」或给出 id 再按**本包主 SKILL.md** 采集并画图。

## 6. 否决再找

有命中 ≠ 找对了。用户说「都不是」「不是这几个」「再找找」或纠正时：

1. 即使刚才是 `title-exact` 也当未命中
2. 排除已展示的 `host:session_id`
3. 按尚未做过的升级：`--deep` → 新关键词 → 放宽项目 → 最后才扩宿主（只进可能相关）
4. 否决轮次重新计算 3 次调用上限

「类似但不是」：保留那条的项目/宿主当线索，换时间或关键词，仍排除该 id。

## 7. 出错

| 情况 | 做法 |
|------|------|
| cascade 后仍零命中 | 列出试过的宿主、项目范围、是否 deep、关键词；问更具体的活动、项目、路径或 id。禁止编造会话 |
| 脚本缺失 | 说明本包 `scripts/find-thread-by-name` 找不到；停 |
| 点名宿主没有、其他宿主有 | 先报点名宿主未中；其他只进可能相关并加声明 |
| 项目名有歧义 | 列出匹配的 workspace slug，问选哪个；用户没说「任意项目」就不要默默 `--all` |
| `--deep` 需要 `rg` 但没有 | 说明无法全文搜；保留标题/首条命中；不要假装有正文命中 |
| 文件不可读 | 丢掉或标出该条；不要编标题/摘要 |
| 用户不再找 | 停 |

## Red flags

- 把 locator 的 CLI 表当作给用户的答案
- 只回 UUID 或只回标题
- 没人要求就画执行地图
- 编造 `cursor://` / resume URL
- 手搓 `find ~` 或调用废弃的 `scripts/find-thread`
- 用户没点名宿主却只搜当前宿主
- 第一跳有标题命中就停，而查询其实是「做了啥」
- 用户说「都不是」后把同一批 id 再展示一遍
- 把本命令做成仓库里另一个一级 skill（`skills/find-thread/`）
