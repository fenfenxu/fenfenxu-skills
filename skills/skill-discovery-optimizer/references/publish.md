# Publish for skills.sh

skills.sh listing is driven by **install telemetry** from `npx skills add`, not by crawling GitHub alone. Public repo + valid `SKILL.md` is required for install; search ranking needs installs + indexed text.

## Checklist

1. `description` ≤ 1024; `name` matches folder  
2. User approved commit/push  
3. Commit message notes discovery iteration (e.g. `discovery(v2): add zh/ja triggers`)  
4. `git push` to default branch  
5. Refresh telemetry:

```bash
npx skills add <owner>/<repo> --skill <skill-name> -g -y
```

6. **Verify listing content** (not just installs): open  
   `https://www.skills.sh/<owner>/<repo>/<skill>`  
   Compare JSON-LD / meta `description` and body opener to GitHub `SKILL.md`.  
   Install count going up ≠ content reindexed.  
7. If body/description still old → record `index lag` in CHANGELOG, **pause** description SEO loop, wait / re-check later. Do not treat search misses as keyword failure.  
8. Only after listing text matches (or you explicitly accept stale-index risk): re-run eval  
9. Record commit SHA + install count + whether skills.sh **content** matched GitHub in CHANGELOG  

## Known unknown: content reindex

Observed (agent-thread-visualizer, 2026-08-15):

| Signal | After `npx skills add` |
|--------|-------------------------|
| Install counter on skills.sh | Updates (e.g. 2 → 5) |
| Page / JSON-LD `description` + SKILL.md body | Can stay on an **older** snapshot for hours+ |
| When / what triggers full content reindex | **Unknown** (not documented; not implied by install telemetry alone) |

Implications for this skill’s loop:

- Description GEO cannot be closed-loop validated while listing text is stale.
- Correct agent behavior: **stop keyword iteration**, keep `--owner` docs, poll the page later; resume eval only after content catch-up.
- Do not promise “skills.sh updated” from push + install alone.

Until Vercel/skills.sh documents reindex timing, treat content refresh as an external blocker.

## Do not

- Force-push unless user asks  
- Skip hooks unless user asks  
- Promise immediate leaderboard placement after one install  
- Keep rewriting `description` while the public page still shows the previous SKILL.md  

## Low-install reality

Document for users:

```bash
npx skills find <primary-query> --owner <owner>
npx skills add <owner>/<repo> --skill <skill-name>
```
