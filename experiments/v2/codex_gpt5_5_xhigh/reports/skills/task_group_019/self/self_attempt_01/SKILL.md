---
name: licensing-structured-review
description: Use for structured licensing examiner tasks that require JSON decisions, restricted liquor staff packages, or alcohol renewal manual-review queues from a shared licensing data environment.
---

# Licensing Structured Review

Use this skill when the user asks for a licensing review output from a task environment: contractor eligibility batches, restricted liquor-license control packages, or alcohol renewal manual-review queues.

## Core Workflow

1. Read the user prompt and the required output template before fetching data.
2. Read `environment_access.md` if a task environment is involved. Use only the base URL, endpoints, and SQL token listed there; do not use unrelated network sources.
3. Fetch only relevant records. Prefer target-filtered SQL when `/api/sql` is allowed; otherwise use the listed GET endpoints and filter locally.
4. Decode embedded JSON fields such as `details_json` and `controls_json`.
5. Build the answer from records and the template. Emit only allowed keys and enum values.
6. Recompute summary counts and summary ID arrays from item-level decisions. Do not hand-enter summaries independently.

If the prompt asks for JSON only, return no prose, markdown, comments, citations, or extra keys.

## Schema Discipline

- Preserve exact target IDs from the prompt.
- Use the ordering specified by the template. If unspecified, use deterministic ordering: IDs lexically ascending; dates ascending for evidence lists; priority queues by rank.
- Deduplicate array values.
- Use empty arrays rather than omitting list fields.
- Use exact enum spelling from the payload. If the evidence suggests a concept but the schema lacks that code, omit it or map to the nearest allowed synonym.
- Use the prompt's review date or release boundary for date-sensitive tests. Do not use the conversation date unless the prompt explicitly says to.

## Contractor Batch Reviews

Fetch contractor policies, applications, bonds, insurance, license history, violations, correspondence, and inspections for the target application IDs.

### Policy Selection

- Match the contractor policy by trade and requested class. Decode the policy `details_json` for minimum bond, minimum insurance, minimum years of experience, required endorsement, and serious-open-violation behavior.
- Treat the current 2025 policy baseline as controlling unless the prompt says otherwise.
- For `policy_impacted`, compare against a legacy/prior baseline only when the policies provide one. Mark true only when the current baseline creates a deficiency or material flag that would not have applied before, such as a new specialty endorsement requirement or a current bond threshold above the prior reduced threshold.

### Deficiency Checks

For each application:

- **Bond**: A current bond must have active status, no effective cancellation, and amount at or above policy minimum. Cancelled/expired-only coverage is a no-current-bond condition; active but under amount is a shortfall.
- **Insurance**: A current insurance row should be active, verified/bound, unexpired as of the review date when provided, and at or above policy minimum. Pending status is not fully current. Active rows that expired before the review date are expired.
- **Endorsement**: If policy requires an endorsement, `verified` passes, `pending` remains a pending/not-verified deficiency, and `missing` remains a missing/not-verified deficiency. If policy has no required endorsement, `not_required` passes.
- **Experience**: Years below the policy minimum create an experience shortfall.
- **License history**: A prior license with suspended status or notes showing active suspension is an active-suspension blocker.
- **Violations**: Open serious violations or complaints are blockers when policy says serious open violations block. Open minor violations are remediable review items when the schema has a minor code. Resolved or dismissed violations are background only.
- **Inspections**: Failed or conditional `DOC_GAP` findings map to document-gap actions when supported. Failed or conditional `SAFETY_RECHECK` findings map to safety-recheck actions when supported. Passing inspection findings do not create deficiency codes.
- **Correspondence**: Do not let applicant-only, stale, conflicting, pending outside-agency, or unverified correspondence override registry/system records. Include stale or unverified correspondence IDs in the summary when the schema asks for them.

### Code Mapping

Map evidence to the exact allowed names in the template:

- No current bond: `bond_cancelled` / `no_active_bond`; action `obtain_current_bond` / `file_active_bond`.
- Bond amount below minimum: `bond_shortfall`; action `increase_bond_amount` / `increase_bond`.
- Pending or unverified insurance: `insurance_pending` / `insurance_not_current`; action `verify_insurance_binding` / `provide_current_insurance`.
- Expired insurance: `insurance_expired`; action `provide_current_insurance` / `renew_insurance`.
- Insurance amount below minimum: `insurance_shortfall`; action `increase_insurance_amount` / `increase_insurance`.
- Missing endorsement: `endorsement_missing` / `endorsement_not_verified`; action `obtain_required_endorsement` / `verify_endorsement`.
- Pending endorsement: `endorsement_pending` / `endorsement_not_verified`; action `verify_pending_endorsement` / `verify_endorsement`.
- Experience below minimum: `experience_shortfall`; action `submit_experience_evidence` / `document_experience`.
- Active suspension: `active_suspension`; action `board_review_suspension`, `clear_suspension`, or `board_review`.
- Open serious violation/complaint: `open_serious_violation` / `unresolved_serious_complaint`; action `resolve_serious_violation`, `resolve_complaint`, or `board_review`.
- Open minor violation: `open_minor_violation`; action `resolve_minor_violation_review`.
- Inspection document gap: `inspection_doc_gap`; action `clear_document_gap`.
- Inspection safety recheck: `inspection_safety_recheck`; action `complete_safety_recheck`.

### Determination And Risk

- `DENY`: active suspension or unresolved/open serious blocker. List all applicable deficiencies and actions, including remediable ones.
- `HOLD`: one or more remediable deficiencies, but no denial blocker.
- `APPROVE`: no current deficiencies.
- `high` risk: denial blockers, open serious discipline, or active suspension.
- `medium` risk: remediable financial, endorsement, experience, open minor, or inspection deficiencies.
- `low` risk: approval with no current deficiency.

## Restricted Liquor Staff Packages

Fetch policies, the target liquor application, settlements, privileges, incidents, and site evidence for the target location.

### Evidence Rules

- `same_premises_basis_applies` is true only when an active current settlement basis is `SAME_PREMISES`.
- `standard_obligation_codes` come from `liquor_privileges` where the application license class matches and `standard_required` is true.
- `location_specific_control_codes` come from active current settlement `controls_json.controls`, not from ordinary standard obligations unless those controls are also active location controls.
- Treat expired or inactive settlement rows as history. They may explain the basis but do not supply current controls.
- Current active settlement basis codes and non-dismissed incidents supply the risk universe. A risk is covered only when active controls plausibly address it.

Common coverage mapping:

- `ID_CHECK` covers `MINOR_SALE`, `SALE_TO_MINOR`, and age-check risks.
- `HOURS` covers `AFTER_HOURS`.
- `SECURITY` and `CCTV` cover `ASSAULT`, `PUBLIC_SAFETY`, and camera/security risks.
- `NOISE` covers `NOISE`.
- `PATIO` covers patio-boundary risks.
- `FOOD_SERVICE` covers `FOOD_SERVICE_GAP`.
- `TAX_HOLD` needs tax clearance; ordinary operating controls do not cover it.

### Verification Gaps

Map site evidence and incident status to the exact enum style in the template:

- Missing evidence: `*_MISSING` or lowercase `*_missing`.
- Stale evidence: `*_STALE` when the schema allows it.
- Conflicting evidence: `*_CONFLICTING` or lowercase `*_conflicting`.
- Current missing control signage: use `CONTROL_SIGNAGE_CURRENT_MISSING` if available.
- Open or referred incident needing staff action: `OPEN_INCIDENT_FOLLOW_UP` or a schema-specific unresolved risk code.
- Open tax hold: `TAX_CLEARANCE_MISSING`, `tax_hold_unresolved`, or an allowed tax-hold gap.
- If the prompt specifically asks about hotel-lounge, camera, food-service, or late-night evidence, verify those subjects directly. If current evidence is absent or conflicting and the schema has a matching code, include `camera_evidence_missing`, `food_service_evidence_missing`, or `late_night_monitoring_needed`.

### Posture, Monitoring, And Escalation

- `deny`: uncontrolled major risk, unresolved legal bar, or no viable restricted-issuance basis.
- `request_follow_up`: material verification gaps, open/referred incidents, unresolved tax issues, or conflicting site evidence.
- `issue_restricted`: active controls cover the material risks and remaining work is monitorable through ordinary first-90-day checks.
- Build the first-90-day plan from active controls, verification gaps, and open risks. Put critical verification in `first_30_days`, field observation in `days_31_60`, and log/review checks in `days_61_90`, unless the schema requires lexical order.
- Escalation triggers should mirror the unresolved risks and control failure modes, using only allowed trigger enums.

## Alcohol Renewal Manual-Review Queues

Fetch target alcohol licensees, alcohol violations, and renewal rules. Use the release boundary in the prompt or the matching renewal rule.

### Matching

- Review only current target licenses unless the prompt says otherwise.
- Include violations with `violation_date` on or before the boundary date.
- Exclude post-boundary rows from queue calculations and list their IDs in the summary when requested.
- Prefer exact `license_no` matches.
- If a current license has `successor_to`, include predecessor-license violations on or before the boundary and mark the target's match confidence `uncertain`.
- If exact license is absent but normalized address/facility evidence clearly matches, use `close_address` when allowed.
- If both exact and predecessor/address matches are used for one target, use the least-certain confidence among them.

### Queue Fields

- `matched_violation_ids`: sort by violation date ascending, then violation ID ascending.
- `violation_count`: number of matched pre-boundary violations.
- `most_recent_violation_date`: latest matched pre-boundary violation date.
- `match_confidence`: `exact`, `close_address`, or `uncertain`, per the evidence used.
- `risk_tier`:
  - `high`: any serious violation, active/open/pending serious matter, unresolved unpaid fine, or uncertain successor match with serious/alert evidence.
  - `medium`: medium severity, multiple alert flags, fine balance above zero, or open/pending non-serious matter.
  - `low`: only minor/settled/paid/warning history with no balance or alert concern.
- `next_step_label` priority:
  - `board_review` for high-risk serious/open/pending matters.
  - `manual_fine_check` for any positive fine balance or unpaid-fine theme.
  - `manual_ALERT_check` for alert-flagged records without a stronger next step.
  - `additional_record_check` for close/uncertain matches or weak evidence without a stronger next step.

### Ranking And Summary

Rank queue entries deterministically:

1. Risk tier: high, then medium, then low.
2. Next-step priority: board review, fine check, alert check, additional record check.
3. Violation count descending.
4. Most recent violation date descending.
5. License number ascending.

Use ranks `1..N` with no gaps. Summary fields should be calculated from the queue and excluded rows:

- `queue_size`: number of queue entries.
- `boundary_date`: exact boundary date used.
- `post_boundary_violation_ids_excluded`: excluded IDs sorted lexically unless the schema says otherwise.
- `close_or_uncertain_match_license_numbers`: target license numbers whose match confidence is not exact, sorted.
- `board_review_license_numbers`: target license numbers whose next step is `board_review`, sorted.
