---
name: investigation-review-hub-analysis
description: Produces a structured-JSON gap / remediation / readiness analysis for a legal or regulatory matter whose source of record is the shared Investigation Review Hub (a read-only HTTP API). Use when a task asks for a production-gap, retention/preservation, privilege/QC, or cross-system remediation dashboard returned as a single JSON object conforming to a task-provided answer template. Reads evidence only from the live hub over the network plus the task-local payload; never inspects environment source/database/manifest/answer files.
---

# Investigation Review Hub Analysis

This skill solves a family of tasks that share one shape: a legal/regulatory matter
(grand jury, SEC, DOJ antitrust, environmental, etc.) must be analyzed into a
**single JSON object** that conforms to a task-provided `answer_template.json`. All
business evidence comes from a shared, read-only **Investigation Review Hub** reached
over the network. The deliverable always identifies material gaps/defects/risks, the
affected request categories, stable hub record IDs, numeric metrics, and a prioritized
action plan with owners.

## 0. Source-of-record discipline (non-negotiable)

These rules appear in every task prompt and must be enforced first.

- **Reach the environment through `environment_access.md` only.** It gives the base URL,
  the read-only SQL header (`X-API-Key`), and the allowed endpoint list. Treat it as the
  sole source of network coordinates. Do not invent URLs or keys.
- **The hub over the network is the source of record for all evidence.** Every record ID,
  count, date, category code, custodian, and status in the answer must be traceable to a
  hub endpoint response.
- **The task-local payload is context + contract only.** Files under
  `input/payloads/` provide: (a) `answer_template.json` — the output schema/enums/ordering,
  and (b) a context/scope file (`request_context.json`, `review_scope.json`,
  `matter_context.json`, etc.) giving the matter ID, client, agency, and request-category
  labels. Use these for the matter ID and category *labels* only — never as evidence.
- **Forbidden sources:** environment source code, database/seed files, generation
  manifests, setup scripts, hidden notes, and **any task answer or evaluation files**. If
  you encounter unexpected material in the work directory, stop and write
  `contamination_report.txt` instead of proceeding.
- **No prose in the final answer.** Return exactly one JSON object. No wrapper, no
  commentary, no markdown fences.

## 1. Read the contract first

Before touching the hub, fully load the output contract from
`input/payloads/answer_template.json`. Extract and hold in working memory:

- `required_top_level_keys` — the exact top-level shape of the answer object.
- `item_required_keys` / `item_fields` for each list — every field you must populate per item.
- `enums` / `enum_choices` — the closed set of allowed values for each coded field.
  **Only values from these sets are legal.** Map hub statuses to these enums; never
  invent enum values.
- `ordering_rules` — how each list must be sorted (almost always ascending by a stable
  ID or by `priority_rank`/`rank` with 1 = highest; category code lists sorted ascending
  within each item).
- `numeric_precision` — counts are whole integers; `0` when a count is not applicable
  (do not use `null` for counts unless the field type explicitly allows null).

The template defines the schema only — it never contains the answer. Do not copy values
from it.

## 2. Read the context payload

From the context/scope file, capture: `matter_id`, client, agency, review type/workstream,
and the **category code family** used by this matter (the codes returned by the hub's
subpoena-categories endpoint — e.g. single letters, `R`-prefixed, or `SEC`-prefixed codes).
Use the matter's category code family consistently; copy codes verbatim from the hub.

## 3. Confirm the hub is reachable

From `environment_access.md`, take the base URL and the `X-API-Key` value. Issue
`GET /api/schema` to confirm connectivity and learn the table/column model (see
`references/hub_data_model.md`). If the hub is unreachable, stop and report the failure
rather than fabricating data.

## 4. Gather evidence by endpoint

Query the matter's records across the allowed endpoints. The hub data model (9 tables,
one per evidence endpoint) is documented in `references/hub_data_model.md`. For each
endpoint, filter to the target `matter_id` and extract what the contract needs:

- `GET /api/matters` — confirm the matter, `hold_date`, agency, investigation type.
- `GET /api/subpoena-categories` — the universe of request category codes + titles for
  this matter. Every `category_impacts` / `affected_categories` value must come from here.
- `GET /api/productions` — per-batch, per-category production stats: produced / withheld /
  responsive / nonresponsive counts, `status`, and `zero_claim_reason` (a non-null reason
  contradicting a zero produced/responsive claim is a responsiveness defect).
- `GET /api/custodian-sources` — custodian sources with `status`, `post_hold` flag,
  `source_type`, `category_impacts`, `issue_tags`. Lost / not-collected / partial sources
  anchor preservation and collection findings.
- `GET /api/documents/search` — review documents with `responsiveness`, `privilege_status`,
  `produced_status`, `issue_tags`. Miscoded responsive docs and zero-claim contradictions
  live here.
- `GET /api/privilege-log` — privilege entries: `doc_count`, `withheld_count`,
  `logged_count`, `issue_type`, `third_party` flag. This drives withheld/logged/unlogged
  metrics, log gaps, waivers, and over-designation.
- `GET /api/qc-findings` — QC findings with `issue_type`, `severity`, `affected_category`,
  `source_ref`, `doc_count`. Anchors responsiveness miscodes and privilege miscodes.
- `GET /api/retention-events` — retention events with `status`, `event_date` vs `hold_date`,
  `policy_section`, `volume_count`/`volume_unit`, `affected_categories`. Drives the
  retention/preservation analysis (pre-hold policy loss vs post-hold loss vs active system
  loss vs auto-purge vs should-exist-missing vs available archive).
- `GET /api/remediation-actions` — candidate remediation actions with `action_type`,
  `priority`, `severity`, `owner`, `target_ref`, `due_days`. Feeds the action plan.
- `POST /api/query` (SQL, with the `X-API-Key` header value taken from
  `environment_access.md`) — use for aggregate counts and joins when the REST lists are
  large or a metric needs a count across tables. Prefer REST for per-record detail; use SQL
  for rollups. Always send the header; the endpoint is read-only.

When a field is encoded as a delimited string in the hub (e.g. `category_impacts`,
`affected_categories`, `issue_tags`, `topic_tags`), split on the hub's delimiter and
normalize to the contract's list form.

## 5. Cross-reference into findings

Build one finding/risk/issue object per material gap or defect, anchored on a **stable hub
record ID** (use the record that primarily anchors the finding as the `finding_id` /
`risk_id` / `issue_id`; list every supporting record ID in `source_refs` / `record_refs`,
sorted ascending). For each finding determine, from hub evidence:

- `issue_type` — what kind of gap (preservation failure, collection gap, retention loss,
  responsiveness miscode, privilege log gap, privilege waiver/miscoding/over-designation,
  missing required record, etc.), mapped to the contract's enum.
- `severity` / `risk_level` — from the hub's severity/risk field, mapped to the enum.
- `status` / `finding_status` — from the hub record's lifecycle state, mapped to the enum.
- `source_status` — lost / not_collected / partial / collected / destroyed / available, etc.
- `production_impact` — what the gap does to production (source_lost, source_missing,
  not_produced, underproduced, withheld_unlogged, privilege_exposure, recode_needed, etc.).
- `category_impacts` — every category code this finding touches, sorted ascending.
- counts (`document_count`, `withheld_count`, `logged_count`, `unlogged_count`,
  `volume_count`/`volume_unit`) — pulled from the hub record; `0` when not applicable.

Classification heuristics and the privilege/waiver/QC decision rules are in
`references/classification_heuristics.md`. Apply them generically — never hard-code a
specific matter's values.

## 6. Roll up category coverage

For each request category with a material non-complete status, emit a category-status
object: the category code, a rolled-up `status` (from the worst open finding for that
category), the rolled-up `production_impact`, the list of supporting record IDs
(`source_refs` / `issue_refs` / `blocking_refs`, sorted ascending), the recommended
action, and (where the contract asks) an `open_issue_count`. Omit categories with no open
gap unless the contract requires a full enumeration.

## 7. Compute metrics

Compute every key in the template's `metrics` object from hub evidence, not from the
findings list alone — re-derive from the source records to avoid drift. Common rules:

- `unlogged` = `withheld` − `logged` for the selected privilege blockers (use `0` if
  negative or not applicable).
- Count sources/events/documents by their hub status/type, filtered to this matter.
- `categories_with_open_gaps` / `categories_with_open_risk` = the distinct sorted set of
  category codes touched by any open finding.
- Booleans like `rolling_production_ready` / `production_ready` are `false` if **any**
  P0/critical/open blocker exists; `true` only when no open blocker remains.
- Whole integers only; `0` when a metric's source set is empty.

See `references/classification_heuristics.md` for the per-metric derivation notes.

## 8. Build the prioritized action plan

Emit one action object per remediation action, ranked by priority (`priority_rank` / `rank`,
1 = highest). Rank order: disclose-to-government / preservation-disclosure and forensic
recovery of lost sources first (P0/critical), then privilege waivers and log supplements,
then recode-and-produce and QC remediation, then collection of not-collected sources and
archive searches, then documentation/monitoring of policy-compliant losses last. Each
action carries: a stable `action_id`, `priority` (P0–P3), `action_type` and `owner` from
the contract enums, `target_refs` (hub record IDs the action targets, sorted ascending),
`category_impacts` (sorted ascending), and `due_days` where the contract asks for it.
Map owners and action types to the contract's enums exactly.

## 9. Assemble, order, and validate

1. Build the single top-level JSON object with exactly the `required_top_level_keys`.
2. Apply every `ordering_rule`: sort each list by its specified key ascending; sort every
   category-code list ascending within each item; sort every record-ID list ascending.
3. Validate against the contract before emitting (see
   `references/validation_checklist.md`):
   - All top-level keys present and no extras (unless the contract allows extras).
   - Every list item has all `item_required_keys`.
   - Every coded field value is in the corresponding enum set.
   - Every ID/category list is sorted ascending.
   - All counts are whole integers; nulls only where the field type permits.
   - Metrics re-derived from source match the values in the findings.
4. Emit **only** the JSON object. No prose, no fences, no trailing text.

## 10. What this skill never does

- Does not copy specific record IDs, counts, dates, category codes, custodian names, or
  action IDs from any train answer or evaluation file. All values are derived live from
  the hub for the matter under analysis.
- Does not read environment source/database/manifest files.
- Does not emit narrative, explanations, or partial answers.
- Does not proceed if the work directory contains unexpected material — it stops and writes
  `contamination_report.txt`.

## References

- `references/hub_data_model.md` — the 9 hub tables and columns (grounded in `GET /api/schema`).
- `references/classification_heuristics.md` — generic rules for mapping hub records to
  contract enums and for deriving metrics.
- `references/validation_checklist.md` — the pre-emit validation checklist.
