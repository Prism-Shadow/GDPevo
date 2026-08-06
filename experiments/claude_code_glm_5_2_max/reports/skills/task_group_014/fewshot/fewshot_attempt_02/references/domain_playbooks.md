# Domain playbooks

Each playbook covers one Northstar payer-ops work type. They describe which
records to pull and how to reason; they do **not** hard-code case-specific
values. Read every concrete identifier, enum, threshold, and date from the
task's own `task_context.json`, `answer_template.json`, and the environment.

## A. UM nurse authorization determination

Requester: UM nurse reviewer. Typical service domains: physical therapy, speech
therapy, occupational therapy, cardiac imaging, and similar clinical services.

**Pull:** the case, member + plan, the requested therapy / procedure line(s)
(CPT, units, modifier), the applicable policy + its criterion IDs, the clinical
documents, and any existing authorization record.

**Decide:**

- Apply each applicable policy criterion and mark it `met` / `not_met` /
  `unclear` / `not_applicable`, using the criterion IDs the template requires.
- `recommendation`: `approve` when all applicable criteria are met;
  `pend_for_information` when criteria are unclear because evidence is missing;
  `escalate_to_md` when criteria are not_met but clinical nuance warrants
  physician review; `deny` when criteria are not_met and no exception applies;
  `partial_approval` when only a subset of requested units/CPTs is supportable.
- `final_status`, `route`, `determination_letter`, and `next_action` follow from
  the recommendation (e.g. approve → `approved` / `nurse_approval` /
  `approval` / `issue_approval`).
- The `authorization` block (`auth_number`, `approved_units`, `approved_start`,
  `approved_end`, `approved_cpt` in ascending CPT order, `modifier`) is
  populated when an approval or partial approval is issued; follow the template's
  guidance for the no-authorization case.
- `evidence_documents`: document IDs relied on, ascending. `excluded_documents`:
  document IDs not relied on (e.g. a stale export superseded by a current
  clinical record), ascending.

**source_precedence:** `current_clinical_records_over_stale_export` when a
current clinical record supersedes a stale export.

## B. Pharmacy coverage appeal + manufacturer-assistance intake

Requester: pharmacy appeals coordinator.

**Pull:** the case, the appeal record (deadline, expedited flag, path
eligibility), the drug, prior-medication trial / fill records, the policy /
criteria, the denial record, the prescriber rationale, and the
manufacturer-assistance program facts.

**Decide:**

- Classify prior medication failures as `documented_failures` vs
  `undocumented_or_insufficient_failures` (alphabetical by medication name
  within each list).
- `criteria_results`: fill the template's required drug-appeal criterion keys
  (e.g. `DRUG-AUTH`, `DRUG-DENIAL`, `DRUG-RATIONALE`, `DRUG-FAILURES`) as
  `met` / `partial` / `not_met` / `unclear` / `not_applicable`.
- `appeal_path`: `standard_internal` / `expedited_internal` /
  `external_review` / `not_eligible`, from the appeal record and expedited flag.
- `appeal_deadline`: from the appeal record (ISO date).
- `owner`: the team that owns the next step (typically `appeals-rx`).
- `required_packet_items` vs `missing_packet_items`: build the packet the policy
  requires; list what is absent. Order per the template (payer-appeal items
  before assistance items; appeal-evidence gaps before assistance-information
  gaps).
- `assistance`: `program_name`, `status` (`eligible_ready` /
  `eligible_missing_information` / `not_eligible` / `not_applicable`), and
  `missing_fields` (alphabetical).
- `next_action`: driven by the gaps — `request_more_information` when
  packet/assistance gaps block filing; `file_appeal` when complete;
  `complete_expedited_appeal_and_request_income_proof` when expedited and only
  income proof is missing; `submit_assistance_application` /
  `issue_denial` / `close_not_eligible` as the situation requires.

**source_precedence:** `payer_appeal_before_manufacturer_assistance`.

## C. Payment-integrity claim repricing

Requester: payment integrity analyst.

**Pull:** the claim, its claim lines (CPT, modifier, units, paid amount), the
associated case / auth, the policy / criteria context, and the rate schedules.

**Decide:**

- Choose the effective rate schedule (`benchmark_source` + `benchmark_version`)
  by plan modifier and service date. Reject stale / non-applicable schedules
  (`stale_source_rejected`).
- For each line, look up the rate for its CPT + modifier, multiply by units →
  `correct_allowed_amount`. Line `disposition`: `correct_upward` if corrected >
  paid, `correct_downward` if corrected < paid, `no_change` if equal, `deny_line`
  if the line should not be paid.
- `paid_total`, `correct_allowed_total`, `recovery_amount` (sum across lines;
  recovery is the underpayment when corrected > paid; round to cents).
- `resubmission_route` (e.g. `payment_integrity_correction`) and `priority` from
  the queue / flag.
- Lines in claim-line order; `modifier` `null` when absent.

**source_precedence:** `effective_benchmark_by_plan_modifier_and_date`.

## D. Peer-to-peer (P2P) final summary

Requester: peer-to-peer coordinator.

**Pull:** the case, the request line (requested CPT), the policy / criteria, the
clinical evidence, the P2P event record, and the authorization status.

**Decide:**

- `p2p_outcome`: `overturn_to_approval` / `uphold_intended_adverse_decision` /
  `not_applicable`.
- `final_status` + `letter_type` from the outcome.
- `criteria_results` for the template's required criterion IDs, and
  `unresolved_criteria` (ascending criterion ID; empty list if none remain
  unresolved).
- `new_information_changed_review`: `true` only if the P2P supplied new
  patient-specific information that materially changed the review.
- The missing-factor list (e.g. modality-specific factors such as PET-over-SPECT
  factors) in the order the template specifies, including each unsupported
  factor.
- `recommended_alternative` modality when the requested modality is denied.
- `internal_appeal_deadline`: when the final result is adverse, compute the
  plan's internal-appeal window from the final adverse determination date — read
  the window length from the `task_context` / local memo. `null` when no internal
  appeal deadline applies.

**source_precedence:** `new_patient_specific_p2p_information`.

## E. UM-finance therapy margin queue

Requester: UM-finance operations analyst.

**Pull:** the margin / service-margin rows for **exactly** the `queue_row_ids`
listed in `task_context` (no others), plus the finance definitions (total-cost
definition, revenue-to-cost threshold).

**Decide:**

- For each row: `total_cost` per the definition (e.g. `variable_cost` +
  `fixed_cost_allocated`), `margin` = revenue − total_cost,
  `revenue_to_cost_ratio` = revenue / total_cost (precision per template,
  typically 4).
- `below_threshold`: ratio < threshold. `charge_sensitive`: per the row's flag.
- `recommended_action`: `payer_contract_review` for below-threshold rows;
  `monitor_charge_sensitive` for charge-sensitive non-below-threshold rows;
  `monitor_no_action` otherwise.
- `rows` in the same order as `task_context` `queue_row_ids`.
- `below_threshold_segments` and `charge_sensitive_segments`: alphabetical by
  enum value.
- `top_issue`: the below-threshold payer-service issue with the largest gap,
  formatted per the template's enum. `gap_to_120pct`: (threshold × total_cost) −
  actual revenue for that top issue, rounded to cents.
- Use only the listed queue row IDs (`review_scope`).

**source_precedence:** `margin_threshold_then_charge_sensitivity`.
