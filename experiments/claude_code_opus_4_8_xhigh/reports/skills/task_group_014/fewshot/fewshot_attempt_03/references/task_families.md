# Task-family derivation recipes

Each recipe maps environment records to the answer_template fields for one work
type. Field names below are illustrative of the recurring template; always defer to
the actual `answer_template.json` for the exact required keys, enum choices,
ordering, and precision. Never copy values from a sample answer — derive every
value from the environment for the current target.

---

## A. UM prior-authorization nurse determination

Trigger: `request_type = prior_authorization`; criteria keyed like `PT-*`; template
has `recommendation`, `authorization`, `evidence_documents`, `excluded_documents`.

Pull: `cases`, `request_lines`, `case_criteria` (for this case_id),
`policy_criteria` (for the case's `policy_id`), `documents`, `authorizations`.

Derive:

- `criteria_results` — map each required criterion key → its `case_criteria.result`.
- Decision from the criteria set, cross-checked with `policy_criteria.result_if_missing`:
  - all met → `recommendation=approve`, `final_status=approved`,
    `route=nurse_approval`, `determination_letter=approval`,
    `next_action=issue_approval`.
  - a criterion is `unclear`/missing whose `result_if_missing=pend` → pend path
    (`pend_for_information` / `pended` / `pending_information` /
    `information_request` / `request_more_information`).
  - a criterion is `not_met` whose `result_if_missing=deny` → deny path
    (`deny` / `denied` / … / `issue_denial`).
  - needs physician judgement → MD-review/escalate path.
- `authorization` — from the `authorizations` row: `auth_number`, `approved_units`,
  `approved_start`, `approved_end`, `modifier` = `approved_modifier`,
  `approved_cpt` = `approved_cpt` split on commas and **sorted ascending**.
- `evidence_documents` — `documents` with `is_current = 1`, sorted ascending by
  `document_id`.
- `excluded_documents` — `documents` with `is_current = 0` (stale export), sorted
  ascending by `document_id`.

basis_audit: `source_precedence = current_clinical_records_over_stale_export`;
`controlling_record_ids` = the current evidence document IDs (operational evidence
order = the `evidence_documents` order); `exception_record_ids` = the stale/excluded
document IDs; `precedence_record_order` = current docs first, then stale docs.

---

## B. Pharmacy coverage appeal + manufacturer-assistance intake

Trigger: template has `appeal_path`, `documented_failures`, `assistance`; criteria
keyed like `DRUG-*`.

Pull: `appeals` (by appeal_id), `case_criteria`, `drug_trials`,
`assistance_screen` (all by case_id).

Derive:

- `appeal_path` — from `appeals.appeal_path`. `expedited` — true only when a valid
  expedited-risk attestation is on file (`expedited_attestation` indicates one);
  `not_requested` → false. `appeal_deadline` — `appeals.appeal_deadline`.
  `owner` — `appeals.owner`.
- `documented_failures` — `drug_trials.medication` where `documented = 1`,
  lowercased, alphabetical.
- `undocumented_or_insufficient_failures` — where `documented = 0`, lowercased,
  alphabetical.
- `criteria_results` — the `DRUG-*` keys from `case_criteria` (a partially
  documented failure set typically makes the failures criterion `partial`).
- `required_packet_items` — the payer-appeal evidence items needed for the path,
  **then** assistance items (operational order: payer-appeal items before
  assistance items).
- `missing_packet_items` — gaps in case-specific order: appeal-evidence gaps first
  (e.g. an undocumented trial → its fill-record item), then assistance-info gaps
  (from `assistance_screen.missing_fields`).
- `assistance` — `program_name` from `assistance_screen`; `status` mapped from
  `assistance_status` (missing income/info → `eligible_missing_information`; ready →
  `eligible_ready`; ineligible → `not_eligible`; no program → `not_applicable`);
  `missing_fields` from `assistance_screen.missing_fields` split, alphabetical.
- `next_action` — from the disposition (outstanding info → `request_more_information`;
  packet complete → `file_appeal`; etc.).

basis_audit: `source_precedence = payer_appeal_before_manufacturer_assistance`;
`controlling_record_ids` = appeal_id then the documented trial IDs;
`exception_record_ids` = undocumented trial IDs then assistance gap tokens (e.g. the
missing-field name); `precedence_record_order` = appeal → documented trials →
undocumented trials → assistance gaps.

---

## C. Payment-integrity claim repricing

Trigger: template has `benchmark_source`, `paid_total`, `lines[]`,
`recovery_amount`, `stale_source_rejected`.

Pull: `claims` (target claim), `claim_lines` (order by `line_number`), the case's
member `plan_type` (`cases`→`members`), `payment_benchmarks`.

Derive:

- Effective benchmark per line: match `payer`, `plan_type`, `service_domain`,
  `cpt_code`, `modifier`, with `effective_start ≤ reporting_date ≤ effective_end`.
  That row's `source_name`/`source_version` → `benchmark_source`/`benchmark_version`.
  A same-key row outside the window (expired) is `stale_source_rejected`; if none,
  `none`. Ignore benchmark rows whose ID stem belongs to another task.
- Per line: `correct_allowed_amount` = benchmark `allowed_amount` × `units`
  (round 2). `recovery_amount` = `correct_allowed_amount` − `paid_amount`.
  `disposition` = `correct_upward` if allowed > paid, `correct_downward` if <,
  `no_change` if equal, `deny_line` if not payable. `modifier` = the line modifier
  or `null`.
- Totals: `paid_total` from the claim (or sum of line paid); `correct_allowed_total`
  = sum of line allowed; `recovery_amount` (top level) = allowed_total − paid_total.
- `lines` in claim-line order. `resubmission_route` (e.g.
  `payment_integrity_correction`) and `priority` (e.g. `standard`) per the memo/
  materiality.

basis_audit: `source_precedence = effective_benchmark_by_plan_modifier_and_date`;
`controlling_record_ids` = the claim-line IDs then the current benchmark IDs used;
`exception_record_ids` = the stale/expired benchmark ID(s); `precedence_record_order`
= the current benchmark IDs (highest priority — they set price) then the stale one.

---

## D. Peer-to-peer (P2P) final summary

Trigger: template has `p2p_outcome`, `missing_pet_factors`,
`internal_appeal_deadline`; criteria keyed like `PET-*`.

Pull: `cases`, `request_lines` (requested CPT), `case_criteria`, `documents`,
`p2p_events` (by case_id), `authorizations`.

Derive:

- `p2p_id`, `p2p_outcome`, `final_status` — from the `p2p_events` row
  (`overturn_to_approval` vs `uphold_intended_adverse_decision`; final_status e.g.
  `denied`/`approved`). `requested_cpt` — from the authorization/request line.
- `criteria_results` — the `PET-*` keys from `case_criteria`.
  `unresolved_criteria` — criterion IDs still not met, ascending; empty list if none.
- `new_information_changed_review` — true only if the P2P supplied new
  patient-specific info that materially changed the outcome (read
  `p2p_events.new_information`; an "uphold" with no new facts → false).
- `missing_pet_factors` — the PET-over-SPECT factors still unsupported, in the
  template's `choices` order.
- `letter_type` — `denial` when final is adverse, `approval` when overturned,
  `no_letter` when N/A. `recommended_alternative` — e.g. `SPECT MPI` when PET is
  denied but a lower-level study is appropriate, else `none`.
- `internal_appeal_deadline` — if final is adverse, the final adverse-determination
  date + the plan's internal-appeal window (e.g. 180 calendar days, per the prompt);
  otherwise `null`.

basis_audit: `source_precedence = new_patient_specific_p2p_information`;
`controlling_record_ids` = supporting clinical document ID(s) and the p2p_id;
`exception_record_ids` = the unmet criterion ID and any unsupported factor tokens;
`precedence_record_order` = p2p event → clinical doc → unmet criterion.

---

## E. UM-finance margin queue

Trigger: template has `rows[]`, `revenue_to_cost_ratio`, `gap_to_120pct`,
`top_issue`; `task_context.finance_memo` lists `queue_row_ids` and a threshold.

Pull: `service_margin` for exactly the `queue_row_ids`, kept **in the listed order**.

Per row:

- `total_cost` = `variable_cost` + `fixed_cost_allocated` (per `total_cost_definition`).
- `margin` = `net_revenue` − `total_cost`.
- `revenue_to_cost_ratio` = `net_revenue` ÷ `total_cost` (round to the stated
  precision, e.g. 4).
- `below_threshold` = ratio < the memo threshold (e.g. 1.2).
- `charge_sensitive` = `service_margin.charge_sensitive` == 1.
- `recommended_action` — margin threshold takes precedence over charge sensitivity:
  below threshold → `payer_contract_review`; else charge-sensitive →
  `monitor_charge_sensitive`; else → `monitor_no_action`.
- Carry `month_id`, `payer_segment`, `service_domain`, `cpt_code` through.

Aggregates:

- `below_threshold_segments` — segments of below-threshold rows, alphabetical, unique.
- `charge_sensitive_segments` — segments of charge-sensitive rows, alphabetical.
- `top_issue` — identifier (e.g. `<segment>_<cpt>`) of the worst below-threshold
  row; `none` if no row is below threshold.
- `gap_to_120pct` — for that top issue, `threshold × total_cost − net_revenue`
  (dollars to reach 120% of cost), round 2.

basis_audit: `source_precedence = margin_threshold_then_charge_sensitivity`;
`controlling_record_ids` = all queue `month_id`s in listed order;
`exception_record_ids` = the below-threshold `month_id`(s); `precedence_record_order`
= the queue rows in listed order.

---

## The sixth source_precedence

`appeal_deadline_then_clinical_then_payment_integrity` appears in the shared enum but
none of the five families above. Use it for a mixed task that weighs an appeal
timeliness/deadline first, then clinical evidence, then payment-integrity — order the
controlling and exception records accordingly (deadline-driving record first).

## basis_audit — general rules (all families)

- `source_precedence`: the single rule governing the task's dominant tension.
- `controlling_record_ids`: environment record IDs that directly determine the
  result, in operational evidence order.
- `exception_record_ids`: gap/exception records explaining exclusions, denials,
  missing info, or route priority — criteria/route gaps before stale/excluded
  records. If an exception has no row (missing packet field, unmet criterion,
  unsupported factor), use its descriptive token / criterion ID.
- `precedence_record_order`: controlling + exception IDs in source-precedence order,
  highest priority first.
