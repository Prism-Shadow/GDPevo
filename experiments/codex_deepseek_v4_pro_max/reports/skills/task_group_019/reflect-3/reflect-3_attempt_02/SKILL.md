 # Licensing Review Examiner Skill

 This skill provides reusable instructions for solving structured licensing review tasks that involve querying a remote data environment and producing JSON determinations. It does not encode task-specific answers, thresholds, or endpoint lists; instead it describes the workflow patterns that repeat across varying task schemas.

 ## Core Workflow

 1. **Read the task prompt and answer template carefully.**
    - The prompt identifies the target entities (application IDs, license numbers, location IDs) and any special parameters (review date, boundary date, queue size).
    - The answer template defines the exact JSON schema, allowed enum values, ordering rules, and required keys. Strictly conform to the template.

 2. **Gather all relevant data from the environment.**
    - Use direct GET endpoints when available for quick exploration.
    - Use `POST /api/sql` with the required token header for targeted queries. Always explore table schemas with `SELECT * FROM <table> LIMIT 1` before writing filters.
    - When a table column name is unknown, inspect it with the LIMIT-1 pattern rather than guessing.

 3. **Retrieve and parse applicable policies.**
    - Policies live at `GET /api/policies` and have a `family` field that scopes them to the domain.
    - The `details_json` field is a JSON string containing the actual rule parameters (minimums, required items, boolean flags). Parse it with a JSON decoder.
    - Match a policy to an entity by combining its `rule_code` or `title` keywords with entity attributes (trade, license class, channel type).

 4. **Apply classification rules derived from policies and data.**
    - For each entity, compare its attributes against the matched policy thresholds.
    - Identify gaps where current values fall short of requirements.
    - Check related records (bonds, insurance, violations, inspections, correspondence) for blocking conditions.

 5. **Produce the answer strictly conforming to the template.**
    - Use empty arrays where no codes apply.
    - Sort coded lists alphabetically/lexically unless the template specifies otherwise.
    - Order entities by their natural identifier unless a ranking is required.
    - Keep summary counts consistent with the detailed determinations.

 ## Data Access Patterns

 ### SQL Query Construction
 - Use parameterized queries: `{"query": "SELECT ... WHERE col LIKE ?", "params": ["pattern%"]}`
 - Always include a `limit` when exploring data.
 - When filtering by a set of IDs, use `LIKE` with a shared prefix pattern (e.g., `"C-TR1-%"`) to capture all target rows in one call.
 - For cross-table lookups, use subqueries: `WHERE col IN (SELECT other_col FROM other_table WHERE ...)`
 - If a query returns "no such column", inspect the table schema first.

 ### REST Endpoint Usage
 - GET endpoints return all rows for their domain. They are useful for quick exploration but may not be filtered to the task's target entities.
 - Prefer SQL for filtered queries once table schemas are known.

 ## Domain-Specific Analysis Patterns

 ### Contractor Application Review
 - Match policy by the `trade` and `requested_class` fields of the application.
 - Check each dimension against policy thresholds:
   - **Experience**: `years_experience` vs `minimum_years_experience`
   - **Endorsement**: `endorsement_status` (missing/pending/verified/not_required) vs `required_endorsement` from policy. If policy has `null` endorsement, `not_required` is acceptable.
   - **Bond**: Look for an active bond row (`status = "active"`). Compare `amount` vs `minimum_bond`. If no active bond exists, the bond is either cancelled or never filed.
   - **Insurance**: Look for an active insurance row. Check `amount` vs `minimum_insurance`. If a review date is provided, verify `expiration_date` is after the review date. Pending insurance is not current coverage.
 - **Violations**: Open violations with `severity = "serious"` typically block approval. Apply the policy's `serious_open_violation_blocks` rule.
 - **License History**: Check for `suspended` status on the prior license. Suspension blocks approval.
 - **Correspondence**: Track `verified_by_agency = 0` rows and rows whose notes indicate "Applicant copy only; no agency confirmation" or "Stale" content. Include these in `stale_or_unverified_correspondence_ids`.
 - **Inspections**: Map finding codes to deficiency codes only when the template includes inspection-related deficiency values. If the template has no inspection codes, inspection results do not create deficiencies.

 ### Liquor License Staff Package
 - **Settlements**: Identify active settlements (`controls_json` containing `"active": true`). Extract the `controls` array to determine active location-specific controls and the `basis_code` to determine covered risks.
 - **Incidents**: Review open/referred incidents as verification gaps. Map incident `risk_code` values to covered-risk or escalation codes.
 - **Site Evidence**: Check evidence statuses (`missing`, `conflicting`, `verified`). Missing and conflicting evidence items become verification gaps. Notes like "Old location name" on a police memo indicate identity discrepancies.
 - **Privileges**: Query by `license_class`. Codes with `standard_required = 1` are standard obligations. Codes with `standard_required = 0` may become location-specific controls when present in an active settlement.
 - **Same-premises basis**: True when an active settlement has `basis_code = "SAME_PREMISES"` or when policy indicates same-premises history matters and prior same-premises settlements exist. False when all same-premises settlements are expired and policy does not preserve them.
 - **Monitoring plan**: Assign checks to time windows based on urgency. Place immediate gaps (camera, food service, tax clearance) in `first_30_days`, control re-verification in `days_31_60`, and follow-up visits in `days_61_90`.

 ### Renewal Review Queue
 - **Boundary date**: Only violations on or before the boundary date are matched. The prompt or renewal rules specify this date.
 - **Source filtering**: Violations from `post_boundary_feed` are distractors and must be excluded from matching. List them in `post_boundary_violation_ids_excluded`. Violations from `legacy_successor_feed` may be matched to successor licenses with `uncertain` confidence; treat based on how the rules define "late rows."
 - **Ranking**: Order by severity of open violations first (serious open/pending), then by unpaid fine balance descending, then by alert flag count, then by most recent violation date.
 - **Match confidence**: `exact` when violation `license_no` equals the target license. `uncertain` when matched through a successor relationship. `close_address` when matched by address similarity.
 - **Risk tier**: `high` for entities with serious open/pending violations. `medium` for entities with alert flags or unpaid fines. `low` for entities with only resolved/warning violations.
 - **Next step**: `board_review` for serious open/pending violations. `manual_fine_check` for unpaid fines. `manual_ALERT_check` for alert flags without fines. `additional_record_check` for uncertain matches or records needing verification.

 ## General Rules

 - Never fabricate data. Every value in the answer must be derived from query results.
 - When a template field expects a list of IDs from related records, extract those IDs directly from the data rather than constructing them manually.
 - If a deficiency or action code is not present in the template's allowed values, it cannot be used — even if the data suggests an issue.
 - Cross-check summary counts against the detailed entries to ensure consistency.
 - For boolean fields like `policy_impacted`, a policy change creates impact when the current policy baseline introduces a requirement that would not have existed under prior rules. If a deficiency (e.g., cancelled bond) would exist regardless of the policy version, consider whether it is truly policy-impacted.
 - Dates should use YYYY-MM-DD format throughout.
