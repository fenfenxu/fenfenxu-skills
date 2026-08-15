# Session health (optional, end of output)

Show only when evidence exists. Place **after** the visualization. Omit if the user declines advice.

## Signals

| Signal | What to look for | Advice direction |
|--------|------------------|------------------|
| Many compressions / compactions | Compaction/summarization events, repeated “context compressed” markers | Suggest new session or split work to reduce long-thread distortion |
| Context nearly full | Host-reported context/token occupancy high; warnings about limit | Finish current goal, then open a new thread; avoid stuffing new topics |
| Frequent topic switching | Multiple unrelated user goals interleaved without clear phase boundaries | One theme per session; side quests → new sessions with links back |

## Rules

- Every tip must cite concrete observations (counts, quotes, event ids, ratios).
- No host metric → qualitative judgment still requires cited observations.
- No evidence → write nothing (do not speculate).
- Keep the section short (typically 1–3 bullets).
- Match the user’s language (output i18n).
