# Review Checklist

Run through this for every task before emitting the JSON.

## Data
- [ ] Read the task's `answer_template.json` first; note allowed enums, ordering, lengths.
- [ ] Pull **all** records via `POST /api/sql` (named columns, `WHERE … IN (…)`), not REST.
- [ ] Cross-check completeness: every active target has the rows you'd expect.

## Contractor tasks
- [ ] Map each app to its `(trade, class)` policy; record bond/ins/exp/endorsement thresholds.
- [ ] Apply the review date to insurance expiration (`expiration_date < review` ⇒ expired).
- [ ] Use **only** this task's deficiency/action enum; no cross-task code borrowing.
- [ ] Inspection `fail` ⇒ deficiency **only if** the enum has an inspection code.
- [ ] `resolved`/`dismissed` violations ⇒ no deficiency.
- [ ] serious-open + `serious_open_violation_blocks` ⇒ DENY.
- [ ] `policy_impacted` only from (specialty endorsement) or (bond shortfall in reduced band).
- [ ] Collect `stale_or_unverified_correspondence_ids` (vba=0 or stale notes), sorted.

## Liquor tasks
- [ ] `same_premises_basis_applies` from an **active** SAME_PREMISES settlement.
- [ ] `location_specific_control_codes` from active settlement controls; `standard_obligation_codes` from privileges `standard_required=1`.
- [ ] `covered_risk_codes` only for risks with an active mitigating control.
- [ ] `verification_gap_codes` from most-recent evidence per type + open incidents.
- [ ] `recommended_posture`: issue_restricted only if basis active + controls current + no blocking gap.

## Renewal task
- [ ] Boundary-filter violations (`date <= release_boundary`); exclude `*-LATE` rows, list their ids.
- [ ] Match: exact (license_no), successor (`successor_to`) ⇒ uncertain, address ⇒ close_address.
- [ ] Rank by serious-unresolved → open → count → most-recent.
- [ ] `next_step_label` from rule flags: serious-unresolved⇒board_review; successor⇒additional_record_check; unpaid⇒manual_fine_check; alert⇒manual_ALERT_check.

## Output
- [ ] Every list sorted exactly as the template specifies.
- [ ] Only allowed enum values; no extra keys; no prose/markdown.
- [ ] Summary internally consistent (counts = decisions; flag lists = per-app flags; ranks 1..N).
- [ ] Return only the JSON object.
