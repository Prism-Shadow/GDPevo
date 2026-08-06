---
name: investigation-review-hub-analysis
description: Produce a structured-JSON gap / retention / remediation / production-readiness analysis for a legal-discovery matter by querying the shared Investigation Review Hub. Use whenever a task points at the Review Hub at http://task-env:9017/ and asks for a single JSON object conforming to a per-task answer_template (critical-findings gap analysis, retention & litigation-hold review, cross-system remediation dashboard, or production-readiness review).
---

# Investigation Review Hub Analysis

This skill turns a matter-level legal-discovery review request into a single JSON object that conforms exactly to the task's `answer_template.json`. The Review Hub at `http://task-env:9017/` is the **only** source of business evidence. The answer template is the **only** source of the output schema. Everything else is method.

Work the six phases below in order. Reference files live alongside this entry file in `skill/reference/`.

## 0. Source-of-record discipline (non-negotiable)

- The hub base URL and allowed endpoints are defined in `environment_access.md`. Read that file for network access and **nothing else** — do not inspect local environment source files, database files, seeds, manifests, setup scripts, generated data, hidden notes, or any task answer / evaluation files.
- If you find any material in the working directory that is not the expected `prompt.txt`, the one context payload, and `answer_template.json` (or `environment_access.md` at the root), **stop** and write `contamination_report.txt` describing the unexpected file(s) instead of producing an answer.
- The read-only SQL endpoint is `POST /api/query` with header `X-API-Key: review-key-017`. Use the hub endpoints / SQL for all business evidence. Never fabricate record IDs or counts.

## 1. Gather and lock the contract

Read, in this order, the task's `input/` directory:

1. `prompt.txt` — the matter, the deliverable type, and the focus (gaps, retention, remediation, readiness).
2. The single context payload (`request_context.json`, `review_scope.json`, or `matter_context.json`) — confirms `matter_id`, client, category labels, and source constraints.
3. `payloads/answer_template.json` — **this is the schema contract.**

From the answer template, extract and hold these for the rest of the run:

- `required_top_level_keys` — the exact top-level object keys the answer must contain.
- `ordering_rules` — how each list must be sorted (almost always ascending by the record-ID field, and `priority_rank` / `rank` ascending with 1 = highest).
- `enums` (a.k.a. `enum_choices`) — the closed vocabularies. Every status, severity, issue type, action type, owner, and priority you emit **must** be drawn from these lists; map hub free-text onto them.
- `fields` / `schema` — required per-item keys and their types. Note which counts are integers, which fields are `null`-able, and which lists must be sorted ascending.
- `numeric_precision` — whole integers everywhere; no floats.

The four deliverable families you will see:

| Family | Signature top-level keys | Root record type |
|---|---|---|
| Gap analysis | `critical_findings`, `category_statuses`, `metrics`, `priority_actions` | qc_findings / custodian_sources |
| Retention & hold review | `retention_events`, `communication_gaps`, `available_archives`, `metrics`, `recommended_actions` | retention_events / custodian_sources |
| Cross-system remediation dashboard | `top_risks`, `category_coverage`, `retained_or_available_sources`, `metrics`, `action_plan` | mixed across all tables |
| Production-readiness review | `readiness_statuses`, `issue_ledger`, `privilege_corrections`, `metrics`, `priority_actions` | privilege_entries / qc_findings |

All four share the same mechanics; only the wrapping keys and some enum names differ. Treat the template as authoritative over any generalization here.

## 2. Pull all hub evidence for the matter

Resolve `matter_id` from the payload/prompt. Then pull **every** relevant table filtered to that matter, so classification in later phases sees the complete picture. See `reference/hub_endpoints.md` for exact calls.

Endpoints (all GET unless noted, all accept a `matter_id` filter):

- `/api/matters` — matter metadata, `hold_date`, `issued_date`, agency, status.
- `/api/subpoena-categories` — the request category codes + titles for the matter (the universe of `category_code` values).
- `/api/productions` — per-batch production stats: produced/withheld/responsive/nonresponsive counts, `status`, `zero_claim_reason`.
- `/api/custodian-sources` — custodian/source records: `source_id`, `source_type`, `status`, `post_hold` flag, `category_impacts`, `issue_tags`.
- `/api/documents/search` — individual review documents: coding (`responsiveness`, `privilege_status`, `produced_status`), `issue_tags`.
- `/api/privilege-log` — privilege entries: `entry_id`, `doc_count`, `withheld_count`, `logged_count`, `issue_type`, `third_party` flag.
- `/api/qc-findings` — QC defect findings: `finding_id`, `issue_type`, `doc_count`, `affected_category`, `severity`.
- `/api/retention-events` — retention/preservation events: `event_id`, `status`, `hold_date`, `policy_section`, `volume_count`/`volume_unit`, `affected_categories`.
- `/api/remediation-actions` — existing proposed actions: `action_id`, `action_type`, `priority`, `owner`, `target_ref`, `due_days`.
- `POST /api/query` — SQL over the same tables (see `reference/hub_schema.md`); use it to aggregate counts that the list endpoints don't pre-compute.

Pull all of these before classifying, even if the deliverable only names a subset — dashboards and gap analyses cross-reference retention, privilege, QC, and sources together.

## 3. Classify evidence into the template's units

Map hub records to the template's enumerated values. Detailed mapping logic is in `reference/classification_rules.md`; the essential rules:

- **Issue type** — read the hub `issue_type` / `issue_tags` / `status` and map to the template's `issue_type` enum. Post-hold destruction → `post_hold_loss` / `retention_loss` / `preservation_failure`. Pre-hold policy destruction → `policy_destroyed_pre_hold`. Personal device/email not collected → `personal_source_gap` / `collection_gap`. Withheld-but-unlogged → `privilege_log_gap`. Wrong responsiveness tag → `responsiveness_miscode` / `responsive_miscoding`. Third-party communication withheld → `third_party_waiver`.
- **Severity / risk_level** — take from the hub record where present; otherwise infer from production impact and post-hold timing (post-hold loss of a produced category = critical/high).
- **Status** — map hub `status` to the template's status enum. Distinguish *open* / *remediation_pending* / *protocol_noncompliant* / *ready* / *closed* / *no_gap* carefully; they drive whether the item appears in the answer at all.
- **Source status** — `lost`/`destroyed`, `not_collected`, `partial`, `collected`/`preserved_available`, `pending`/`collection_pending`, `available_archive`, `not_applicable`. Only items whose source status indicates a gap or a remediation path belong in the answer.
- **Production impact** — derive from source status + coding: lost source → `source_lost`; missing/uncollected → `source_missing`/`not_produced`; withheld unlogged → `withheld_unlogged`; wrong coding → `recode_needed`; archive usable → `source_available` / `no_production_impact`.
- **Pre-hold vs post-hold** is the single most important distinction: pre-hold policy-compliant destruction is `no_action` / `low` risk and is reported as a fact, **not** a remediation priority; post-hold loss is a preservation risk requiring disclosure/collection. Use the matter `hold_date` and each event's `event_date` / `post_hold` flag to decide.

When a finding is anchored to one hub record, use that record's stable ID (`finding_id`, `event_id`, `source_id`, `entry_id`, `doc_id`, `action_id`, `batch_id`) as the `finding_id` / `risk_id` / `issue_id` / `correction_id` / `event_id` / `source_id` in the answer. Collect every supporting hub ID into `source_refs` / `record_refs` / `blocking_refs` / `target_refs`.

## 4. Roll up categories and compute metrics

- **Category statuses** — for each subpoena category code, aggregate the findings/events/sources that touch it and assign one `category_status` (complete / incomplete / collection_gap / preservation_risk / responsiveness_gap / privilege_log_gap / withholding_gap / source_gap_with_archive_available / no_open_gap …). Include a category only if it has a material non-complete status **unless** the template's description demands full coverage. Attach `source_refs` / `issue_refs` and a `recommended_action`.
- **Metrics** — compute strictly from hub records, whole integers. The recurring ones:
  - `unlogged_privilege_docs` = Σ(`withheld_count` − `logged_count`) over the privilege entries flagged as incomplete-log blockers.
  - `withheld_privileged_doc_count` / `logged_privilege_doc_count` = Σ over the same selected blockers.
  - `miscoded_responsive_doc_count` = count of documents/findings tagged as responsiveness miscoding.
  - `lost_personal_device_count` / `uncollected_*_source_count` / `personal_email_gap_source_count` = count of source records with the matching status/type.
  - `categories_with_open_gaps` / `categories_with_open_risk` = unique category codes touched by an open finding/event.
  - `post_hold_loss_event_count`, `pre_hold_policy_destroyed_event_count`, `available_archive_count`, `missing_required_record_count` = counts of the corresponding retention/source records.
  - `*_ready` / `production_ready` / `rolling_production_ready` = boolean: true only when **no** open critical/high blocker remains.
  - Where a template restricts a count to "selected incomplete-log blockers only," apply that filter rather than summing all entries.
- Verify each metric against the underlying record list a second way (e.g. SQL `COUNT` / `SUM`) before emitting; off-by-one and wrong-filter are the common failure modes.

## 5. Build the prioritized action plan

- One action per material remediation need, keyed by a stable `action_id` / `rank`, sorted by `priority_rank` / `rank` ascending (1 = highest).
- Map each action to the template's `action_type` and `owner` enums. Typical mapping: post-hold loss of a produced category → `disclose_to_government` / `disclose_preservation_issue` owned by outside/privilege counsel; uncollected personal source → `collect_source` / `collect_personal_device` owned by forensics / client_it; archive available → `search_archive` / `restore_from_backup` owned by ediscovery_vendor; unlogged privilege → `supplement_privilege_log` owned by privilege_team; miscoding → `recode_and_produce` owned by review_qc; third-party waiver → `waiver_assessment_and_disclosure` owned by privilege_counsel.
- Assign `priority` (P0–P3) by severity × production impact: P0 for post-hold loss / waiver on produced categories; P1 for unlogged privilege on withheld docs and uncollected personal sources; P2 for miscoding and missing-record items; P3 / `monitor_only` / `no_action` for pre-hold policy losses.
- `target_refs` and `category_impacts` must list the hub record IDs and category codes the action addresses, sorted ascending.

## 6. Emit exactly one JSON object

- Output **only** the JSON object — no prose, no markdown fences, no trailing commentary. The template's `output_rule` usually says so explicitly.
- Include exactly the `required_top_level_keys`, no extras.
- Every list sorted per `ordering_rules`; every ID/`*_refs` list sorted ascending; every category-code list sorted ascending (uppercase).
- Every enum value spelled exactly as in the template's enum lists (snake_case, no synonyms).
- All counts whole integers; use `0` where a count is not applicable (per template field notes); use `null` only where the template permits it (dates, `third_party`, `policy_section`, etc.).
- Use hub stable IDs verbatim — never invent, rename, or renumber them.
- Final self-check before finishing: re-read the template's required-keys and enum lists and confirm every field is present, correctly typed, and enum-conformant; re-confirm every sort order.

## When to use which reference file

- `reference/hub_endpoints.md` — exact endpoint URLs, query params, SQL header, and response shapes (use while pulling evidence in phase 2).
- `reference/hub_schema.md` — table/column reference for mapping hub fields to template fields and for writing SQL aggregates (phases 2 and 4).
- `reference/classification_rules.md` — the detailed mapping tables for issue types, statuses, source statuses, production impacts, retention pre/post-hold logic, privilege-log math, and priority assignment (phases 3 and 5).
- `reference/output_contract.md` — the JSON emission checklist and the common failure modes to avoid (phase 6).

These references describe the hub and the method generically; they contain **no** matter-specific answer values. Apply them to whatever `matter_id` and `answer_template.json` the current task provides.
