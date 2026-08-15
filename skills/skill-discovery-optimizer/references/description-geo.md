# Description GEO (skills SEO)

`description` is the primary discovery string for agents **and** a strong signal for skills.sh semantic search. Keep it honest for local triggering while packing search synonyms.

## Hard limits

- ≤ **1024** characters after YAML fold (`>-` → single line)
- Third person; WHAT + WHEN
- Prefer `description: >-` for long copy (not `|`)

## Packing order (when space is tight)

1. One-sentence capability + hosts  
2. EN P0 phrases (skill name, session timeline, session report, …)  
3. User-language P0 (e.g. ZH `会话可视化`, JA `セッション可視化`)  
4. Host session phrases  
5. Colloquial / P2 last  

## Good pattern

```yaml
description: >-
  <capability>. Triggers (EN): .... (ZH): .... (JA): ....
```

## Bad patterns

- Synonym spam with no capability sentence  
- Only English when users search Chinese/Japanese  
- Renaming the skill for SEO when it breaks identity (prefer description keywords)  
- Claiming competitors' brand names as if this skill were theirs  

## Surfaces beyond description

| Surface | Why |
|---------|-----|
| SKILL.md first body paragraph | skills.sh page / scrapers |
| README Find-with column | humans + some crawlers |
| `agents/openai.yaml` short_description | Codex-style UIs |
| `npx skills add` telemetry | actually enters skills.sh index |

## After every edit

```bash
python3 -c "
from pathlib import Path
import re
text=Path('SKILL.md').read_text()
fm=text.split('---',2)[1]
# fold >- body until license/metadata
..."
```

Or use the eval script's `--check-description` if provided.
