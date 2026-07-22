# Licensing Review Skill

## Purpose
Solve structured licensing review tasks by querying a shared licensing environment, cross-referencing entity records against active policies, and producing JSON answers conforming to a supplied answer template.

## Task Categories

There are three recurring task patterns:

### 1. Contractor Batch Eligibility Review
Review a batch of contractor applications against the State Contractors Licensing Board policies. Each application must be evaluated for bond, insurance, experience, endorsement, license history, violations, and inspection compliance.

### 2. Liquor License Staff Package
Prepare a single-application staff review package for a restricted liquor license (transfer, renewal with controls, or new). Evaluate settlements at the target location, active controls, incidents, site evidence, and applicable privilege obligations.

### 3. Alcohol Renewal Manual Review Queue
Build a ranked queue of licensees for manual review before a release boundary date. Match violations to licensees, exclude post-boundary records, assess match confidence, and assign risk tiers and next-step labels.

---

## General Workflow

### Phase 1: Read the Answer Template First
Before querying any endpoint, read `input/payloads/answer_template.json`. Memorize:
- Every allowed value for every enum field
- The exact top-level keys required
- The ordering rules (ascending by application_id, ascending lexical, etc.)
- Which fields use empty arrays vs. omitted keys when no values apply
- The schema version and any date-format instructions

### Phase 2: Identify the Applicable Policies
Fetch `/api/policies` once. For each target entity, identify which policy rule applies by matching the entity's trade/class/family against policy metadata (`family`, `rule_code`, `title`). Note:
- The `effective_date` tells you when the policy became active
- The `details_json` contains machine-readable thresholds (minimum_bond, minimum_insurance, minimum_years_experience, required_endorsement, blocking flags)
- Legacy/comparison policies (look for `use_for_prior_rule_comparison: true`) define the baseline for `policy_impacted` determinations
- For renewal tasks, match the rule whose `release_boundary` matches the prompt's stated boundary date

### Phase 3: Query Entity Records
For each target entity, fetch all relevant records from the endpoints listed in the prompt. Use SQL when available to filter by the target IDs rather than fetching and filtering the full dataset manually. Always use any required authentication headers.

**Contractor tasks** — fetch for each target application_id:
- `/api/contractor/applications` — trade, class, experience, endorsement status, prior license
- `/api/contractor/bonds` — amount, status (active/cancelled/expired), effective/cancel dates
- `/api/contractor/insurance` — amount, status, expiration date, verified date
- `/api/contractor/license-history` — status (active/suspended/expired), status_date
- `/api/contractor/violations` — severity, status (open/resolved/dismissed), theme, dates
- `/api/contractor/correspondence` — verified_by_agency flag, notes for staleness
- `/api/contractor/inspections` — finding_code, result (pass/fail/conditional)

**Liquor tasks** — fetch for the target location_id:
- `/api/liquor/applications` — license_class, requested_posture, location_id
- `/api/liquor/settlements` — basis_code, active flag in controls_json, controls list, review_required
- `/api/liquor/privileges` — standard_required flag by license_class and obligation_code
- `/api/liquor/incidents` — risk_code, severity, status (open/closed/dismissed/referred)
- `/api/liquor/site-evidence` — evidence_code, status (verified/missing/conflicting/stale)

**Renewal tasks** — fetch for the target license numbers:
- `/api/alcohol/licensees` — license_no, address, facility_name, successor_to
- `/api/alcohol/violations` — violation_id, date, disposition, fine_balance, alert_flag, source_name
- `/api/renewal/rules` — release_boundary, details_json for matching rules

### Phase 4: Cross-Reference and Evaluate

#### Policy Compliance Check (Contractor)
For each application, compare its records against the applicable policy thresholds:
- **Bond**: Active bond amount >= policy minimum_bond. If cancelled → no_active_bond. If active but amount short → bond_shortfall.
- **Insurance**: Active insurance amount >= policy minimum_insurance. If status is "pending" → insurance_not_current. If expiration date is before the review date → insurance_expired. If active but amount short → insurance_shortfall.
- **Experience**: years_experience >= policy minimum_years_experience. Otherwise → experience_shortfall.
- **Endorsement**: If policy has required_endorsement (non-null) and endorsement_status is "missing" → endorsement_missing. If "pending" → endorsement_pending.
- **License History**: If prior license status is "suspended" → active_suspension.
- **Violations**: Open violations with serious severity → open_serious_violation. Open minor → open_minor_violation. Resolved/dismissed violations generally don't create deficiencies unless the schema specifically includes them.
- **Inspections**: Only flag when the finding_code is meaningful AND the result is "fail" or "conditional" (not "pass"). Map finding_code to the appropriate deficiency code.
- **Correspondence**: Stale = notes contain "Stale attachment predates application." Unverified = verified_by_agency = 0 OR notes contain "Applicant copy only; no agency confirmation" (even if verified_by_agency = 1).

#### Determination Logic
- **APPROVE**: No deficiencies found. All financial coverage is current and meets thresholds.
- **HOLD**: Deficiencies exist but are fixable (missing documents, shortfalls that can be remedied, pending verifications). Active suspension → HOLD with board_review action (not DENY).
- **DENY**: Unresolved serious violations that block issuance per policy (`serious_open_violation_blocks: true`), or a combination of severe unfixable issues.

#### Policy Impacted
Compare the current policy against the legacy baseline policy. `policy_impacted` is true when at least one deficiency or material review flag exists under the current 2025 policy that would NOT have existed under the legacy baseline. Key legacy differences:
- Legacy `minimum_bond_reduction` (e.g., 10000) means legacy minimum bond = current min - reduction
- Legacy `endorsement_required_for_specialty: false` means specialty-class applications didn't need endorsements under legacy
- Insurance and experience requirements are typically unchanged between current and legacy

#### Risk Tier
- **high**: Active suspension, open serious violations, cancelled bond, or 3+ distinct deficiency categories
- **medium**: Multiple deficiencies but none blocking, or a single significant financial deficiency
- **low**: One minor fixable issue, no violations or adverse history

#### Liquor Staff Package Logic
- **recommended_posture**: `issue_restricted` when active controls exist and gaps are minor; `request_follow_up` when significant verification gaps or open incidents exist; `deny` when blocking issues are present.
- **same_premises_basis_applies**: true only when there is an ACTIVE settlement with basis_code SAME_PREMISES (check the `active` field in controls_json, not just the settlement's existence).
- **covered_risk_codes**: Risk codes addressed by active settlements. The active settlement's basis_code is always covered. The controls in controls_json may indicate additional covered risks.
- **verification_gap_codes**: Evidence items with status "missing" or "conflicting", plus open incidents requiring follow-up. Evidence types completely absent from the location may also be gaps.
- **standard_obligation_codes**: Privilege codes where `standard_required = 1` for the license class.
- **location_specific_control_codes**: The `controls` list from the active settlement's controls_json.
- **escalation_trigger_codes**: Scenarios that would escalate the case — unresolved verification gaps becoming violations, open incidents remaining unresolved, control failures.

#### Renewal Queue Logic
- **Boundary filtering**: Only include violations dated on or before the release boundary. Exclude violations with `source_name = "post_boundary_feed"` regardless of date (these are listed in `post_boundary_violation_ids_excluded`).
- **Violation matching**: Match violations to licensees by exact `license_no` first. Address-based matching applies when violations exist at the same address with different license numbers.
- **Match confidence**: `exact` when all matched violations share the licensee's license_no. `close_address` when some matched violations have different license numbers but the same address. `uncertain` when the license has a `successor_to` relationship.
- **Violation count**: Count of pre-boundary matched violations (renewal_case_export source, not post_boundary_feed).
- **Risk tier**: Based on open/serious violations, unpaid fines, and alert flags. High = open serious violations or significant unpaid fines. Medium = moderate violations or moderate fines. Low = only warning/minor violations with no fines.
- **Next step**: `manual_fine_check` when fine_balance > 0 exists. `manual_ALERT_check` when alert_flag = 1 but no fines. `board_review` when serious pending/open violations exist. `additional_record_check` for uncertain matches with no fines or alerts.
- **Summary fields**: `close_or_uncertain_match_license_numbers` includes all licensees with close_address or uncertain confidence. `board_review_license_numbers` includes those needing escalated review.

### Phase 5: Assemble the Answer
- Build the JSON object exactly matching the answer template structure
- Sort all arrays as specified (ascending by ID, lexical order, etc.)
- Use empty arrays `[]` when no codes apply — never omit the key
- Ensure summary counts are consistent with application-level decisions
- Double-check that every enum value is from the allowed set
- Verify the output is pure JSON with no prose, markdown, or comments

---

## Pattern Reference

### Deficiency Code Mapping (Contractor)

**Financial:**
| Condition | Deficiency Code |
|-----------|----------------|
| Active bond cancelled | no_active_bond / bond_cancelled |
| Active bond amount < policy min | bond_shortfall |
| Insurance status = "pending" | insurance_not_current / insurance_pending |
| Insurance exp date < review date | insurance_expired |
| Insurance amount < policy min | insurance_shortfall |

**Qualification:**
| Condition | Deficiency Code |
|-----------|----------------|
| Years experience < policy min | experience_shortfall |
| Endorsement status = "missing" | endorsement_missing / endorsement_not_verified |
| Endorsement status = "pending" | endorsement_pending / endorsement_not_verified |

**History:**
| Condition | Deficiency Code |
|-----------|----------------|
| License status = "suspended" | active_suspension |
| Open violation, serious severity | open_serious_violation / unresolved_serious_complaint |
| Open violation, minor severity | open_minor_violation |

### Evidence Gap Mapping (Liquor)
| Evidence Status | Gap Code Pattern |
|----------------|-----------------|
| Status = "missing" | `{EVIDENCE_TYPE}_missing` or `{EVIDENCE_TYPE}_CURRENT_MISSING` |
| Status = "conflicting" | `{EVIDENCE_TYPE}_conflicting` or `{EVIDENCE_TYPE}_CONFLICTING` |
| Status = "stale" | `{EVIDENCE_TYPE}_stale` or `{EVIDENCE_TYPE}_STALE` |
| Open incident, not closed | `OPEN_INCIDENT_FOLLOW_UP` |

### Staleness Indicators (Correspondence)
A correspondence item is stale or unverified when:
- `verified_by_agency = 0`, OR
- Notes contain "Stale attachment predates application", OR
- Notes contain "Applicant copy only; no agency confirmation" (regardless of verified_by_agency value)

A correspondence item with notes "Linked to registry case notes" is NOT automatically stale — it must also meet one of the above criteria.

### Inspection Treatment
- Finding code "NONE" with any result → typically no deficiency
- Finding code with result "pass" → typically no deficiency (the finding was resolved)
- Finding code with result "fail" or "conditional" → flag if a matching deficiency code exists

### Date Handling
- Use the prompt-specified review date when provided. If not specified, evaluate insurance expiration dates against the latest data timestamp available.
- Insurance status "active" with expiration date before review date → treat as expired.
- The renewal boundary date is used for violation inclusion cutoff (on or before = included, after = excluded).
