---
name: portfolio-env-analysis
description: Answer portfolio-engineering analysis tasks (portfolio-mix review, SLA-aging review, release-readiness assessment) that run against a shared HTTP environment. Use when a task supplies an environment_access.md file (base URL + X-Env-Token + allowed endpoints), a natural-language prompt defining a scope, and an answer_template.json JSON Schema, and asks for a single JSON object as the answer. Covers querying work items / mix targets / SLA policy / releases / milestones / dependencies / blockers, separating primary work from duplicate / mirror / cancelled / distractor records, resolving portfolio categories from conflicting signals, computing counts / percentages / gaps / rates with the required precision and ordering, and emitting a schema-conformant JSON answer.
---

# Portfolio Environment Analysis

You are answering an analysis task against a shared "portfolio engineering" environment exposed
over HTTP. The task always gives you three things:

1. **`environment_access.md`** — the *only* sanctioned way to reach the running environment. It
   lists the base URL, the `X-Env-Token` value, and the allowed endpoints.
2. **A prompt** (e.g. `input/prompt.txt`) — the natural-language question plus the **scope**
   (teams, quarter or as-of date, product areas / categories, `scope_id` or `release_id`, closed
   window, and any required enum values).
3. **`answer_template.json`** — a JSON Schema that is the strict output contract.

Your job: query the environment, apply the data-hygiene rules, compute the requested metrics, and
return **a single JSON object** that validates against the template. No prose outside the JSON.

> This skill teaches the procedure. It deliberately contains **no task-specific answer values**
> (no specific work-item IDs, scope ids, counts, or percentages). Derive every value from the live
> environment for the scope in the current prompt.

## Hard rules

- **Reach the environment only via `environment_access.md`.** Read it for the base URL, the
  `X-Env-Token` value, and the allowed endpoint list. Send the token as the `X-Env-Token` header on
  every request. Substitute the prompt's `<TASK_ENV_BASE_URL>` placeholder with the base URL from
  `environment_access.md`. Do not invent endpoints, fields, or data; do not read data from any
  other source.
- **The template is the contract.** Match it exactly: every `required` field, every `enum`, every
  `const`, every `additionalProperties: false`. Echo `const` values verbatim. Add no extra
  properties. The schema's `description` strings state the ordering and rounding rules — follow
  them literally.
- **Output is JSON only.** Return one JSON object. No surrounding prose, no markdown fences, no
  commentary.
- **Never copy "answer values" from memory or from examples.** Recompute everything from live data
  for the current scope.

## Procedure

### 1. Load access + scope + contract
- Read `environment_access.md` → base URL, token, endpoints.
- Read the prompt → extract the scope (teams, quarter / as-of date, product areas, categories,
  `scope_id` / `release_id`, closed window, required enums).
- Read `answer_template.json` → note `required`, `enum`, `const`, `additionalProperties`,
  ordering descriptions, and precision. These drive steps 5–7.

### 2. Pull the raw records you need
Use the GET endpoints and/or the read-only SQL `POST /api/query`. Full catalog and field names in
`references/environment_and_endpoints.md`. Typical needs:
- work items — `GET /api/work-items`, or `POST /api/query` over the `work_items` table for
  filtered/aggregated pulls.
- target mix — `GET /api/mix-targets`, select the row whose `scope_id` equals the task's target
  scope (mix tasks).
- SLA policy — `GET /api/sla-policy` (SLA tasks).
- release context — `GET /api/releases/{release_id}` (returns release + its milestones + its
  blockers), plus `GET /api/milestones`, `GET /api/dependencies`, `GET /api/blockers`
  (release-readiness tasks).

### 3. Apply data hygiene — every task
These rules recur across all task types (detail in `references/data_hygiene.md`):
- **Primary vs duplicate.** A work item with `duplicate_of` non-null is a **duplicate** that points
  at a canonical primary (the record named by `duplicate_of`). The `duplicate_of` field — *not*
  `status` — is the authoritative duplicate signal (a duplicate can still carry `status: "Closed"`).
  Report duplicates in the schema's duplicate/exclusion fields, but **never** count them in totals,
  counts, percentages, aging, overdue sets, or milestone denominators. The primary is the record
  duplicates point *at*.
- **Authoritative fields over stale mirrors.** Use the authoritative `status` and resolve category
  from `work_type` / `labels` / `title`. **Ignore** `mirror_status` and `legacy_category` — they
  are stale mirror/export fields. Where the schema asks, acknowledge this explicitly (e.g. set
  `ignored_mirror_status_and_legacy_category: true`).
- **Exclude cancelled.** In-scope records with `status: "Cancelled"` are excluded; report them in
  whichever exclusion field the schema provides.
- **Exclude distractors.** Records that look in-scope (same quarter / product area / team) but are
  not primary closed portfolio work are distractors — exclude and report them in the schema's
  exclusion field(s).
- **Inclusion = closed/complete + in-scope + primary.** Determine the closed/complete status set
  from the task's closed-window semantics (terminal statuses such as Closed / Done / Deployed /
  Verified — confirm against the live `status` vocabulary). `Cancelled` and `Duplicate` are never
  included. Then filter to the prompt's teams / product area / quarter / categories.

### 4. Resolve portfolio categories
Classify each included primary item into exactly one of **NewFeature, TechDebt, Reliability,
Security** by aggregating signals from `work_type`, `labels`, and `title` (in that priority of
signal source), **not** `legacy_category`. When signals point to more than one category, apply the
precedence **Security > Reliability > TechDebt > NewFeature** (highest wins). See the full
signal→category table in `references/data_hygiene.md`. SLA tasks reuse this same resolution to
select the reliability/security population.

### 5. Compute the metrics
Per-archetype playbooks in `references/task_archetypes.md`. Common computations:
- **Actual mix %** = category count ÷ total included × 100, to 1 decimal.
- **Target %** = the mix_targets row's fraction × 100 (mix targets are stored as 0–1 fractions),
  to 1 decimal.
- **Gap** = actual − target, to 1 decimal.
- **Under-invested / deficit** = categories with negative gap; order most-negative first.
- **Breach / readiness rates** = a ratio rounded to **exactly 3 decimals** (e.g.
  `breach_rate` = overdue primary count ÷ included primary count; `readiness_score` = completed
  primary ÷ primary denominator).
- Aging buckets, severity counts, escalation order, and dependency-chain paths follow the bucket
  boundaries and ordering stated in each task's schema/prompt.

### 6. Order everything as the schema specifies
- ID lists: ascending / lexicographic — *unless* the schema says otherwise (e.g.
  `included_work_item_ids` ordered by `closed_at` then id; escalation queue in priority order).
- Teams: alphabetical (some schemas fix a specific order — follow the schema's `description`).
- Mix/gap tables: fixed order NewFeature, TechDebt, Reliability, Security.
- Duplicate clusters: sorted by `primary_id`, with each cluster's `duplicate_ids` sorted ascending.
- Milestone completion: by `milestone_id` ascending.
- Dependency chains: lexicographically by the full path.

### 7. Assemble + validate + return
- Build the object with exactly the schema's required fields and no extras.
- Validate it against `answer_template.json`: run
  `python3 scripts/validate_answer.py <answer.json> <answer_template.json>`, or apply the checklist
  in `references/output_contract.md`.
- Return the JSON object alone.

## Pick the archetype
- **Portfolio-mix review** — `scope_id` + quarter + teams + product area, compare actual mix to a
  target mix, gaps + rebalance action + exclusion flags → `references/task_archetypes.md` §A.
- **SLA-aging review** — as-of date + closed window + reliability/security categories, overdue
  primaries + aging/severity/escalation + duplicate clusters + breach rate → §B.
- **Release-readiness assessment** — `release_id` + milestones + blockers + dependencies, ship
  decision + completion + gating items + blocker causes + dependency chains + readiness score → §C.

## References
- `references/environment_and_endpoints.md` — endpoint catalog, auth, SQL query surface, record
  field names, status/severity vocabularies.
- `references/data_hygiene.md` — primary/duplicate, authoritative-vs-stale, cancelled/distractor
  exclusion, and the verified portfolio-category resolution table.
- `references/task_archetypes.md` — the three archetypes' computation playbooks (no task-specific
  values).
- `references/output_contract.md` — schema conformance, precision, ordering, validation checklist.
- `scripts/validate_answer.py` — validate a candidate answer against a JSON-Schema template
  (dependency-free).
