---
name: portfolio-env-analytics
description: Produce a schema-validated JSON answer for portfolio-mix, SLA-aging/breach, or release-readiness tasks run against the shared work-item environment (work items, mix targets, SLA policy, releases, milestones, blockers, dependencies). Use when a task points at <TASK_ENV_BASE_URL> / environment_access.md and asks for a single JSON object matching an answer_template.json. Covers scope filtering, primary-vs-duplicate/cancelled/distractor separation, authoritative-field-only data quality, portfolio-category classification, derived metrics with fixed rounding, and stable ordering.
---

# Portfolio Environment Analytics

Turn a scoped analytics prompt over the shared portfolio environment into a single
JSON object that **exactly matches the task's `answer_template.json`**. Three task
families share one procedure: portfolio mix, SLA aging/breach, and release readiness.

## When to use
- The prompt references `<TASK_ENV_BASE_URL>` or `environment_access.md`, **and**
- asks you to "return a single JSON object matching `input/payloads/answer_template.json`"
  (no prose outside the JSON), **and**
- the work is a portfolio-mix readout, an SLA / reliability / security aging or breach
  audit, or a release-readiness assessment.

## Entry procedure (run in order)

1. **Read the contract.** Read `train_tasks/<task>/input/prompt.txt` for scope and
   deliverables, then `train_tasks/<task>/input/payloads/answer_template.json`. The
   template **is** the contract: its `required`, `additionalProperties:false`, `const`,
   `enum`, `minItems`/`maxItems`, and `description` fields encode the exact shape,
   ordering, and rounding. Never add a forbidden field; never omit a required one; pull
   every controlled vocabulary (action/rationale codes, `ship_decision`, category enums)
   from the template's enums — never invent values.

2. **Resolve environment access from `environment_access.md` — network access comes ONLY
   from this file.** Re-read it each run; do not hardcode the base URL or token. The base
   URL line (e.g. `GDPEVO_ENV_BASE_URL=…`) is `<TASK_ENV_BASE_URL>`; the `X-Env-Token`
   value is the auth header. Call only the allowed endpoints listed there. See
   `references/env_access.md` for endpoint shapes and the restricted SQL query endpoint.

3. **Gather data, filtering by scope.** Scope fields come from the prompt: teams, quarter,
   product_area, scope_id, as-of date, recent-closed window, release_id. Prefer the
   restricted `POST /api/query` (SELECT-only SQL over the 7 tables) to filter/aggregate
   server-side; fall back to the GET list endpoints + client filter. Pull every table the
   deliverable needs (work_items, mix_targets, sla_policy, releases, milestones, blockers,
   dependencies).

4. **Apply data-quality rules before any counting.** See `references/data_quality.md`.
   In short: use authoritative `status` (never `mirror_status`); ignore `legacy_category`;
   treat `Duplicate`/`duplicate_of` and `Cancelled` as non-primary; classify each item
   into exactly one portfolio category {NewFeature, TechDebt, Reliability, Security} via
   the conventions in the reference, never via `legacy_category`. Surface every excluded
   record in the template's exclusion/cluster fields — never drop a record silently.

5. **Compute derived metrics with the template's precision.** Percentages → 1 decimal
   place (percentage points; `mix_targets` fractions are 0–1, multiply by 100). Rates
   (breach / sla_breach / readiness) → exactly 3 decimals. Counts are item counts, not
   story points. Formulas and per-family field maps live in `references/metrics_ordering.md`
   and `references/task_families.md`.

6. **Order everything stably.** ID lists ascending/lexicographically (or closed_at asc then
   id asc where the template says so); teams alphabetical; categories in fixed order
   NewFeature, TechDebt, Reliability, Security; milestones by milestone_id asc; duplicate
   clusters by primary_id; dependency chains lexicographically by full path. Use each id once.

7. **Validate and emit.** Run `python3 skill/validate_answer.py <template.json> <answer.json>`
   (or any JSON-Schema validator). Fix every violation. Then emit **exactly one JSON object**
   — no prose, no markdown fences.

## Cross-cutting rules (always apply)
- **The template is truth.** Match its shape exactly; pull controlled vocabularies from its enums.
- **Authoritative fields only.** `mirror_status` and `legacy_category` are distractors; release truth lives in the release/milestone/blocker/dependency records.
- **Primary work is counted; duplicates/cancellations/distractors are reported, not counted.**
- **One JSON object, matching the template, nothing else.**

## Supporting files (in this package)
- `references/env_access.md` — endpoints, query SQL semantics, work_items field list.
- `references/data_quality.md` — authoritative vs mirror/legacy, primary vs duplicate/cancelled/distractor, category classification convention.
- `references/metrics_ordering.md` — formulas, rounding, ordering rules.
- `references/task_families.md` — per-family field checklists (mix / SLA / release).
- `validate_answer.py` — generic answer-vs-template JSON-Schema validator.
