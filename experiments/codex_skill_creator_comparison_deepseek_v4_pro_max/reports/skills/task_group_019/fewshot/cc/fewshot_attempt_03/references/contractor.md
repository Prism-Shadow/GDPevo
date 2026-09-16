# Contractor Licensing Review — Domain Reference

Load this reference when the task involves contractor applications, bonds,
insurance, endorsements, experience, violations, inspections, or license
history. Use it alongside the main SKILL.md workflow.

## Endpoints

| Endpoint | What it returns |
|---|---|
| GET /api/policies | Current policy baseline that may create new deficiencies |
| GET /api/contractor/applications | Application records keyed by application_id |
| GET /api/contractor/bonds | Bond records with status, amount, effective dates |
| GET /api/contractor/insurance | Insurance policies with coverage amounts, expiry, status |
| GET /api/contractor/license-history | Prior licenses, suspensions, disciplinary actions |
| GET /api/contractor/violations | Open complaints and violation records |
| GET /api/contractor/correspondence | Board-applicant correspondence with dates and status |
| GET /api/contractor/inspections | Inspection reports, findings, recheck requirements |
| POST /api/sql | Arbitrary SQL against the task database |

## Determination Rules

Assign determination using this hierarchy:

1. **DENY** — any of:
   - Active license suspension (active_suspension)
   - Unresolved serious complaint/violation (unresolved_serious_complaint, open_serious_violation)
   - Combination of multiple high-severity deficiencies where board review is the only path forward

2. **HOLD** — fixable deficiencies present but none that require outright denial:
   - Bond issues (cancelled, shortfall, not active)
   - Insurance issues (expired, pending, shortfall, not current)
   - Endorsement issues (missing, pending, not verified)
   - Experience shortfall
   - Inspection documentation gaps or safety rechecks
   - Open minor violations
   - Any combination of the above that is resolvable

3. **APPROVE** — no deficiencies found across all data sources

## Deficiency Codes

Map findings to these codes. Use exact strings; sort alphabetically within each application.

| Finding | Code |
|---|---|
| No active bond on file | no_active_bond (train-004 schema) or bond_cancelled (train-001 schema) |
| Bond amount below required minimum | bond_shortfall |
| Insurance policy expired | insurance_expired |
| Insurance not yet current/binding | insurance_not_current or insurance_pending |
| Insurance coverage below required minimum | insurance_shortfall |
| Specialty endorsement not verified | endorsement_not_verified or endorsement_missing |
| Endorsement submitted but not yet confirmed | endorsement_pending |
| Work experience documentation insufficient | experience_shortfall |
| License currently under active suspension | active_suspension |
| Unresolved serious complaint | unresolved_serious_complaint or open_serious_violation |
| Unresolved minor violation | open_minor_violation |
| Inspection documentation gap | inspection_doc_gap |
| Inspection safety recheck required | inspection_safety_recheck |

Use the code vocabulary that matches the task answer_template.json. If the
template lists allowed deficiency codes, use only those. If two tasks share
overlapping concepts but use different code strings, match the template, not
the other task.

## Required Actions

Map deficiencies to corrective actions. Sort alphabetically within each application.

| Deficiency | Required Action |
|---|---|
| Bond cancelled / no active bond | obtain_current_bond or file_active_bond |
| Bond shortfall | increase_bond_amount or increase_bond |
| Insurance expired | provide_current_insurance or renew_insurance |
| Insurance pending | verify_insurance_binding or provide_current_insurance |
| Insurance shortfall | increase_insurance_amount or increase_insurance |
| Endorsement missing | obtain_required_endorsement or verify_endorsement |
| Endorsement pending | verify_pending_endorsement or verify_endorsement |
| Experience shortfall | submit_experience_evidence or document_experience |
| Active suspension | board_review_suspension or clear_suspension + board_review |
| Unresolved serious complaint/violation | resolve_serious_violation or resolve_complaint + board_review |
| Open minor violation | resolve_minor_violation_review |
| Inspection doc gap | clear_document_gap |
| Inspection safety recheck | complete_safety_recheck |

## Risk Tiering

- **high**: Any DENY determination, or any application with active_suspension,
  unresolved_serious_complaint, open_serious_violation, or three or more
  distinct deficiency codes
- **medium**: HOLD determination with one or more deficiencies but none of the
  high triggers
- **low**: APPROVE determination (no deficiencies)

## Policy Impact

Set policy_impacted to true when a current policy standard creates a
deficiency or material review flag that would not have existed under the prior
baseline. Check this by comparing the current /api/policies against what each
application would need. Common signals: new endorsement requirements, increased
bond/insurance minimums, new experience thresholds.

## Correspondence

Review /api/contractor/correspondence for each application. Identify
correspondence IDs that are stale (no response beyond expected reply window) or
where the status cannot be verified. List them in
stale_or_unverified_correspondence_ids sorted ascending. Use exact IDs as
returned by the API.

## Summary Construction

- approve_count, hold_count, deny_count: tally from application_decisions
- high_risk_application_ids: all application_ids with risk_tier "high", sorted ascending
- policy_impacted_application_ids: all application_ids with policy_impacted true, sorted ascending
- stale_or_unverified_correspondence_ids: collected from correspondence review, sorted ascending
