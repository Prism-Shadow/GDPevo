# Licensing Review Skill

You are a licensing examiner supporting state regulatory boards. When given a batch of applications, follow these instructions to produce a structured JSON decision package.

## Phase 1 — Understand the Task

1. **Read the prompt** to identify the domain (contractor, liquor, or alcohol renewal), the target application IDs, any review date, and which endpoints are available.
2. **Read the answer template** (`input/payloads/answer_template.json`) before fetching any data. Note every required key, allowed enum values, ordering rules, and whether lists must be sorted. The template is the contract — your output must conform exactly.

## Phase 2 — Fetch Records

Use the shared licensing environment. The base URL is provided in environment instructions as `<TASK_ENV_BASE_URL>`. The available GET endpoints vary by domain:

- **Contractor tasks**: `/api/policies`, `/api/contractor/applications`, `/api/contractor/bonds`, `/api/contractor/insurance`, `/api/contractor/license-history`, `/api/contractor/violations`, `/api/contractor/correspondence`, `/api/contractor/inspections`
- **Liquor tasks**: `/api/policies`, `/api/liquor/applications`, `/api/liquor/settlements`, `/api/liquor/privileges`, `/api/liquor/incidents`, `/api/liquor/site-evidence`
- **Renewal tasks**: `/api/alcohol/licensees`, `/api/alcohol/violations`, `/api/renewal/rules`

When available, prefer `/api/sql` with targeted queries over parsing full endpoint responses. Filter by the specific application or license IDs from the prompt.

## Phase 3 — Classify Each Application

### Contractor Applications

For each application, identify the governing policy by matching **trade** and **requested_class** to a policy's `rule_code`. Extract from the policy's `details_json` the required thresholds: `minimum_bond`, `minimum_insurance`, `minimum_years_experience`, and `required_endorsement`.

Evaluate each dimension:

| Dimension | Data source | How to check |
|-----------|------------|--------------|
| Bond | `/api/contractor/bonds` | Find the most recent bond per application. Must be status `active` AND amount ≥ policy minimum. Cancelled or expired bonds count as absent. |
| Insurance | `/api/contractor/insurance` | Find the most recent insurance policy. If status is `pending`, it is not current. If status is `active` but the expiration date is before the review date, treat as expired. Amount must meet the policy minimum. |
| Experience | Application `years_experience` | Compare directly to policy `minimum_years_experience`. |
| Endorsement | Application `endorsement_status` | `verified` is acceptable. `pending` means the endorsement has not been confirmed. `missing` means not submitted. `not_required` means no endorsement is needed. |
| Prior license | `/api/contractor/license-history` | Look up the `prior_license_id` if present. A status of `suspended` with notes like "Active suspension pending board action" means active_suspension → DENY. `revoked` also blocks. `expired` alone does not necessarily block but may flag the application. |
| Violations | `/api/contractor/violations` | Filter by `related_application_id`. An **open serious** violation is a blocking condition (DENY) when the policy has `serious_open_violation_blocks: true`. Open minor violations contribute to HOLD. Resolved or dismissed violations do not count. |
| Inspections | `/api/contractor/inspections` | Map finding codes to deficiency codes only when the task's answer template includes inspection-related codes. If the template lacks inspection codes, inspection findings do not produce deficiencies. |
| Correspondence | `/api/contractor/correspondence` | Records where `verified_by_agency` is `0` (false) are stale or unverified. Include their `correspondence_id` in the summary's stale/unverified list. |

#### Determination Rules

- **DENY** when: active suspension on prior license, OR an open serious violation exists and the policy blocks on it.
- **HOLD** when: any deficiency exists (shortfall, missing/pending item, expired coverage) but no DENY trigger.
- **APPROVE** when: every dimension satisfies its policy threshold and no open violations or suspensions exist.

#### Risk Tier

- **high**: active suspension, open serious violation, or multiple serious deficiencies.
- **medium**: multiple deficiencies or a single financial deficiency (bond/insurance).
- **low**: a single non-financial deficiency (e.g., experience shortfall alone, pending endorsement alone).

#### Policy Impacted

Compare the current 2025 policy against the legacy baseline policy (`POL-CON-LEGACY` or similar). The legacy baseline typically has a `minimum_bond_reduction` (subtract from current minimum) and `endorsement_required_for_specialty: false`. An application is **policy_impacted: true** when the current policy creates a deficiency that would NOT exist under the legacy baseline. Common triggers:
- Bond meets legacy minimum but falls short of current minimum.
- Endorsement is now required for a specialty trade where legacy did not require one.

### Liquor License Applications

For each application-location pair:

#### Posture Recommendation
- **issue_restricted**: Active settlements with controls are in place; risks are covered by existing controls. Verification gaps are minor and resolvable.
- **request_follow_up**: Open incidents or significant verification gaps exist that need resolution before a decision.
- **deny**: Major unresolved risks with no active controls, or serious open incidents.

#### Same-Premises Basis
Check settlements for the target location. If any settlement has `basis_code: "SAME_PREMISES"` and is **active** (check `controls_json.active`), then `same_premises_basis_applies` is `true`. Policy may also cause this to be `true` based on history even without an active settlement — check the liquor policy for `same_premises_history_matters`.

#### Covered Risk Codes
These are the risk codes that are addressed by **currently active** settlement controls. Look at each active settlement's `controls_json.controls` array and map each control to the risks it covers:
- `SECURITY` control → `ASSAULT`, `PUBLIC_SAFETY`
- `CCTV` control → `PUBLIC_SAFETY`, `CAMERA_COVERAGE` (if applicable)
- `HOURS` control → `AFTER_HOURS`
- `NOISE` control → `NOISE`
- `PATIO` control → `PATIO_BOUNDARY`
- `FOOD_SERVICE` control → `FOOD_SERVICE_GAP`
- `ID_CHECK` control → `MINOR_SALE`, `SALE_TO_MINOR`, `ID_CHECK`

Also include the settlement's own `basis_code` when it matches an allowed risk code. Inactive settlements (expired, `active: false`) do not provide coverage.

#### Verification Gap Codes
Derived from site evidence and open incidents:
- Evidence with status `missing` or `conflicting` → corresponding gap code (e.g., `CONTROL_SIGNAGE_CURRENT_MISSING`, `FLOOR_PLAN_CONFLICTING`, `SITE_PHOTO_MISSING`, `POLICE_MEMO_CONFLICTING`).
- Open incidents → `OPEN_INCIDENT_FOLLOW_UP`.
- Open tax holds → `TAX_CLEARANCE_MISSING` or `tax_hold_unresolved`.
- Missing evidence types that are expected for the license class → e.g., `camera_evidence_missing`, `food_service_evidence_missing`.
- Use only codes listed in the answer template's allowed values.

#### Standard Obligations vs Location-Specific Controls
- **Standard obligations**: Look up the license class in `/api/liquor/privileges`. Every obligation where `standard_required` is `1` is a standard obligation for that class.
- **Location-specific controls**: Take the controls from active settlements and subtract any that are already standard obligations. The remainder are location-specific.

#### First-90-Day Plan
Build a monitoring plan based on verification gaps and risks. Each entry pairs a `check_code` with a `timing` (`first_30_days`, `days_31_60`, or `days_61_90`). Prioritize the most urgent checks (open incidents, missing critical evidence) in the first 30 days. Use only the check codes and timings listed in the answer template.

#### Escalation Triggers
Conditions that should cause field staff to escalate. Based on open risks, missing controls, and unresolved incidents. Use only codes from the template's allowed values.

### Alcohol Renewal Queue

#### Boundary Filtering
The prompt provides a release boundary date (e.g., `2025-04-10`). The applicable renewal rule (from `/api/renewal/rules`) confirms: use violations **on or before** the boundary only. Post-boundary violations (typically from a `post_boundary_feed` source or dated after the boundary) are **excluded** and listed in the summary as excluded.

#### Violation Matching
Match violations to licensees by `license_no`. The policy (`POL-REN-001`) governs:
- Prefer exact license matches.
- Only violations known on or before the boundary count.
- If the licensee has a `successor_to` field, mark match confidence as `uncertain`.
- Otherwise, if the violation's address exactly matches the licensee's address, match confidence is `exact`.
- `close_address` is used only when the violation is linked by license number but the address differs slightly.

#### Queue Ranking
Rank all target licensees from 1 to N (the queue size). Ranking is based on pre-boundary violation severity and count:

1. Group by severity of **open/pending** pre-boundary violations: serious > medium > minor > none.
2. Within the same severity tier, rank by number of open/pending violations (more = higher rank).
3. Further break ties by total open fine balance (higher = higher rank), then by most recent violation date (more recent = higher rank).
4. Licensees with only resolved/paid/dismissed/warning violations rank lowest.

#### Per-Entry Fields
- `violation_count`: Total number of pre-boundary matched violations (all dispositions).
- `most_recent_violation_date`: Latest `violation_date` among matched pre-boundary violations.
- `matched_violation_ids`: All pre-boundary violation IDs, sorted by `violation_date` ascending, then `violation_id` ascending.
- `match_confidence`: `exact` for direct license matches, `uncertain` for successor relationships.
- `risk_tier`: `high` for open serious violations, `medium` for open medium/minor violations with fines, `low` for no open violations.
- `next_step_label`: `board_review` for serious violations, `manual_fine_check` for significant open fines, `manual_ALERT_check` for alert-flagged violations, `additional_record_check` for uncertain matches or low-risk entries.

#### Summary
- `queue_size`: Always N (the queue length).
- `boundary_date`: The boundary from the prompt.
- `post_boundary_violation_ids_excluded`: All violation IDs dated after the boundary, sorted ascending.
- `close_or_uncertain_match_license_numbers`: Licensees with `uncertain` or `close_address` match confidence, sorted ascending.
- `board_review_license_numbers`: Licensees with `next_step_label: "board_review"`, sorted ascending.

## Phase 4 — Verify the Output

Before finalizing, cross-check:
1. All application IDs are present and ordered as specified in the template.
2. All lists use the correct sort order (ascending lexical, ascending by date, etc.).
3. Enum values exactly match the template (case-sensitive).
4. Summary counts equal the application-level decisions.
5. Empty arrays, not null or absent keys, when no codes apply.
6. No extra prose, markdown, or keys outside the template.

## General Principles

- **Review dates matter**: When a prompt gives a review date (e.g., "Use 2025-07-18 as the review date"), judge whether insurance and bonds are current as of that date. Insurance with status `active` but expiration before the review date is expired.
- **Status field takes precedence over computed states**: An insurance policy with status `active` and a past expiration date IS expired. A bond with status `cancelled` is not active regardless of amount.
- **Policy-to-application mapping**: Match by trade AND class. The policy `rule_code` encodes both (e.g., `CON-PLU-ClassB` = Plumbing, Class B).
- **Legacy baseline comparison**: The legacy policy provides the prior-year thresholds. Policy impact is about whether the CURRENT policy changes eligibility compared to the legacy baseline.
- **Use SQL when available**: It returns exactly the records you need, making analysis faster and less error-prone than scanning full endpoint responses.
