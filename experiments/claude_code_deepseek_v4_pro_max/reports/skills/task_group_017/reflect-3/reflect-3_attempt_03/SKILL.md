# Investigation Review Hub — Structured JSON Deliverable Skill

## When to use

Use this skill when a task prompt asks you to produce a structured JSON deliverable from an **Investigation Review Hub** — a read-only REST API serving matter metadata, subpoena categories, production stats, custodian sources, review documents, privilege logs, QC findings, retention events, and remediation actions. The prompt will reference `<TASK_ENV_BASE_URL>` and provide an `answer_template.json` schema. Return **only** the JSON object; no surrounding prose.

## Phase 1 — Inventory the input directory

Every task instance ships with these files inside `input/`:

| File | What it carries |
|---|---|
| `prompt.txt` | Business narrative, matter name, deliverable type, `<TASK_ENV_BASE_URL>` placeholder |
| `payloads/answer_template.json` | Required JSON schema: top-level keys, per-item required keys, enum choices, ordering rules, numeric precision |
| `payloads/request_context.json` *or* `review_scope.json` *or* `matter_context.json` | The `matter_id` string, client-facing category labels, any scope notes |

1. Read `prompt.txt` first to learn the **matter_id** and the deliverable description.
2. Read the template second. Memorise every **enum** list — these are the *only* valid values for their fields.
3. Read the context payload last to confirm the matter_id and get supplementary category titles.

## Phase 2 — Discover the environment base URL

The prompt contains `<TASK_ENV_BASE_URL>`. Resolve it from `environment_access.md` in the task root (if present), or from the runtime environment variable. The actual value is an HTTP base URL (e.g., `http://task-env:9017/`). All subsequent API calls use this base.

## Phase 3 — Retrieve matter data from the hub

The hub exposes two kinds of endpoints. Prefer the **REST GET** endpoints as the source of record; use the **SQL POST** endpoint only as a supplement when you need cross-table filtering the REST endpoints don't support.

### REST GET endpoints (no auth required)

| Endpoint | Returns |
|---|---|
| `GET /api/matters` | All matters; filter to your `matter_id` |
| `GET /api/subpoena-categories` | Request categories with codes, date ranges, topic tags |
| `GET /api/productions` | Batch-level production stats per category |
| `GET /api/custodian-sources` | Custodian-level sources with collection status, post-hold flag, category impacts |
| `GET /api/privilege-log` | Privilege entries with doc/withheld/logged counts, issue type, third-party flag |
| `GET /api/qc-findings` | QC findings with issue type, severity, doc count, affected category |
| `GET /api/retention-events` | Retention events with status, record type, volume, affected categories, event/hold dates |
| `GET /api/remediation-actions` | Pre-populated remediation actions with priority, severity, owner, target |

**Filter pattern:** Call the endpoint, parse the JSON, and filter `rows` where `matter_id` equals your target matter. Do this for every endpoint — different endpoints may return varying row counts for the same matter, and the REST surface is the authority.

### SQL POST endpoint (requires API key header)

```
POST /api/query
Header: X-API-Key: <value from environment_access.md credentials>
Body: {"sql": "<SQL statement>"}
```

The schema is available at `GET /api/schema`. Use SQL when you need precise counts (e.g., `SELECT SUM(withheld_count), SUM(logged_count) FROM privilege_entries WHERE matter_id = "..." AND issue_type = "incomplete_log"`) or filtered document searches. **Never use SQL as your sole data source** — cross-check findings against the REST GET responses.

## Phase 4 — Map hub values to template enums

The hub returns its own status vocabulary. The answer template defines a separate, stricter enum vocabulary. **Always map from hub value → template enum; never pass hub raw values into the answer.**

### Common mappings observed across training tasks

| Hub field | Hub raw value examples | Template enum (look up per schema) |
|---|---|---|
| `custodian_sources.status` | `lost`, `not_collected`, `partial_collection`, `collected`, `available`, `in_review` | `lost`, `not_collected`, `partial`, `collected`, `pending`, `not_applicable` |
| `retention_events.status` | `policy_destroyed_pre_hold`, `auto_purged`, `system_loss`, `post_hold_loss`, `should_exist_missing`, `retained`, `available`, `post_hold_partial_recovery` | Schema-specific; "system_loss" often maps to "active_system_loss", "retained" → "preserved_available", "available" → "available_archive" |
| `privilege_entries.issue_type` | `incomplete_log`, `over_designated`, `third_party_waiver`, `clean`, `family_mismatch` | Schema-specific enum like `privilege_log_gap`, `over_designation`, `third_party_waiver` |
| `qc_findings.issue_type` | `miscoded_nonresponsive`, `miscoded_privilege`, `zero_claim_contradiction`, `family_break`, `metadata_gap`, `near_duplicate`, `duplicate_overlay`, `date_normalization` | Schema-specific enum like `responsiveness_miscode`, `privilege_miscoding`, `other` |

**Rule:** Open the template's `enums` block. For every field you populate, verify the value appears in the corresponding enum list. If you need to map a hub value, choose the closest semantic match. When in doubt, prefer `"other"` (if available) over inventing a value.

## Phase 5 — Construct the answer

### General rules (apply to every task)

1. **Top-level keys must exactly match** `required_top_level_keys` in the template — no more, no fewer.
2. **Every required key** inside each list-item object must be present, even if the value is `0`, `null`, `[]`, or `"not_applicable"`.
3. **Ordering:** Follow `ordering_rules` exactly. Sort `category_code`/`finding_id`/`event_id`/`source_id`/`issue_id`/`correction_id` ascending within each list. Sort `priority_rank`/`rank` ascending. Sort category code lists ascending within each item.
4. **Numeric precision:** All counts are whole integers. Boolean fields (`true`/`false`, not `"true"`/`"false"` and not `1`/`0`).
5. **Null vs. 0:** Use `0` when a count is zero. Use `null` only when the template explicitly says `"string or null"` for a field like `third_party`, `policy_section`, `missing_component`, or `cutoff_date`.

### Finding/risk/issue IDs

When the template says "Use a stable hub record ID as finding_id when one record anchors the finding," use the exact hub record ID:
- Custodian source gaps → `source_id` (e.g., `"SRC-SENT-ALDEN-PHONE"`)
- Privilege issues → `entry_id` (e.g., `"PRIV-SENT-LOG-GAP"`)
- QC findings → `finding_id` (e.g., `"QC-SENT-R09-NR"`)
- Retention events → `event_id` (e.g., `"RET-HARB-EHS-POST"`)
- Remediation actions → `action_id` (e.g., `"ACT-SENTINELGJ-001"`)

### Category statuses / coverage

- When the template says "One object for each ... category with a material non-complete status," include **only** categories that have at least one documented gap, loss, or issue. Do **not** include categories with `no_current_gap`/`no_open_gap` status unless the template explicitly asks for all categories.
- Conversely, when the template is a "coverage" or "dashboard" type, include every category that has any open risk, and use the appropriate `category_status` enum value for each.

### Source references

- `source_refs`, `issue_refs`, `blocking_refs`, `target_refs`, `record_refs` — these are **lists of hub record IDs** that support the claim. Sort them ascending.
- `category_impacts`, `affected_categories` — these are **lists of category codes** (like `["R09", "R15"]` or `["SEC-1", "SEC-3"]`). Sort them ascending.
- When the hub returns `category_impacts` as a comma-separated string in SQL but as an array in REST, always use the **array form** and sort it.

### Metrics

- Sum counts across the relevant records. For privilege log gaps, sum `withheld_count - logged_count` across all entries of type `incomplete_log` (or whatever the template identifies as the gap type).
- For "destroyed_lab_archive_box_count" and similar task-specific metrics, use `0` when the task's matter has no such source.
- `categories_with_open_gaps` / `categories_with_open_risk` is a **sorted list** of category codes, not a count.
- `rolling_production_ready` / `production_ready` is a **boolean**.

### Actions

- `priority_rank` / `rank` starts at 1 (highest priority).
- `priority` uses `P0`/`P1`/`P2`/`P3` (or whatever enum the template provides).
- `owner` must be one of the template's `owner` enum values — map hub owner names (e.g., "Review Operations", "Forensics", "Privilege Team") to template enum values (e.g., `"review_vendor"`, `"ediscovery_vendor"`, `"privilege_team"`).
- `action_type` must be one of the template's `action_type` enum values — map hub action types to template enums.

## Phase 6 — Validate before output

Before returning the answer, run these checks:

1. **Schema conformance:** Every required top-level key present. Every list item has all required keys.
2. **Enum audit:** Spot-check 5 random enum-valued fields against the template's enum lists.
3. **Sort audit:** Verify `category_code`/`finding_id`/`event_id`/`source_id` lists are ascending. Verify `priority_rank`/`rank` are ascending.
4. **Count accuracy:** Re-derive one metric from the raw data to verify.
5. **Type audit:** Confirm `true`/`false` for booleans, integers for counts, arrays for lists, `null` for nullable string fields.
6. **Output format:** Return only the JSON object. No markdown fences, no trailing prose.

## Common pitfalls

- **Hub status ≠ template enum:** The hub may say `"system_loss"` but the template only accepts `"active_system_loss"`. Always map.
- **SQL vs REST divergence:** Custodian sources and other endpoints may return different rows via SQL vs REST. The REST GET surface is authoritative; treat SQL as a secondary check.
- **All categories vs. non-complete-only:** Some templates want every category listed; others want only categories with gaps. Read the template's field description to decide.
- **Null fields:** When the template says `"string or null"`, use `null` (JSON null, not the string `"null"`). When it says `"integer or null"`, similarly use `null` for absent data.
- **Sorting nested lists:** Category code lists inside items must also be sorted ascending, not just the outer item list.
- **Third-party waiver documents:** These are counted separately from privilege log gaps. Look for `third_party: 1` or `third_party_waiver` issue type in privilege entries.
- **Noise records:** The hub may include records with `NOISE` in the ID or `routine` in tags. These are realistic operational noise — include them in counts but don't elevate them to critical findings.
- **Post-hold vs pre-hold:** Compare `event_date` to `hold_date` to determine if a loss happened before or after the legal hold was issued. This affects the `issue_type` and `severity` classification.

## Supporting files

- `skill/SCHEMA_REFERENCE.md` — Full table schemas for the Investigation Review Hub, listing every column name and type for each REST endpoint. Use as a quick reference when constructing SQL queries or verifying API responses.
