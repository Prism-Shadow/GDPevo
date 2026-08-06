---
name: work-portfolio-analysis
description: Produce JSON readouts (portfolio-mix, SLA-aging, or release-readiness) from a shared work-item portfolio environment exposed over REST + a restricted SQL endpoint. Use when a task points at a shared portfolio environment containing work items, mix targets, SLA policy, releases/milestones/blockers/dependencies and asks for a single JSON object matching a provided answer_template.json. Knows the environment's stale-field traps (mirror_status, legacy_category), primary-vs-duplicate-vs-cancelled record handling, the portfolio category classification convention, and the exact ordering/precision rules each template requires.
---

# Work Portfolio Analysis

This skill solves tasks that ask for a structured JSON readout from a shared
**work-item portfolio environment**. The environment is reached over the network
via `environment_access.md`; it exposes REST endpoints plus a restricted SQL
passthrough. Three task families recur:

1. **Portfolio mix** — closed work, count-based category mix vs. a target mix.
2. **SLA aging** — primary SLA population, overdue items, aging, breach rate.
3. **Release readiness** — ship decision, milestone completion, gating items,
   blockers, dependency chains, readiness score.

Every task supplies `input/payloads/answer_template.json`. **The template is
authoritative for output shape** (field names, required keys, enums, ordering).
Two tasks that compute the same concept can name fields differently, so always
emit values in the template's exact structure — do not carry field names over
from one task to another.

## How to run a task

1. **Read the prompt.** Extract scope parameters: `scope_id`, quarter, teams,
   product area(s), as-of date, recent-closed window, release id, etc. These
   vary per task — never hardcode them.
2. **Read `environment_access.md`** for the base URL, the `X-Env-Token` header
   value, and the allowed endpoint list. Reach the environment **only** through
   this file. See `references/environment.md` for the endpoint inventory, the
   SQL passthrough shape, and the full data model.
3. **Fetch the data** you need (REST list endpoints or `POST /api/query` with a
   SQL string). Prefer the SQL endpoint for filtered/aggregated reads.
4. **Apply the record-handling and classification rules** (see below and
   `references/classification.md`).
5. **Compute** per the task family in `references/procedures.md`.
6. **Emit one JSON object** matching the template exactly — no prose outside the
   JSON. Apply the ordering and precision rules in `references/procedures.md`.

## Core record-handling rules (apply to every family)

The `work_items` table carries two **stale trap fields** that must be ignored,
and one **authoritative linkage field**:

- `mirror_status` — STALE. Ignore. Use the authoritative `status` field.
- `legacy_category` — STALE. Ignore. Classify from `work_type` + `labels` +
  `title` per `references/classification.md`.
- `duplicate_of` — AUTHORITATIVE duplicate linkage. A record is a **duplicate**
  when `duplicate_of` is non-null **or** `status == "Duplicate"`. A record is
  **cancelled** when `status == "Cancelled"`.

Record roles:

- **Primary** = not a duplicate and not cancelled (`duplicate_of` is null AND
  `status` not in `{Duplicate, Cancelled}`). Only primary records are counted in
  totals, mixes, SLA populations, and milestone denominators.
- **Duplicate** = reported (grouped into clusters by the `duplicate_of` target)
  but **never counted** as primary work.
- **Cancelled** = excluded; reported in exclusion lists when the template asks.

**Terminal / "complete" statuses** (authoritative `status`): `Closed`, `Done`,
`Verified`, `Deployed`. Non-terminal: `In Progress`, `Review`, `Backlog`,
`Reopened`.

## Portfolio category classification

Classify each **primary** item into exactly one of `NewFeature`, `TechDebt`,
`Reliability`, `Security`. Gather signals from `work_type`, `labels` (array),
and `title` (substring), then apply strict priority — **first match wins**:

**Security > Reliability > TechDebt > NewFeature**

Full signal sets and worked resolution rules are in
`references/classification.md`. `legacy_category` is never used.

## Ordering & precision (universal)

- ID lists: ascending / lexicographic, unless the prompt says otherwise.
- "Included work item" lists (portfolio mix): order by `closed_at` ascending,
  then `id` ascending.
- Teams: alphabetical (note any template that pins a specific order).
- Duplicate clusters: sorted by `primary_id`; each cluster's `duplicate_ids`
  sorted ascending.
- Percentages: 1 decimal place (percentage points).
- Rates and scores (`breach_rate`, `sla_breach_rate`, `readiness_score`): 3
  decimal places.
- `gap_pct` = `actual_pct` − `target_pct`.

## Output discipline

- Return a **single JSON object** matching `answer_template.json` exactly.
- **No prose** outside the JSON.
- Do **not** copy task-specific answer values from any example — recompute every
  value from the live environment for the current scope.

## References

- `references/environment.md` — access, endpoints, SQL passthrough, full data
  model, stale-field traps.
- `references/classification.md` — portfolio category signal sets and
  resolution rules.
- `references/procedures.md` — per-family procedures, computations, and
  output-shape notes.
