# Task-family playbook

Five recurring work types share one environment and one `basis_audit` contract. Identify
the family, then apply its mapping. A sixth `source_precedence` value exists for a
combined appeal/clinical/payment scenario — handle it with the same principles.

## Family router

Discriminate from `cases.request_type` (authoritative), corroborated by the target-id
prefix and the answer-template's required keys / criterion ids.

| Family | `request_type` | id prefix | template tell | `source_precedence` |
|---|---|---|---|---|
| UM nurse determination | `prior_authorization` | `CASE-` | `recommendation`,`authorization`,`evidence_documents` | `current_clinical_records_over_stale_export` |
| Appeal + assistance intake | `coverage_exception` | `APPEAL-`/`APL-` | `appeal_path`,`assistance`,`documented_failures` | `payer_appeal_before_manufacturer_assistance` |
| Claim repricing | `claim_payment_review` | `CLAIM-` | `benchmark_source`,`lines`,`recovery_amount` | `effective_benchmark_by_plan_modifier_and_date` |
| Peer-to-peer summary | `peer_to_peer` | `P2P-` | `p2p_outcome`,`missing_pet_factors` | `new_patient_specific_p2p_information` |
| Margin / finance queue | `queue_analysis` | `QUEUE-` | `revenue_to_cost_ratio`,`charge_sensitive_segments` | `margin_threshold_then_charge_sensitivity` |
| Combined appeal ↔ payment | (mixed) | varies | appeal deadline + clinical + payment-integrity fields together | `appeal_deadline_then_clinical_then_payment_integrity` |

Always let the actual `answer_template.json` shape win — build to its keys, enums,
orderings, and precision, not to the examples here.

---

## 1 — UM nurse determination (`current_clinical_records_over_stale_export`)

Pull: `cases`, `request_lines`, `documents`, `case_criteria`, `authorizations` (and
`policy_criteria` for `result_if_missing`).

- `criteria_results` — take each required criterion id's `result` from `case_criteria`
  (coerce to the template's enum).
- **Decision** — the `authorizations` row is the controlling disposition:
  `recommended_approval`/`approved` → approve; `pended` → pend_for_information;
  `denied` → deny; MD-scope/unresolved required criteria → escalate_to_md. Corroborate
  with criteria: all required met → approve; a `pend`-if-missing criterion missing →
  pend; a `deny`-if-missing criterion not met → deny.
- `authorization{}` — copy from the `authorizations` row: `auth_number`, `approved_units`,
  `approved_start`, `approved_end`, `approved_cpt` split into a **list sorted ascending by
  CPT**, `modifier` from `approved_modifier`.
- `evidence_documents` — `documents` with `is_current=1` for the case, **ascending
  document_id**. `excluded_documents` — `documents` with `is_current=0` (stale exports),
  ascending. This split *is* the current-over-stale precedence.
- Map `recommendation`/`final_status`/`route`/`determination_letter`/`next_action`
  consistently (approve→approved→nurse_approval→approval→issue_approval; pend→pended→
  pending_information→information_request→request_more_information; etc.).

## 2 — Appeal + manufacturer assistance intake (`payer_appeal_before_manufacturer_assistance`)

Pull: `appeals` (by appeal id), `case_criteria` (DRUG-*), `drug_trials`,
`assistance_screen`, `documents`. Payer-appeal facts outrank assistance facts.

- `appeal_path` ← `appeals.appeal_path`; `appeal_deadline` ← `appeals.appeal_deadline`
  (read directly — do not recompute); `owner` ← `appeals.owner` mapped to template enum.
- `expedited` — true only if `appeal_path='expedited_internal'` or
  `expedited_attestation='provider_attested_serious_health_risk'`.
- `documented_failures` — `drug_trials` with `documented=1`; `undocumented_or_insufficient_failures`
  — `documented=0`. Values are **lowercase medication names, alphabetical**.
- `criteria_results` — DRUG-AUTH/DRUG-DENIAL/DRUG-RATIONALE/DRUG-FAILURES from
  `case_criteria` (`partial` is a valid value here).
- `required_packet_items` / `missing_packet_items` — required set comes from the appeal
  `notes` / policy; order **payer-appeal items before assistance items**; missing =
  required not yet on file, ordered **appeal-evidence gaps before assistance-info gaps**
  (e.g. a missing fill record before a missing income proof).
- `assistance{}` — `program_name` from `assistance_screen`; map `assistance_status`
  (`pending_missing_income_proof` → `eligible_missing_information`); `missing_fields` from
  the `missing_fields` column, **alphabetical**.
- `next_action` — from the combined state (e.g. missing appeal evidence →
  request_more_information; expedited appeal ready but income proof missing →
  complete_expedited_appeal_and_request_income_proof; assistance only → submit_assistance_application).

## 3 — Claim repricing (`effective_benchmark_by_plan_modifier_and_date`)

Pull: `claims` (target claim), `claim_lines`, member `plan_type` (via `members`),
`payment_benchmarks`. Reporting date = `task_context.reporting_date`.

For each claim line, select the benchmark row matching **payer + plan_type +
service_domain + cpt_code + modifier** (null modifier matches null) that is **effective on
the reporting/service date** (`effective_start ≤ date ≤ effective_end`):

- Reject rows whose window has ended (`effective_end < date`) — these are the **stale**
  schedule (e.g. `Legacy Imaging Export`). Reject *Distractor Schedule* and duplicate
  `BM-TE-*` decoys.
- `correct_allowed_amount` (per line) = benchmark `allowed_amount` × `units`, 2 dp.
- `recovery_amount` (line) = `correct_allowed_amount − paid_amount`;
  `disposition` = correct_upward (correct > paid) / correct_downward (correct < paid) /
  no_change (equal) / deny_line (not payable / no valid benchmark).
- Totals: `paid_total` = Σ paid; `correct_allowed_total` = Σ correct; `recovery_amount`
  (top) = `correct_allowed_total − paid_total` (underpayment when positive).
- `benchmark_source`/`benchmark_version` = the selected row's `source_name`/`source_version`;
  `stale_source_rejected` = the ended source that had been used (else `none`).
- `auth_number` from the claim/authorization. `lines` in **claim-line order**; `modifier`
  is `null` (not `""`) when absent. Currency = JSON numbers, dollars rounded to cents.

## 4 — Peer-to-peer summary (`new_patient_specific_p2p_information`)

Pull: `p2p_events` (target), `cases`, `case_criteria` (PET-*), `authorizations`,
`request_lines` (for `requested_cpt`).

- `p2p_outcome` ← `p2p_events.outcome` (overturn_to_approval / uphold_intended_adverse_decision;
  reschedule/incomplete → `not_applicable`). `final_status` ← `p2p_events.final_status`
  (`pending` → `pended`). **Read both columns directly — do not infer one from the other.**
- `criteria_results` — PET-IND, PET-FACTOR from `case_criteria`.
- `new_information_changed_review` — true only if the P2P `new_information` actually
  supplied patient-specific facts that changed a criterion; false when it states none were
  supplied.
- `missing_pet_factors` — from the choices list (prior_equivocal_spect, bmi_limitation,
  attenuation_artifact), include each PET-over-SPECT factor still unsupported, **in the
  choices order**.
- `unresolved_criteria` — required criterion ids not `met`, **ascending**.
- `letter_type` (approval/denial/…) and `recommended_alternative` (SPECT MPI when PET is
  denied for lack of a PET-specific factor; else none).
- `internal_appeal_deadline` — only when the final result is adverse: **adverse
  determination date + 180 calendar days** (plan's internal-appeal window). Anchor on the
  final-determination date given by the memo/P2P completion; otherwise `null`.

## 5 — Margin / finance queue (`margin_threshold_then_charge_sensitivity`)

Pull `service_margin` for exactly the `finance_memo.queue_row_ids` (preserve their order).
Threshold = `finance_memo.revenue_to_cost_threshold` (e.g. 1.2).

Per row:
- `total_cost` = `variable_cost + fixed_cost_allocated` (per `total_cost_definition`), 2 dp.
- `margin` = `net_revenue − total_cost`, 2 dp.
- `revenue_to_cost_ratio` = `net_revenue / total_cost`, 4 dp.
- `below_threshold` = ratio < threshold. `charge_sensitive` = bool(`charge_sensitive`).
- `recommended_action`: charge-sensitive → `monitor_charge_sensitive`; else below-threshold
  → `payer_contract_review`; else `monitor_no_action` (charge-sensitivity is a carve-out
  applied *after* the threshold test — hence "threshold then charge sensitivity").

Aggregates:
- `below_threshold_segments` / `charge_sensitive_segments` — segments meeting each flag,
  **alphabetical by enum value**.
- `top_issue` = the actionable below-threshold, **non**-charge-sensitive row
  (`<segment>_<cpt>`), worst ratio; `none` if there is none.
- `gap_to_120pct` = `threshold × total_cost − net_revenue` for the top-issue row, 2 dp
  (the dollars needed to reach 120 % of cost). If `top_issue='none'`, use `0`/per template.

---

## `basis_audit` (identical contract in every template)

Four keys:

- `source_precedence` — the enum for the family (router table above).
- `controlling_record_ids` — ids of the records that **directly drive the result**, in
  operational evidence order. Examples: the current documents + `case_criteria` +
  `authorizations` row (UM); the `appeals` row + documented `drug_trials` (appeal); the
  selected `payment_benchmarks` rows + `claim_lines` (repricing); the `p2p_events` row +
  controlling `case_criteria` (P2P); the below-threshold `service_margin` rows (margin).
- `exception_record_ids` — the gap/exception records that explain exclusions, denials,
  missing information, or route priority: **criteria/route-gap records first, then
  stale/excluded/decoy records** (e.g. a not_met criterion before a stale document; a
  missing-packet gap before an excluded export; the rejected stale benchmark).
- `precedence_record_order` — the controlling + exception ids listed in
  source-precedence order, **highest priority first** (current before stale; payer-appeal
  before assistance; effective before stale benchmark; new-P2P-info first; below-threshold
  before charge-sensitive; appeal-deadline → clinical → payment-integrity).

Use the exact environment record ids (e.g. `DOC-…`, `AUTH-…`, `BM-…`, `SM-…`,
`TRIAL-…`, criterion ids), not prose.
