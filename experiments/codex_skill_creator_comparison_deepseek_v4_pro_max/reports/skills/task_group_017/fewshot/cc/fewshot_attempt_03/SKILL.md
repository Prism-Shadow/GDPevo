---
name: investigation-hub
description: Produces structured JSON analysis for legal investigation matters by querying an Investigation Review Hub API. Use this skill whenever the task mentions matter IDs like MTR-*, subpoena categories, production gaps, privilege logs, retention events, QC findings, custodian sources, remediation actions, grand jury or SEC investigations, or asks for any kind of gap analysis, readiness review, or remediation dashboard from a review hub. Even if the task only mentions a "hub" or "review endpoint" without full terminology, consult this skill.
---

# Investigation Review Hub Analyst

Use this skill to produce structured JSON analyses of investigation matters from a shared Investigation Review Hub. The hub is a read-only REST API that holds matter metadata, subpoena categories, production statistics, custodian sources, review documents, privilege entries, QC findings, retention events, and remediation actions.

## Quick start

Every task provides a base URL through a placeholder like `<TASK_ENV_BASE_URL>`. Substitute it with the actual value from the task environment before issuing any request.

1. Fetch the hub schema to confirm available tables and column names:
   ```
   GET {BASE_URL}/api/schema
   ```
2. Fetch the matter record to confirm the matter ID:
   ```
   GET {BASE_URL}/api/matters
   ```
   Filter by `matter_id` from the task prompt or payload.

3. Identify which hub endpoints the task needs by matching the answer template keys and the task description to the hub tables. Read the reference [Hub Data Model](references/data_model.md) for table and column details before querying.

4. Query every needed endpoint, always filtering by `matter_id`:
   - For GET endpoints: fetch all rows, then filter client-side by `matter_id`.
   - For `POST /api/query`: include `WHERE matter_id = '...'` in every SQL statement.

5. Cross-reference records across endpoints using the ID relationships documented in the data model reference.

6. Build the output JSON exactly matching the provided answer template.

## Workflow

### Phase 1: Understand the output contract

The task always provides an answer template (usually at `input/payloads/answer_template.json`). Read it first. It defines:

- **Required top-level keys** — every key listed must be present in the output.
- **Ordering rules** — lists must be sorted as specified (typically by ID ascending, category code ascending, or priority rank ascending).
- **Enum choices** — string fields must use exactly the values listed.
- **Field types and required sub-keys** — every object in a list must include every required key.
- **Numeric precision** — all counts are whole integers.

If the template defines an `output_rule` saying "Return exactly one JSON object and no prose outside the JSON," follow it strictly. Do not wrap the JSON in markdown fences or add any commentary.

### Phase 2: Gather evidence from the hub

Query the hub endpoints relevant to the task. Each GET endpoint returns `{"count": N, "rows": [...]}`. Filter rows by `matter_id` on the client side. For the SQL endpoint, always filter server-side.

**Always query these endpoints** when their data appears in the answer shape:
- `/api/matters` — matter metadata (hold date, agency, investigation type).
- `/api/subpoena-categories` — request categories with titles, date ranges, and topic tags. Filter by `matter_id`.
- `/api/productions` — production batches per category with produced/withheld/responsive/nonresponsive counts and status. Filter by `matter_id`.
- `/api/custodian-sources` — data sources per custodian with collection statuses, issue tags, and category impacts. Filter by `matter_id`.
- `/api/documents/search` — individual review documents with responsiveness, privilege, and production coding. Filter by `matter_id`.
- `/api/privilege-log` — privilege entries with withheld/logged counts, issue types, and third-party flags. Filter by `matter_id`.
- `/api/qc-findings` — QC findings with issue types, affected categories, severity, and source references. Filter by `matter_id`.
- `/api/retention-events` — retention events with status, volume, dates, and affected categories. Filter by `matter_id`.
- `/api/remediation-actions` — pre-defined remediation actions with owners, priorities, and target references. Filter by `matter_id`.

Use `POST /api/query` with header `X-API-Key: review-key-017` for SQL access. The body format is `{"sql": "SELECT ... FROM ... WHERE matter_id = '...'"}`. This is especially useful for aggregations and for fetching documents filtered by multiple criteria at once.

**Critical rule**: Every query must filter by `matter_id`. The hub holds data for many matters (16 in the standard instance), and including another matter's records will corrupt the analysis.

### Phase 3: Cross-reference and identify gaps

Records across the hub reference each other through ID fields. Use these relationships to build a complete picture:

- **QC findings** → documents (via `source_ref`), categories (via `affected_category`).
- **Custodian sources** → categories (via `category_impacts` array), and their `issue_tags` signal problems like `collection_gap`, `personal_messaging`, `post_hold_wipe`, `deleted_channel`.
- **Retention events** → categories (via `affected_categories` array), sources (via `source_ref`).
- **Privilege entries** → categories (via `category_code`).
- **Documents** → categories (via `category_code`), and their `issue_tags`, `responsiveness`, `privilege_status`, `produced_status` signal individual problems.
- **Production batches** → categories (via `category_code`), and `status` values like `zero_claim_contradicted` or `supplement_pending` signal category-level issues.

**Identifying material gaps**: Look for:
- `status: "not_collected"` or `"lost"` in custodian sources → collection/preservation gaps.
- `issue_tags` containing `"collection_gap"`, `"personal_messaging"`, `"post_hold_wipe"`, `"deleted_channel"` → material risks.
- `status: "zero_claim_contradicted"` in productions → responsiveness miscodes.
- QC findings with `severity: "critical"` or `"high"` → confirmed defects.
- Privilege entries where `logged_count < withheld_count` → privilege log gaps.
- Privilege entries with `third_party: 1` → potential waiver issues.
- Retention events with `status: "post_hold_loss"` or `"should_exist_missing"` → preservation failures.
- Documents with `responsiveness: "responsive"` and `produced_status: "not_produced"` → underproduction.
- Documents with `privilege_status: "privileged"` and QC findings flagging miscoding → privilege miscodes.

### Phase 4: Compute metrics

Metrics fields are derived by counting across hub records. Common patterns:

- **Unlogged privilege docs**: Sum `(withheld_count - logged_count)` across privilege entries with incomplete logs.
- **Miscoded responsive docs**: Count documents flagged by QC findings as miscoded nonresponsive.
- **Lost/destroyed sources**: Count custodian sources with `status: "lost"` or retention events with `post_hold_loss`/`policy_destroyed_pre_hold`.
- **Uncollected sources**: Count custodian sources with `status: "not_collected"` or having `collection_gap` in `issue_tags`.
- **Available archives**: Count custodian sources with `status: "available"` and `issue_tags` containing `"archive_available"`.
- **Affected categories**: Collect the union of all `category_code`/`category_impacts`/`affected_categories` values from records with material gaps.
- **Boolean readiness flags**: Set to `true` only when zero material gaps exist across all categories.

Always count exactly from hub records, not from the answer template or from task descriptions. When the answer template specifies a metric with a name like `destroyed_lab_archive_box_count`, match the metric name precisely and compute its value from the specific source type referenced in the hub.

### Phase 5: Build the action plan

Prioritize actions by severity and operational urgency:

- **P0 (rank 1-2)**: Disclose preservation issues to the government, recover lost sources, address critical QC findings.
- **P1 (rank 3-5)**: Collect uncollected sources, recode and produce miscoded documents, supplement privilege logs, assess privilege waivers.
- **P2 (rank 6+)**: Archive searches, downgrade over-designations, custodian follow-ups, documentation of policy-compliant losses.

Assign owners from the template's enum. Common mappings:
- `outside_counsel` / `litigation_counsel`: disclosure, waiver assessment.
- `ediscovery_vendor` / `forensics`: collection, forensic recovery, archive search.
- `privilege_team` / `privilege_counsel`: privilege log, waiver, privilege recoding.
- `review_qc` / `review_vendor`: recoding, QC remediation.
- `client_it` / `it_messaging`: system collection, communication gap documentation.
- `compliance_audit` / `records_management`: missing record location, policy-documented losses.

Include `target_refs` listing every hub record ID that the action addresses. Include `category_impacts` listing every affected category code. Sort both arrays ascending.

### Phase 6: Validate and output

Before finalizing:

1. Verify every required top-level key is present.
2. Verify every required sub-key is present in every object within every list.
3. Verify all enum string values match the template exactly (case-sensitive).
4. Verify all lists are sorted according to the template's ordering rules.
5. Verify all IDs match their source hub records exactly.
6. Verify all counts are whole integers.
7. Verify the output is a single JSON object with no surrounding text.

## Reference files

- [Hub Data Model](references/data_model.md) — Table schemas, column types, and cross-reference relationships for every hub endpoint.
- [Analysis Patterns](references/analysis_patterns.md) — Common gap types, how to detect them from hub records, and how the train evidence connects endpoints to findings.

Always read the data model reference before querying so you know which columns to expect and how records join. Read the analysis patterns reference if the task type (gap analysis, retention review, remediation dashboard, readiness review) matches one of the documented patterns.

## Key principles

**Matter isolation**: Every query must filter by the task's matter ID. The hub is multi-tenant and including foreign records will produce incorrect metrics, duplicate IDs, and wrong category assignments.

**Schema conformance over narrative**: The task always wants structured JSON matching a template. Do not write prose, markdown, or commentary around the JSON output unless the template's output rule explicitly permits it.

**Hub as source of truth**: The task environment provides prompt context and answer templates, but the actual evidence — counts, statuses, IDs, dates — comes only from the hub. Do not deduce values from task descriptions or payload files when the hub has the data.

**Stable IDs**: Use record IDs exactly as they appear in hub responses. Do not generate or fabricate IDs.

**Sorting**: Apply the template's ordering rules after building every list. Most templates sort categories and IDs ascending, and priority ranks ascending.
