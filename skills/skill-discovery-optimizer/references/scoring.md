# Scoring

## Pass rule

Default: a result **hits** if its `id` / CLI slug contains both:

- configured `owner` (e.g. `fenfenxu`)
- skill `name` (e.g. `agent-thread-visualizer`)

Override with `pass` string in `queries.json` if needed.

## Channels

| Channel | Hit@K | Notes |
|---------|-------|-------|
| `api` | Hit@40 useful for “is it indexed at all” | Deep rank; not what users see in CLI |
| `cli` | **Hit@10** is the find-skills bar | `npx skills find` default limit |
| `cli-owner` | Hit@10 with `--owner` | Fairness under low installs |

## Aggregate metrics

Per iteration report:

- `cli_p0_hit_at_10` = hits / P0 count on `cli`
- `cli_all_hit_at_10` = hits / all cases on `cli`
- `api_hit_at_40` = hits / all on `api`
- `agree_rate` = share of queries where api-hit⇔cli-hit (same boolean; ranks may differ)

Mark each case `priority`: `p0` | `p1` | `p2` in queries.json.

## Interpreting gaps

| Pattern | Likely cause | Lever |
|---------|--------------|-------|
| api miss & cli miss | not indexed / no lexical-semantic match | description keywords + install telemetry |
| api hit@30+, cli miss | buried by installs / limit=10 | installs, sharper query phrases, `--owner` docs |
| cli-owner hit only | indexed but globally drowned | expected early; keep owner docs |
| api/cli disagree often | limit / sort difference | compare both; optimize for cli |

## Stop / optimal

“Optimal” for a new skill usually means:

1. P0 cli-owner = 100%  
2. P0 cli global improving or documented as install-bound  
3. Description still good for agent trigger  
4. Two iterations with <5pp P0 gain → stop unless user wants more installs campaign  
