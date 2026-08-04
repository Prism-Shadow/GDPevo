## Licensing Review Skill

### Overview

This skill covers structured eligibility review of contractor, liquor, and alcohol-renewal
applications against policy baselines. The work is data-driven: every decision traces to
specific records returned by environment endpoints. No information outside the provided
API responses should be used.

### General Workflow

1.  **Read the prompt and answer template first.** The template defines the exact JSON
    shape, allowed enum values, ordering rules, and which fields are required. Never
    invent keys or values not present in the template.

2.  **Fetch all relevant endpoint data.** Use every endpoint listed in the prompt. Some
    records reference applications through `related_application_id` rather than
    `application_id`; always check the actual field names in the response.

3.  **Filter records to the target set.** Isolate only the records that belong to the
    application IDs or location IDs named in the prompt. Ignore distractor records from
    other task families (e.g., C-DIS-*, C-TE1-*, C-TE4-* when the prompt asks for
    C-TR1-* or C-TR4-*).

4.  **Apply policy rules.** Map each application to its governing policy using the
    trade and requested-class fields. Policy records carry minimum-bond, minimum-insurance,
    minimum-years-experience, and required-endorsement values. Compare the
    application's actual figures against those minimums.

5.  **Check supplementary records.** After policy comparison, inspect bonds, insurance,
    violations, license history, inspections, settlements, incidents, and site evidence
    for additional flags that affect the determination.

6.  **Respect date boundaries.** When the prompt or policy specifies a boundary date
    (e.g. "on or before 2025-04-10"), exclude records dated after that boundary from the
    primary analysis. Post-boundary records are distractor data. List them separately
    in the summary only if the template asks for excluded items.

7.  **Sort everything as instructed.** Most templates require ascending sort by ID or
    code. Plan items may require operational-sequence ordering. Follow the template
    ordering rules exactly.

### Contractor Application Review

#### Policy Mapping

Map each application to a policy by matching `trade` and `requested_class`:

| Trade | Requested Class | Policy Rule Code Prefix |
|---|---|---|
| Electrical | Class A | CON-ELE |
| Plumbing | Class B | CON-PLU |
| HVAC | Class B | CON-HVA |
| General Building | Class A | CON-GEN |
| Roofing | Limited | CON-ROO |
| Solar | Specialty | CON-SOL |

The legacy policy (CON-LEGACY) provides a pre-2025 baseline for determining whether a
deficiency is policy-impacted. Under the legacy baseline, specialty endorsements were
not required and minimum bonds were reduced by 10,000.

#### Financial Coverage

- **Active bond** means `status == "active"`. If no active bond exists, flag a bond
  deficiency. If an active bond exists but its amount is below the policy minimum, flag
  a bond-shortfall deficiency.
- **Active insurance** means `status == "active"`. If the only insurance records are
  expired or pending, flag accordingly. A pending policy that meets the minimum amount
  should be flagged as pending (not expired).
- If an application has no bond or insurance records at all, it lacks required
  financial coverage.

#### Endorsements

Check `endorsement_status` against the policy's `required_endorsement`. If the policy
requires an endorsement and the status is `missing` or `pending`, flag the deficiency.
If `required_endorsement` is null or `endorsement_status` is `not_required`, no
deficiency applies.

#### Experience

Compare `years_experience` against the policy's `minimum_years_experience`. If below
the minimum, flag an experience shortfall.

#### Violations

Only violations with `status == "open"` are active blockers. Resolved, dismissed,
settled, or paid violations do not block but may inform risk tier.
- Open + `severity == "serious"` → unresolved-serious-complaint or open-serious-violation
- Open + `severity == "minor"` → open-minor-violation

#### License History

Check the applicant's `prior_license_id` against the license-history endpoint. A
history record with `status == "suspended"` is a blocking deficiency.

#### Inspections

Inspection findings inform risk but may or may not map to deficiency codes depending
on the template's allowed code set. Check whether the template includes inspection
codes before flagging them as deficiencies.

#### Policy-Impacted Determination

An application is policy-impacted when the current 2025 policy baseline creates a
deficiency that would not have existed under the legacy baseline. The two key
differences in the legacy policy are:
1. `endorsement_required_for_specialty: false` — specialty endorsements were not required.
2. `minimum_bond_reduction: 10000` — bond thresholds were lower.

If either difference turns a passing application under legacy into a deficient one
under the current policy, mark `policy_impacted: true`.

#### Determination Logic

- **DENY**: active suspension, or an open serious/unresolved-serious violation.
- **HOLD**: one or more curable deficiencies but no blocking condition.
- **APPROVE**: zero deficiencies.

#### Risk Tier

- **high**: active suspension, open serious violation, or three or more deficiencies.
- **medium**: one or two deficiencies.
- **low**: zero deficiencies.

### Liquor License Staff Review

#### Data Sources

Liquor reviews draw from: policies, applications, settlements, incidents, site evidence,
and privileges (when available).

#### Settlement Analysis

Settlements contain a `controls_json` field with `active`, `controls`, `expires`, and
`review_required` sub-fields. The currently active settlement(s) define the
location-specific controls.

- **same_premises_basis_applies** is true when at least one settlement has
  `basis_code == "SAME_PREMISES"` AND its controls are `active: true`. If the
  SAME_PREMISES settlement is inactive or expired, the basis does not apply.

#### Covered Risks

Map each active control to the risks it mitigates:
- SECURITY → ASSAULT
- CCTV → ASSAULT
- HOURS → AFTER_HOURS
- ID_CHECK → MINOR_SALE, SALE_TO_MINOR
- NOISE → NOISE
- PATIO → PATIO_BOUNDARY

Include SAME_PREMISES in covered risks when the same-premises basis is active.

#### Verification Gaps

Examine site evidence for missing, conflicting, or stale records. Map each evidence
status to the corresponding gap code:
- `CONTROL_SIGNAGE` with status `conflicting` or `missing` → signage gap codes.
- `FLOOR_PLAN` with status `conflicting` → floor-plan-conflicting.
- `POLICE_MEMO` with status `conflicting` → police-memo-conflicting.
- Absence of camera evidence → camera-evidence-missing.
- Absence of food-service evidence → food-service-evidence-missing.
- Open TAX_HOLD incident → tax-hold-unresolved.
- Open/referred incidents → open-incident-follow-up (if the template has this code).

#### Standard vs. Location-Specific Obligations

- **Standard obligations** are those required by the license class itself (e.g.,
  Restaurant → FOOD_SERVICE, HOURS, ID_CHECK; BeerWine → HOURS, ID_CHECK).
- **Location-specific controls** are the active controls from current settlements.
  They may overlap with standard obligations but are listed separately.

#### Recommended Posture

- **issue_restricted**: same-premises basis applies, controls are active, no open
  incidents or verification gaps.
- **request_follow_up**: open incidents or verification gaps exist but no blocking
  condition.
- **deny**: open serious incident or other blocking condition.

#### First 90-Day Plan

Include a plan item for each active control and each verification gap. Assign timing:
- `first_30_days`: immediate checks (signage, noise, tax clearance).
- `days_31_60`: mid-period checks (ID observation, food service, camera export).
- `days_61_90`: late-period checks (late-night visits, incident log reviews).

Order items by timing phase, then alphabetically by check_code within each phase.

#### Escalation Triggers

Include triggers for each risk that is not fully mitigated by active controls and for
each verification gap that could escalate into a violation.

### Alcohol Renewal Queue

#### Boundary Date

The prompt or renewal rules specify a boundary date (e.g., 2025-04-10). Only
violations with `violation_date <= boundary` are included in the analysis. Violations
after the boundary are excluded from the main queue and listed in the summary under
`post_boundary_violation_ids_excluded`.

#### Violation Matching

- **Exact match**: violations where `license_no` directly matches the target license.
- **Successor match**: if the license has a `successor_to` field, also check for
  violations under the predecessor license number. Mark these as `match_confidence:
  "uncertain"`.

#### Ranking Heuristic

Rank licenses in descending priority order:
1. Count of violations with `alert_flag == 1` (more alerts → higher rank).
2. Count of open/pending/warning violations (active issues → higher rank).
3. Highest severity among violations (serious > medium > minor).
4. Total unpaid fine balance among active issues.
5. Most recent violation date (more recent → higher rank).

#### Risk Tier and Next Step

- **board_review**: one or more open serious violations.
- **manual_fine_check**: unpaid fines > 0 but no open serious violations.
- **manual_ALERT_check**: alert-flagged violations exist but fines are paid and no
  serious open issues.
- **additional_record_check**: remaining cases.

### Common Pitfalls

- Records reference applications through different field names across endpoints:
  `application_id` in bonds/insurance, `related_application_id` in
  violations/correspondence/inspections, `license_id` in history, `license_no` in
  alcohol data.
- Some records have `null` values for certain fields. Always guard against None
  before calling string methods.
- Endpoint responses may contain distractor records for other task families. Always
  filter to the specific application IDs or location IDs mentioned in the prompt.
- The same deficiency may have different code names in different templates. Always
  use only the allowed values listed in the answer template, not codes from other
  tasks.
- Inspections: a finding with result `pass` may not constitute a deficiency even if
  the finding code suggests an issue. Check whether the template includes inspection
  codes before flagging them.
