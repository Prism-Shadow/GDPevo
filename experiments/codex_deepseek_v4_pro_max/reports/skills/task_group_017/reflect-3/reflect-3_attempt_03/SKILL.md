## Investigation Review Hub — Structured Gap & Remediation Analysis

### Purpose
Produce structured JSON gap-analysis, retention-review, production-readiness, or remediation-dashboard deliverables by querying the Investigation Review Hub API and strictly conforming to the task-provided answer template.

### Hub API Usage

- **Base URL**: read from the task prompt or `matter_context.json` / `review_scope.json` payloads (look for `environment_base_url` or `<TASK_ENV_BASE_URL>`).
- **API Key**: `review-key-017` sent in the `X-API-Key` header on every request.

**Read-only GET endpoints** (append `?matter_id=<id>` where applicable):

| Endpoint | Key records |
|---|---|
| `GET /api/schema` | Table/column catalog for SQL queries |
| `GET /api/matters` | Matter metadata, agency, hold date, status |
| `GET /api/subpoena-categories` | Request categories with codes, date ranges, topic tags |
| `GET /api/productions` | Batch-level production stats, statuses, counts |
| `GET /api/custodian-sources` | Custodian devices/sources, collection status, category impacts, issue tags |
| `GET /api/documents/search` | Individual review documents with responsiveness, privilege, issue tags |
| `GET /api/privilege-log` | Privilege entries with withheld/logged counts, issue types |
| `GET /api/qc-findings` | QC findings with issue types, doc counts, severity, affected categories |
| `GET /api/retention-events` | Retention events with statuses, volume, policy sections, affected categories |
| `GET /api/remediation-actions` | Planned remediation actions with owners, priorities, targets |

**SQL query endpoint** (use when aggregations or filtered lookups are needed):

```
POST /api/query
Content-Type: application/json
X-API-Key: review-key-017
{"sql": "<SELECT statement>", "params": ["<value>"]}
```

### Workflow

1. **Parse the answer template** (`input/payloads/answer_template.json`):
   - Identify `required_top_level_keys` — every one must appear in the output.
   - Extract `enums` — every categorical field must use one of the listed values exactly.
   - Note `ordering_rules` — sort list items as specified.
   - For each section, capture `item_required_keys` so no field is omitted.

2. **Query all relevant hub endpoints** for the matter under review. Do not inspect local files, database files, manifests, or seed data. Use only the live API responses.

3. **Map hub records to template items**:
   - Use stable record IDs from the hub (`source_id`, `event_id`, `finding_id`, `entry_id`, `action_id`, `doc_id`, `batch_id`) as reference values in `source_refs`, `target_refs`, `issue_refs`, etc.
   - Derive category-code lists from `category_impacts` or `affected_categories` fields.
   - Sort category-code arrays ascending within each item.

4. **Compute metrics** from hub aggregates:
   - Count records by status, type, or issue-type using the raw endpoint data.
   - For privilege metrics: sum `withheld_count`, `logged_count`, and compute `unlogged = withheld - logged` from privilege-log entries filtered by the issue types specified in the template's metric descriptions.
   - For box/volume counts: filter by `volume_unit == "boxes"` and sum `volume_count` for relevant statuses.
   - Use exact integer values; do not round or approximate.

5. **Build the answer JSON**:
   - Include every top-level key from the template.
   - Populate every required field in every item.
   - Use `0` for integer fields when not applicable; use `[]` for empty lists; use `null` for optional string fields only when the template explicitly allows it.
   - Follow ordering rules exactly.
   - Validate that all enum fields use values from the template's enum lists.
   - Output only the JSON object — no surrounding prose, markdown fences, or commentary.

### Common Enum Values

Across tasks, the following enum families recur. Always check the specific template for the exact set, but these are typical:

- **Severity / risk levels**: `critical`, `high`, `medium`, `low`
- **Priorities**: `P0`, `P1`, `P2`, `P3`
- **Source statuses**: `available`, `collected`, `not_collected`, `partial_collection`, `lost`, `in_review`
- **Production statuses**: `produced`, `closed`, `supplement_pending`, `rolling_review`, `zero_claim_contradicted`
- **Retention statuses**: `policy_destroyed_pre_hold`, `post_hold_loss`, `system_loss`, `auto_purged`, `should_exist_missing`, `retained`, `available`
- **Issue types**: `privilege_log_gap`, `preservation_failure`, `collection_gap`, `responsiveness_miscode`, `miscoded_privilege`, `retention_loss`, `third_party_waiver`, `over_designation`

### Key Data Relationships

- **Custodian sources** link to categories via `category_impacts`; their `status` determines collection gaps.
- **Retention events** link to categories via `affected_categories`; compare `event_date` to `hold_date` to determine pre/post-hold.
- **QC findings** link to categories via `affected_category` and to documents via `source_ref`.
- **Privilege entries** link to categories via `category_code`; `issue_type` of `incomplete_log` means `unlogged = withheld - logged`.
- **Productions** link to categories via `category_code`; `status` indicates production readiness.
- **Remediation actions** link to targets via `target_ref`; filter out noise actions (those with `NOISE` in their ID).

### Pitfalls

- Do not include task-specific final answer values, candidate answers, or judge transcripts in the skill.
- Do not include instructions to call any judge/evaluation endpoint.
- Always sort category codes and reference IDs ascending within arrays as required by ordering rules.
- Verify that every enum value used appears in the template's enum definition for that field.
- When the template says "from selected incomplete-log blockers only" for a metric, filter privilege entries to only those with `issue_type == "incomplete_log"`.
