# Workbuddy

- last_verified: 2026-08
- confidence: low

Host manual for locating agent conversation threads stored by Workbuddy. Treat paths as heuristics; verify against live signals before relying on a match. Layout details are largely unverified — mark unknowns as 待核实.

## Live signals

- Workbuddy product/app context in the session (UI references, app name, or rules mentioning Workbuddy)
- macOS: presence of `~/Library/Application Support/com.workbuddy.workbuddy/`
- Session or thread identifiers mentioned in Workbuddy UI or export output — field names 待核实

## Known locations

- **App support root:** `~/Library/Application Support/com.workbuddy.workbuddy/`
- **Exact session file layout:** 待核实 — probe for `sessions`, `threads`, `conversations`, `*.jsonl`, `*.db` under the app support tree
- **Never invent SQLite schemas** — if a DB is found, prefer official export/API or ask the user for a known-good export path rather than guessing table/column names

## ID vs name

- **ID:** 待核实 field names; try filename stems and any obvious `id`/`title` JSON keys when readable files are found
- **Name:** 待核实 — match title/summary keys if present in JSON/JSONL; else fuzzy over filename stems or first user message snippet
- Do not assume Workbuddy persists a separate human title outside session file content

## Probe order

1. Confirm Workbuddy is the current host (app support dir exists or product cues in context)
2. List likely session containers under app support (`sessions`, `threads`, `conversations`, or similar — names 待核实)
3. ID then name match within discovered containers
4. On miss: ask user for export/path; keep skill usable via pasted content

## Failure / staleness notes

- **Low confidence** until layout is verified on a real install — directory structure and file formats may differ from expectations
- macOS-only app support path is the primary known root; other platforms 待核实
- Do not invent transcript content or DB queries — if no session file resolves, report steps tried and manual confidence level before asking the user for a direct path or paste
