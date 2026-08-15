# Discovery iterations — agent-thread-visualizer

Append one section per loop. Keep queries.json frozen within a campaign.

## Goals (this campaign)

- P0 `cli-owner` hit@10 ≥ 100% (achieved at v0)
- P0 `cli` global hit@10: improve if installs allow; else document `--owner`
- P0 `api` hit@40: raise zh/ja phrase recall after reindex
- Host session phrases (Cursor/Claude/…) should hit on `cli-owner`
- description ≤ 1024; stop after 2 rounds with <5pp P0 api/cli gain

## v0-smoke — 2026-08-15

- Smoke only (3 queries). See `v0-smoke.json`.

## v0-baseline — 2026-08-15

- Hypothesis: measure dual-channel after zh/en/ja description already landed
- Changes: none (measurement)
- Metrics (41 queries):
  - api hit_rate 0.122 (P0 0.286) — EN name ~#13; zh/ja P0 mostly miss in top40
  - cli hit_rate 0.000 (P0 0.000) — limit≈10 drowned by installs
  - cli-owner hit_rate 0.561 (P0 1.000)
- Publish: prior commit `fcf7e62` / telemetry via local `npx skills add`
- Decision: continue — front-load 会话可视化; add Cursor/Claude host session phrases; republish + telemetry

## v1 — 2026-08-15

- Hypothesis: leading with `Agent 会话可视化` + explicit host `会话|session|セッション` improves api/cli-owner host recall; global cli still install-bound
- Changes:
  - `SKILL.md` description lead + host phrases (834 chars)
  - body opener + README find examples (zh/en/ja)
  - `agents/openai.yaml` short_description
- Metrics vs v0 (`v1-postpublish.json`):
  - api 0.122 / P0 0.286 (unchanged)
  - cli 0.000 / P0 0.000 (unchanged)
  - cli-owner 0.561→0.585 (+1: `子agent 可视化`); P0 still 1.000
  - Host-only queries still miss on cli-owner (EN often loses to `fenfenxu/droplink-skills@droplink-cli`)
- Publish: `57558ff` + repo/global `npx skills add` (installs≈3)
- Finding: https://skills.sh/fenfenxu/fenfenxu-skills/agent-thread-visualizer still shows **pre-GEO body** (“先收集 thread…”); GitHub main already has new opener → **index lag / scrape not refreshed**. Further description churn won't move search until skills.sh reindexes content.
- Decision: **stop** description loop for this campaign; treat optimal-as-of-now = P0 cli-owner 100% + documented `--owner` finds; residual risk = global CLI + stale skills.sh snapshot + host-query collisions under owner `fenfenxu`
