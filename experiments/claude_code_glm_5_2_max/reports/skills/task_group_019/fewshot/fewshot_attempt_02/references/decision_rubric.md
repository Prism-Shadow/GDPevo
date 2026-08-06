# Decision Rubric — Licensing Board Review Families

This reference holds the reusable *procedure* for mapping evidence in the licensing environment's records to the codes/fields each task's `answer_template.json` defines. It contains no task-specific answer values. The allowed enum values for any given task come from that task's own `answer_template.json`; the rubric below describes how to reason from records to whichever codes that template permits.

## Environment protocol (all families)

- Read `environment_access.md` for the base URL and the allow-list; substitute the base URL placeholder exactly.
- Only call endpoints that the **prompt** lists for the task, even if more appear in the allow-list.
- Always `GET /api/policies` first — it holds the current policy baseline and prior baseline used by the `policy_impacted` test.
- For each family, fetch each listed collection once and index locally; do not re-fetch per application.
- `POST /api/sql` is optional cross-check only. Send the documented header (e.g. `X-Task-Token`) if the endpoint requires it. Use it to verify joins/counts (e.g. "violations matched to this licensee before the boundary"); never to mutate or to bypass public endpoints. If SQL is unavailable in the environment, proceed with the public-endpoint data.

## Baseline-relative `policy_impacted` test

For families carrying a `policy_impacted` boolean:

> `policy_impacted = true` when a current policy standard (from `/api/policies`) creates a deficiency or material review flag that **would not have applied under the prior baseline**.

So a deficiency that exists under both baselines is *not* policy-impacted; a deficiency that only arises because the current standard is stricter (e.g. a new bond/insurance threshold, a newly-required endorsement, a new experience floor) *is* policy-impacted. Base the flag on the content of `/api/policies`, not on intuition about the value.

---

## Family A — Contractor batch eligibility review

Targets: a batch of `C-…` application ids. Endpoints: `/api/policies`, `/api/contractor/applications`, `/bonds`, `/insurance`, `/license-history`, `/violations`, `/correspondence`, `/inspections`, optionally `/api/sql`.

For each application, evaluate these evidence checks and, **for every check that fires**, add the matching deficiency code and required-action code **if and only if they appear in that task's `answer_template.json` allowed_values** (vocabularies change between batches — always re-read the template):

| Evidence (read from the records) | typical deficiency | typical required action |
|---|---|---|
| Active suspension in license history | active_suspension | board_review / clear_suspension |
| Bond absent or not active (no current, in-force bond) | no_active_bond / bond_cancelled | file_active_bond / obtain_current_bond |
| Bond present but amount below the policy-required threshold | bond_shortfall | increase_bond / increase_bond_amount |
| Insurance past its expiration as of the review date | insurance_expired | renew_insurance / provide_current_insurance |
| Insurance in force but amount below threshold | insurance_shortfall | increase_insurance / increase_insurance_amount |
| Insurance not current / pending as of review date | insurance_not_current / insurance_pending | provide_current_insurance / verify_insurance_binding |
| Required specialty endorsement missing | endorsement_missing | obtain_required_endorsement |
| Required endorsement pending/unverified | endorsement_pending / endorsement_not_verified | verify_pending_endorsement / verify_endorsement |
| Documented experience below the policy floor | experience_shortfall | submit_experience_evidence / document_experience |
| Open minor violation | open_minor_violation | resolve_minor_violation_review |
| Open serious violation / unresolved serious complaint | open_serious_violation / unresolved_serious_complaint | resolve_serious_violation / resolve_complaint |
| Inspection documented but doc gap vs. inspection record | inspection_doc_gap | clear_document_gap |
| Inspection requires safety recheck | inspection_safety_recheck | complete_safety_recheck |

**Determination logic:**
- `DENY` when there is an active suspension, an unresolved serious violation/complaint, or a combination of severe deficiencies that the policy treats as disqualifying.
- `HOLD` when curable deficiencies exist but none are disqualifying (most bond/insurance/endorsement/experience/minor gaps).
- `APPROVE` when no deficiencies apply at all.

**Risk tier:** `high` for DENY-worthy severity (active suspension, serious unresolved violation) or high deficiency count; otherwise `medium` for any HOLD with non-trivial gaps; `low` for APPROVE.

**Policy-impacted:** apply the baseline-relative test above to each deficiency on the application.

**Correspondence staleness (`stale_or_unverified_correspondence_ids`):** flag a correspondence id when its record is stale (old date relative to the review date) or unverified (pending/open) per the correspondence data. Sort ascending.

**Summary consistency:** `approve_count`+`hold_count`+`deny_count` = batch size; `high_risk_application_ids` = all apps tiered `high`; `policy_impacted_application_ids` = all apps with `policy_impacted=true`; both id lists sorted ascending; correspondence ids sorted ascending.

---

## Family B — Restricted liquor-license staff package

Target: a single `L-…` application at a `LOC-…` location. Endpoints: `/api/policies`, `/api/liquor/applications`, `/settlements`, `/privileges`, `/api/liquor/incidents`, `/site-evidence`, optionally `/api/sql`.

Output skeleton (field names): `recommended_posture`, `same_premises_basis_applies`, `covered_risk_codes`, `verification_gap_codes`, `standard_obligation_codes`, `location_specific_control_codes`, `first_90_day_plan`, `escalation_trigger_codes`. **Allowed codes are task-specific** — read that task's template.

- **recommended_posture** — `issue_restricted` when all material risks are covered by current controls and verification gaps are minor/closeable; `request_follow_up` when meaningful verification gaps remain but the application is fundamentally approvable with conditions (most common when site evidence or camera/food-service evidence is missing/conflicting); `deny` when a disqualifying condition exists (e.g. unresolved tax hold plus open major incident plus board-order conflict).
- **same_premises_basis_applies** — true when the transfer/restricted issuance rests on a same-premises basis and the location/premises evidence still supports it (no conflicting floor plan / location identity break). False only when the premises identity is broken.
- **covered_risk_codes** — each risk for which there is a *current, verified* control at the location (e.g. a working CCTV camera covers CAMERA_COVERAGE / PUBLIC_SAFETY; an active food-service setup covers FOOD_SERVICE / FOOD_SERVICE_GAP). Include only risks actually mitigated by current controls; do not list risks that still have open gaps.
- **verification_gap_codes** — each gap where evidence is missing, stale, or conflicting (missing/conflicting control signage, stale or conflicting floor plan, missing site photo, missing neighbor notice, conflicting police memo, open incident needing follow-up, missing/absent camera or food-service evidence, late-night monitoring not arranged, unresolved tax hold). These are the things the follow-up must close.
- **standard_obligation_codes** — obligations that are *ordinary, class-level* required obligations for this license class (drawn from policies), independent of the specific location.
- **location_specific_control_codes** — controls that are *currently active and tied to this specific location* (subset of the obligation vocabulary; only what is actually installed/active here).
- **first_90_day_plan** — an ordered set of `{check_code, timing}` monitoring checks that target the verification gaps above, sequenced `first_30_days` → `days_31_60` → `days_61_90` in operational order. Each gap worth flagging should have a corresponding check; do not duplicate check_code/timing pairs.
- **escalation_trigger_codes** — the events that would escalate the licensee to enforcement/board action, derived from the open risks and gaps (e.g. footage not produced maps to a camera-evidence gap; after-hours service maps to late-night monitoring gap). Sort/sequence per the template's ordering rule (one template requires ascending lexical; another accepts any order — follow the live template).

**Hotel-lounge / patio / late-night emphasis:** when the application is a hotel lounge or otherwise emphasizes patio boundary, camera, food-service, and late-night controls, weight those evidence checks heavily — missing camera/food-service evidence and needed late-night monitoring are typically the deciding gaps between `issue_restricted` and `request_follow_up`.

---

## Family C — Alcohol renewal manual-review queue

Target: `AL-…` license ids, a release boundary date (e.g. 2025-04-10), a target queue size (e.g. 10). Endpoints: `/api/policies`, `/api/alcohol/licensees`, `/api/alcohol/violations`, `/api/renewal/rules`, optionally `/api/sql`.

- **Match violations to licensees** by the data's id/address fields. Distinguish `exact` (id/identity match) from `close_address` (alternate/old location record on the same premises) from `uncertain`.
- **Boundary handling:** a violation dated **on or after** the release boundary is *excluded* from the queue's matching and must be listed in `post_boundary_violation_ids_excluded` (sorted by violation_id ascending). Only pre-boundary violations count toward `violation_count` and `most_recent_violation_date`.
- **Queue ordering / rank:** assign ranks 1..N (no gaps) by the ranking key the template implies — generally by severity: serious/board-level violations first, then by violation count and recency. When two entries tie on the primary key, break the tie by recency of `most_recent_violation_date` then by violation count. The exact ranking rule is dictated by the live task; keep ranks contiguous integers.
- **`matched_violation_ids` ordering:** sort by violation date ascending, then violation_id ascending (per template). (Note: the *most_recent_violation_date* is the last element's date.)
- **risk_tier:** `high` for serious/board-level matches or high counts; `medium` for moderate; `low` otherwise. Be consistent across the queue.
- **next_step_label:** `board_review` for the most serious (e.g. licensees with serious/ALERT-board-level violations or close/uncertain matches needing board attention); `manual_ALERT_check` for the ALERT-flag tier; `manual_fine_check` where the open items are fineable violations; `additional_record_check` when the match confidence is uncertain and another record pull is needed first.
- **Summary:** `queue_size` = N; `boundary_date` = the prompt's release boundary; `post_boundary_violation_ids_excluded` = every excluded late violation, sorted by id; `close_or_uncertain_match_license_numbers` = every licensee whose `match_confidence` is not `exact`, sorted ascending; `board_review_license_numbers` = every queue entry whose `next_step_label` is `board_review`, sorted ascending. Keep these derived from the queue rows.

---

## Output checklist (all families)

Before returning JSON, confirm:
1. Only keys present in the template appear; no prose, markdown, comments, or citations.
2. Every array/list is in the template's required order and meets its length/ordering constraints (fixed lengths, no-gap ranks, ascending sorts, dedup where required).
3. Every enum value is from that task's allowed_values — re-checked against the live template, not memory.
4. Booleans (`policy_impacted`, `same_premises_basis_applies`) are baseline/evidence-relative, not defaulted.
5. Summary fields are internally consistent with the per-item decisions.
6. Dates use `YYYY-MM-DD` and respect the release boundary where applicable.
