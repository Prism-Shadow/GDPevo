---
name: licensing-review
description: Solve structured licensing-review tasks for state contractor, liquor, and alcohol-renewal domains. Use when a task requires batch eligibility review, a restricted liquor license staff package, or an alcohol renewal manual-review queue, each producing JSON output conforming to a supplied answer template.
---

# Licensing Review Solver

This skill covers three recurring licensing-review task types used by state licensing boards and alcohol control units. Every task follows the same core workflow: read the answer template, collect all relevant records from the API, cross-reference entities, derive structured decisions from the data, and emit JSON output that exactly conforms to the template.

## Core Workflow

1. **Read the template first.** The `answer_template.json` in the task payloads directory is authoritative. Every field name, enum value, ordering rule, and required key comes from the template. Never guess at a schema — use only the `allowed_values` listed in the template.

2. **Identify the domain.** Match the template top-level keys and prompt endpoint references to one of the three domains below. If a task spans domains, treat each sub-task independently with its own template.

3. **Collect all endpoint data.** Fetch every endpoint listed for that domain in the prompt. Use REST endpoints for bulk entity retrieval. Use the SQL endpoint for filtered joins or aggregations the REST endpoints cannot express directly — for example, matching licensees to violations by partial license number, or checking recency against a boundary date.

4. **Cross-reference entities.** Use common identifiers (application IDs, license numbers, location IDs, correspondence ID prefixes) to connect records across endpoints. Every deficiency, risk code, or action must be traceable to specific data in the fetched records.

5. **Derive decisions rule-by-rule.** Apply the domain-specific decision rules below. Map API record conditions to template-allowed deficiency codes, action codes, risk tiers, and determinations.

6. **Format output exactly to template.** Sort all arrays per template ordering rules (ascending lexical unless stated otherwise). Remove duplicates. Use empty arrays `[]` when no codes apply — never `null` or absent keys. Produce only the JSON object with the top-level keys the template requires. No prose, markdown, or comments.

## Environment

The task environment is reachable at `<TASK_ENV_BASE_URL>`. All REST endpoints use `GET`. When a SQL endpoint is listed in the environment instructions (`POST /api/sql`), it requires:

- Header: `X-Task-Token: licensing-review-019`
- Body: `{"query": "...", "params": [], "limit": 1000}`
- Only `SELECT` statements are accepted.

Set the SQL `limit` to at least the number of target entities plus a generous margin. Default to 1000.

## Domain Routing

Identify the domain from the prompt's endpoint list and the template's top-level keys.

### Domain A: Contractor Eligibility Review

**Template signals:** `application_decisions` array with fields `determination` (APPROVE/HOLD/DENY), `deficiency_codes`, `required_actions`, `risk_tier`, `policy_impacted`, and a `summary` object.

**Endpoints:** `GET /api/policies`, `GET /api/contractor/applications`, `GET /api/contractor/bonds`, `GET /api/contractor/insurance`, `GET /api/contractor/license-history`, `GET /api/contractor/violations`, `GET /api/contractor/correspondence`, `GET /api/contractor/inspections`, and `POST /api/sql`.

### Domain B: Restricted Liquor License Staff Package

**Template signals:** `recommended_posture` (issue_restricted/request_follow_up/deny), `same_premises_basis_applies`, `covered_risk_codes`, `verification_gap_codes`, `standard_obligation_codes`, `location_specific_control_codes`, `first_90_day_plan`, and `escalation_trigger_codes`.

**Endpoints:** `GET /api/policies`, `GET /api/liquor/applications`, `GET /api/liquor/settlements`, `GET /api/liquor/privileges`, `GET /api/liquor/incidents`, `GET /api/liquor/site-evidence`, and `POST /api/sql` (when the prompt includes it).

### Domain C: Alcohol Renewal Manual Review Queue

**Template signals:** `queue` array with ranked entries containing `violation_count`, `most_recent_violation_date`, `matched_violation_ids`, `match_confidence` (exact/close_address/uncertain), `risk_tier`, `next_step_label`, and a `summary` object with `boundary_date` and `post_boundary_violation_ids_excluded`.

**Endpoints:** `GET /api/alcohol/licensees`, `GET /api/alcohol/violations`, `GET /api/renewal/rules`, and `POST /api/sql`.

## Decision Rules: Contractor (Domain A)

### Determination

Derive for each application by checking all fetched records against the review date (if the prompt supplies one):

- **APPROVE:** All financial coverage (bond + insurance) is active and meets policy minimums, all required endorsements are verified, experience is documented, no active suspension exists, no unresolved serious complaints exist, all inspections are cleared, and no correspondence is stale or unverified.
- **HOLD:** One or more curable deficiencies are present. These include: bond cancelled or below required amount, insurance expired (but not permanently lapsed) or below required amount, endorsements not yet verified (pending, not rejected), experience below threshold, inspection documentation gaps, open minor violations, or unverified correspondence. The key distinction from DENY is that no active suspension is present and no serious unresolved complaint exists.
- **DENY:** An active suspension is present on the license history, or an unresolved serious complaint/violation is combined with multiple other deficiencies, or a safety recheck is required from an inspection.

### Deficiency-to-Action Mapping

Each deficiency code maps to a corresponding required action. The template defines the allowed pairings. Derive the mapping as follows:

- Any **bond** deficiency (cancelled, expired, shortfall, not active) → the corresponding bond action (obtain, increase, file).
- Any **insurance** deficiency (expired, not current, shortfall, pending) → the corresponding insurance action (provide, renew, increase, verify).
- Any **endorsement** deficiency (missing, not verified, pending) → the corresponding endorsement action (obtain, verify).
- Any **experience** deficiency → submit or document experience evidence.
- Any **inspection** deficiency (doc gap, safety recheck) → clear gap or complete recheck.
- Any **suspension** deficiency → board review and clear suspension.
- Any **serious complaint/violation** → resolve complaint and/or board review.

Always use the exact code strings from the template's `allowed_values`. If the template lists both `bond_cancelled` and `no_active_bond`, use whichever matches the actual data condition. Never invent codes outside the template's allowed set.

### Risk Tier

- **high:** The determination is DENY, or an active suspension exists, or an unresolved serious complaint exists, or a safety recheck is required.
- **medium:** The determination is HOLD and at least one deficiency exists.
- **low:** The determination is APPROVE and no deficiencies exist.

### Policy Impact

Set `policy_impacted` to `true` when the current policy baseline (from the policies endpoint) introduces a deficiency or material review flag that would not have applied under the prior baseline. Check policies for recent effective dates, changed minimum amounts (bond, insurance), new endorsement requirements, or modified experience thresholds. Compare each application's deficiencies against these policy changes. If a deficiency exists only because a policy threshold was recently raised, flag it as policy-impacted. If the deficiency would exist regardless of the policy change, set `false`.

### Stale or Unverified Correspondence

Correspondence IDs from the correspondence endpoint that have a status indicating unresolved, unverified, pending, or overdue. Match correspondence to applications by the application ID embedded in the correspondence ID (e.g., a correspondence ID containing `C-TR1-001` maps to application `C-TR1-001`). Also include any standalone correspondence IDs in the correspondence records (such as `COR-DIS-XXXX` patterns) that indicate unresolved issues. Include these in `stale_or_unverified_correspondence_ids` sorted ascending.

## Decision Rules: Liquor (Domain B)

### Recommended Posture

- **issue_restricted:** All risks identified in the application are covered by verified active controls, no verification gaps remain, the same-premises basis is confirmed (or not required), and there are no unresolved incidents, tax holds, or conflicting evidence.
- **request_follow_up:** Verification gaps remain (missing evidence, conflicting records, unresolved incidents or tax holds), or controls are not fully confirmed. This is the default when evidence is incomplete but not outright disqualifying.
- **deny:** Major unresolved incidents exist, a tax hold cannot be cleared, or there are serious and unresolvable control failures.

### Same Premises Basis

Set `same_premises_basis_applies` to `true` when the application references the same physical premises as a prior license at that location. Evidence comes from the liquor/applications endpoint (prior license references, same location ID) and site-evidence (consistent address/history). Set to `false` when it is a new location, when records contradict the same-premises claim, or when the template does not require same-premises evaluation.

### Covered Risk Codes

These are the risk areas that are currently addressed by verified controls. For each risk code in the template's `allowed_values`:
- Check if the application, site evidence, or incident records indicate this risk exists at the location.
- If the risk exists, check whether a corresponding verified control is active (from privileges, site evidence, or policies).
- Include the risk code in `covered_risk_codes` only if both conditions hold: the risk is present AND a verified control covers it.

Risks that are present but NOT covered by verified controls should appear in `verification_gap_codes` or inform `escalation_trigger_codes`, not in `covered_risk_codes`.

### Verification Gap Codes

For each gap code in the template's `allowed_values`, check the corresponding evidence:
- **Signage-related gaps:** Check site evidence for control signage records. Missing, conflicting, or stale signage → include the matching gap code.
- **Floor plan gaps:** Check site evidence for floor plan records. Conflicting or stale plans → include the matching gap code.
- **Notice/document gaps:** Check for neighbor notices, police memos, tax clearances. Missing or conflicting → include matching gap codes.
- **Photo/evidence gaps:** Check for site photos or other physical evidence requirements. Missing → include matching gap codes.
- **Incident follow-up gaps:** Check incidents for any with open/unresolved status → include the open incident follow-up code.
- **Tax hold gaps:** Check settlements or privileges for unresolved tax holds → include the matching gap code.

### Standard Obligation Codes vs. Location-Specific Control Codes

- **standard_obligation_codes:** Obligations that apply to ALL licenses of this class under current policy. Derive from the policies endpoint — look for class-wide requirements (e.g., ID checking, food service, hours restrictions).
- **location_specific_control_codes:** Controls currently active at THIS specific location. Derive from site evidence and privilege records — look for location-tagged controls (e.g., CCTV at this address, patio restrictions, security requirements).

The same code may appear in both lists if it is both a class-wide obligation and separately enforced at this location. Use only the template's `allowed_values` for each array.

### First 90-Day Plan

Build a monitoring plan covering the verification gaps and risk areas. Each entry pairs a `check_code` with a `timing` bucket. Assign timing based on urgency:
- **first_30_days:** Critical verifications needed immediately — signage checks, CCTV/camera walkthroughs, ID check observations, police memo follow-ups, tax clearance checks, food service verification.
- **days_31_60:** Secondary checks — after-hours visits, noise monitoring, ongoing compliance observation.
- **days_61_90:** Follow-up checks — reinspection of previously flagged items, patio boundary checks, log reviews.

Use only the `check_code` and `timing` values from the template's `allowed_values`. Order entries in intended operational sequence (earliest timing first). Each check should correspond to a specific verification gap or risk area.

### Escalation Trigger Codes

List conditions observable in the field that would trigger escalation to board or enforcement. Each trigger derives from an uncovered risk or verification gap. For each trigger code in the template's allowed set, include it if:
- The corresponding risk exists (from incident records or application data) AND it is not fully covered by verified controls, OR
- The corresponding verification gap exists and field observation would confirm a violation.

Example mappings:
- Missing camera coverage → `missing_camera_coverage` or `SECURITY_CCTV_CONTROL_FAILURE`
- Unresolved incident → `MAJOR_INCIDENT_REPORTED` or `unreported_violent_incident`
- After-hours risk → `AFTER_HOURS_VIOLATION` or `after_hours_service`
- Signage not verified → `CONTROL_SIGNAGE_NOT_VERIFIED`
- Tax hold unresolved → `TAX_HOLD_REOPENED` or `open_tax_hold_uncleared`
- Minor sale risk → `REFERRED_MINOR_SALE_UNRESOLVED` or `minor_sale`

Use only the template's `allowed_values` for escalation trigger codes.

## Decision Rules: Alcohol Renewal (Domain C)

### Violation Matching

For each target license, match violations from the violations endpoint by license number:

- Parse each violation record's ID and date. The violation ID typically encodes the license number (e.g., `AV-AL-TR3-007-1` matches license `AL-TR3-007`).
- **exact:** The violation ID contains the exact license number string.
- **close_address:** The violation references the same facility but a different or former license number — indicated by an ID pattern like `AV-AL-TR3-OLD-006-S1` where the numeric portion matches the target license number but with a different prefix. Use SQL to confirm facility name/address match.
- **uncertain:** The match is ambiguous or partial, and facility data does not clearly confirm it.

### Boundary Date

The prompt supplies a boundary date (release date). Violations dated strictly after the boundary date are excluded from the queue's violation counts and `matched_violation_ids`. These excluded violations must be listed in `post_boundary_violation_ids_excluded`, sorted ascending by violation ID.

Violations dated on or before the boundary date are included. Check the `renewal/rules` endpoint to confirm boundary handling if the rules endpoint is available.

### Next Step Label

- **board_review:** The licensee has a high volume of recent violations, or violations that individually or collectively warrant board-level attention (serious incidents, close_address matches requiring verification, or patterns of escalation). Typically assigned to the top-ranked entries.
- **manual_fine_check:** The licensee has a significant violation count but the violations are of a type that can be resolved through fine verification rather than board review.
- **manual_ALERT_check:** The licensee has a moderate violation count and needs alert-level verification — less urgent than board review or fine check.
- **additional_record_check:** The licensee has uncertain matches that require deeper record investigation before a recommendation can be made.

### Queue Ranking

Rank entries from most to least concerning using this priority order:

1. Group by `next_step_label` priority: **board_review** first, then **manual_fine_check**, then **manual_ALERT_check**, then **additional_record_check**.
2. Within each group, sort by `violation_count` descending (more violations = higher rank).
3. Within equal violation counts, sort by `most_recent_violation_date` descending (more recent = higher rank).
4. Within equal dates, sort by `license_no` ascending as a tiebreaker.

Assign ranks 1 through N with no gaps.

### Risk Tier

- **high:** next_step_label is board_review, or violation_count >= 3 with most_recent_violation_date within 90 days of the boundary date, or match_confidence is close_address/uncertain with recent violations.
- **medium:** next_step_label is manual_ALERT_check or additional_record_check, or lower violation counts.
- **low:** No matched violations or all violations are old and fully resolved.

### Summary

- `queue_size`: Number of entries in the queue (integer).
- `boundary_date`: The boundary date from the prompt (YYYY-MM-DD string).
- `post_boundary_violation_ids_excluded`: All violation IDs with dates after the boundary, sorted ascending.
- `close_or_uncertain_match_license_numbers`: License numbers whose match_confidence is close_address or uncertain, sorted ascending.
- `board_review_license_numbers`: License numbers whose next_step_label is board_review, sorted ascending.

## Cross-Referencing Patterns

**Contractor applications ↔ Bonds/Insurance:** Match by `application_id` embedded in bond and insurance records. Verify coverage amount against policy minimums. For bonds, check whether the bond is active (not cancelled). For insurance, check whether the policy is current as of the review date.

**Contractor applications ↔ License History:** Match by `application_id` or contractor identifier. Look for `active_suspension` status entries. A single active suspension entry on the history means the application cannot be approved.

**Contractor applications ↔ Violations:** Match by `application_id` or contractor identifier. Check for `open` or `unresolved` status. Distinguish serious from minor violations by the violation type or severity field.

**Contractor applications ↔ Correspondence:** Match by the application ID prefix embedded in correspondence IDs (e.g., `COR-C-TR1-001-1` → application `C-TR1-001`). Check the correspondence status for `unverified`, `pending`, `overdue`, or similar unresolved states. Also scan for standalone correspondence IDs (e.g., `COR-DIS-XXXX`) that indicate unresolved issues.

**Contractor applications ↔ Inspections:** Match by `application_id` or location/contractor identifier. Check for inspection statuses requiring follow-up (`safety_recheck`, `doc_gap`, `pending`).

**Liquor applications ↔ Site Evidence:** Match by `application_id` and `location_id`. Check for floor plans, control signage records, site photos, police memos, and neighbor notices. Compare dates for staleness.

**Liquor applications ↔ Incidents:** Match by `location_id`. Check for incidents with `open` or `unresolved` status.

**Liquor applications ↔ Settlements:** Match by `application_id`. Check for unresolved settlements or tax holds.

**Liquor applications ↔ Privileges:** Match by `application_id` and `location_id`. These define which controls are currently active at the location.

**Alcohol licensees ↔ Violations:** Match by license number embedded in violation ID. For close_address matches, use SQL to join on facility name or address.

## SQL Query Patterns

When REST endpoints do not provide direct filtering, use SQL. Common query shapes:

- Find violations matching a license: `SELECT * FROM violations WHERE violation_id LIKE '%' || $1 || '%'`
- Filter violations by date boundary: `SELECT * FROM violations WHERE violation_date <= $1`
- Join applications to bonds: `SELECT a.*, b.* FROM applications a LEFT JOIN bonds b ON a.application_id = b.application_id WHERE a.application_id = ANY($1)`
- Find stale correspondence: `SELECT * FROM correspondence WHERE status IN ('unverified', 'pending', 'overdue')`
- Match licensees to violations by facility name/address for close_address matching: `SELECT v.*, l.* FROM violations v JOIN licensees l ON v.facility_name = l.facility_name OR v.address LIKE '%' || l.address || '%'`

Always parameterize queries with `params` array. Set `limit` generously.

## Formatting Rules

- Output only the JSON object the template specifies. No prose, no markdown, no code fences, no commentary.
- Sort all arrays ascending (alphabetical/lexical) unless the template explicitly specifies a different ordering (e.g., ranked, chronological, or operational sequence).
- Remove duplicates from all code arrays.
- Use empty arrays `[]` when no items apply. Never use `null` or omit the key.
- Include every required top-level key from the template, even if its value is an empty array or zero count.
- For batch summaries, derive counts by iterating over the individual decisions. `approve_count + hold_count + deny_count` must equal the total number of applications.
- `high_risk_application_ids` includes only applications with `risk_tier: "high"`.
- `policy_impacted_application_ids` includes only applications with `policy_impacted: true`.
- Dates use `YYYY-MM-DD` format when present.
- Integer fields use integer types, not strings.
- Boolean fields use `true`/`false`, not strings.

## Common Pitfalls

- **Skipping an endpoint.** Every domain endpoint contributes data. An unfetched endpoint means missing cross-reference evidence and incorrect decisions. Fetch every endpoint the prompt lists for the domain.
- **Using codes outside the template.** The template's `allowed_values` are the only valid codes. If the data shows a condition not matching any allowed code, map it to the closest matching code or omit it. Never invent codes.
- **Ignoring ordering rules.** Templates specify ordering (ascending, lexical, by ID, etc.). Apply the exact ordering specified.
- **Forgetting the SQL endpoint.** When the prompt or environment lists `POST /api/sql`, use it. Cross-entity matching often requires SQL joins or LIKE queries that REST endpoints cannot provide.
- **Missing stale correspondence.** Check all correspondence records for unresolved statuses. Correspondence IDs may reference multiple applications — scan all of them, not just the ones whose prefix matches a target application.
- **Misidentifying policy impact.** A deficiency creates `policy_impacted: true` only when the current policy baseline is the cause. Check the policies endpoint's effective dates and thresholds. If a deficiency would exist under both old and new policies, it is not policy-impacted.
- **Including post-boundary violations in the queue.** Violations after the boundary date go only in `post_boundary_violation_ids_excluded`, never in `matched_violation_ids` or `violation_count`.
- **Inconsistent summaries.** The summary counts and ID lists must exactly reflect the individual application decisions above them. Recompute, don't estimate.
- **Using the wrong code set for a variant template.** Different tasks within the same domain may use different template `allowed_values`. Always use the template delivered with the task, not codes memorized from other runs.
