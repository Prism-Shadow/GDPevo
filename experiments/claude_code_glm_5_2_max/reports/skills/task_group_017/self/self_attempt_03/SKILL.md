---
name: investigation-review-hub-answer
description: Produce a single-JSON-object answer for an e-discovery / regulatory investigation review task served by the Investigation Review Hub (http://task-env:9017/). Use when a task asks for a production-readiness, retention/preservation, privilege/QC, or cross-system remediation dashboard keyed to a matter ID (MTR-*-GJ / MTR-*-SEC) and an answer_template.json defines the output schema.
---

# Investigation Review Hub — Structured-JSON Answer Skill

This skill produces the deliverable for tasks built on the shared **Investigation Review Hub**: a regulatory-investigation / e-discovery review system holding matter metadata, subpoena categories, production stats, custodian sources, review documents, privilege-log entries, QC findings, retention events, and remediation actions. The deliverable is always **exactly one JSON object** conforming to a task-supplied `answer_template.json`.

## What every task looks like

All tasks on this hub follow the same shape. Recognize it, then run the same playbook:

- A **prompt** naming a client, a matter ID (`MTR-<CLIENT>-GJ` or `MTR-<CLIENT>-SEC`), and a review workstream (rolling-production gap, retention/hold gap, production-readiness, privilege/QC, cross-system remediation dashboard).
- A **context/scope payload** (`request_context.json`, `review_scope.json`, or `matter_context.json`) carrying the matter ID, client, category labels/family, and the base URL.
- An **`answer_template.json`** that is the *authoritative* output contract: required top-level keys, per-item required keys, enum choices, ordering rules, and numeric precision. The template **never contains the answer**; it defines field names, types, ordering, and enums.
- The **base URL** `http://task-env:9017/`.

## Hard source constraints

- The hub endpoints are the **only** source of business evidence. Pull matter metadata, categories, production stats, custodian sources, documents, privilege log, QC findings, retention events, and remediation actions from the hub — never from local files.
- **Do not inspect** environment source files, database/seed files, generation manifests, setup scripts, hidden notes, standard-answer files, or any task answer/evaluation files. If you encounter such material in the working directory, stop and write `contamination_report.txt` instead of continuing.
- `environment_access.md` is **only for network access** (base URL + API key). Treat its contents as access config, not as evidence.
- Use **stable record IDs and category codes exactly as they appear in the hub** (matter IDs, source IDs, event IDs, finding IDs, entry IDs, action IDs, category codes). Never invent or reformat IDs.

## Hub access (see references/hub_endpoints.md for full detail)

Base URL: `http://task-env:9017/`
SQL endpoint auth header: `X-API-Key: review-key-017`

Nine resource endpoints return JSON with `{count, rows}` or a schema object:
`GET /api/schema`, `/api/matters`, `/api/subpoena-categories`, `/api/productions`, `/api/custodian-sources`, `/api/documents/search`, `/api/privilege-log`, `/api/qc-findings`, `/api/retention-events`, `/api/remediation-actions`.

Read-only SQL: `POST /api/query`.
**Request body uses the `sql` key** (NOT `query`), with a `params` array for placeholders:
`{"sql": "SELECT ... WHERE matter_id = ?", "params": ["MTR-..."]}`
Always send header `X-API-Key: review-key-017`. Response: `{"columns":[...], "row_count":N, "rows":[...], "truncated":bool}` — when `truncated` is true, page or narrow the query.

## Playbook (run in order)

1. **Read all task inputs first.** Read the prompt, the context/scope payload, and `answer_template.json` completely before querying anything. The template defines the contract you must satisfy.
2. **Orient on the data model.** `GET /api/schema` lists every table and its columns (see references/data_model.md). Confirm the exact column names you will select before writing SQL.
3. **Pin the matter.** Pull `/api/matters` (or query `matters WHERE matter_id = ?`) to confirm the matter exists, its hold_date, agency, and investigation type. The hold_date is the pivot for "pre-hold" vs "post-hold" retention loss judgments.
4. **Pull the category set for that matter.** `/api/subpoena-categories?matter_id=...` (or SQL). These category codes are the keys you join against in every list field. Most matters use single letters (A, B, C…); SEC matters may use a `SEC-*` family. Always echo the hub's exact codes.
5. **Gather evidence per workstream.** Query the relevant tables filtered by `matter_id`:
   - Production gaps / readiness → `production_stats` (produced/withheld/responsive counts, `zero_claim_reason`, status).
   - Retention & preservation gaps → `retention_events` (status, event_date vs hold_date, policy_section, retention_period_months, volume_count/unit) + `custodian_sources` (post_hold flag, status).
   - Privilege / QC → `privilege_entries` (doc_count, withheld_count, logged_count, issue_type, third_party) + `qc_findings` (issue_type, severity, affected_category) + `review_documents` (responsiveness, privilege_status, produced_status, issue_tags).
   - Remediation / actions → `remediation_actions` (action_type, priority, severity, owner, target_ref, due_days).
   - Personal-source / archive gaps → `custodian_sources` filtered by source_type (personal_phone, personal_messaging, personal_email, *_archive) and status (lost / not_collected / partial / collected).
6. **Map evidence to template fields.** For each finding/risk/issue/category row the template requires, anchor it on a **stable hub record ID** (`finding_id`, `event_id`, `source_id`, `entry_id`, `action_id`, `doc_id`). Populate `source_refs`/`record_refs`/`issue_refs`/`target_refs` with those IDs. Count fields (`document_count`, `withheld_count`, `logged_count`, `unlogged_count`, volume counts) come from the hub's integer columns; use `0` when a field does not apply.
7. **Derive metrics by aggregation, not guessing.** Every numeric metric in the `metrics` object is a count you compute from the hub rows for that matter (e.g. `unlogged_privilege_docs = Σ(withheld_count − logged_count)` over the selected privilege entries; `categories_with_open_gaps` = distinct category codes with open issues). Whole integers only.
8. **Classify with the template's enums — exactly.** Every status/severity/impact/action_type/owner/priority value must be a string from the template's `enums`/`enum_choices`/`enum_choices`. Map hub free-text to the closest enum; if nothing fits, the template usually exposes an `other` / `unknown` / `not_applicable` bucket — prefer the explicit `no_*` / `not_applicable` bucket over inventing a value.
9. **Order every list per `ordering_rules`.** Defaults: lists of records sort by their stable ID ascending; action/priority lists sort by `priority_rank`/`rank` ascending (1 = highest); category-code lists sort ascending and use the hub's exact casing. Apply before emitting.
10. **Emit one JSON object only.** No prose, no markdown fences, no trailing text. Top-level keys must be exactly the template's `required_top_level_keys`. Each list item must carry all of its `item_required_keys`. Booleans (e.g. `production_ready`, `rolling_production_ready`) are real JSON booleans, not strings.

## Cross-cutting judgment rules (distilled from the workstreams)

- **Pre-hold vs post-hold:** a retention loss with `event_date` on or before the matter `hold_date` (and a valid `policy_section`) is generally **policy-compliant / pre-hold** (low or no preservation risk, action `no_action_policy_loss`-style). A loss *after* the hold_date, or any loss of a source with no policy basis, is a **preservation failure** and drives disclosure/forensic-recovery actions. The `custodian_sources.post_hold` flag is the authoritative marker.
- **Privilege log completeness:** `withheld − logged = unlogged`. Withheld-but-unlogged docs are the `privilege_log_gap` / `withheld_unlogged` production impact and trigger `supplement_privilege_log`. `third_party = 1` entries tilt toward waiver assessment; miscoded privilege entries (over-designation, wrong basis) trigger `privilege_re_review`/`privilege_recode_and_log`.
- **Responsiveness miscoding:** documents flagged responsive that should be nonresponsive (or vice versa) appear in `review_documents.responsiveness` + `issue_tags` and in `qc_findings` with `issue_type` like `responsive_miscoding`. These drive `recode_and_produce`.
- **Zero-production claims:** a category with `produced_count = 0` and a `zero_claim_reason` must be tested against the evidence — if responsive docs exist for that category, the zero claim is contradicted (`not_ready_zero_claim_contradicted`-style status).
- **Available archives limit loss:** when a destroyed/lost source has a surviving archive of the same `source_type`/`affected_categories`, classify the category as `source_gap_with_archive_available` (not pure `preservation_loss`) and route the action to `search_archive`/`restore_from_backup`/`collect_archive`. Only call a loss irretrievable when no archive source covers those categories.
- **Personal sources:** personal_phone / personal_messaging / personal_email sources that are `not_collected` or `partial` are `personal_source_gap`; collect via `collect_personal_device` / `collect_signal_messages` / `collect_personal_email`.
- **Readiness boolean:** `production_ready` / `rolling_production_ready` is `true` only when no category has an open blocker; any critical/high open finding flips it to `false`.

## Output conventions (see references/output_conventions.md)

- Exactly one JSON object; no prose.
- Top-level keys = template's `required_top_level_keys`, no extras.
- Every list item includes all `item_required_keys`.
- Enums must match template strings character-for-character (including underscores and casing).
- All counts are whole integers; `0` (not `null`) when a count field is not applicable; use `null` only where the template explicitly allows it (e.g. dates, `third_party`, `policy_section`).
- Dates are `YYYY-MM-DD` strings.
- Sort all lists per `ordering_rules` before emitting.

## Pre-submit checklist

- [ ] Read prompt + context payload + full `answer_template.json`.
- [ ] Confirmed matter and category codes from the hub.
- [ ] Every record reference is a real hub ID, copied verbatim.
- [ ] Every enum value is from the template.
- [ ] Every list sorted per `ordering_rules`.
- [ ] Every count is a computed integer (0 where N/A).
- [ ] Top-level keys exactly match `required_top_level_keys`.
- [ ] Output is one bare JSON object, no prose/fences.
- [ ] No local env/db/manifest/answer files were read as evidence.
