---
name: licensing-review-solver
description: Structured licensing data-service review for contractor eligibility batches, restricted liquor-license staff packages, and alcohol renewal manual-review queues. Use when a prompt provides licensing environment endpoints plus a JSON answer template and asks Codex to return exact JSON decisions, risk codes, monitoring plans, queue ranks, or summaries for contractor applications, liquor premises controls, or alcohol renewal releases.
---

# Licensing Review Solver

## Overview

Solve licensing review tasks by building a record-backed decision table from the task environment, applying the current policy records, mapping findings to the answer template's allowed code vocabulary, and returning only schema-conformant JSON.

## Core Workflow

1. Read the prompt and `input/payloads/answer_template.json` before querying data.
2. Extract the target identifiers, review date or release boundary, queue size, required endpoints, ordering rules, allowed enum values, and required summary keys.
3. Read the environment access instructions when present. Use the prompt base URL or the access file's base URL. If SQL is allowed, send the documented token header and only `SELECT` queries.
4. Query `/api/policies` for all task families. Query `/api/renewal/rules` for renewal queues.
5. Prefer filtered SQL queries over unfiltered endpoint dumps. Filter to the prompt's target application IDs, location IDs, license numbers, and any predecessor or successor license numbers discovered from target rows.
6. Normalize records into one case file per target. Keep the raw IDs needed for summary arrays.
7. Apply the task-family rules below. When the template offers different names for the same concept, use only the allowed names from that template.
8. Validate the final JSON mechanically: exact top-level keys, no prose, no extra keys, all required targets, sorted arrays where requested, correct counts, and empty arrays when nothing applies.

Never use the real current date for licensing cutoffs. Use the prompt's review date, release boundary, or date implied by the task data. Do not call judge or evaluator endpoints.

## Contractor Eligibility

Use for State Contractors Licensing Board application batches.

Data to collect:

- `contractor_applications` for trade, class, experience, endorsement status, prior license, and submitted date.
- `contractor_bonds`, `contractor_insurance`, `contractor_license_history`, `contractor_violations`, `contractor_correspondence`, and `contractor_inspections` for related facts.
- Contractor policies whose `details_json` gives `minimum_bond`, `minimum_insurance`, `minimum_years_experience`, `required_endorsement`, and serious-violation blocking behavior.

Per application:

- Match the policy by trade and requested class. Parse `details_json`; do not infer thresholds from names when policy data is available.
- Bond: use active, uncancelled current bonds. If no qualifying active bond exists, add the template's no-active-bond concept such as `no_active_bond` or `bond_cancelled`. If an active bond exists below the policy minimum, add `bond_shortfall`.
- Insurance: require active status, a non-expired expiration date as of the task review date, and amount at least the policy minimum. Pending coverage is a pending/not-current deficiency; expired active coverage is an expired deficiency; below-minimum coverage is a shortfall deficiency.
- Endorsement: if the policy requires an endorsement, `verified` passes. `missing` maps to a missing/not-verified code. `pending` maps to pending when available, otherwise not-verified.
- Experience: years below the policy minimum maps to `experience_shortfall`.
- License history: a prior license with `status` suspended maps to `active_suspension`.
- Violations: open serious violations or complaints are denial-level. Open minor violations matter only when the template has a minor-violation code. Resolved or dismissed violations usually support context but do not create deficiencies.
- Inspections: include inspection deficiencies only when the template supports them. Failed or conditional `DOC_GAP` maps to document-gap action; failed `SAFETY_RECHECK` maps to safety-recheck action.
- Correspondence summary: include correspondence IDs that are unverified by the agency or stale for the application, such as received before submission or noted as stale. Sort IDs as the template requires.

Determination and risk:

- `DENY` when denial-level codes apply, especially active suspension or open serious violation/complaint.
- `HOLD` when any non-denial deficiency remains.
- `APPROVE` only when no deficiencies or actions remain.
- Risk is `high` for denial-level issues, `medium` for holds, and `low` for clean approvals unless the prompt supplies a different risk rule.

Common contractor code mapping:

| Concept | Deficiency code | Required action |
| --- | --- | --- |
| No active/current bond | `no_active_bond`, `bond_cancelled` | `file_active_bond`, `obtain_current_bond` |
| Bond below policy minimum | `bond_shortfall` | `increase_bond`, `increase_bond_amount` |
| Insurance pending/not bound | `insurance_pending`, `insurance_not_current` | `verify_insurance_binding`, `provide_current_insurance` |
| Insurance expired | `insurance_expired`, `insurance_not_current` | `renew_insurance`, `provide_current_insurance` |
| Insurance below minimum | `insurance_shortfall` | `increase_insurance`, `increase_insurance_amount` |
| Required endorsement missing | `endorsement_missing`, `endorsement_not_verified` | `obtain_required_endorsement`, `verify_endorsement` |
| Required endorsement pending | `endorsement_pending`, `endorsement_not_verified` | `verify_pending_endorsement`, `verify_endorsement` |
| Experience below minimum | `experience_shortfall` | `submit_experience_evidence`, `document_experience` |
| Active suspension | `active_suspension` | `board_review_suspension`, `clear_suspension`, `board_review` |
| Open serious complaint/violation | `open_serious_violation`, `unresolved_serious_complaint` | `resolve_serious_violation`, `resolve_complaint`, `board_review` |
| Open minor violation | `open_minor_violation` | `resolve_minor_violation_review` |
| Inspection document gap | `inspection_doc_gap` | `clear_document_gap` |
| Inspection safety recheck | `inspection_safety_recheck` | `complete_safety_recheck` |

For `policy_impacted`, mark true when current 2025 policy standards create a material deficiency that the prior baseline would not have created. In the staged pattern this includes current-policy amount shortfalls and required-endorsement deficiencies; it does not include old suspensions, open violations, expired or pending documents, or experience shortfalls unless the prompt or policy records explicitly make experience a current-policy change.

## Restricted Liquor Staff Packages

Use for restricted liquor-license transfers, renewals with controls, hotel lounges, restaurants, or similar premises-control packages.

Data to collect:

- Target liquor application for `application_id`, `location_id`, license class, and posture.
- `liquor_settlements` for same-premises basis and active location controls. Parse `controls_json`.
- `liquor_privileges` for standard obligations by license class.
- `liquor_incidents` for current and historical risk codes. Exclude dismissed incidents unless the prompt says to use them.
- `liquor_site_evidence` for missing, conflicting, stale, or current evidence.

Classification rules:

- `standard_obligation_codes`: include only `liquor_privileges` rows for the license class where `standard_required` is true.
- `location_specific_control_codes`: include only active, unexpired settlement controls for the target location. Do not include inactive historical controls here.
- `same_premises_basis_applies`: true when policy says same-premises history matters and the location has any SAME_PREMISES settlement basis, active or historical.
- `covered_risk_codes`: include risks that current standard obligations or active controls actually cover. Useful mappings are `ID_CHECK` to minor-sale/sale-to-minor risk, `HOURS` to after-hours risk, `SECURITY` or `CCTV` to assault/public-safety risk, `FOOD_SERVICE` to food-service risk, and `NOISE` or `PATIO` to noise/patio-boundary risk. Include `SAME_PREMISES` when the basis applies and the template allows it. Do not list open risks that are not covered by current obligations or controls.
- `verification_gap_codes`: derive from site evidence and unresolved incidents. Missing/conflicting control signage, floor plans, police memos, site photos, tax clearance, camera evidence, and food-service evidence map directly to similarly named template codes. Open or referred incidents map to open-incident follow-up or specific unresolved-risk codes when available. Late-night or after-hours risk without enough current verification maps to a late-night monitoring gap when that code exists.
- `recommended_posture`: use `issue_restricted` only when current controls cover the relevant risks and no material verification gap remains. Use `request_follow_up` for unresolved evidence, open incident follow-up, tax clearance, camera/food-service proof gaps, or late-night monitoring needs. Use `deny` only for blocking policy or severe unresolved risk that cannot be handled by restrictions.

Monitoring and escalation:

- Build `first_90_day_plan` from the actual gaps and active controls: camera export/walkthrough for camera or CCTV gaps, food-service checks for food evidence, late-night visits for after-hours or late-night concerns, ID observation for minor-sale risk, control-signage recheck for signage gaps, police memo follow-up for memo conflicts, noise/patio checks for active noise or patio controls, and tax clearance review only when the template and prompt call for operational tax follow-up.
- Follow the template's ordering rule. Some templates require alphabetical `check_code`; others require operational sequence.
- Build escalation triggers from the same facts: after-hours service, missing or failed camera coverage, footage not produced, food service unavailable, noise or patio breach, unresolved tax hold, unresolved referred minor sale, major incident, control signage not verified, and security/CCTV control failure.

## Alcohol Renewal Queues

Use for pre-release renewal screens and manual-review queues.

Data to collect:

- Target licensees from `alcohol_licensees`, including facility name, address, active flag, and `successor_to`.
- Violations from `alcohol_violations` for each current license and any predecessor/successor license numbers discovered from target rows.
- Renewal rules for the prompt's release boundary.

Matching and filtering:

- Use only violations with `violation_date` on or before the release boundary for queue decisions.
- Put later violation IDs in `post_boundary_violation_ids_excluded`, sorted as requested.
- Exact match means the violation's `license_no` equals the target license number.
- Close-address match means the violation is on a predecessor/successor license tied to the target and the facility/address is substantially the same.
- Use `uncertain` when the match is based on successor history, name, or address but the identity is not clean.
- Sort `matched_violation_ids` by violation date ascending, then violation ID ascending. `most_recent_violation_date` is the latest included violation date.

Queue fields:

- `violation_count` is the count of matched pre-boundary violations.
- `next_step_label` should follow rule priority: `board_review` for close/uncertain successor matches, major or serious unresolved matters, sale-to-minor issues needing board attention, or other board-review triggers; `manual_fine_check` for unpaid/open fine balances requiring hold; `manual_ALERT_check` for alert-flag review without higher priority; `additional_record_check` for lower-confidence or residual record work.
- Rank entries by priority group first: board review, then manual fine check, then manual alert check, then additional record check. Within a group, sort by most recent matched violation date descending, then violation count descending, then license number ascending unless the prompt or renewal rule provides a different ordering.
- Risk is high for board-review cases, material unpaid-fine holds, serious/open recent violations, high counts, or close/uncertain successor matches; medium for lower-priority alert/manual review; low only for minimal resolved history.

Summary fields:

- `queue_size` must equal the number of queue entries returned.
- `boundary_date` must echo the prompt boundary.
- `close_or_uncertain_match_license_numbers` includes target licenses whose `match_confidence` is not exact.
- `board_review_license_numbers` includes queue entries whose next step is `board_review`.
- Sort summary arrays exactly as the template requires.

## Final JSON Checks

- Include exactly the target applications/licenses requested; do not include distractor records.
- Use the answer template's exact enum spellings and casing.
- Sort item arrays lexically when requested; otherwise use the operational order requested by the template.
- Recompute summaries from the final item-level records after edits.
- Return only the JSON object, with no markdown, comments, citations, or explanatory text.
