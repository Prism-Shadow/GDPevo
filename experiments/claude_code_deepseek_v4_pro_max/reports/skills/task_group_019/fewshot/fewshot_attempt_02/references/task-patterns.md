# Task Patterns

This file catalogs the three recurring task types observed across the training
distribution.  For each type: the prompt signature, the API endpoints used, the
output structure, and the decision logic.

---

## Type A — Contractor Batch Eligibility Review

**Examples:** train_001 (8 apps: C-TR1-001–008), train_004 (7 apps: C-TR4-001–007)

**Prompt signature:** "You are a Senior Licensing Examiner for the State
Contractors Licensing Board" reviewing a batch of application IDs.

**API endpoints:**
- `GET /api/policies`
- `GET /api/contractor/applications`
- `GET /api/contractor/bonds`
- `GET /api/contractor/insurance`
- `GET /api/contractor/license-history`
- `GET /api/contractor/violations`
- `GET /api/contractor/correspondence`
- `GET /api/contractor/inspections`
- `POST /api/sql` (when needed)

**Output structure:**
```
{
  "application_decisions": [
    {
      "application_id": "<id>",
      "determination": "APPROVE" | "HOLD" | "DENY",
      "deficiency_codes": ["<code>", ...],
      "required_actions": ["<action>", ...],
      "risk_tier": "low" | "medium" | "high",
      "policy_impacted": true | false
    },
    ...
  ],
  "summary": {
    "approve_count": <int>,
    "hold_count": <int>,
    "deny_count": <int>,
    "high_risk_application_ids": ["<id>", ...],
    "policy_impacted_application_ids": ["<id>", ...],
    "stale_or_unverified_correspondence_ids": ["<cor-id>", ...]
  }
}
```

**Decision tree (per application):**

1. Check `license-history` for active suspensions → if yes, `active_suspension`
   deficiency, determination leans DENY.
2. Check `bonds` for active bond and sufficient amount:
   - No active bond → `no_active_bond` / `bond_cancelled`
   - Active but below required → `bond_shortfall`
3. Check `insurance` for currency and sufficient coverage:
   - Expired → `insurance_expired` / `insurance_not_current`
   - Below required → `insurance_shortfall`
   - Pending (not bound) → `insurance_pending`
4. Check endorsements are verified → if not, `endorsement_not_verified` /
   `endorsement_missing` / `endorsement_pending`
5. Check experience meets threshold → if not, `experience_shortfall`
6. Check `violations` for open items:
   - Serious open → `open_serious_violation` / `unresolved_serious_complaint`
   - Minor open → `open_minor_violation`
7. Check `inspections` for gaps → `inspection_doc_gap` /
   `inspection_safety_recheck`
8. Check `correspondence` for stale/unverified items → collect IDs for summary.
9. Assign risk tier:
   - Any DENY-worth deficiency (suspension, serious unresolved) → `high`
   - Only curable deficiencies, none severe → `medium`
   - No deficiencies → `low`
10. Assign determination:
    - Active suspension or serious unresolved → `DENY`
    - Curable deficiencies → `HOLD`
    - No deficiencies → `APPROVE`
11. Check each deficiency against current policy baseline from `/api/policies` →
    `policy_impacted: true` if the policy changed the outcome.

**Deficiency code vocabulary (observed across training):**

*Contractor batch v1 (train_001):*
`active_suspension`, `bond_cancelled`, `bond_shortfall`, `endorsement_missing`,
`endorsement_pending`, `experience_shortfall`, `inspection_doc_gap`,
`inspection_safety_recheck`, `insurance_expired`, `insurance_pending`,
`insurance_shortfall`, `open_minor_violation`, `open_serious_violation`

*Contractor batch v2 (train_004):*
`active_suspension`, `bond_shortfall`, `endorsement_not_verified`,
`experience_shortfall`, `insurance_expired`, `insurance_not_current`,
`insurance_shortfall`, `no_active_bond`, `unresolved_serious_complaint`

**Action code vocabulary:**

*Contractor batch v1:*
`board_review_suspension`, `clear_document_gap`, `complete_safety_recheck`,
`increase_bond_amount`, `increase_insurance_amount`, `obtain_current_bond`,
`obtain_required_endorsement`, `provide_current_insurance`,
`resolve_minor_violation_review`, `resolve_serious_violation`,
`submit_experience_evidence`, `verify_insurance_binding`,
`verify_pending_endorsement`

*Contractor batch v2:*
`board_review`, `clear_suspension`, `document_experience`, `file_active_bond`,
`increase_bond`, `increase_insurance`, `provide_current_insurance`,
`renew_insurance`, `resolve_complaint`, `verify_endorsement`

**Key insight:** The code vocabulary varies between task instances — always read
the template's `allowed_values` and use only those codes.  The underlying
concepts (bond, insurance, endorsement, experience, violations, inspections) are
stable; the exact code strings are not.

---

## Type B — Liquor License Staff Package

**Examples:** train_002 (L-TR2-001 at LOC-TR2), train_005 (L-TR5-001 at
LOC-TR5, hotel lounge)

**Prompt signature:** "You are preparing a staff review package for a restricted
liquor license transfer" or "internal staff package for the restricted
liquor-license review."  Names one application and one location.

**API endpoints:**
- `GET /api/policies`
- `GET /api/liquor/applications`
- `GET /api/liquor/settlements`
- `GET /api/liquor/privileges`
- `GET /api/liquor/incidents`
- `GET /api/liquor/site-evidence`
- `POST /api/sql` (when available and needed)

**Output structure:**
```
{
  "application_id": "<id>",
  "recommended_posture": "issue_restricted" | "request_follow_up" | "deny",
  "same_premises_basis_applies": true | false,
  "covered_risk_codes": ["<code>", ...],
  "verification_gap_codes": ["<code>", ...],
  "standard_obligation_codes": ["<code>", ...],
  "location_specific_control_codes": ["<code>", ...],
  "first_90_day_plan": [
    { "check_code": "<code>", "timing": "first_30_days" | "days_31_60" | "days_61_90" },
    ...
  ],
  "escalation_trigger_codes": ["<code>", ...]
}
```

**Decision tree:**

1. **Recommended posture:**
   - No material risks, all evidence verified → `issue_restricted`
   - Material risks covered by controls but verification gaps remain →
     `request_follow_up`
   - Uncovered serious risks, unresolved incidents, or tax holds → `deny`

2. **Same-premises basis:** True when the application is for the same physical
   premises as a prior license (check `applications` and `site-evidence` for
   premises linkage).

3. **Covered risk codes:** Risks present at this premises that are already
   mitigated by existing controls.  Review `incidents` for the risk types that
   have occurred; cross-reference with `site-evidence` for controls in place.

4. **Verification gap codes:** Evidence items that are missing, conflicting, or
   stale for this application.  Check `site-evidence` for each category:
   cameras, floor plans, signage, photos, police memos, neighbor notices, tax
   clearance.

5. **Standard obligation codes:** Obligations that apply to this license class
   by default (not location-specific).  Derived from `policies` and
   `applications` license class.

6. **Location-specific control codes:** Controls actively tied to this specific
   location, as evidenced by `site-evidence` or `privileges`.

7. **First 90-day plan:** A monitoring schedule of check-code/timing pairs.
   Map each verification gap and risk to an appropriate check:
   - Camera gaps → `camera_export_test` / `security_cctv_walkthrough`
   - Food service gaps → `food_service_check` / `food_service_service_area_check`
   - Late-night risks → `late_night_closing_visit` / `after_hours_visit`
   - Signage gaps → `control_signage_recheck` / `control_signage_review`
   - ID check risks → `id_check_observation`
   - Noise/patio risks → `noise_patio_boundary_check` / `patio_boundary_check`
   - Tax holds → `tax_clearance_check` / `tax_clearance_review`
   - Police memos → `police_memo_follow_up`
   - Incident logs → `incident_log_review`
   - Timing: most urgent checks → `first_30_days`; follow-ups → `days_31_60`;
     sustained monitoring → `days_61_90`.

8. **Escalation trigger codes:** Events that would cause staff to escalate:
   - After-hours violations
   - Missing camera coverage / footage not produced
   - Food service not available
   - Noise or patio breaches
   - Open tax hold uncleared
   - Unreported violent incident
   - Minor sale / ID check failure
   - Board order conflict
   - Control signage not verified

**Code vocabulary varies between instances** — always read the template's
`allowed_values` and use only those codes.  The semantic categories (risk,
verification gap, obligation, check, trigger) are stable; the exact strings are
not.

---

## Type C — Alcohol Renewal Manual-Review Queue

**Examples:** train_003 (10 licenses: AL-TR3-001–010, boundary 2025-04-10)

**Prompt signature:** "You are supporting the Alcohol Renewal Unit with a
pre-release renewal screen" and "Build a ranked manual-review queue."

**API endpoints:**
- `GET /api/alcohol/licensees`
- `GET /api/alcohol/violations`
- `GET /api/renewal/rules`
- `POST /api/sql`

**Output structure:**
```
{
  "queue": [
    {
      "rank": <int 1..N>,
      "license_no": "<id>",
      "facility_name": "<name>",
      "violation_count": <int>,
      "most_recent_violation_date": "<YYYY-MM-DD>",
      "matched_violation_ids": ["<vid>", ...],
      "match_confidence": "exact" | "close_address" | "uncertain",
      "risk_tier": "low" | "medium" | "high",
      "next_step_label": "manual_fine_check" | "manual_ALERT_check"
                       | "board_review" | "additional_record_check"
    },
    ...
  ],
  "summary": {
    "queue_size": <int>,
    "boundary_date": "<YYYY-MM-DD>",
    "post_boundary_violation_ids_excluded": ["<vid>", ...],
    "close_or_uncertain_match_license_numbers": ["<id>", ...],
    "board_review_license_numbers": ["<id>", ...]
  }
}
```

**Decision tree:**

1. Fetch all licensees and all violations.
2. Apply the boundary date: violations on or before the boundary are in scope;
   violations after are excluded (list in summary).
3. Match violations to licensees by license number, address, or facility name.
4. For each licensee with in-scope violations:
   - Count matched violations.
   - Find the most recent violation date.
   - Determine match confidence (`exact` / `close_address` / `uncertain`).
5. **Rank the queue.**  Primary sort: by risk tier descending (high first).
   Secondary sort within the same tier: by recency of most recent violation
   (more recent = higher rank).  Tertiary sort: by violation count (more =
   higher).  The goal is to surface the highest-risk, most-recent, most-frequent
   offenders first.
6. **Risk tier assignment:**
   - `high` — multiple recent violations, serious violations, or match
     uncertainty requiring deeper review.
   - `medium` — some violations but older or less severe.
   - `low` — few/old violations, no concerning patterns.
7. **Next-step label:**
   - `board_review` — patterns severe enough to warrant board attention.
   - `manual_fine_check` — violations likely to involve fines.
   - `manual_ALERT_check` — requires ALERT system verification.
   - `additional_record_check` — needs supplementary records pulled.
8. **Summary construction:**
   - `queue_size` = length of queue (should match the target size from the prompt).
   - `boundary_date` = the boundary date from the prompt.
   - `post_boundary_violation_ids_excluded` = all violation IDs with dates after
     the boundary.
   - `close_or_uncertain_match_license_numbers` = licensees whose match
     confidence is not `exact`.
   - `board_review_license_numbers` = licensees with `next_step_label:
     "board_review"`.

**Key insight:** The ranking is the core deliverable.  Surface the worst
offenders first, using recency as the primary tiebreaker within a risk tier.
The queue size must match the target from the prompt exactly.
