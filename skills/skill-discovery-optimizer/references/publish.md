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

6. Optional: open/verify https://skills.sh/\<owner\>/\<repo\>/\<skill\>  
   - Compare page body to GitHub `SKILL.md`. If the site still shows an old intro, treat search as **stale index** and pause description-only SEO loops.  
7. Wait for reindex (minutes to longer); then re-run eval  
8. Record commit SHA + install time + whether skills.sh body matched GitHub in CHANGELOG  

## Do not

- Force-push unless user asks  
- Skip hooks unless user asks  
- Promise immediate leaderboard placement after one install  

## Low-install reality

Document for users:

```bash
npx skills find <primary-query> --owner <owner>
npx skills add <owner>/<repo> --skill <skill-name>
```
