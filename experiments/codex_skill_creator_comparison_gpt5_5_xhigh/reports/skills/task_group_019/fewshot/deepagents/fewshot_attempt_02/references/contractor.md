# Contractor Batch Reviews

Use this reference for State Contractors Licensing Board application batches.

## Data Assembly

Fetch policies and every contractor endpoint named in the prompt. Use a high `limit` on GET endpoints and confirm that every target `application_id` appears in the application records. Join related records by:

- `application_id` or `related_application_id` for bonds, insurance, violations, correspondence, and inspections.
- `prior_license_id` to `license-history.license_id` and `violations.license_id`.
- Applicant name only as supporting evidence when an explicit prior-license link is absent.

Select the current contractor policy by matching the application's `trade` and `requested_class` to a contractor policy row. Parse `details_json` and use its `minimum_bond`, `minimum_insurance`, `minimum_years_experience`, `required_endorsement`, and blocking-violation fields.

Do not use the host machine's current date for coverage. Use the prompt's explicit review date. If no review date is given, infer a batch review date from the latest relevant submitted/source/verified/inspection/correspondence date in the target batch.

## Findings

Map findings to the exact allowed codes in the answer template:

- Bond: no active bond or cancelled current bond -> `bond_cancelled` or `no_active_bond`; active bond below policy minimum -> `bond_shortfall`.
- Insurance: pending/not bound -> `insurance_pending` or `insurance_not_current`; active record expiring before the review date -> `insurance_expired` or `insurance_not_current`; amount below policy minimum -> `insurance_shortfall`.
- Experience: `years_experience` below policy minimum -> `experience_shortfall`.
- Endorsement: if the policy requires an endorsement and `endorsement_status` is `missing`, use `endorsement_missing` or `endorsement_not_verified`; if `pending`, use `endorsement_pending` or `endorsement_not_verified`.
- License history: active `suspended` status for the linked prior license -> `active_suspension`.
- Violations: open serious complaint/violation -> `open_serious_violation` or `unresolved_serious_complaint`; open minor violation -> `open_minor_violation` when the template allows it. Resolved or dismissed rows do not block.
- Inspections: `DOC_GAP` with non-pass result -> `inspection_doc_gap`; `SAFETY_RECHECK` with non-pass result -> `inspection_safety_recheck`. Ignore inspection issues when the template has no matching allowed code.

If multiple records exist, use the current active financial record with the latest relevant effective/source date. Cancelled, expired, or old records are history unless no current active record exists.

## Required Actions

Translate each deficiency to the template's action vocabulary:

- Active suspension -> board/suspension review, such as `board_review_suspension`, `clear_suspension`, and `board_review` when allowed.
- No active/cancelled bond -> `obtain_current_bond` or `file_active_bond`.
- Bond shortfall -> `increase_bond_amount` or `increase_bond`.
- Endorsement missing/pending/not verified -> `obtain_required_endorsement`, `verify_pending_endorsement`, or `verify_endorsement`.
- Experience shortfall -> `submit_experience_evidence` or `document_experience`.
- Inspection document gap -> `clear_document_gap`.
- Inspection safety recheck -> `complete_safety_recheck`.
- Insurance expired/not current -> `provide_current_insurance` or `renew_insurance`.
- Insurance pending -> `verify_insurance_binding`.
- Insurance shortfall -> `increase_insurance_amount` or `increase_insurance`.
- Open minor violation -> `resolve_minor_violation_review`.
- Open serious violation/complaint -> `resolve_serious_violation`, `resolve_complaint`, and `board_review` when allowed.

Sort deficiency and action arrays as the template specifies, usually lexical order.

## Determination And Risk

Use these defaults unless the prompt or policy states stricter rules:

- `DENY`: active suspension or unresolved/open serious complaint or violation.
- `HOLD`: one or more curable deficiencies and no denial-level block.
- `APPROVE`: no deficiencies.
- `high` risk: denial-level block.
- `medium` risk: hold-level deficiencies.
- `low` risk: approval with no deficiencies.

Set `policy_impacted` to true only when a current policy standard creates a deficiency or material flag that would not exist under the prior baseline policy. Typical current-policy impacts include new endorsement requirements, higher bond/insurance thresholds, and higher experience thresholds. Do not mark old unresolved discipline or ordinary expired paperwork as policy-impacted unless the current policy changes the analysis.

## Summary Fields

Compute summary counts from `application_decisions`. Build high-risk and policy-impacted ID lists directly from item-level fields.

For `stale_or_unverified_correspondence_ids`, include correspondence tied to a target application when it is unverified, explicitly stale, or explicitly conflicting. Use `verified_by_agency == 0`, notes containing stale/unverified/no agency confirmation, assertion values indicating conflict, or attachments predating the application when the row says the attachment is stale. Sort IDs ascending.
