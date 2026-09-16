# Decision Patterns

This reference describes how to interpret raw API data into structured
determinations. The patterns below emerge from the training evidence;
use them as heuristics, not as rigid rules that override the specific
template you are given.

---

## Contractor batch review

### Deficiency mapping

Derive deficiency codes from the data, then map each to its corrective action.
The mapping is:

| Deficiency | Evidence | Corrective action |
|---|---|---|
| `bond_cancelled` / `no_active_bond` | Bond record shows cancelled or no active bond | `obtain_current_bond` / `file_active_bond` |
| `bond_shortfall` | Bond amount < required minimum (check `/api/policies`) | `increase_bond_amount` / `increase_bond` |
| `insurance_expired` | Policy end date < review date | `provide_current_insurance` / `renew_insurance` |
| `insurance_not_current` | No policy active on review date | `provide_current_insurance` |
| `insurance_shortfall` | Coverage amount < required limit | `increase_insurance_amount` / `increase_insurance` |
| `endorsement_missing` | Required endorsement not on file | `obtain_required_endorsement` |
| `endorsement_not_verified` | Endorsement present but not confirmed | `verify_endorsement` |
| `endorsement_pending` | Endorsement application is in progress | `verify_pending_endorsement` |
| `experience_shortfall` | Documented experience < required threshold | `submit_experience_evidence` / `document_experience` |
| `active_suspension` | Current suspension in license history | `board_review_suspension` / `clear_suspension` + `board_review` |
| `open_minor_violation` | Minor violation with no resolution recorded | `resolve_minor_violation_review` |
| `open_serious_violation` / `unresolved_serious_complaint` | Serious violation not adjudicated | `resolve_serious_violation` / `resolve_complaint` + `board_review` |
| `inspection_doc_gap` | Inspection record references missing documents | `clear_document_gap` |
| `inspection_safety_recheck` | Inspection requires safety re-inspection | `complete_safety_recheck` |

Use only the codes that appear in the task's answer template. The template is
authoritative; this table shows how to reason about the mapping.

### Determination thresholds

- **APPROVE**: Zero deficiencies. All financial coverage is active and
  sufficient, endorsements verified, experience meets threshold, no open
  violations or suspension.
- **HOLD**: One or more addressable deficiencies. No active suspension, no
  unresolved serious violations. The applicant can fix these before the next
  cycle.
- **DENY**: Active suspension, unresolved serious complaint/violation, or a
  combination of deficiencies that makes interim approval unsafe (e.g.
  expired insurance plus endorsement gap plus experience shortfall all at
  once on a high-risk classification).

### Risk tiers

- **high**: Active suspension, serious violation, safety recheck, or a
  cluster of three or more material deficiencies.
- **medium**: One or two correctable deficiencies, no suspension or serious
  violation.
- **low**: No deficiencies.

### Correspondence

Scan the correspondence endpoint for items that are stale (sent > 30 days ago
with no response) or unverified (status is `pending` or `sent`). List their
IDs in `stale_or_unverified_correspondence_ids`. Include correspondence IDs
that appear in the data even if they belong to a different applicant when the
template explicitly allows cross-cutting IDs.

---

## Liquor license staff package (single application)

### Posture

- **issue_restricted**: All evidence verified, all controls in place, no
  unresolved incidents. The license can issue with restricted conditions.
- **request_follow_up**: One or more verification gaps exist (missing camera
  evidence, stale floor plan, unresolved tax hold) or incidents require
  follow-up. The application is viable but not ready to issue.
- **deny**: Same-premises basis does not apply AND multiple control failures
  exist, or a major unresolved incident pattern makes issuance unsafe.

### Same-premises basis

When the application is a transfer at the same physical location as a previous
license, `same_premises_basis_applies` is `true`. Check the application record
for a transfer flag or a matching predecessor location ID. When the location
is new or substantially different, it is `false`.

### Covered risk codes

Derive from incidents and site evidence. A risk is *covered* when the
application or location already has controls that address it (e.g. a noise
incident history with a current noise-control condition). A risk is *not
covered* when incidents exist but no corresponding control is documented.

### Verification gap codes

Derive from site evidence completeness:

- **Missing**: Required item not in evidence (camera_evidence_missing,
  food_service_evidence_missing, etc.)
- **Conflicting**: Evidence contradicts application data (floor_plan_conflicting,
  control_signage_conflicting, police_memo_identity_note)
- **Stale**: Evidence predates the application and may no longer be accurate
  (floor_plan_stale)
- **Unresolved**: External dependency not cleared (tax_hold_unresolved,
  open_incident_follow_up)

### Obligation vs. location-specific controls

- **Standard obligations** (`standard_obligation_codes`): Conditions that
  attach to this license class by default -- ID_CHECK, HOURS, FOOD_SERVICE,
  CCTV, SECURITY, NOISE, PATIO, DELIVERY. Include only those the template
  allows and that the license class ordinarily requires.
- **Location-specific controls** (`location_specific_control_codes`): Active
  conditions tied to the physical location, not the license class. These may
  overlap with standard obligations but are location-driven (e.g. a specific
  noise curfew for a location with prior complaints).

### 90-day plan

Build from verification gaps and risk codes. Each entry pairs a `check_code`
with a `timing` bucket:

- `first_30_days`: Urgent verification items (signage recheck, police memo
  follow-up, camera export test, food service check)
- `days_31_60`: Operational checks (after-hours visit, id check observation,
  security/CCTV walkthrough)
- `days_61_90`: Follow-through items (noise/patio boundary check, tax
  clearance review, incident log review)

Sequence items in operational order: verification first, then observation,
then boundary/compliance checks.

### Escalation triggers

Conditions that should cause field staff to escalate to a supervisor or board:

- Incident patterns that could recur (AFTER_HOURS_VIOLATION,
  MAJOR_INCIDENT_REPORTED)
- Control failures (SECURITY_CCTV_CONTROL_FAILURE, CONTROL_SIGNAGE_NOT_VERIFIED)
- External holds (TAX_HOLD_REOPENED, BOARD_ORDER_CONFLICT)
- Unresolved referrals (REFERRED_MINOR_SALE_UNRESOLVED)

---

## Alcohol renewal queue

### Queue construction

The queue ranks licensees by priority for manual review before renewal release.

**Matching violations to licensees.** Violation records may reference the
licensee by `license_no` (exact match), by address (close match), or by a
legacy identifier. Use the strongest key available:

- `exact`: Violation's `license_no` equals the licensee's `license_no`.
- `close_address`: Address matches by street and number but the license
  number differs (e.g. old license at same location).
- `uncertain`: Name or partial address match only.

**Boundary filtering.** The task provides a release boundary date (e.g.
`a stated cutoff date`). Include only violations with dates *on or before* that date.
Violations after the boundary go into `post_boundary_violation_ids_excluded`.

**Ranking.** Sort by descending priority:

1. Violation count (more violations → higher rank)
2. Most recent violation date (more recent → higher rank)
3. Match confidence (exact beats close_address beats uncertain)

For tie-breaking, prefer the licensee with the most recent violation.

**Risk tiers in queue context:**

- `high`: 2+ violations, or any violation within 30 days of the boundary,
  or a close/uncertain match with 3+ violations.
- `medium`: 1-2 violations, all older than 30 days from boundary.
- `low`: 0 violations matched within the boundary window.

**Next-step labels:**

- `board_review`: Close/uncertain match, or 3+ violations, or any violation
  with a serious classification.
- `manual_fine_check`: Exact match, violations likely involve financial
  penalties.
- `manual_ALERT_check`: Exact match, violations may involve alert-level
  triggers.
- `additional_record_check`: Uncertain match requiring further investigation.

### Summary fields

- `post_boundary_violation_ids_excluded`: All violation IDs with dates after
  the boundary, sorted ascending.
- `close_or_uncertain_match_license_numbers`: License numbers of any licensee
  in the queue matched by close_address or uncertain confidence, sorted
  ascending.
- `board_review_license_numbers`: License numbers of any licensee in the
  queue with next_step_label `board_review`, sorted ascending.

---

## General cross-domain rules

### Date handling

Always use `YYYY-MM-DD` format. When determining whether coverage is current,
compare the policy end date against the review date provided in the prompt.
"Current" means the policy end date is on or after the review date. "Expired"
means the end date is before the review date.

### Policy impact

A `policy_impacted: true` flag means the current policy baseline (from
`/api/policies`) creates a deficiency that would not exist under a prior
standard. Common triggers:

- A bond or insurance minimum was raised and the application meets the old
  minimum but not the new one.
- A new endorsement requirement was added that the application lacks.
- Experience thresholds were raised.

When no policy endpoint is available, or the policy contains no changes
relative to the applications under review, the flag is `false`.

### Correspondence staleness

A correspondence item is stale when its `sent_date` is more than 30 days
before the review date and its `status` is not `acknowledged` or `resolved`.
A correspondence item is unverified when its `status` is `pending`. Include
the item's ID in `stale_or_unverified_correspondence_ids`.

Correspondence IDs that appear in the data but belong to other applications
may still be included when the template's summary permits cross-cutting IDs.
For example, a disclosure-record correspondence tagged with a different
prefix than the applications under review may still belong in the summary.
