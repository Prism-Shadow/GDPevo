---
name: investigation-review-hub-gap-analysis
description: >
  Produce a structured-JSON e-discovery gap / remediation dashboard for a legal
  investigation matter (grand jury or SEC/DOJ subpoena) by pulling matter-scoped
  evidence from the Investigation Review Hub API and mapping it onto a
  task-supplied answer_template.json. Use when a task asks for a production gap
  analysis, retention/litigation-hold gap review, cross-system remediation
  dashboard, or production-readiness review, and provides an answer_template.json
  plus a hub base URL and X-API-Key. Covers reading the contract, querying the
  hub, classifying material vs. non-material issues, computing privilege/QC
  metrics, and assembling one validated JSON object.
---

# Investigation Review Hub — production gap & remediation analysis

## What these tasks are

Outside counsel / legal-ops needs a **single structured JSON object** that turns
the state of one litigation matter into a gap-and-remediation deliverable:
material production gaps and defects, per-category coverage, retained/available
remediation sources, numeric privilege & QC metrics, and a prioritized action
plan with owners. The exact key names, enum vocabularies, metric list, and
ordering **change every task** — the only fixed input is the matter and the
`answer_template.json` you are handed. Never reuse another task's field names,
enum values, or numbers; derive them from *this* task's template and hub data.

The Investigation Review Hub is the **sole source of business evidence**. The
task's local payload (`request_context.json` / `review_scope.json` /
`matter_context.json`) supplies only context: `matter_id`, client, category
codes/labels, API config, cutoff. Do **not** read environment source files,
database/seed files, generated manifests, hidden notes, or any answer/evaluation
file — event and source evidence must come from the hub.

## Operating procedure

1. **Read the context payload** in `input/payloads/` — capture `matter_id`,
   client, category-code family, review cutoff, and any allowed/excluded-source
   notes. This tells you *which* matter and gives human-readable category labels.

2. **Read `input/payloads/answer_template.json` and treat it as the contract.**
   Extract, for this task specifically:
   - `required_top_level_keys` (the object's shape),
   - each list's `item_required_keys` and field types,
   - the `enums` / `enum_choices` (you MUST emit only these exact strings),
   - `ordering_rules` (how to sort each list), and
   - the `metrics` required keys with their precise definitions.
   The template *defines the schema; it never contains the answer.* See
   `references/output_contract.md` for the recurring 5-part archetype that these
   templates all instantiate under different names.

3. **Get network config from `environment_access.md`** (the only file to use for
   network access): the base URL (`GDPEVO_ENV_BASE_URL`), the `X-API-Key`
   header value, and the allowed endpoint list. Send the `X-API-Key` header on
   every request. Do not hardcode a base URL or key — read them each run.

4. **Pull matter-scoped evidence from the hub.** Confirm the matter via
   `GET /api/matters`, then read the evidence tables — always filtered to this
   `matter_id`. `GET` endpoints accept `?matter_id=<id>` (and other column
   filters) and return normalized arrays; `POST /api/query` runs read-only SQL
   (`{"sql": "..."}` → `{columns,row_count,rows,truncated}`) for joins and
   aggregation. Endpoint→table map, field semantics, and query recipes are in
   `references/hub_api.md`. Note `hold_date` from the matter — it is the pivot
   for retention classification.

5. **Classify each candidate into material findings vs. noise**, and map raw hub
   values to this template's enums, using `references/gap_classification.md`.
   Core judgments that recur:
   - **Pre-hold, policy-compliant destruction is NOT a preservation failure**
     (`event_date` < `hold_date` and within `retention_period_months`); only
     **post-hold loss** is spoliation to disclose.
   - Uncollected / partially collected personal or key sources = collection gap.
   - `retained` / available archives *limit irretrievable loss* for the
     categories they cover — list them as remediation sources.
   - Responsiveness miscoding → recode & produce; privilege **log gaps**
     (`withheld_count` > `logged_count`) → supplement log; **over-designation /
     miscoded privilege** → re-review/downgrade; **third-party** entries →
     waiver assessment; a zero-production claim contradicted by responsive docs
     → readiness blocker; `should_exist_missing` → locate missing record.
   - **Filter distractors:** routine QC (`metadata_gap`, `duplicate_overlay`),
     `issue_tags: routine`, and `*-NOISE-*` / sampling actions are not material
     unless the template's definitions pull them in.

6. **Compute metrics exactly as the template defines them**, as whole integers.
   Recurring identity: **`unlogged = withheld_count − logged_count`**. Honor
   scoping qualifiers in a metric's description (e.g. "from selected
   incomplete-log blockers only") rather than summing every row. Booleans like
   `production_ready`/`rolling_production_ready` are `true` only when no material
   blocker remains for any in-scope category.

7. **Use stable hub IDs verbatim** for every id/ref field — `event_id`,
   `source_id`, `finding_id`, `entry_id`, `action_id`, `doc_id`, and
   `category_code` exactly as returned. Never invent, renumber, or reformat IDs.
   Ref lists (`source_refs`, `issue_refs`, `blocking_refs`, `target_refs`,
   category sets) are sorted ascending.

8. **Build the action plan** from `remediation_actions` where they exist, mapping
   the hub's human-readable `owner` and `action_type` to the template's `owner`
   and `action_type` enums, and its `priority`/`severity` to the template's
   `priority` enum. Rank by severity/production impact with **1 = highest**; make
   each material finding traceable to an action and vice-versa.

9. **Assemble, order, and validate.** Include only material/non-complete items
   where the template scopes a list that way. Ensure every `required_top_level_key`
   is present, every `item_required_key` is present on every item (use `0` for
   N/A integers, `null` for N/A strings/dates), every enum value is legal, and
   every list obeys its `ordering_rules`. Cross-check that findings, category
   coverage, sources, metrics, and actions tell one consistent story.

10. **Output exactly one JSON object and nothing else** — no prose, no code
    fences, no trailing commentary.

## Guardrails
- Hub = evidence; payload = context/labels; nothing else is a source.
- The template is authoritative for names/enums/order/precision — re-read it per
  task; do not carry over vocabulary from a prior matter.
- Every hub read is filtered to the current `matter_id` (the hub holds many
  matters).
- Emit only enum strings that appear in *this* template; when unsure, pick the
  closest legal value and keep it consistent across sections.
