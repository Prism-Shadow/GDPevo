 # Investigation Review Hub — Agent Skill

 ## Purpose

 Use this skill when an e-discovery or legal-operations task requires structured analysis of the Investigation Review Hub API. The hub exposes matter metadata, subpoena categories, custodian sources, production statistics, privilege-log data, quality-control findings, retention events, and remediation actions through REST endpoints and a read-only SQL query interface.

 ## When to Apply

 Apply this skill whenever a task prompt references:

 - "Investigation Review Hub"
 - A `<TASK_ENV_BASE_URL>` placeholder
 - Matter IDs in the format `MTR-<ENTITY>-<TYPE>` (e.g., `MTR-ACME-SEC`, `MTR-GLOBEX-GJ`)
 - Deliverables such as gap analyses, retention and preservation reviews, remediation dashboards, or production-readiness assessments
 - `input/payloads/answer_template.json` defining the expected output schema

 Do **not** apply this skill for tasks that do not involve the hub API.

 ## Environment Discovery

 ### Base URL

 The task prompt provides a `<TASK_ENV_BASE_URL>` placeholder. Substitute it with the actual base URL before making any requests. Confirm reachability with:

 ```
 GET <TASK_ENV_BASE_URL>/
 ```

 ### API Key

 All POST requests to the query endpoint require the header:

 ```
 X-API-Key: review-key-017
 ```

 GET endpoints do not require an API key.

 ### Available GET Endpoints

 | Endpoint | Purpose |
 |---|---|
 | `GET /api/schema` | List all tables and their column names and types |
 | `GET /api/matters` | List all matters in the hub |
 | `GET /api/subpoena-categories` | Request/subpoena categories |
 | `GET /api/productions` | Production batch statistics |
 | `GET /api/custodian-sources` | Custodian data sources and collection status |
 | `GET /api/documents/search` | Search documents by matter or keyword |
 | `GET /api/privilege-log` | Privilege-log entries |
 | `GET /api/qc-findings` | Quality-control findings |
 | `GET /api/retention-events` | Retention and destruction events |
 | `GET /api/remediation-actions` | Recommended remediation actions |

 ### SQL Query Endpoint

 ```
 POST /api/query
 Content-Type: application/json
 X-API-Key: review-key-017

 {"sql": "<SELECT statement>", "params": ["<value>", ...]}
 ```

 Use parameterised queries. Filter by `matter_id` for all tables.

 ## Schema Reference

 After calling `GET /api/schema`, note the following tables and their key columns.

 ### `matters`

 `matter_id`, `name`, `agency`, `investigation_type`, `issued_date`, `hold_date`, `lead_partner`, `description`, `status`

 ### `subpoena_categories`

 `matter_id`, `category_code`, `title`, `date_start`, `date_end`, `request_text`, `topic_tags`

 Category codes are stable identifiers. Use them exactly as returned by the hub.

 ### `custodian_sources`

 `source_id`, `matter_id`, `custodian_name`, `role`, `source_type`, `source_label`, `status`, `event_date`, `post_hold` (0/1), `category_impacts` (comma-separated codes), `issue_tags`, `notes`

 Key status values: `collected`, `not_collected`, `lost`, `partial_collection`, `available`, `in_review`

 ### `production_stats`

 `matter_id`, `batch_id`, `batch_date`, `category_code`, `produced_count`, `withheld_count`, `responsive_count`, `nonresponsive_count`, `status`, `zero_claim_reason`, `notes`

 ### `privilege_entries`

 `entry_id`, `matter_id`, `category_code`, `custodian_name`, `doc_count`, `withheld_count`, `logged_count`, `issue_type`, `third_party` (0/1), `notes`

 Key issue types: `incomplete_log`, `over_designated`, `family_mismatch`, `third_party_waiver`, `clean`

 ### `qc_findings`

 `finding_id`, `matter_id`, `batch_id`, `issue_type`, `doc_count`, `affected_category`, `source_ref`, `severity`, `notes`

 ### `retention_events`

 `event_id`, `matter_id`, `record_type`, `event_date`, `hold_date`, `policy_section`, `retention_period_months`, `volume_count`, `volume_unit`, `status`, `affected_categories`, `source_ref`, `notes`

 Key status values: `policy_destroyed_pre_hold`, `post_hold_loss`, `system_loss`, `should_exist_missing`, `retained`, `available`, `auto_purged`

 ### `remediation_actions`

 `action_id`, `matter_id`, `action_type`, `priority`, `severity`, `owner`, `target_ref`, `due_days`, `description`

 ### Document Search

 `GET /api/documents/search?matter_id=<MATTER_ID>&q=<query>`

 Returns `doc_id`, `category_code`, `custodian_name`, `doc_date`, `issue_tags`, `privilege_status`, `produced_status`, `responsiveness`, `source_system`, `summary`, `title`

 ## Answer Construction Protocol

 ### 1. Read the Template

 Every task includes `input/payloads/answer_template.json`. Read it first. It defines:

 - `required_top_level_keys` — the top-level JSON keys that must be present
 - `schema` or `fields` — the structure of each section
 - `enums` or `enum_choices` — the exact set of allowed values for every enum field
 - `ordering_rules` — how to sort list items
 - `numeric_precision` — expected numeric format (always whole integers)

 ### 2. Use Stable Hub Identifiers

 Every record ID (`source_id`, `event_id`, `entry_id`, `finding_id`, `action_id`, `doc_id`, `batch_id`, `category_code`, `matter_id`) must be taken verbatim from the hub. Never invent IDs.

 ### 3. Follow Enum Values Exactly

 Compare every enum-valued field against the allowed list in the template. Use the exact string, including case and underscores (`snake_case`).

 ### 4. Sort Lists as Specified

 Each template section has an `ordering_rules` entry. Typical rules:

 - Lists of findings/risks: sort by `finding_id` or `event_id` ascending, or by `priority_rank` ascending
 - Category lists: sort by `category_code` ascending
 - Action plans: sort by `rank` ascending

 ### 5. Populate Metrics from Hub Data

 Metrics are numeric aggregates derived from the hub tables. Count only records that belong to the target matter. Common metrics include:

 - Counts of events with specific statuses (e.g., `post_hold_loss_event_count` counts retention events where `status = 'post_hold_loss'`)
 - Counts of sources with specific statuses (e.g., `lost_personal_device_count` counts custodial sources where `status = 'lost'` and `source_type` indicates personal device)
 - Document counts from QC findings and privilege entries
 - Category counts derived from `SELECT DISTINCT` across affected categories

 Always filter all queries by `matter_id`.

 ### 6. Distinguish Material from Noise

 The hub contains operational "noise" records (e.g., entries with `notes` like "Routine action included as realistic operational noise" or "Entry included to create similar labels across matters"). These are not material findings. Focus on records with substantive notes, escalated issues, or non-routine statuses.

 ### 7. Construct Action Plans

 Map hub remediation actions and material findings to the `action_plan` or `priority_actions` section. Use the hub's `remediation_actions` table as a starting point, filtering out noise actions (identified by `action_id` containing `NOISE` or descriptions indicating routine work). Derive additional actions from material findings that lack existing remediation entries. Order by descending priority (P0 > P1 > P2 > P3).

 ## Common Task Patterns

 ### Pattern A: Rolling Production Gap Analysis

 - Query `production_stats` for batches with non-closed statuses
 - Cross-reference `custodian_sources` for uncollected or lost sources
 - Check `qc_findings` for miscoded documents
 - Review `privilege_entries` for incomplete logs or over-designation
 - Identify categories with collection gaps, preservation risks, or privilege-log gaps

 ### Pattern B: Retention and Preservation Gap Review

 - Query `retention_events` and classify each by status
 - Identify pre-hold policy-compliant destruction vs. post-hold losses
 - Check `custodian_sources` for available archives that can remediate gaps
 - Count destroyed volumes by status type
 - Note communication gaps (auto-purged messages, active system losses) separately

 ### Pattern C: Cross-System Remediation Dashboard

 - Aggregate risks from `retention_events`, `custodian_sources`, `qc_findings`, and `privilege_entries`
 - Rank risks by severity and production impact
 - Map each subpoena category to its coverage status
 - Identify retained or available sources that can limit losses
 - Build a ranked action plan with responsible owners and due dates

 ### Pattern D: Production-Readiness Review

 - Check `production_stats` for categories not yet produced or with supplement-pending status
 - Review `qc_findings` for issues that block certification
 - Audit `privilege_entries` for withheld-but-unlogged documents
 - Classify each category as ready or not-ready with supporting record references

 ## Output Rules

 1. Return exactly one JSON object. No prose, no markdown fences, no commentary.
 2. Include every `required_top_level_key` from the template.
 3. Use `null` (not the string `"null"`) for nullable fields.
 4. Use whole integers for all count and numeric fields.
 5. Use stable hub IDs for all reference fields.
 6. Sort all list fields according to the template's ordering rules.
 7. Do not include any fields that are not defined in the template.

 ## Error Recovery

 - If an endpoint returns an error, verify the base URL, API key header, and matter ID.
 - If a SQL query fails, check the table name against `GET /api/schema` and verify column names.
 - If document search returns no results, try without the `q` parameter to browse all documents for the matter.
 - If a field requires a value not present in the hub, use `0` for counts, `[]` for lists, `null` for nullable strings, and `"not_applicable"` or `"none"` for enum fields that offer those choices.
