# Field Vocabulary Mapping Reference

The single biggest source of error across licensing-review tasks is using a code from the
wrong vocabulary. Two structurally identical tasks can expect **different enum strings**
for the same concept. This reference maps the underlying *concepts* to the families of
strings you will see, so you can pick the string the current template allows. It is
generic — it contains no task-specific answers.

Read the task's own `answer_template.json` first; the code strings below are the typical
variants, not a fixed contract for any one task.

## Contractor eligibility — deficiency code concept families

| Concept (when it applies) | Typical enum variants |
|---|---|
| No operative bond (no active bond row, or only cancelled/expired) | `no_active_bond`, `bond_cancelled` |
| Bond exists but below policy minimum | `bond_shortfall` |
| Insurance not current at the review date (expired by date, or non-current status) | `insurance_not_current`, `insurance_expired`, `insurance_pending` |
| Insurance amount below policy minimum | `insurance_shortfall` |
| Endorsement required by policy but not satisfied | `endorsement_missing`, `endorsement_pending`, `endorsement_not_verified` |
| Experience years below policy minimum | `experience_shortfall` |
| Prior license suspended / pending board action | `active_suspension` |
| Open serious violation (block policy) | `open_serious_violation`, `unresolved_serious_complaint` |
| Open minor violation | `open_minor_violation` |
| Inspection DOC_GAP finding | `inspection_doc_gap` |
| Inspection SAFETY_RECHECK finding | `inspection_safety_recheck` |

**Selection rule**: pick the variant that (a) appears in the current template's
`allowed_values`, and (b) matches the *operative* record state. "Shortfall" vs "no active
bond" is a real distinction: shortfall requires a bond to exist but be short; "no active
bond"/"cancelled" requires no operative bond.

## Contractor eligibility — required action concept families

| Concept | Typical enum variants |
|---|---|
| File a new active bond | `obtain_current_bond`, `file_active_bond` |
| Raise bond amount to minimum | `increase_bond_amount`, `increase_bond` |
| Provide current insurance | `provide_current_insurance` |
| Renew expired insurance | `renew_insurance` |
| Raise insurance amount | `increase_insurance_amount`, `increase_insurance` |
| Verify a pending/missing endorsement | `obtain_required_endorsement`, `verify_pending_endorsement`, `verify_endorsement` |
| Submit experience evidence | `submit_experience_evidence`, `document_experience` |
| Clear a suspension / board review | `board_review_suspension`, `clear_suspension`, `board_review` |
| Resolve an open violation/complaint | `resolve_serious_violation`, `resolve_minor_violation_review`, `resolve_complaint` |
| Cure an inspection finding | `clear_document_gap`, `complete_safety_recheck` |
| Verify pending insurance binding | `verify_insurance_binding` |

Pair each deficiency with the action(s) that cure it, using only the current template's
action vocabulary.

## Liquor staff package — code families

### covered_risk_codes (risks addressed by the ACTIVE settlement's controls)
Typical set: `SAME_PREMISES`, `AFTER_HOURS`, `ASSAULT`, `MINOR_SALE` / `SALE_TO_MINOR`,
`NOISE`, `PUBLIC_SAFETY`, `TAX_HOLD`, `FOOD_SERVICE_GAP`, `PATIO_BOUNDARY`,
`CAMERA_COVERAGE`, `ID_CHECK`. Include only risks the active controls cover — keep this
list minimal.

### verification_gap_codes
Typical set: `camera_evidence_missing`, `food_service_evidence_missing`,
`floor_plan_conflicting`, `floor_plan_stale`, `late_night_monitoring_needed`,
`tax_hold_unresolved`, `control_signage_missing` / `CONTROL_SIGNAGE_CURRENT_MISSING` /
`CONTROL_SIGNAGE_CONFLICTING`, `police_memo_identity_note` / `POLICE_MEMO_CONFLICTING`,
`neighbor_notice_missing`, `site_photo_missing`, `OPEN_INCIDENT_FOLLOW_UP`,
`TAX_CLEARANCE_MISSING`. Derive each from a concrete `site-evidence` status or an open
incident at the location.

### standard_obligation_codes vs location_specific_control_codes
- `standard_obligation_codes` = obligations with `standard_required=1` for the
  application's `license_class` in `/api/liquor/privileges`.
- `location_specific_control_codes` = the `controls` array of the **active** settlement
  only. Use the same short obligation codes (ID_CHECK, HOURS, SECURITY, FOOD_SERVICE, CCTV,
  PATIO, NOISE, DELIVERY) for both — but populate them from different sources. Do not
  duplicate inactive settlements' controls here.

### first_90_day_plan check_code families
`after_hours_visit`, `control_signage_recheck`, `food_service_check`,
`id_check_observation`, `noise_log_review`, `patio_boundary_check`,
`police_memo_follow_up`, `security_cctv_walkthrough`, `tax_clearance_check` (one variant);
hotel-lounge variant: `camera_export_test`, `food_service_service_area_check`,
`late_night_closing_visit`, `noise_patio_boundary_check`, `id_check_observation`,
`control_signage_review`, `tax_clearance_review`, `incident_log_review`. `timing` ∈
`first_30_days`, `days_31_60`, `days_61_90`. Sequence urgent gaps early.

### escalation_trigger_codes
Typical set: `after_hours_service` / `AFTER_HOURS_VIOLATION`, `missing_camera_coverage` /
`SECURITY_CCTV_CONTROL_FAILURE`, `footage_not_produced`, `food_service_not_available`,
`noise_or_patio_breach`, `open_tax_hold_uncleared` / `TAX_HOLD_REOPENED`,
`unreported_violent_incident` / `MAJOR_INCIDENT_REPORTED`, `minor_sale` /
`REFERRED_MINOR_SALE_UNRESOLVED`, `patio_boundary_failure`, `id_check_failure`,
`CONTROL_SIGNAGE_NOT_VERIFIED`, `BOARD_ORDER_CONFLICT`. Tie each to a concrete open item
or evidence conflict present at the location.

## Renewal queue — code families

### match_confidence
`exact` (direct `license_no` match), `close_address` (address/facility-name inferred
match — usually a distractor, exclude), `uncertain` (successor/predecessor license match
per `successor_to`, marked uncertain per policy). Only `exact` and `uncertain` produce
queue matches; `close_address` distractors are not queue matches.

### risk_tier
`high` (open serious matched violations or large unpaid fines), `medium` (moderate matched
history), `low` (light history).

### next_step_label
`board_review` (open serious violations / major incidents), `manual_ALERT_check`
(`alert_flag=1` on matched violations), `manual_fine_check` (large unpaid fine balances),
`additional_record_check` (otherwise). Prefer the most severe applicable label.

## Cross-cutting reminders

- The **review date** governs financial currency; a record's `status: active` does not
  override an `expiration_date` before the review date.
- **Endorsement** deficiencies apply only when the matched policy's `required_endorsement`
  is non-null.
- **policy_impacted** is a legacy-baseline comparison, not a record of applicant fault.
- **Resolved/dismissed** violations and **pass** inspections generally produce no
  deficiency (the inspection finding code, not the pass/fail result, is the trigger).
- Summary fields are always recomputed from the per-record decisions, never hand-set.
