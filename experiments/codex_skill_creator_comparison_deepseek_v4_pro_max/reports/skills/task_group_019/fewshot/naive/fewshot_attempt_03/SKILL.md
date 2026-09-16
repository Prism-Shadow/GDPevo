---
name: licensing-reviewer
description: Solve state licensing review tasks by querying the task environment API and applying regulatory decision rules for contractor eligibility, liquor license transfers, and alcohol renewal screening.
---

# Licensing Reviewer

This skill solves state regulatory licensing review tasks across three
domains: contractor eligibility batches, restricted liquor license staff
packages, and alcohol renewal manual-review queues. Every task uses the same
shared licensing environment; this skill provides the decision logic.

## Environment Setup

Every task provides a base URL. Substitute it for `<TASK_ENV_BASE_URL>` below.
All GET endpoints return JSON arrays. The SQL endpoint accepts only SELECT.

```
GET  <TASK_ENV_BASE_URL>/health
GET  <TASK_ENV_BASE_URL>/api/policies
POST <TASK_ENV_BASE_URL>/api/sql
Header: X-Task-Token: licensing-review-019
Body: {"query": "...", "params": [], "limit": 1000}
```

The health endpoint confirms database availability and record counts.

## Task Routing

Read the prompt and the input answer template to identify which task type is
requested:

1. **Contractor eligibility batch** — The prompt mentions "contractor",
   "applications", and target IDs like `C-TR*-*`. The answer template has
   `application_decisions` and `summary` top-level keys.

2. **Restricted liquor license staff package** — The prompt mentions "liquor",
   a single application like `L-TR*-*`, and a location like `LOC-TR*`. The
   answer template has `recommended_posture`, `covered_risk_codes`,
   `verification_gap_codes`, `standard_obligation_codes`,
   `location_specific_control_codes`, `first_90_day_plan`, and
   `escalation_trigger_codes`.

3. **Alcohol renewal manual-review queue** — The prompt mentions "renewal",
   license numbers like `AL-TR*-*`, a release boundary date, and a target
   queue size. The answer template has `queue` (ranked list) and `summary`.

Use the template's enum values as the authoritative vocabulary for that task.
Never invent deficiency codes, risk codes, or action labels outside the
template's allowed values.

---

## Task 1: Contractor Eligibility Batch

### Data Sources

Fetch all records upfront, then filter to the target application IDs:

| Endpoint | Key fields |
|---|---|
| `/api/policies` | `policy_id`, `family`, `rule_code`, `effective_date`, `details_json`, `citation` |
| `/api/contractor/applications` | `application_id`, `trade`, `requested_class`, `years_experience`, `endorsement_status`, `prior_license_id`, `self_disclosed_issue` |
| `/api/contractor/bonds` | `application_id`, `amount`, `status`, `cancel_date` |
| `/api/contractor/insurance` | `application_id`, `amount`, `status`, `expiration_date` |
| `/api/contractor/license-history` | `license_id` (join on `prior_license_id`), `status`, `status_date` |
| `/api/contractor/violations` | `related_application_id`, `severity`, `status`, `theme` |
| `/api/contractor/correspondence` | `related_application_id`, `verified_by_agency`, `received_date`, `assertion_type` |
| `/api/contractor/inspections` | `related_application_id`, `finding_code`, `result`, `inspection_date` |

Also use SQL for targeted queries when the GET endpoints contain noise. Example:

```sql
SELECT * FROM contractor_applications WHERE application_id IN ('C-TR1-001','C-TR1-002',...)
```

### Policy Matching

Map each application to its governing policy. Parse `details_json` for the
policy's numeric thresholds. The policies in the environment are:

| Policy | Rule Code | Trade / Class | Bond Min | Insurance Min | Exp Min | Endorsement | Eff. Date |
|---|---|---|---|---|---|---|---|
| POL-CON-001 | CON-ELE-ClassA | Electrical / A | 50000 | 1000000 | 5 | EE-1 | 2025-01-01 |
| POL-CON-002 | CON-PLU-ClassB | Plumbing / B | 30000 | 750000 | 4 | PH-2 | 2025-03-15 |
| POL-CON-003 | CON-HVA-ClassB | HVAC / B | 25000 | 500000 | 3 | MECH-H | 2025-01-01 |
| POL-CON-004 | CON-GEN-ClassA | General Building / A | 75000 | 1000000 | 5 | GB-A | 2025-03-15 |
| POL-CON-005 | CON-ROO-Limited | Roofing / Limited | 20000 | 500000 | 2 | none | 2025-01-01 |
| POL-CON-006 | CON-SOL-Specialty | Solar / Specialty | 30000 | 750000 | 3 | SOL-PLUS | 2025-03-15 |
| POL-CON-LEGACY | CON-LEGACY | Prior baseline | — | — | — | — | 2024-01-01 |

Match by `trade` and `requested_class`. When the prompt provides a review date,
use it to decide whether insurance has expired (expiration_date < review_date).
When no explicit review date is given, treat insurance with expiration_date
before roughly the latest application submitted_date + a few months as expired,
and insurance with status "pending" as not yet confirmed.

### Deficiency Rules

Check each application against these rules in order. **Multiple deficiencies can
apply.** Map to the deficiency codes from the answer template.

**Bond deficiencies:**
- No active bond: no bond record with `status = "active"` → `no_active_bond` / `bond_cancelled`
- Active bond amount < policy minimum → `bond_shortfall`

**Insurance deficiencies:**
- No active insurance: all records expired or cancelled → `insurance_not_current` / `insurance_expired`
- Active insurance `status = "pending"` → `insurance_pending`
- Active insurance amount < policy minimum → `insurance_shortfall`

**Endorsement deficiencies:**
- `endorsement_status = "missing"` and policy requires endorsement → `endorsement_missing` / `endorsement_not_verified`
- `endorsement_status = "pending"` and policy requires endorsement → `endorsement_pending` / `endorsement_not_verified`
- `endorsement_status = "verified"` or `"not_required"` → no deficiency

**Experience deficiencies:**
- `years_experience` < policy `minimum_years_experience` → `experience_shortfall`

**License history / suspension:**
- Prior license (`prior_license_id`) has `status = "suspended"` in license-history → `active_suspension`

**Violations:**
- Open violation with `severity = "serious"` → `open_serious_violation` / `unresolved_serious_complaint`
- Open violation with `severity = "minor"` → `open_minor_violation`
- Resolved or dismissed violations → no deficiency

**Inspection deficiencies:**
- `finding_code = "DOC_GAP"` and `result = "fail"` or `"conditional"` → `inspection_doc_gap`
- `finding_code = "SAFETY_RECHECK"` and `result = "fail"` → `inspection_safety_recheck`
- `finding_code = "SAFETY_RECHECK"` and `result = "pass"` → no deficiency
- `finding_code = "NONE"` and `result = "pass"` or `"conditional"` → no deficiency

### Determination and Risk Tier

```
DENY when: active_suspension OR open_serious_violation/unresolved_serious_complaint
           OR (inspection_safety_recheck AND result=fail) OR insurance_pending
           combined with other major deficiencies.

APPROVE when: zero deficiencies, bond active with sufficient amount,
              insurance active/current with sufficient amount, endorsement ok,
              experience meets minimum, no suspension, no open violations.

HOLD when: any other deficiency present but no DENY trigger.
```

Risk tier:
- `high` — DENY determination, or active_suspension, or open_serious_violation
- `medium` — HOLD determination
- `low` — APPROVE determination only

### Required Actions

Map each deficiency to one or more actions from the template's allowed values:

| Deficiency | Action(s) |
|---|---|
| no_active_bond / bond_cancelled | `file_active_bond` / `obtain_current_bond` |
| bond_shortfall | `increase_bond` / `increase_bond_amount` |
| insurance_not_current / insurance_expired | `provide_current_insurance` / `renew_insurance` |
| insurance_pending | `verify_insurance_binding` |
| insurance_shortfall | `increase_insurance` / `increase_insurance_amount` |
| endorsement_missing / endorsement_not_verified / endorsement_pending | `verify_endorsement` / `obtain_required_endorsement` / `verify_pending_endorsement` |
| experience_shortfall | `submit_experience_evidence` / `document_experience` |
| active_suspension | `clear_suspension` / `board_review_suspension` (+ `board_review`) |
| open_serious_violation / unresolved_serious_complaint | `resolve_complaint` / `resolve_serious_violation` (+ `board_review`) |
| open_minor_violation | `resolve_minor_violation_review` |
| inspection_doc_gap | `clear_document_gap` |
| inspection_safety_recheck | `complete_safety_recheck` |

Include `board_review` as an additional action when the determination is DENY
or when active_suspension or unresolved_serious_complaint is present.

### policy_impacted

Set `true` when the application is governed by a policy whose thresholds exceed
the prior baseline (POL-CON-LEGACY) AND at least one deficiency is directly
caused by that policy threshold (bond_shortfall, insurance_shortfall,
experience_shortfall, endorsement_missing/not_verified/pending). Set `false`
when the application has no deficiencies, when all deficiencies are
non-policy-driven (e.g., bond cancelled, insurance expired, inspection
findings, suspension), or when the governing policy's effective_date predates
the task's implicit new-policy cutoff. Read the prompt for any review-date or
policy-cutoff guidance; absent that, treat policies effective January 2025 as
the established baseline and policies effective March 2025 or later as the
"current policy change."

### Summary

Count APPROVE / HOLD / DENY. Collect `high_risk_application_ids` (all
applications with risk_tier=high). Collect `policy_impacted_application_ids`
(all with policy_impacted=true). Collect `stale_or_unverified_correspondence_ids`
— correspondence records where `verified_by_agency = 0` that are linked to any
target application. Sort all lists ascending.

---

## Task 2: Restricted Liquor License Staff Package

### Data Sources

| Endpoint | Key fields |
|---|---|
| `/api/policies` | POL-LIQ-001, POL-LIQ-002 for control/review rules |
| `/api/liquor/applications` | `application_id`, `license_class`, `location_id`, `dba`, `address` |
| `/api/liquor/settlements` | `location_id`, `basis_code`, `controls_json`, `settlement_type`, `effective_date` |
| `/api/liquor/privileges` | `license_class`, `obligation_code`, `standard_required` |
| `/api/liquor/incidents` | `location_id`, `risk_code`, `severity`, `status`, `incident_date` |
| `/api/liquor/site-evidence` | `location_id`, `evidence_code`, `status`, `notes` |

Filter to the target application and its location. Fetch all settlements,
incidents, and evidence for that location. Also fetch privileges for the
license class of the target application.

### Recommended Posture

- `issue_restricted` — All verification evidence is present and current, no
  open incidents, all settlement controls are active and confirmed.
- `deny` — Active major incidents (board-order, high severity open/referred),
  unresolved tax holds, missing critical evidence, or settlement controls
  that have been breached.
- `request_follow_up` — Gaps exist (missing/stale evidence, open incidents,
  conflicting records) but no outright denial trigger. This is the most
  common posture for applications with verification gaps.

### same_premises_basis_applies

Set `true` when any settlement for the location has `basis_code =
"SAME_PREMISES"`. This is typically true when the location has a legacy
registration or historic settlement that activates the same-premises review
policy (POL-LIQ-001).

### covered_risk_codes

Collect risk codes from settlements where `controls_json` shows `"active":
true`. Each active settlement's `basis_code` becomes a covered risk. Also
check for SAME_PREMISES — include it when present. Scan incidents: closed
incidents with risk codes that have corresponding active settlement controls
are "covered." Include risk codes for any active settlement controls.

Use only the codes from the template's allowed list.

### verification_gap_codes

Map each piece of site evidence to its status:

| Evidence status / condition | Gap code |
|---|---|
| `status = "missing"` | `CONTROL_SIGNAGE_CURRENT_MISSING` / `control_signage_missing` / `SITE_PHOTO_MISSING` / `camera_evidence_missing` / `food_service_evidence_missing` / `TAX_CLEARANCE_MISSING` / `NEIGHBOR_NOTICE_MISSING` |
| `status = "conflicting"` | `CONTROL_SIGNAGE_CONFLICTING` / `FLOOR_PLAN_CONFLICTING` / `POLICE_MEMO_CONFLICTING` |
| `status = "stale"` | `FLOOR_PLAN_STALE` |
| Open incident with `status = "referred"` | `OPEN_INCIDENT_FOLLOW_UP` |
| `evidence_code = "TAX_CLEARANCE"` with `status != "verified"` | `tax_hold_unresolved` / `TAX_CLEARANCE_MISSING` |
| `evidence_code = "POLICE_MEMO"` with `status = "conflicting"` | `POLICE_MEMO_CONFLICTING` / `police_memo_identity_note` |
| Late-night license class and no camera evidence | `late_night_monitoring_needed` |

Map each evidence_code/status combination to the template's allowed gap codes.
Use the template's specific vocabulary — it varies between train_002 and
train_005.

### standard_obligation_codes

Query privileges for the application's `license_class`. Every privilege with
`standard_required = 1` is a standard obligation. Return those codes. Only
include codes from the template's allowed list.

### location_specific_control_codes

Collect `controls` from the `controls_json` of active settlements
(`"active": true`) for the location. These are the location-specific controls.
Return only codes present in the template's allowed list. Do not duplicate
codes that are already standard obligations unless they appear separately in
the active controls.

### first_90_day_plan

Build a monitoring plan from the template's allowed `check_code` and `timing`
values. The plan should address every verification gap and open risk:

- Missing/stale evidence → early checks (first_30_days)
- Active controls verification → early checks (first_30_days)
- Late-night or after-hours concerns → days_31_60 or days_61_90
- Noise/patio boundary → days_61_90 (allow time for seasonal patterns)
- Incident follow-up → first_30_days
- Camera/CCTV checks → first_30_days
- Tax clearance → first_30_days

Use only `check_code` and `timing` enum values from the template. Each
check_code/timing pair must be unique. Sort by operational sequence rather than
alphabetically — put immediate verification checks first, followed by
observation-based checks.

### escalation_trigger_codes

Every unchecked risk becomes an escalation trigger:
- Open incidents (referred) → `MAJOR_INCIDENT_REPORTED` / `unreported_violent_incident`
- Missing CCTV/camera evidence → `SECURITY_CCTV_CONTROL_FAILURE` / `missing_camera_coverage` / `footage_not_produced`
- After-hours risk → `AFTER_HOURS_VIOLATION` / `after_hours_service`
- Unverified control signage → `CONTROL_SIGNAGE_NOT_VERIFIED`
- Tax hold unresolved → `TAX_HOLD_REOPENED` / `open_tax_hold_uncleared`
- Minor sale incidents → `REFERRED_MINOR_SALE_UNRESOLVED` / `minor_sale`
- Noise/patio breach risk → `noise_or_patio_breach` / `patio_boundary_failure`
- ID check gaps → `id_check_failure`

Use only trigger codes from the template's allowed list.

---

## Task 3: Alcohol Renewal Manual-Review Queue

### Data Sources

| Endpoint | Key fields |
|---|---|
| `/api/alcohol/licensees` | `license_no`, `facility_name`, `address`, `active`, `successor_to` |
| `/api/alcohol/violations` | `license_no`, `violation_id`, `violation_date`, `severity`, `disposition`, `fine_balance`, `alert_flag`, `source_name`, `address`, `facility_name` |
| `/api/renewal/rules` | `rule_id`, `release_boundary`, `details_json` |
| `/api/policies` | POL-REN-001 for boundary/match guidance |

### Boundary Rule
The prompt specifies a release boundary date (e.g., `2025-04-10`). Use only
violations with `violation_date` on or before the boundary date. Violations
after the boundary date are excluded but recorded in the summary under
`post_boundary_violation_ids_excluded`.
The matching renewal rule is the one whose `release_boundary` matches the
prompt's boundary date. Parse its `details_json` for:
- `alert_flag_requires_manual_review: true`
- `late_rows_are_distractors: true` — post-boundary violations are distractors
- `unpaid_fines_require_hold: true`
- `use_violations_on_or_before: "<boundary date>"`

### License-Violation Matching

Match violations to licensees using `license_no`. When a licensee has
`successor_to` set, also check for violations under the predecessor license
number — mark those matches as `close_address` or `uncertain` per
POL-REN-001 (`successor_match_mark_uncertain: true`).

Match confidence levels:
- `exact` — violation's `license_no` exactly matches the target license number
- `close_address` — violation matches via `successor_to` or address similarity
- `uncertain` — match is ambiguous (e.g., successor chain, address drift)

### Queue Ranking

Rank licenses by priority for manual review. The primary sort key is severity
and urgency:

1. Licenses with `alert_flag = 1` violations get highest priority
2. Within that, sort by `violation_count` descending
3. Then by `most_recent_violation_date` descending (more recent = higher rank)
4. Ties broken by `license_no` ascending

Risk tier:
- `high` — any matched violation has `severity = "serious"` or `alert_flag = 1`
  with multiple violations, OR `fine_balance > 0` with open violations
- `medium` — violations present but none serious, or fine_balance = 0
- `low` — minimal or no pre-boundary violations

Next step label:
- `board_review` — serious violations, alert_flag=1 with multiple violations,
  or close_address/uncertain matches with violations
- `manual_fine_check` — unpaid fines (`fine_balance > 0`)
- `manual_ALERT_check` — alert_flag=1 but less severe patterns
- `additional_record_check` — uncertain matches needing further verification

### Summary

- `queue_size` — number of entries (should equal the prompt's target queue size)
- `boundary_date` — the boundary date from the prompt
- `post_boundary_violation_ids_excluded` — all violation IDs with date >
  boundary, sorted ascending
- `close_or_uncertain_match_license_numbers` — licenses where any match is not
  `exact`, sorted ascending
- `board_review_license_numbers` — licenses with `next_step_label =
  "board_review"`, sorted ascending

---

## General Rules

### Answer Format

Return only the JSON object matching the input answer template. No prose,
citations, markdown, or extra keys. Use the exact enum values from the
template — do not invent codes.

### Empty Values

Use `[]` for empty arrays and `0` for zero counts. Never use `null` for a
required array field.

### Ordering

Sort application IDs, license numbers, and violation IDs in ascending lexical
order within each list. Queue entries are ordered by rank ascending. Plan
items are ordered by operational sequence.

### Dates

Use YYYY-MM-DD format throughout. When the prompt provides a review date, use
it for insurance/bond currency checks. When it does not, infer from submitted
dates and record dates.

### Stale Correspondence

Correspondence with `verified_by_agency = 0` linked to any target application
is "stale or unverified." Include those correspondence IDs in the summary.
