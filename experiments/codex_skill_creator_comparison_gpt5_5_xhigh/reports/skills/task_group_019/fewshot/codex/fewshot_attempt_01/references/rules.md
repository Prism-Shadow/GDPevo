# Licensing Decision Rules

## Data Access

- Fetch policies and the domain endpoints named in the prompt. Parse any `details_json` or `controls_json` fields as JSON.
- Link records by stable IDs: contractor `application_id`, liquor `location_id`, and renewal `license_no`. For contractor license history, use the application's `prior_license_id` when present.
- If a broad GET endpoint is noisy, filter locally to the target IDs. Do not infer from unrelated distractor rows.
- SQL may be unavailable even when listed; fall back to GET records when authentication or token errors occur.

## Contractor Batches

### Policy Lookup

Map each contractor application to the current contractor policy by trade and requested class:

- Electrical Class A: electrical Class A standards.
- Plumbing Class B: plumbing Class B standards.
- HVAC Class B: HVAC Class B standards.
- General Building Class A: general building Class A standards.
- Roofing Limited: roofing limited standards.
- Solar Specialty: solar specialty standards.

Use the policy's minimum bond, minimum insurance, minimum years of experience, required endorsement, and serious-open-violation rule.

### Deficiency Mapping

Choose the code names from the active answer template:

- Active bond missing, cancelled, or expired: use `no_active_bond` when available; otherwise use `bond_cancelled` for cancelled bond records. Required action is `file_active_bond` or `obtain_current_bond`.
- Active bond amount below the current minimum: `bond_shortfall`; action `increase_bond` or `increase_bond_amount`.
- Active insurance with expiration before the review date: `insurance_expired` when available; otherwise `insurance_not_current`. Action `renew_insurance` or `provide_current_insurance`.
- Insurance status `pending`: `insurance_pending` when available; otherwise `insurance_not_current`. Action `verify_insurance_binding` or `provide_current_insurance`.
- Active/current insurance amount below the current minimum: `insurance_shortfall`; action `increase_insurance` or `increase_insurance_amount`.
- Years of experience below the policy minimum: `experience_shortfall`; action `document_experience` or `submit_experience_evidence`.
- Required endorsement `missing`: use `endorsement_missing` when available; otherwise `endorsement_not_verified`. Action `obtain_required_endorsement` or `verify_endorsement`.
- Required endorsement `pending`: use `endorsement_pending` when available; otherwise `endorsement_not_verified`. Action `verify_pending_endorsement` or `verify_endorsement`.
- Prior license history status `suspended`: `active_suspension`; action `clear_suspension` or `board_review_suspension`. Add `board_review` if the schema includes it as a required action for high-risk discipline.
- Open serious contractor violation or complaint: use `open_serious_violation` or `unresolved_serious_complaint`; action `resolve_serious_violation` or `resolve_complaint`, plus `board_review` when available.
- Open minor violation: `open_minor_violation`; action `resolve_minor_violation_review`.
- Inspection `finding_code` `DOC_GAP` with a non-pass result: `inspection_doc_gap`; action `clear_document_gap`.
- Inspection `finding_code` `SAFETY_RECHECK` with a fail/non-pass result: `inspection_safety_recheck`; action `complete_safety_recheck`.
- Ignore dismissed/resolved violations for deficiency codes unless the prompt or template asks for historical risk.

### Determination, Risk, and Policy Impact

- `DENY` when there is an active suspension or an open serious violation/complaint.
- `HOLD` when there is any deficiency or required action but no denial-level issue.
- `APPROVE` only when no deficiency or action remains.
- Risk tier is `high` for denial-level issues, `medium` for holds, and `low` for clean approvals unless the prompt defines a different matrix.
- `policy_impacted` is true when a current policy standard creates a deficiency or material flag that would not have applied under the prior baseline, especially current bond/insurance increases and newer endorsement requirements. Do not mark true for ordinary stale documents, active suspensions, or unresolved violations alone.

### Contractor Summary

- Counts must equal the number of item-level `APPROVE`, `HOLD`, and `DENY` decisions.
- `high_risk_application_ids` are applications with `risk_tier` `high`, sorted ascending.
- `policy_impacted_application_ids` are item-level true values, sorted ascending.
- `stale_or_unverified_correspondence_ids` include target correspondence where `verified_by_agency` is false, or the notes indicate a stale attachment. Include conflicting or unverified applicant notes when they are tied to a target application. Sort ascending.

## Restricted Liquor Staff Packages

### Record Interpretation

- The target application gives the `application_id`, license class, and `location_id`.
- Settlement rows provide historical bases and current location-specific controls. Only controls with parsed `controls_json.active == true` are current location-specific controls.
- Same-premises basis applies when any settlement/history row for the location has basis `SAME_PREMISES`; inactive history still matters when policy says same-premises history matters.
- Keep standard license obligations separate from location-specific controls. For restaurant, beer/wine, and hotel-lounge restricted reviews, ordinary obligations usually include `ID_CHECK`, `HOURS`, and `FOOD_SERVICE` when those codes are allowed.

### Risks and Gaps

- Covered risks come from incident history and settlement bases that current active controls or standard obligations address. Examples: hours/security/CCTV controls can cover after-hours, assault/public-safety, and minor-sale risks; active noise/patio controls cover noise and patio-boundary risks.
- Dismissed incidents are not covered risks unless the prompt explicitly asks for historical dismissed risks.
- Open, referred, or unresolved incidents create verification gaps or escalation triggers when not fully covered by current controls.
- Site evidence with `status` `missing` creates the corresponding missing evidence gap; `conflicting` creates the corresponding conflicting evidence gap.
- Missing current camera/CCTV evidence creates `camera_evidence_missing` or the template's CCTV/control-signage equivalent.
- Missing food-service proof creates `food_service_evidence_missing`.
- A conflicting floor plan creates `floor_plan_conflicting` or `FLOOR_PLAN_CONFLICTING`.
- An open tax hold creates `tax_hold_unresolved` and a tax escalation trigger when allowed.
- After-hours history or late-night prompt emphasis creates a late-night monitoring gap and first-90-day late-night check when allowed.

### Posture and Plans

- `deny` only for a disqualifying unresolved major issue with no feasible restricted-control path.
- `request_follow_up` when current controls exist but evidence gaps, open incidents, tax holds, or conflicting records remain.
- `issue_restricted` when risks are covered and verification gaps are empty.
- First-90-day plan mappings:
  - camera/CCTV gap or active CCTV/security control: camera export test or security/CCTV walkthrough in the first 30 days.
  - food-service gap: food-service area check in the first 30 days.
  - ID/minor-sale risk: ID-check observation in the first 30 days.
  - control-signage gap: control-signage recheck in the first 30 days.
  - police memo conflict: police-memo follow-up in the first 30 days.
  - after-hours/late-night risk: after-hours or late-night visit in days 31-60.
  - noise or patio control: noise/patio boundary check, often days 61-90 unless the template says otherwise.
- Escalation triggers mirror unresolved high-value risks: after-hours service, missing or failed camera coverage, footage not produced, food service unavailable, noise/patio breach, uncleared tax hold, unreported major/violent incident, minor sale, ID-check failure, or control signage not verified.

## Alcohol Renewal Manual-Review Queues

### Matching and Boundary

- Use the release boundary from the prompt or the matching renewal rule.
- Include violations known on or before the boundary date. Exclude later violations and list excluded post-boundary IDs in the summary.
- Prefer exact `license_no` matches. If a current license has `successor_to`, include predecessor violations only when the address/facility clearly matches; mark confidence `close_address` unless the template or data supports exact confidence.
- Use `uncertain` for successor or address matches with unresolved identity ambiguity.

### Queue Fields

- `matched_violation_ids`: sort by violation date ascending, then violation ID ascending.
- `violation_count`: count matched pre-boundary violations.
- `most_recent_violation_date`: latest matched pre-boundary date.
- `match_confidence`: `exact` for current license rows only; `close_address` for predecessor/successor rows with matching address; `uncertain` for weaker matches.
- `next_step_label` priority:
  - `board_review` for severe public-safety clusters, sale-to-minor or tax-hold clusters with multiple alerts, serious open/pending matters, or close-address successor history that materially affects release.
  - `manual_fine_check` for unpaid fine balances or fine-hold themes not escalated to board review.
  - `manual_ALERT_check` for alert-flagged rows without a stronger fine or board-review reason.
  - `additional_record_check` for weak or uncertain matches without stronger reasons.
- Risk tier is `high` for board-review cases, serious/open clusters, multiple recent alerts, or unresolved fine/tax/sale-to-minor concerns; `medium` for lower-severity alert clusters; `low` only for minimal residual issues.

### Ranking and Summary

- Rank board-review entries first, then manual-fine entries, then manual-ALERT entries, then additional-record entries.
- Within each priority group, sort by most recent matched violation date descending, then higher violation count, then license number ascending unless the prompt specifies a different ranking rule.
- Ranks must be consecutive integers starting at 1 and the queue size must match the prompt/template.
- Summary lists:
  - `queue_size`: actual queue length.
  - `boundary_date`: boundary used.
  - `post_boundary_violation_ids_excluded`: all excluded later target/successor violation IDs, sorted ascending.
  - `close_or_uncertain_match_license_numbers`: queued licenses with non-exact confidence, sorted ascending.
  - `board_review_license_numbers`: queued board-review licenses, sorted ascending.
