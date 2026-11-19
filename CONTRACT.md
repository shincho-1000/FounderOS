# Founder OS — API Contract

Base URL: `/api/v1` (all endpoints below are also mounted without the `/api/v1`
prefix, e.g. `/memory/...`, hidden from Swagger).
Auth: `Authorization: Bearer <JWT>` on every endpoint below.

---

## Memory (Phase 4)

Three tiers, all in MongoDB, all scoped to the caller's business:

| Tier | Collection | Purpose |
|---|---|---|
| Short-term | `short_term_memory` | Exact recent turns, max `SHORT_TERM_WINDOW` (10) |
| Summary | `memory_summary` | One rolling compressed summary of interactions that overflowed short-term (≤ `SUMMARY_MAX_CHARS`, 1500) |
| Long-term | `long_term_memory` | Durable facts; top `LONG_TERM_TOP_K` (8) by `importance*2 + recency` go to the LLM |

When a user has no business yet, every memory endpoint returns
`400 {"detail": "Create a business profile first"}`.
MongoDB outages return `503 {"detail": "Memory store (MongoDB) is temporarily unavailable. Please try again."}`.

`category` ∈ `goal | constraint | past_decision | preference | metric`

`decision_id` is a **string** (Decision ids are UUIDs) or `null`.

### `GET /memory/short-term` → `200`
Chronological (oldest first).
```json
[
  {
    "id": "674c1f0e9b1d4a3e8c5f1a22",
    "question": "Should we hire a second engineer?",
    "answer_summary": "Yes, after reaching $20k MRR...",
    "decision_id": "3f2b8c1e-5a77-4b0e-9c61-1d2e3f4a5b6c",
    "created_at": "2026-11-19T10:15:00.123000+00:00"
  }
]
```

### `DELETE /memory/short-term` → `204`
"Reset conversation": clears short-term **and** the summary. Long-term is kept.

### `GET /memory/summary` → `200`
```json
{
  "summary": "Q: Should we raise a seed round? -> Wait until 6 months of runway...",
  "interactions_summarized": 4,
  "updated_at": "2026-11-19T10:15:00.456000+00:00"
}
```
Empty state: `{"summary": "", "interactions_summarized": 0, "updated_at": null}`.

### `GET /memory/long-term?category=goal` → `200`
`category` is optional; invalid values return `422`. Newest first.
```json
[
  {
    "id": "674c1f0e9b1d4a3e8c5f1a23",
    "business_id": "b1c2d3e4-...",
    "category": "goal",
    "content": "Reach $50k MRR by Q4",
    "importance": 5,
    "created_at": "2026-11-19T10:00:00+00:00",
    "updated_at": "2026-11-19T10:00:00+00:00"
  }
]
```

### `POST /memory/long-term` → `201`
Request:
```json
{ "category": "constraint", "content": "Runway is 8 months", "importance": 4 }
```
`content`: 3–1000 chars (trimmed). `importance`: 1–5, default 3.
Response: one long-term entry (shape above).
Posting identical content (case/whitespace-insensitive) in the same category does
**not** create a duplicate: the existing entry is returned with
`importance = max(old, new)` and a fresh `updated_at`.

### `DELETE /memory/long-term/{id}` → `204`
`404 {"detail": "Long-term memory entry not found"}` if the id doesn't exist, is
malformed, or belongs to another business.

### `GET /memory/context` → `200`
Exactly what the LLM sees (debug view).
```json
{
  "short_term": [ /* ShortTermEntry, oldest first */ ],
  "summary": "…",
  "long_term":  [ /* LongTermEntry, ranked by score */ ]
}
```

### Internal API for the Phase 7 decision engine (`app/services/memory_service.py`)
```python
ctx    = await memory_service.get_context(business_id)       # never raises
parts  = await memory_service.format_for_prompt(ctx)
# parts = {"long_term_text": "...", "summary_text": "...", "recent_text": "..."}
#  -> [LONG-TERM MEMORY], [HISTORY SUMMARY], [RECENT CONTEXT] prompt sections
...
await memory_service.record_decision(business_id, question, recommendation,
                                     decision_id, important=False)  # never raises
```
