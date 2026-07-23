# Determination Playbooks

Per-task-type logic. Each playbook lists the records to gather, the determination
rules, and how to fill the task's fields. Rules are generic — read the actual
values (limits, thresholds, deadlines, enum choices) from the environment and
the `task_context`/`answer_template` for the specific instance.

---

## 1. UM prior-authorization (physical/occupational/speech therapy)

**Records:** cases, members+plans, request_lines, policies, policy_criteria,
case_criteria, documents, document_facts, authorizations.

**Determination:**
- Mirror `case_criteria.result` into `criteria_results` (keyed by criterion id).
- The authorization record usually carries the recommended status, approved
  units/dates/CPT/modifier. If all approval-required criteria are `met` **and**
  requested units are within the policy unit limit (read the limit from
  `policy_criteria` text, e.g. the PT-UNITS "do not exceed N units" rule), the
  determination is an approval:
  - `recommendation = approve`, `final_status = approved`,
    `route = nurse_approval`, `determination_letter = approval`,
    `next_action = issue_approval`.
- If a `result_if_missing = deny` criterion is `not_met` → deny/escalate per the
  template enums; if a `pend` criterion is unresolved → pend/route to MD or
  request info.

**Fields:**
- `authorization`: copy `auth_number`, `approved_units` (integer total),
  `approved_start`/`approved_end` (`YYYY-MM-DD`), `approved_cpt` as a list of
  CPT strings sorted **ascending by CPT code** (split the comma-separated
  stored value), `modifier` (the line modifier from the request line).
- `evidence_documents`: `document_id`s of the current (`is_current=1`)
  documents whose facts `supports_criteria` — sorted ascending by document_id.
- `excluded_documents`: `document_id`s of stale/non-current documents
  (`is_current=0`) — sorted ascending.

**Source precedence:** `current_clinical_records_over_stale_export`.

---

## 2. Pharmacy coverage-exception appeal + manufacturer assistance

**Records:** appeals, assistance_screen, drug_trials, case_criteria,
policy_criteria, policies, documents, document_facts, members.

**Determination:**
- `appeal_id`, `drug` (the requested specialty drug enum), `appeal_path`,
  `expedited` (boolean from `expedited_attestation` — true only if expedited was
  requested), `appeal_deadline` (`YYYY-MM-DD`), `owner` — all from the appeal
  record.
- `documented_failures`: lowercase medication names from drug_trials where
  `documented = 1`, alphabetical.
- `undocumented_or_insufficient_failures`: lowercase medication names where
  `documented = 0` (notes like "mentioned but pharmacy fill missing"),
  alphabetical.
- `criteria_results`: mirror `case_criteria.result` (DRUG-AUTH, DRUG-DENIAL,
  DRUG-RATIONALE, DRUG-FAILURES). A partial failure evidence set gives
  `DRUG-FAILURES = partial`.
- `required_packet_items`: the standard packet for this appeal type, ordered
  **payer-appeal items before assistance items** (the appeal record's `notes`
  usually lists them in operational order).
- `missing_packet_items`: case-specific gaps, ordered **appeal-evidence gaps
  before assistance-information gaps**. A drug trial with `documented = 0` and a
  "fill missing" note means that medication's fill record is a missing
  appeal-evidence item; the assistance screen's `missing_fields` are the
  assistance-information gaps.
- `assistance`: `program_name` and `assistance_status` from assistance_screen,
  mapped to the template's status enum (e.g. denial on file but a missing
  assistance field → `eligible_missing_information`); `missing_fields` split
  from the comma-separated stored value, alphabetical.
- `next_action`: if the appeal packet is incomplete (a criterion is `partial`
  or a packet item is missing) → `request_more_information`. Payer appeal is
  pursued before the manufacturer-assistance application.

**Source precedence:** `payer_appeal_before_manufacturer_assistance`.

---

## 3. Payment-integrity claim repricing

**Records:** claims, claim_lines, cases, members+plans, policies,
payment_benchmarks, documents (remittance/EOB), case_criteria.

**Determination:**
- `auth_number` from the claim record.
- For each claim line, find the **current** benchmark: match payer + plan_type +
  service_domain + cpt_code + modifier, then pick the row whose
  `[effective_start, effective_end]` covers the line's `service_date`. Reject
  any source whose effective window ends before the service date (e.g. a "Legacy
  … Export"). The current schedule's `source_name` and `source_version` become
  `benchmark_source` / `benchmark_version`; the rejected source becomes
  `stale_source_rejected`.
- `correct_allowed_amount` per line = `allowed_amount * units` (apply units,
  then round to 2 decimals).
- `recovery_amount` per line = `correct_allowed_amount - paid_amount` (positive
  when underpaid).
- `disposition`: `correct_upward` if correct > paid (underpayment),
  `correct_downward` if correct < paid (overpayment), `no_change` if equal,
  `deny_line` if the line should not be paid.
- Totals: `paid_total` from the claim (equals sum of line paid amounts);
  `correct_allowed_total` = sum of line correct_allowed_amounts;
  `recovery_amount` = `correct_allowed_total - paid_total` (use the
  underpayment amount when corrected > paid).
- `lines` in `line_number` order; `modifier` = `null` when absent.
- `resubmission_route` / `priority`: pick from the template enums based on the
  correction needed (a stale-schedule repricing → `payment_integrity_correction`;
  priority follows the case urgency / no special signal → `standard`).

**Source precedence:** `effective_benchmark_by_plan_modifier_and_date`.

---

## 4. Peer-to-peer final summary

**Records:** p2p_events, cases, request_lines, policies, policy_criteria,
case_criteria, documents, document_facts, authorizations, members+plans.

**Determination:**
- `p2p_id`, `requested_cpt` (from the request line), `p2p_outcome` and
  `final_status` from the p2p event (and authorization status).
- `criteria_results`: mirror `case_criteria.result` for the applicable
  criterion ids (e.g. PET-IND, PET-FACTOR).
- `unresolved_criteria`: criterion ids that remain not_met/unclear, ascending.
- `new_information_changed_review`: true only if the p2p `new_information`
  field supplies patient-specific information that materially changes the
  review. If the field states no supporting factor was supplied → false (the
  decision is upheld).
- `missing_pet_factors` (PET-over-SPECT tasks): list each factor that remains
  unsupported, in the order shown in the template's choices (typically
  `prior_equivocal_spect`, `bmi_limitation`, `attenuation_artifact`).
- `letter_type`: `approval` / `denial` / `partial_denial` / `no_letter` based
  on the final status.
- `recommended_alternative`: when the requested advanced modality is denied for
  lack of a superiority factor, the standard modality is the alternative (e.g.
  PET denied → `SPECT MPI`).
- `internal_appeal_deadline`: if the final determination is **adverse**, compute
  it as `final_adverse_determination_date + appeal_window_days`, where the
  window length and the determination date both come from `task_context` / plan
  notes. Use `null` only when no appeal deadline applies (non-adverse final
  status).

**Source precedence:** `new_patient_specific_p2p_information`.

---

## 5. Therapy margin queue

**Records:** service_margin (only the queue row IDs named in `task_context`),
plus the finance definitions in `task_context` (total-cost formula, threshold,
review scope).

**Determination (per queue row):**
- `total_cost = variable_cost + fixed_cost_allocated` (or whatever formula
  `task_context` states).
- `margin = net_revenue - total_cost`.
- `revenue_to_cost_ratio = net_revenue / total_cost`, rounded to the template's
  ratio precision (usually 4).
- `below_threshold = ratio < threshold` (threshold value comes from
  `task_context`).
- `charge_sensitive` = the row's flag (0/1 → boolean).
- `recommended_action`:
  - below_threshold and not charge_sensitive → `payer_contract_review`
    (the margin-threshold issue takes priority);
  - charge_sensitive and not below_threshold → `monitor_charge_sensitive`;
  - neither → `monitor_no_action`.
- `rows` in the **same order as `task_context`'s queue_row_ids**.
- `below_threshold_segments` / `charge_sensitive_segments`: distinct
  `payer_segment` values, **alphabetical by enum value**.
- `top_issue`: the below-threshold segment's CPT (the template enum pairs
  segment + cpt). If none below threshold → `none`.
- `gap_to_120pct`: `threshold * total_cost - net_revenue` for the top
  below-threshold issue (the dollar shortfall to the threshold), 2 decimals.

**Source precedence:** `margin_threshold_then_charge_sensitivity`.

---

## Cross-cutting reminders

- `criteria_results` is a direct mirror of `case_criteria.result` keyed by
  criterion id — do not re-derive it from documents.
- Evidence vs. exclusion hinges on `documents.is_current` and on whether a
  document fact's `supports_criteria` is null.
- All enums, orderings, and precisions are in `answer_template.json` — read
  them for the specific instance; do not assume from memory.
