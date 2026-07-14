# Cascadia Licensing Review Portal (CLRP) — Review Skill

## Overview

This skill covers eligibility reviews, license assessments, manual-review
queues, and monitoring plans within the CLRP domain. Every task follows a
**fetch → filter → match → decide → format** pipeline against a remote
CLRP API. Output is always a single JSON object conforming to the supplied
answer-template schema; never emit markdown, prose, or narrative outside
the JSON.

## Environment

The CLRP base URL is provided at task time via an `environment_access.md`
or `TASK_ENV_BASE_URL` placeholder. All API calls use this base. Never
assume localhost, inspect local files, or run setup scripts. The remote
environment is authoritative.

## API Surface & Source Precedence

### Contractor eligibility reviews
| Source | Endpoint | Notes |
|---|---|---|
| Applications | `GET /api/contractors/applications?batch_id=...` | Primary roster |
| Batch CSV export | `GET /exports/contractor_batch_<id>.csv` | Redundant with applications; use for cross-check only |
| Bonds | `GET /api/contractors/bonds?name=<legal_name>` | Actual bond amount + status |
| Insurance | `GET /api/contractors/insurance?name=<legal_name>` | Verification status + coverage |
| Violations | `GET /api/contractors/violations?name=<legal_name>` | Penalty amounts + resolution |
| Complaints | `GET /api/contractors/complaints?name=<legal_name>` | Open/closed; may link field notes |
| Field notes | `GET /api/contractors/field-notes?name=<legal_name>` | Inspector findings + holds |
| Correspondence | `GET /api/contractors/correspondence?batch_id=...` | Material notices per batch |
| Bulletins | `GET /api/contractors/bulletins?effective_on=YYYY-MM-DD` | Rule thresholds |

### Alcohol license reviews
| Source | Endpoint | Notes |
|---|---|---|
| Applications | `GET /api/alcohol/applications?review_month=YYYY-MM` | All apps in review month |
| Premises | `GET /api/alcohol/premises?premises_id=...` | Prior licensee + risk |
| Incidents | `GET /api/alcohol/incidents?premises_id=...` | Dispositions, severity |
| Settlements | `GET /api/alcohol/settlements?premises_id=...` | Prior/current posture |
| Restrictions | `GET /api/alcohol/restrictions?premises_id=...` | Location-specific + standard |
| Standard obligations | `GET /api/alcohol/standard-obligations?license_type=...` | License-type defaults |

### Renewal manual-review queues
| Source | Endpoint | Notes |
|---|---|---|
| Licensees | `GET /api/renewals/licensees?release_batch=...` | Roster with successor hints |
| Roster CSV | `GET /exports/renewal_roster_<batch>.csv` | Redundant; cross-check |
| Violations by city | `GET /api/renewals/violations?city=...` | Per-city violation records |
| **Address search (critical)** | `GET /api/search/address?address=...` | Returns both the licensee AND all violations at that address — use this as the definitive matching source |

### Alcohol monitoring plans
| Source | Endpoint | Notes |
|---|---|---|
| Same as alcohol license review, plus: | | |
| Address search | `GET /api/search/address?address=...` | Cross-reference premises history |

## Cutoff / Boundary Date Handling

Every review has a cutoff or boundary date (stated in the task prompt or
answer template):

- **Violations, correspondence, field notes, incidents:** only consider
  records dated **on or before** the cutoff date. Records after the cutoff
  are excluded from deficiency counts and decision logic.
- **Bulletins:** effective on or before the cutoff apply. Bulletins
  effective exactly on the cutoff date do apply.
- **Renewal release boundary:** exclude violation records with
  `violation_date` strictly after the boundary. Count these in
  `excluded_post_boundary_count`.
- For correspondence, the `received_date` is the date to check against the
  cutoff.

## Contractor Eligibility Determination Logic

### Step 1: Gather all data per application
For each application in the batch: bonds, insurance, violations,
complaints, field notes, correspondence (filtered by cutoff).

### Step 2: Apply bulletin thresholds
Match bulletins to application trades. A bulletin applies when its
`trade_scope` equals the application trade or is `ALL`.

- **EXAM_MINIMUM:** `exam_score < threshold_value` → `EXAM_SCORE_SHORTFALL`
- **BOND_MINIMUM:** Compare the **actual bond record amount** (not the
  declared amount) against `threshold_value`. If `actual < threshold` →
  `BOND_SHORTFALL`.
- **INSURANCE_MINIMUM:** Compare actual insurance `coverage_amount` against
  threshold. If below → `INSURANCE_VERIFY`.
- **EXPERIENCE_MINIMUM:** `experience_years < threshold` →
  `EXPERIENCE_VERIFY`.

### Step 3: Check bond status
- Bond `status: "cancelled"` → `BOND_CANCELLED`
- Bond `status: "reduced"` with amount below bulletin → `BOND_SHORTFALL`
- Bond note "below current bulletin minimum" → `BOND_SHORTFALL`

### Step 4: Check insurance status
- `verification_status: "pending"` → `INSURANCE_VERIFY`
- `status: "expired"` or `verification_status: "stale"` → `INSURANCE_VERIFY`

### Step 5: Check violations (pre-cutoff)
- Any unresolved violation → `UNRESOLVED_PENALTY`
- Violation type "fraudulent registration" or "unlicensed activity" →
  `DISQUALIFYING_CONDUCT`
- AG referral (`ag_referral: 1`) on unresolved violations strengthens the
  case for HOLD or DENY

### Step 6: Check field notes
- `finding_type: "open hold"` and `recommended_action` contains "hold" →
  `FIELD_NOTE_HOLD`

### Step 7: Check correspondence (pre-cutoff only)
- `document_status: "needs_review"` or `"new"` on a `material notice` →
  `CORRESPONDENCE_HOLD`

### Step 8: Check background and prior registration
- `background_status: "adverse"` or `"needs_review"` with a non-empty
  `prior_registration_id` → `ADVERSE_PRIOR_REGISTRATION`

### Step 9: Determine outcome
- **APPROVE:** `NO_DEFICIENCY` only. No issues found.
- **HOLD:** One or more fixable issues (bond shortfall, insurance verify,
  unresolved penalty, field note hold, correspondence hold, financial
  statement missing, experience verify). Use `COMBINED_HOLD_REVIEW` for
  multiple issues.
- **DENY:** Reserved for `ADVERSE_PRIOR_REGISTRATION` combined with
  `DISQUALIFYING_CONDUCT`, or multiple severe unresolved violations with
  AG referrals. Be conservative — prefer HOLD when issues are potentially
  fixable.

### Step 10: Next action mapping
- `BOND_SHORTFALL` → `REQUEST_BOND_RIDER`
- `BOND_CANCELLED` → `REQUEST_REPLACEMENT_BOND`
- `INSURANCE_VERIFY` → `REQUEST_INSURANCE_VERIFICATION`
- `UNRESOLVED_PENALTY` → `REFER_UNRESOLVED_PENALTY`
- `FIELD_NOTE_HOLD` → `REQUEST_FIELD_CLEARANCE`
- Multiple issues → `COMBINED_HOLD_REVIEW`
- `DENY` → `DENY_APPLICATION`
- No issues → `NO_ACTION`

## Bulletin Impact Calculation

- **applicable_bulletin_ids:** List every bulletin effective on or before
  the cutoff whose `trade_scope` matches a trade present in the batch or
  is `ALL`. Sort ascending.
- **applications_changed_by_2026_bulletins:** An application is
  "changed" when, without the bulletin(s), its bond/insurance/exam would
  have passed (using the bulletin's `prior_rule` threshold), but with the
  bulletin it triggers a deficiency.
- **deficiency_count_by_rule_type:** Count applications with at least one
  deficiency attributable to each rule type.
- **unchanged_by_bulletins_count:** `total_applications` minus count of
  applications that are changed by any bulletin.

## Alcohol License Review Logic

### Recommendation
- `ISSUE_RESTRICTED` — premises has history but adequate controls exist or
  can be imposed.
- `REQUEST_FOLLOWUP` — pending incidents, verification gaps, or insufficient
  controls require follow-up before issuing.
- `DENY` — severe history with no feasible control path.

### Risk assessment
- **same_premises_basis:** From premises data. `SAME_ADDRESS_OVERLAP` when
  same address + overlapping service area; `PRIOR_SETTLEMENT_AT_ADDRESS`
  when only settlement exists; `NONE` otherwise.
- **prior_incident_level:** `HIGH` if any high-severity incident; `MODERATE`
  if multiple medium or mixed; `LOW` if only low-severity; `NONE` if zero.
- **incident_count:** Total incidents for the premises.
- **unresolved_incident_count:** Incidents with `disposition: "pending"` or
  blank disposition.
- **high_severity_incident_count:** Count of `severity: "high"` incidents.
- **settlement_posture:** `PRIOR_WARNING_WITH_CONTROLS` if prior settlement
  was warning/restricted with controls; `PRIOR_RESTRICTED_OR_DENIAL` if
  prior was denial or strict restriction; `CURRENT_SETTLEMENT` if
  settlement is current; `NONE` if no settlement.
- **control_coverage:** `STANDARD_ONLY` if only standard obligations
  exist; `ADEQUATE_LOCATION_SPECIFIC` if premises-specific controls
  address key risks; `NO_CONTROLS` if nothing exists.
- **overall_risk:** Synthesize from all above. `ELEVATED` for high incident
  level + standard-only controls; `SEVERE` for high + no controls + current
  settlement issues.

### Verification gaps
Common gap patterns (check all that apply):
- `AGE_VERIFICATION_CONTROL_NOT_IN_CURRENT_RESTRICTIONS` — settlement
  required age checks but current restrictions lack AGE_CHECK.
- `PENDING_POLICE_CALL_DISPOSITIONS` — incidents sourced from police call
  logs with pending dispositions.
- `SECURITY_PLAN_LAPSE_DISPOSITION_MISSING` — security plan lapse incident
  with blank disposition.
- `SETTLEMENT_TERMS_NOT_FOUND` — settlement referenced but terms not in
  current restrictions.
- `NO_VERIFICATION_GAPS` — only when none of the above apply.

### Review month comparison
- `review_month_application_count:` Count of all applications in the
  review month.
- `restricted_reviews_with_location_specific_controls_count:` Count
  applications with `requested_posture: "restricted issuance"` AND at
  least one premises-specific restriction. Exclude standard-issuance
  applications.
- `application_ids_with_location_specific_controls:` All application IDs
  with at least one premises-specific restriction (any posture).
- `target_has_location_specific_controls:` Boolean for the target premises.

## Renewal Manual-Review Queue Logic

### Matching violations to licensees (the critical step)
**Use the address search API** (`GET /api/search/address?address=...`)
for each licensee's address. This returns the definitive set of violations
at that address — no fuzzy name-matching needed.

### Match confidence
- `exact` — violation and licensee share the same address AND the
  `historical_name` matches the `facility_name`.
- `close` — same address but names differ slightly (used when matching
  by city-level endpoint fallback).
- `shared_address_manual` — multiple licensees at the same address;
  violations could belong to either.

### Pre-boundary filtering
Only count violations with `violation_date <= release_boundary`. Count
post-boundary violations in `excluded_post_boundary_count`.

### Ranking
Primary: violation count descending. Secondary: most recent violation
date descending (more recent = higher priority). Select top 10.

### Next-step label priority
1. If any violation has `alert_related: 1` → `manual ALERT check`
2. Else if any has `fine_cents > 0` → `manual fine check`
3. Else if violations include `SUSPENSION` or `REVOCATION` →
   `board review`
4. Else → `additional record check`

### Method flags
- `post_boundary_exclusion_applied: true` always when you filtered.
- `shared_address_records_not_spread: true` when no licensees share an
  address; `false` when shared addresses exist and you deliberately did
  not spread records across them.

## Alcohol Monitoring Plan Logic

### Recommendation
- `ISSUE_STANDARD` — clean premises, no issues.
- `ISSUE_RESTRICTED_WITH_MONITORING` — some risk factors but manageable
  with monitoring and controls.
- `REQUEST_RECORDS_BEFORE_ISSUE` — significant gaps require documentation
  before issuing.
- `DENY` — severe, unmanageable risk.

### Successor risk classification
- `HIGH` — same address, overlapping service area, prior licensee had
  incidents overlapping proposed controls.
- `MODERATE` — same address but different service type or fewer overlaps.
- `LOW` — different premises or clean prior history.

### Verification gaps
Derive from comparing incidents, settlements, restrictions, and standard
obligations. Common patterns:
- `CONTROL_EVIDENCE_NOT_VERIFIED` — premises-specific control lacks
  evidence of implementation.
- `PENDING_INCIDENT_DISPOSITIONS` — incidents with pending or blank
  dispositions.
- `POST_REVIEW_SETTLEMENT_TIMING` — settlement dated after the review
  month.
- `STANDARD_CONTROL_OVERLAP` — restriction duplicates a standard
  obligation.
- `SUCCESSOR_CONTROL_SEPARATION` — need to distinguish new licensee
  controls from prior licensee issues.

### Standard obligations
Pull from `GET /api/alcohol/standard-obligations?license_type=...`. Each
entry needs `obligation_code`, `source_obligation_id` (from the API),
and `evidence_required`.

### Premises-specific controls
Derive from restrictions (category `premises-specific`) and settlement
terms. Map each to an appropriate `check_code`:
- `AGE_CHECK` → `DEVICE_AUDIT`
- `NO_AFTER_MIDNIGHT_SERVICE` → `SERVICE_LOG_REVIEW`
- `PATIO_LIMIT` → `PATROL_OBSERVATION` (or `SERVICE_LOG_REVIEW`)
- `SECURITY_LOG` → `SECURITY_LOG_REVIEW`
- Quarterly inspection terms → `SITE_INSPECTION`
- Late-night disorder history → `LATE_NIGHT_DISORDER_MONITORING` with
  `PATROL_OBSERVATION` or `POLICE_CALL_LOG_REVIEW`

### Records requests
Include requests for: age verification audit, standard obligation
evidence, first-90-day inspection calendar, pending incident
dispositions, prior licensee settlement packet, and successor ownership
statement. Each entry needs a `request_code` and `source_ids`.

### Escalation triggers
Include: age check audit missing/failed, first-90-day check missed,
new/confirmed high-severity incident, pending incident confirmed
violation, and successor link confirmed to prior licensee. Each trigger
needs a `trigger_code` and `source_ids`.

## Output Conventions

1. **Return JSON only.** No markdown fences, no prose.
2. **Sort lists as specified** in the answer template (ascending by ID,
   enum order, etc.).
3. **Use exact enum values** from the template. Case-sensitive.
4. **Counts are integers.** Never floats.
5. **Empty lists `[]`** when no items apply; never `null` for list fields.
6. **Dates in YYYY-MM-DD format.** Months in YYYY-MM format.
7. **Include every application** in application_decisions for the stated
   batch; do not skip any.
8. **Source IDs** in verification gaps, controls, records requests, and
   escalation triggers must reference actual IDs from the API responses
   (e.g., `AR-2026-0014`, `AO-2026-0007`, `AI-2026-0008`).

## Common Pitfalls

- **Not filtering by cutoff date.** Always exclude records after the
  cutoff/boundary date from decision-driving logic.
- **Using declared values instead of actual records.** The actual bond
  record amount, not the declared amount, determines bulletin compliance.
- **Address-based matching for renewal queues.** Use the address search
  API (`/api/search/address`) — it returns both the licensee and all
  violations at that address in one call. Matching by city-level
  violation endpoints is error-prone.
- **Over-assigning DENY.** DENY should be rare — prefer HOLD when issues
  are potentially fixable. Reserve DENY for adverse prior registration
  + disqualifying conduct, or multiple severe AG-referred violations.
- **Missing correspondence holds.** Material notices with `needs_review`
  or `new` status received before the cutoff trigger
  `CORRESPONDENCE_HOLD`.
- **Including standard-issuance applications in restricted counts.** When
  counting `restricted_reviews_with_location_specific_controls`, only
  count applications with `requested_posture` containing "restricted".
- **Not including all applicable bulletins.** List every bulletin
  effective on/before cutoff whose trade_scope matches a trade in the
  batch (or is ALL), even if no application triggers its threshold.
- **Forgetting source IDs in monitoring plans.** Every verification gap,
  control, records request, and escalation trigger must cite the actual
  API record IDs that justify it.
