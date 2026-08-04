## Investigation Review Hub — Legal Ediscovery Gap Analysis & Remediation

Use this skill whenever the task requires structured gap analysis, remediation dashboards, production-readiness reviews, privilege audits, or retention assessments against a shared Investigation Review Hub API. The hub is the single source of record for matters, subpoena categories, productions, custodian sources, review documents, privilege logs, QC findings, retention events, and remediation candidates.

### Environment Setup

The hub runs at `<TASK_ENV_BASE_URL>`. Confirm the actual base URL from the task prompt or from `environment_access.md` / `input/payloads/matter_context.json`. All evidence must come from the hub endpoints — never inspect local environment source files, database files, generated manifests, setup scripts, or answer/evaluation files.

**Available GET endpoints:**
- `GET /` — root healthcheck
- `GET /api/schema` — database schema reference
- `GET /api/matters` — matter metadata
- `GET /api/subpoena-categories` — request/subpoena category definitions
- `GET /api/productions` — production status records
- `GET /api/custodian-sources` — custodian data sources
- `GET /api/documents/search` — review-document search
- `GET /api/privilege-log` — privilege-log entries
- `GET /api/qc-findings` — QC finding records
- `GET /api/retention-events` — retention/destruction events
- `GET /api/remediation-actions` — remediation action records

**POST endpoint (read-only SQL):**
- `POST /api/query`
- Required headers: `Content-Type: application/json`, `X-API-Key: review-key-017`
- Body: `{"sql": "<SELECT statement>", "params": ["<value>"]}`
- Use parameterized queries only. Do not construct SQL by string interpolation.

### Task Workflow

**1. Orient from the prompt and payloads.** Read `prompt.txt` and every file under `input/payloads/`. Identify:
- The matter ID, client name, and review type (gap analysis, remediation dashboard, production readiness, retention review, privilege audit).
- The answer template file (`answer_template.json`) and its required top-level keys, enums, ordering rules, and numeric precision rules.
- Any task-specific payloads (`request_context.json`, `review_scope.json`, `matter_context.json`) that provide category labels, scope details, or client-facing context.

**2. Load the answer schema.** The `answer_template.json` defines the output contract. Extract:
- `required_top_level_keys` — the keys that MUST appear in the JSON answer.
- `fields` / `item_required_keys` / `item_field_types` — the shape of each list or object.
- `enums` / `enum_choices` — the closed vocabulary for statuses, types, severities, actions, owners, and priorities.
- `ordering_rules` — sort order for each list (typically by ID, rank, or category code ascending).
- `numeric_precision` — whether fields are integer counts, whole days, etc.

**3. Query the hub for evidence.** For every investigation, systematically pull:
- `/api/matters` to confirm the matter and its metadata.
- `/api/subpoena-categories` to get the full category list, codes, and descriptions.
- `/api/custodian-sources` for source collection status, availability, and gaps.
- `/api/documents/search` for responsive/non-responsive coding and production status.
- `/api/privilege-log` for withheld documents, logged/unlogged counts, and third-party exposure.
- `/api/qc-findings` for miscoded documents, privilege errors, and responsiveness defects.
- `/api/retention-events` for pre-hold destruction, post-hold losses, auto-purges, and missing records.
- `/api/remediation-actions` for existing or proposed remediation steps.

Use `POST /api/query` for cross-entity joins, filtered lookups, or aggregate counts when GET endpoints alone are insufficient. Explore `/api/schema` first if table structures are unfamiliar.

**4. Cross-reference findings to categories.** Map every material defect, gap, or risk to the subpoena/request categories it affects. A single source loss can impact multiple categories; a single category can have multiple distinct issues.

**5. Build the answer JSON.** Construct the JSON object one top-level key at a time, following the answer template exactly:
- Use stable hub record IDs (matter IDs, document IDs, source IDs, event IDs, QC finding IDs, action IDs) exactly as returned by the API.
- For lists, apply the ordering rules from `ordering_rules` (e.g., sort by `finding_id` ascending, `category_code` ascending, `priority_rank` ascending).
- For enums, use only values listed in the template's enum definitions.
- For numeric fields, output whole integers as specified.
- Every finding/issue/risk must include the record refs that support it.
- Every category status must reference the hub records that justify the status.
- Metrics must be exact counts derived from hub data — not estimates.
- Action plans must be prioritized with `P0` for critical/urgent items, `P1` for high, etc.

**6. Validate before output.** Before returning the answer:
- Confirm every required top-level key is present.
- Confirm every list item has all required sub-keys.
- Confirm every enum value matches the allowed set.
- Confirm all IDs come from the hub (no fabricated identifiers).
- Confirm ordering rules are satisfied.
- Confirm counts are whole integers and consistent (e.g., `logged_count + unlogged_count = withheld_count` where applicable).

### Common Task Archetypes

**Gap Analysis** — Identify what is missing, lost, uncollected, or miscoded. Output critical findings, category statuses, metrics, and priority actions. Typical top-level keys: `matter_id`, `critical_findings`, `category_statuses`, `metrics`, `priority_actions`.

**Remediation Dashboard** — Cross-system view of all material risks with category coverage and retained/available sources. Typical top-level keys: `matter_id`, `top_risks`, `category_coverage`, `retained_or_available_sources`, `metrics`, `action_plan`.

**Production Readiness** — Assess whether each request category is ready for production. Output readiness statuses per category, an issue ledger, privilege corrections, metrics, and a priority action list. Typical top-level keys: `matter_id`, `readiness_statuses`, `issue_ledger`, `privilege_corrections`, `metrics`, `priority_actions`.

**Retention & Hold Review** — Analyze retention events, communication-system gaps, and available archives. Typical top-level keys: `matter_id`, `retention_events`, `communication_gaps`, `available_archives`, `metrics`, `recommended_actions`.

### Common Enum Vocabularies

These appear across answer templates. Always use the exact enum sets from the current task's `answer_template.json` — the lists below are illustrative:

- **issue_type**: `preservation_failure`, `collection_gap`, `responsiveness_miscode`, `privilege_log_gap`, `retention_loss`, `privilege_waiver`, `over_designation`, `miscoded_privilege`, `post_hold_loss`, `personal_source_gap`, `third_party_waiver`, `privilege_miscoding`, `other`
- **severity / risk_level**: `critical`, `high`, `medium`, `low`
- **status types**: `open`, `confirmed`, `protocol_noncompliant`, `needs_recode`, `waived`, `incomplete_log`, `remediation_pending`, `no_gap`, `ready`, `not_ready_multiple_blockers`, `not_ready_privilege_log_incomplete`, `policy_destroyed_pre_hold`, `post_hold_loss`, `auto_purged`, `active_system_loss`, `should_exist_missing`, `available_archive`, `preserved_available`, `collection_pending`, `not_applicable`
- **production_impact**: `underproduced`, `not_produced`, `withheld_unlogged`, `source_missing`, `source_lost`, `recode_needed`, `privilege_exposure`, `source_available`, `multiple_impacts`, `no_production_impact`
- **source_status**: `lost`, `not_collected`, `partial`, `collected`, `pending`, `destroyed`, `not_applicable`
- **action_type**: `disclose_to_government`, `disclose_preservation_issue`, `forensic_recovery`, `collect_source`, `collect_personal_device`, `recode_and_produce`, `supplement_privilege_log`, `quality_control_review`, `privilege_re_review`, `privilege_recode_and_log`, `waiver_assessment_and_disclosure`, `qc_remediation`, `search_archive`, `collect_archive`, `restore_from_backup`, `locate_missing_record`, `custodian_followup`, `document_system_gap`, `escalate_to_counsel`, `investigate`, `no_action`, `no_action_policy_loss`
- **owner**: `outside_counsel`, `client_legal`, `client_it`, `ediscovery_vendor`, `review_vendor`, `review_qc`, `privilege_team`, `privilege_counsel`, `records_vendor`, `records_management`, `investigation_team`, `forensics`, `litigation_counsel`, `it_messaging`, `compliance_audit`, `legal_operations`
- **priority**: `P0`, `P1`, `P2`, `P3`

### Rules & Constraints

- **Source-of-record**: The shared hub endpoints are authoritative. Do not use local environment files, database files, generated data, hidden manifests, or task answer files as evidence.
- **Stable IDs**: Record identifiers (matter, source, event, document, QC finding, action, privilege record) must match the hub exactly. Do not invent, abbreviate, or transform IDs.
- **Parameterized queries only**: When using `POST /api/query`, always use `?` placeholders and the `params` array. Never embed user-supplied or task-derived values directly into SQL strings.
- **JSON-only output**: Return exactly one JSON object — no surrounding text, markdown fences, or commentary unless the answer template explicitly allows it.
- **Schema conformance**: Every required key must be present. Every enum must be from the allowed set. Every list must be sorted per ordering rules. Every count must be a whole integer.
- **Factual and normalized**: Report only what the hub data supports. Do not extrapolate, estimate narratively, or add qualitative commentary beyond the structured fields.
- **Priority ordering**: `P0` is the most urgent (preservation failures, post-hold losses requiring immediate disclosure). `P1` is high-priority remediation. `P2`/`P3` are lower-tier follow-ups.

### Quick-Start Checklist

- [ ] Read `prompt.txt` and every payload file in `input/payloads/`.
- [ ] Study `answer_template.json` — note required keys, enums, ordering rules, precision rules.
- [ ] Confirmed `<TASK_ENV_BASE_URL>` and API key header.
- [ ] Pulled matter metadata, categories, sources, documents, privilege log, QC findings, retention events, and remediation actions from the hub.
- [ ] Mapped every finding to affected categories with supporting record refs.
- [ ] Computed exact integer metrics from hub data.
- [ ] Built action plan sorted by priority, with owners, target refs, and affected categories.
- [ ] Validated JSON against answer template (keys, enums, ordering, numeric precision, ID provenance).
