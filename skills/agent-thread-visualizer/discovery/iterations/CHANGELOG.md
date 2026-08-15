# Discovery iterations — agent-thread-visualizer

Append one section per loop. Keep queries.json frozen within a campaign.

## v0-smoke — 2026-08-15

- Hypothesis: dual-channel script works; multilingual P0 still weak on global CLI
- Changes: none (script smoke); description already has zh/en/ja triggers locally (731 chars)
- Metrics (3 P0: `agent 会话可视化`, `agent thread visualizer`, `セッション可視化`):
  - api hit_rate 0.33 (EN exact phrase hit@13; zh/ja miss)
  - cli hit_rate 0.00 (limit≈10, drowned)
  - cli-owner hit_rate 1.00
- Publish: not in this step
- Decision: continue full matrix after publishing skill-discovery-optimizer
