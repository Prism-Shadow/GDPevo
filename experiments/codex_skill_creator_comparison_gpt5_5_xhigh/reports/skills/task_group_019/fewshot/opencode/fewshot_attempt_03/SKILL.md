---
name: licensing-review-decisions
description: Structured licensing decision support for task-environment regulatory records. Use this skill whenever the user asks Codex to review contractor licensing applications, restricted liquor-license applications or transfers, alcohol renewal hold queues, licensing policies, violations, bonds, insurance, inspections, settlements, site evidence, or any task that must return an exact JSON answer from licensing-environment API records.
---

# Licensing Review Decisions

Use this skill to produce exact JSON answers for licensing review tasks backed by the shared task environment. The recurring work is not writing a memo; it is joining policy and record endpoints, applying the schema's allowed codes, and returning only valid JSON.

## First Pass

1. Read the prompt and `input/payloads/answer_template.json`.
2. Extract the domain, target identifiers, review date or boundary date, queue size, endpoint list, required keys, allowed enum codes, ordering rules, and whether SQL is listed as available.
3. Read the environment instructions for the base URL. Replace `<TASK_ENV_BASE_URL>` with that base URL.
4. Fetch the listed public endpoints. If SQL is listed and credentials are available in the environment instructions, use SQL for complete joins and to find rows not exposed through simple GET endpoints. If SQL returns an auth error, continue with the public endpoints and do not invent missing records.
5. Parse embedded JSON fields such as `details_json` and `controls_json`.
6. Keep a scratch table per target entity showing the record facts, derived codes, and why each code applies. Use the scratch table for reasoning only; final output must be JSON only.

Always trust the answer template over generic rules for field names, code names, sort order, and whether optional-looking fields are allowed.

## Shared JSON Rules

- Return exactly one JSON object and no prose, markdown, comments, citations, or extra keys.
- Include every required target from the prompt, even when no deficiencies or matched records apply.
- Use only enum values allowed by the template. When two task families use different names for the same concept, translate into the template's vocabulary.
- Use empty arrays for no applicable codes.
- Enforce every ordering rule in the template. Typical requirements are application IDs ascending, code arrays ascending, and renewal queue ranks from 1 with no gaps.
- Recompute summary counts and summary ID lists from the application or queue rows after drafting the body.
- Before finalizing, mentally validate that every array item is permitted by the template and every summary field is consistent with the row-level decisions.

## Data Joining Patterns

Contractor application reviews:

- Join applications by `application_id`.
- Join bonds and insurance by `application_id`; prefer current active rows and ignore old cancelled or expired rows except as evidence that no current coverage exists.
- Join license history by the application's `prior_license_id`.
- Join violations by `related_application_id` and by prior `license_id`; unresolved rows have `status: open` and no `resolved_date`.
- Join correspondence by `related_application_id`.
- Join inspections by `related_application_id`.
- Apply current contractor policy by matching trade and requested class to the policy's `rule_code` and `details_json`.

Restricted liquor-license reviews:

- Join the target application by `application_id`, then use its `location_id`.
- Join settlements, incidents, and site evidence by `location_id`.
- Join standard privileges by `license_class`.
- Treat settlement `controls_json.active` as the source for current location-specific controls. Expired or inactive settlement rows can still prove historical basis, but they are not current controls.

Alcohol renewal queues:

- Join target licensees by `license_no`; include only active current target licenses unless the prompt says otherwise.
- Join violations by exact `license_no`.
- If a target license has `successor_to`, also inspect predecessor license rows and same-address legacy violations. Assign `close_address` confidence when successor or address matching, rather than a direct exact license match, is what brings violations into the target queue.
- Exclude violations after the release boundary from queue scoring and list their IDs in the post-boundary summary if requested.

## Contractor Decisions

Current contractor policy standards observed in the environment:

| Trade and class | Minimum bond | Minimum insurance | Minimum experience | Required endorsement |
| --- | ---: | ---: | ---: | --- |
| Electrical Class A | 50000 | 1000000 | 5 | EE-1 |
| Plumbing Class B | 30000 | 750000 | 4 | PH-2 |
| HVAC Class B | 25000 | 500000 | 3 | MECH-H |
| General Building Class A | 75000 | 1000000 | 5 | GB-A |
| Roofing Limited | 20000 | 500000 | 2 | none |
| Solar Specialty | 30000 | 750000 | 3 | SOL-PLUS |

Coverage and eligibility checks:

- Bond: require an active, uncancelled bond meeting the current policy amount. Use the template's no-current-bond code when no active row exists; use the cancelled-bond code when the current record is cancelled; use the shortfall code when active amount is below minimum.
- Insurance: require a current, verified active policy whose expiration is on or after the review date and whose amount meets the current policy minimum. Treat `pending` as a binding-verification problem. Treat expired status or an expiration before the review date as expired or not-current, using the template's available code.
- Experience: compare `years_experience` with policy minimum.
- Endorsement: if policy requires an endorsement, `missing` and `pending` are deficiencies. Use separate missing and pending codes only when the template offers them; otherwise use the template's generic not-verified code.
- License history: an active suspension on the prior license is a deny-level issue.
- Violations and complaints: open serious violations or unresolved serious complaints are deny-level issues. Open minor violations are hold-level only when the template includes a minor-review code.
- Inspections: when the template includes inspection codes, failed or conditional `DOC_GAP` maps to a document-gap deficiency, and failed `SAFETY_RECHECK` maps to a safety-recheck deficiency. Ignore inspection findings not represented in the template.

Common contractor code translations:

| Condition | If template uses detailed codes | If template uses compact codes |
| --- | --- | --- |
| No active bond | `bond_cancelled` or nearest no-current-bond code | `no_active_bond` |
| Bond amount below policy | `bond_shortfall` | `bond_shortfall` |
| Insurance expired or past review date | `insurance_expired` | `insurance_expired` or `insurance_not_current` |
| Insurance pending | `insurance_pending` | `insurance_not_current` |
| Insurance amount below policy | `insurance_shortfall` | `insurance_shortfall` |
| Endorsement missing | `endorsement_missing` | `endorsement_not_verified` |
| Endorsement pending | `endorsement_pending` | `endorsement_not_verified` |
| Experience below policy | `experience_shortfall` | `experience_shortfall` |
| Active suspension | `active_suspension` | `active_suspension` |
| Open serious complaint or violation | `open_serious_violation` | `unresolved_serious_complaint` |

Action mapping:

- Bond currentness: `obtain_current_bond` or `file_active_bond`.
- Bond amount: `increase_bond_amount` or `increase_bond`.
- Insurance currentness: `provide_current_insurance` or `renew_insurance`, depending on template wording.
- Insurance pending: `verify_insurance_binding`.
- Insurance amount: `increase_insurance_amount` or `increase_insurance`.
- Endorsement missing: `obtain_required_endorsement`; endorsement pending: `verify_pending_endorsement`; generic endorsement: `verify_endorsement`.
- Experience: `submit_experience_evidence` or `document_experience`.
- Active suspension: include the suspension-clearing action and any board-review action allowed by the template.
- Serious unresolved complaint or violation: include the resolve action and any board-review action allowed by the template.
- Minor open violation: include the minor-review action when allowed.
- Inspection gap or recheck: include the matching clear/recheck action when allowed.

Determination and risk:

- `DENY` if there is an active suspension or unresolved serious complaint or violation.
- `HOLD` if there is any non-deny deficiency.
- `APPROVE` only when no deficiency or required action remains.
- Risk is `high` for deny-level issues, `medium` for holds, and `low` for approvals unless the template or policy provides a stronger risk rule.

Policy impact:

- Set `policy_impacted` only when a current 2025 contractor policy standard creates a material deficiency or review flag that would not have applied under the prior baseline.
- Use the legacy contractor policy for comparison: prior baseline reduces minimum bond by 10000 and did not require specialty endorsements. Do not mark policy impact for suspensions, old complaints, expired coverage, or stale correspondence unless the current policy itself changes the outcome.

Contractor summary fields:

- Count determinations from the row-level decisions.
- `high_risk_application_ids` is every application with `risk_tier: high`, sorted by ID.
- `policy_impacted_application_ids` is every row with `policy_impacted: true`, sorted by ID.
- `stale_or_unverified_correspondence_ids` includes correspondence with a stale attachment note or `verified_by_agency` false. Sort IDs lexically.

## Restricted Liquor Decisions

Separate ordinary obligations from location-specific controls:

- `standard_obligation_codes` come from `privileges` rows for the application's license class where `standard_required` is true.
- `location_specific_control_codes` come only from active settlement controls for the target location. Do not copy ordinary obligations into this field unless they are active settlement controls too.
- `same_premises_basis_applies` is true when the location has same-premises settlement or history relevant to the current application, even if the current active control set comes from a different active basis.

Risk and coverage:

- Start from active settlement basis codes and active controls.
- Add incident risk codes only when they are relevant to the restricted review and are covered by current standard obligations or current location controls.
- Dismissed incidents are distractors unless another record keeps the risk alive.
- Open or referred incidents usually create verification gaps or escalation triggers rather than covered risks.
- If the schema has location-specific risk names, translate controls into those names. For example, a current patio or noise control can cover `PATIO_BOUNDARY` and `NOISE` when those codes are available.

Verification gaps:

- Site evidence with `status: missing` creates a missing-evidence gap for that evidence type.
- Site evidence with `status: conflicting` creates a conflicting-evidence gap for that evidence type.
- A required or emphasized control without current verified evidence creates a missing-evidence gap when the template has one.
- Open tax holds create tax-clearance or unresolved-tax gaps.
- Referred minor sale or open major incidents create open-incident follow-up gaps when the template has such a code.
- Conflicting police memo, floor plan, control signage, neighbor notice, and site photo evidence map directly to the closest allowed verification-gap code.

Recommended posture:

- Use `issue_restricted` only when current controls cover the relevant risks and no material verification gaps remain.
- Use `request_follow_up` when restrictions appear viable but evidence gaps, open incident follow-up, tax clearance, or conflicting records remain.
- Use `deny` only when the prompt, policy, or unresolved severe record makes restricted issuance untenable.

First-90-day plan:

- Include checks that correspond to uncovered gaps, active controls, and priority risks.
- Typical mappings are: control signage gap to signage recheck; police memo gap to police memo follow-up; CCTV or camera gap to camera or CCTV walkthrough/export test; food-service gap to food-service check; ID or minor-sale risk to ID observation; after-hours or late-night risk to after-hours or closing visit; noise or patio control to noise or patio boundary check; tax hold to tax clearance review.
- Use only check codes allowed by the template.
- Follow the template order. If it says sort by `check_code`, sort alphabetically. If it says operational sequence, put first-30-day evidence checks first, later night checks next, and later noise/patio monitoring last.

Escalation triggers:

- Map after-hours risk to the allowed after-hours trigger.
- Map missing camera/CCTV evidence to missing-camera or control-failure triggers; include footage-not-produced when a camera export test is part of the plan.
- Map food-service evidence gaps to the food-service trigger.
- Map noise or patio controls to noise/patio breach triggers.
- Map open tax holds to the tax-hold trigger.
- Map referred minor-sale or ID-check risk to the minor-sale or ID-failure trigger.
- Map open major/violent incidents to the major-incident or violent-incident trigger when the record is not dismissed and the template allows it.

## Alcohol Renewal Queue

Build the queue from target licensees and pre-boundary matched violations.

1. Select target license numbers from the prompt.
2. Select the applicable renewal rule by the prompt's release boundary date.
3. For each target, collect matched violations with `violation_date` on or before the boundary.
4. Record all target-related violations after the boundary in `post_boundary_violation_ids_excluded`; do not let them affect rank, count, most-recent date, risk, or next step.
5. Include predecessor or successor violations only when the licensee relationship or same-address evidence supports the match. Mark those rows `close_address`; use `uncertain` for weaker non-exact matches.
6. Sort each `matched_violation_ids` list by violation date ascending, then violation ID ascending, unless the template overrides that rule.

Queue fields:

- `violation_count` is the number of pre-boundary matched violations used for ranking.
- `most_recent_violation_date` is the latest date among those matched violations.
- `match_confidence` is `exact` for direct license matches, `close_address` for successor or same-address predecessor matches, and `uncertain` only when the match is plausible but weak.
- `next_step_label` priority is usually `board_review`, then `manual_fine_check`, then `manual_ALERT_check`, then `additional_record_check`.
- Use `board_review` for serious unresolved patterns, severe sale-to-minor or public-safety patterns, or close-address successor records that need board-level confirmation.
- Use `manual_fine_check` for non-board cases with meaningful unpaid fine balances or fine-hold themes.
- Use `manual_ALERT_check` for alert-flag-driven cases without stronger board or fine priority.
- Use `additional_record_check` for weak matches or low-evidence rows when no stronger label applies.
- Risk is `high` for board-review rows and other repeated serious/fine-hold patterns, `medium` for alert-only rows, and `low` only when the task still requires a row but the matched risk is minimal.

Ranking:

- Rank only rows included in the requested queue.
- Sort first by next-step priority: board review before fine check before alert check before additional record check.
- Within the same priority, sort by most recent matched violation date descending.
- Break remaining ties by higher violation count, higher risk tier, then license number ascending.
- Assign ranks 1 through the requested queue size after sorting.

Renewal summary:

- `queue_size` equals the number of queue rows returned.
- `boundary_date` is the prompt's release boundary date.
- `post_boundary_violation_ids_excluded` is sorted by violation ID.
- `close_or_uncertain_match_license_numbers` includes every queue license whose confidence is not `exact`, sorted ascending.
- `board_review_license_numbers` includes every queue license with `next_step_label: board_review`, sorted ascending.

## Final Check

Before answering:

1. Compare the draft object against `answer_template.json` key by key.
2. Remove any field not requested by the template.
3. Sort every list according to its own rule, not by habit.
4. Recompute counts and summary IDs from the final rows.
5. Ensure the answer contains no copied training examples, no citations, and no explanatory wrapper.
