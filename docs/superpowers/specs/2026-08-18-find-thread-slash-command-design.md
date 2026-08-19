# Find Thread Slash Command — Design

Date: 2026-08-18  
Status: approved  
Skills: `skills/agent-thread-visualizer` (slash command `/find-thread` lives inside this package)

## 1. Goal and scope

### Goal

Users can find a past agent session when they remember **what happened**, not the sidebar title or UUID. They type `/find-thread` (or equivalent natural language), get a ranked list, and can reject the list to search again.

Typical recall: which project, what they did with the agent, optionally which host (Cursor / Codex / Claude Code / Workbuddy / kimi-code). Host may be unknown.

### In scope

- Slash command `/find-thread` **inside** `agent-thread-visualizer` (not a top-level skill)
- Natural-language recall → facet parse → existing locator scripts (no duplicated scanners)
- Default search **all five hosts**; named host is a hard filter
- Ranked two-bucket presentation: **最相关** and **可能相关**
- Each candidate: title, summary, host, project, time, absolute path, session id, match reason, honest open/jump affordance
- Reject / refine loop when first hits are not the target session
- Empty `/find-thread` lists recent sessions (cwd, all hosts)

### Out of scope

- A separate `skills/find-thread/` package
- Auto-visualize after search (user must ask to visualize a chosen id)
- Embedding / session-summary index / semantic vector search
- New `find-thread-by-recall` scoring engine in Python (may happen later if ranking is unstable)
- Invented IDE deeplinks (`cursor://`, unverified resume URLs)
- Changing visualizer’s own default (“current host first”) except where this spec says `/find-thread` differs
- Installing locator scripts onto the user PATH

### Package structure

`/find-thread` is nested in the visualizer skill so one `npx skills add --skill agent-thread-visualizer` ships both the map and the search command. Cursor/Codex recurse `SKILL.md`; the command identity is the folder that contains it (`find-thread`), not a second repo-level skill.

```text
skills/agent-thread-visualizer/
  SKILL.md                 # /agent-thread-visualizer — collect + visualize
  find-thread/
    SKILL.md               # /find-thread — recall search only
    agents/openai.yaml
  scripts/                 # shared locators
```

Scripts used by the command (same package):

- `scripts/find-thread-by-name`
- `scripts/find-thread-by-id`

If locators are missing, stop; do not hand-roll `find ~`.

`find-thread/SKILL.md`:

- `argument-hint`: `<项目 / 做了什么 / 可选宿主>`
- `$ARGUMENTS` is the raw recall string
- `disable-model-invocation: true` so it behaves as a slash command; parent SKILL.md dispatches here when the user is doing recall search in natural language

---

## 2. Query parse and retrieval cascade

The model extracts facets from `$ARGUMENTS`. The scripts never guess UUID vs name; the model chooses which entrypoint.

### Facets

| Facet | Source | Default |
|-------|--------|---------|
| Activity keywords | Content words from “做了啥”; drop filler | Required unless empty invocation |
| Hosts | Named: cursor / Cursor; codex / Codex; claude / Claude Code / claude-code; workbuddy / Workbuddy; kimi / kimi-code / kimi code | All five |
| Project | Named repo / path | Current cwd |
| Time | “昨天”, “上周”, … | Ranking only, not a hard filter |
| Shape | Looks like UUID / path fragment | `find-thread-by-id`; else `find-thread-by-name` |

Named host = **hard filter**. Unnamed host = search all hosts; host is only a ranking signal.

Project stays cwd-scoped unless the user names another project (then `-C` that path, or `--all` if the path cannot be resolved). “Host unknown” does **not** imply “project unknown”.

Always pass `--json`. Do not call deprecated `scripts/find-thread`. Do not install scripts on PATH.

Compress the recall sentence into search tokens before calling the script. Do not pass the full utterance as `query`.

### Cascade (max three script invocations per turn, until the user rejects)

```text
UUID / path fragment?  → find-thread-by-id
No $ARGUMENTS?         → find-thread-by-name  (recent; hosts as above; cwd)
Otherwise:
  1. by-name + keywords  (title / first-user prompt)
  2. Zero hits OR all weak hits OR query is activity-shaped
       → same filters + --deep
  3. Still zero AND user named a non-cwd project
       → -C that project or --all
```

**Activity-shaped** means the recall is about work done mid-thread (“加过 slash command”, “修过登录”), not a title. For these queries, run `--deep` even if step 1 already has title hits, and merge extra hits into **可能相关** so a false-positive title does not hide the real session.

**Weak hit**: only `prompt-tokens` / low-score fuzzy, and no `title-*` and no `--deep` snippet.

If a named host has zero hits: **report that miss first**, then optionally search other hosts. Those results may only appear under **可能相关**, labeled “你说是 \<host\>，但这些在别的宿主”. Never promote cross-host expansion to **最相关**.

If the first keyword set misses, at most one synonym retry. Total script calls this turn ≤ 3. Further search happens only after user rejection (section 3).

---

## 3. Reject / refine (hits exist but are the wrong session)

Having hits is not success. Title / first-prompt matches are often false positives; the real session is often in the middle of a transcript.

After every result screen, the user can say 「都不是」「不是这几个」「再找找」 or give a correction.

On rejection:

1. Treat the previous list as a miss even if `match_via` was `title-exact`.
2. **Exclude** already shown session ids (`host:session_id`).
3. Escalate, in order, whatever has not been done yet:
   - `--deep` if not used
   - new keywords from the user’s correction
   - widen project (`--all` / `-C`)
   - only then widen host, and only into **可能相关** with the disclaimer above
4. Rejection turns get their own three-call budget.

If the user points at one card and says 「类似但不是」: keep that card’s project/host as clues, change time or keywords, still exclude that id.

The result footer always tells the user they can reject or add a more specific “做了啥”.

---

## 4. Ranking and presentation

### Two buckets

| Bucket | Count | Meaning |
|--------|-------|---------|
| **最相关** | Usually 1; at most 3 if tied | Agent’s pick; must include a one-line why |
| **可能相关** | Remaining signal-bearing hits, default cap 5 | Same project/tokens/deep snippet, lower confidence |

**Tie for 最相关**: same `match_via` tier and score difference ≤ 0.05. Cap 3; overflow goes to 可能相关.

**Rank signals** (high to low): `match_via` (`title-exact` > `title-substr` > `title-fuzzy` > `title-tokens` > `prompt-*` > `rg` / `rg-fulltext`) → user-named host match → recency → current project.

Cross-host expansion hits cannot enter **最相关**.

Do not auto-visualize. If the user then says 「画出这个」 / gives an id, hand off to `agent-thread-visualizer`.

### Required fields per candidate

UUID alone or title alone is invalid output. Every card includes:

1. **Title** — sidebar title; if missing, truncated first user prompt
2. **Summary** — 2–4 sentences a human can recognize: title + first-user goal + `--deep` match snippet when present. For the **最相关** card only, if that is still too thin, read a few more user turns and add one sentence “后来做了什么”. Do not dump the transcript into the list.
3. **Metadata** — host · project · relative age + clock time
4. **Path** — absolute path, required; markdown link `file://<absolute-path>`
5. **ID** — full session id, monospace, copyable
6. **Why** — one sentence plus `match_via`
7. **Open** — only verified jump/resume. Host manuals currently do not document stable deeplinks:
   - Do **not** invent `cursor://` or other unverified URLs
   - Claude Code / Codex: if a `resume` command is later verified in `references/host-*.md`, print that command; until then, say open method unknown
   - Cursor / others: “search this title in the Agents sidebar” or “pass this path/id to `/agent-thread-visualizer`”
   - Never imply a click returns the user to the live chat UI unless that mechanism is verified

Language of the list follows the user (Chinese in this product’s common case). Technical ids/paths stay as-is.

### Shape (chat markdown, not the CLI table)

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

The locator CLI table remains for debugging. The user-facing find-thread skill must render cards, not dump that table as the answer.

---

## 5. Error handling

| Case | Behavior |
|------|----------|
| Zero hits after cascade | List what was tried (hosts, project scope, deep or not, keyword sets). Ask for another project name, a more specific activity, a path, or a pasted id. Do not invent a session. |
| Scripts missing | Say this package’s `scripts/find-thread-by-name` was not found; stop. Do not `find ~`. |
| Named host miss, other hosts hit | Named-host miss stated first; other hosts only in 可能相关 with disclaimer. |
| Ambiguous project name | Show matching workspace slugs; ask which one; do not silently `--all` unless the user already implied “any project”. |
| `rg` missing on `--deep` | Report that deep search is unavailable; keep title/prompt hits; do not fake full-text matches. |
| Unreadable / missing file | Omit or mark that card; never fabricate title/summary. |
| User declines further search | Stop. |

---

## 6. Testing / verification

Technique skill: verify an agent with the SKILL present follows the contract.

Minimum checks:

- Empty `/find-thread` → recent, all hosts, cwd, two-bucket cards (or a single 最相关 plus empty 可能相关).
- Recall with named host + activity → `-a` that host; `--deep` used because activity-shaped.
- Recall with no host → no `-a` filter (all `HOSTS`).
- First-pass title hits that user rejects → excluded ids, `--deep` or widened search, not a repeat of the same list.
- Every card has title (or prompt fallback), summary, path with `file://`, full id, why. No UUID-only or title-only answers.
- No `cursor://` or other unverified deeplink in output.
- No auto-visualize.
- Named-host miss + other-host hits → other-host cards only under 可能相关.
- Does not call deprecated `find-thread` or `find ~`.

Script behavior itself is already covered by `scripts/verify-find-thread.py` in the visualizer skill; this spec does not require changing that suite unless locator flags change (they should not in v1).

---

## 7. Relationship to visualization (same package)

| | `/find-thread` | `/agent-thread-visualizer` |
|--|----------------|---------------------------|
| Job | Find and rank | Collect facts and draw execution map |
| Host default | All hosts | Current host first (unchanged) |
| Input | Recall / empty=recent / UUID | UUID or name after the user is targeting a session |
| Output | Two-bucket cards | Layered swimlane map |

Both live in `skills/agent-thread-visualizer/`. The main SKILL.md dispatches recall search to `find-thread/SKILL.md`. After the user picks a card and asks to visualize, continue with the main SKILL workflow.

---

## 8. Implementation notes (not extra product scope)

- Prefer `--json` hits: `title`, `prompt`, `path`, `session_id`, `host`, `project`, `mtime`, `match_via`, `score`.
- Summary is written by the model from those fields (+ optional extra user turns for 最相关 only).
- v1 does not add Python `best` / `related` labels; the skill contract assigns buckets. If ranking proves noisy, a later spec can move scoring into the locator (approach B).
