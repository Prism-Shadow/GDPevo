# Domain Playbooks

One playbook per archetype. Each gives: trigger, evidence to gather, decision logic, criteria keys, special rules, and the `source_precedence` to record. These describe the **method** — apply them to whatever target identifiers the task provides. Do not hard-code any task's final answer values.

Common shape: gather evidence → evaluate each criterion/line/row → derive the recommendation/route/letter/next-action → populate `criteria_results` (or line/row results) → build `basis_audit`.

---

## A. UM nurse prior-auth determination (physical therapy)

**Trigger.** `requester_role` = UM nurse reviewer; target is a case (`CASE-…`); `service_domain` = physical therapy; asks for a determination summary.

**Gather.** `cases` (member, provider, policy, request/due dates, status, urgency); `members` + `plans` (active member and plan context); `request_lines` (requested therapy lines: CPT, modifier, requested_units, start/end, diagnosis codes); `policies` + `policy_criteria` (the PT criteria); `case_criteria` (evaluated result + `evidence_fact_ids` + `gap_description` per criterion); `documents` + `document_facts` (note `is_current` and `source_system`); `authorizations` (any existing auth record).

**Criteria map** (`criteria_results`, values ∈ `met` / `not_met` / `unclear` / `not_applicable`):
- `PT-ACTIVE` — member/plan active and therapy currently indicated.
- `PT-DEFICIT` — documented functional deficit supporting skilled therapy.
- `PT-DX` — supporting diagnosis present.
- `PT-POC` — plan of care on file.
- `PT-UNITS` — requested units within policy limits.

**Decision logic.**
- All required criteria `met` → `recommendation=approve`, `final_status=approved`, `route=nurse_approval`, `determination_letter=approval`, `next_action=issue_approval`. Populate `authorization` from the approved line(s).
- Any required criterion `unclear` / missing evidence → `pend_for_information`, `final_status=pended`, `route=pending_information`, `letter=information_request`, `next_action=request_more_information`.
- Criteria require clinical judgment beyond nurse scope → `escalate_to_md`, `final_status=md_review_required`, `route=medical_director_review` (or `peer_to_peer`), `next_action=route_md_review` (or `schedule_p2p`).
- Required criteria `not_met` and not pendeable → `deny`, `final_status=denied`, `letter=adverse_determination`, `next_action=issue_denial` (or `file_appeal` when an appeal path exists).
- Partial — some lines/units met, others not → `partial_approval`, `final_status=partially_approved`, `letter=partial_approval`.

**`authorization` object.** `auth_number` (from the auth record or a generated determination reference), `approved_units` (integer service units), `approved_start` / `approved_end` (`YYYY-MM-DD`), `approved_cpt` (list, **ascending CPT code**), `modifier` (line modifier; `""` or the recorded modifier per template). Only populated when the recommendation approves/partially approves; otherwise use empty/`null` per the template's field types.

**Documents.** `evidence_documents` = document_ids relied on for the determination (**ascending document_id**). `excluded_documents` = document_ids excluded — typically stale exports (`documents.is_current=false`) or non-applicable records (**ascending document_id**).

**`source_precedence`:** `current_clinical_records_over_stale_export`. Current clinical records / `is_current=true` documents control; stale exports are exceptions and are excluded.

---

## B. Pharmacy coverage appeal + manufacturer assistance intake

**Trigger.** `requester_role` = pharmacy appeals coordinator; target is an appeal (`APPEAL-…` / `APL-…`); asks for an appeal + assistance disposition.

**Gather.** `appeals` (`appeal_path`, `expedited_attestation`, `appeal_deadline`, `owner`, `appeal_type_requested`); `drug_trials` (prior medication trials; `medication`, `outcome`, `documented`); `case_criteria` + `policy_criteria` (drug criteria); `assistance_screen` (`program_name`, `income_percent_fpl`, `denial_required`, `denial_on_file`, `missing_fields`, `assistance_status`); `documents` + `document_facts` for packet evidence.

**Criteria map** (`criteria_results`, values ∈ `met` / `not_met` / `partial` / `unclear` / `not_applicable`):
- `DRUG-AUTH` — drug is otherwise covered/authorized under policy.
- `DRUG-DENIAL` — a valid denial exists that the appeal addresses.
- `DRUG-RATIONALE` — prescriber rationale / clinical justification on file.
- `DRUG-FAILURES` — required formulary alternatives tried and failed.

**Prior medication classification.** From `drug_trials`, split into:
- `documented_failures` — trials with `documented=true` and a failure outcome.
- `undocumented_or_insufficient_failures` — trials that are undocumented or whose failure evidence is insufficient.
Both lists: **lowercase medication name**, **alphabetical**.

**Packet.**
- `required_packet_items` — the full set the appeal+assistance flow needs, ordered **payer appeal items before assistance items** (e.g., denial notice, member authorization, prescriber rationale, formulary failure evidence, diagnosis confirmation, expedited risk attestation, pharmacy claim history … then assistance items like household income proof, lurasidone fill record as applicable).
- `missing_packet_items` — the subset absent, ordered **appeal evidence gaps before assistance information gaps**.

**Assistance.** `assistance.{program_name, status, missing_fields}`. `program_name` is the manufacturer program for the drug (e.g., Vraylar Connect / Dupixent MyWay / Humira Complete / `not_applicable`). `status` ∈ `eligible_ready` / `eligible_missing_information` / `not_eligible` / `not_applicable`, driven by `assistance_screen.assistance_status` and whether `denial_required` is satisfied by `denial_on_file`. `missing_fields` from `assistance_screen.missing_fields`, **alphabetical by field id**.

**Appeal routing / deadline / owner.** `appeal_path` ∈ `standard_internal` / `expedited_internal` / `external_review` / `not_eligible` (from `appeals.appeal_path`, gated by eligibility). `expedited` (boolean, from `expedited_attestation`). `appeal_deadline` (`YYYY-MM-DD`, from `appeals.appeal_deadline`). `owner` ∈ `appeals-rx` / `um-nurse` / `medical-director` / `payment-integrity` / `member-services`.

**`next_action`** ∈ `request_more_information` / `file_appeal` / `complete_expedited_appeal_and_request_income_proof` / `submit_assistance_application` / `issue_denial` / `close_not_eligible`. Choose from packet gaps, assistance eligibility, and expediting — e.g., expedited appeal with missing income proof → `complete_expedited_appeal_and_request_income_proof`; assistance eligible and ready → `submit_assistance_application`.

**`source_precedence`:** `payer_appeal_before_manufacturer_assistance`. The payer appeal path/packet/deadline controls; manufacturer assistance is secondary and conditional on the denial being on file.

---

## C. Payment-integrity claim repricing (cardiac imaging)

**Trigger.** `requester_role` = payment integrity analyst; target is a claim (`CLAIM-…`); `service_domain` = cardiac imaging; asks for a correction packet (repricing against the current benchmark).

**Gather.** `claims` (`paid_total`, `auth_number`, `case_id`, `payer`); `claim_lines` (`line_number`, `cpt_code`, `modifier`, `units`, `paid_amount`, `service_date`, `denial_code`); `payment_benchmarks` / `GET /api/rate-schedules` (`source_name`, `source_version`, `modifier`, `effective_start`, `effective_end`, `allowed_amount`); `cases` + `policies` for context.

**Benchmark selection.** For each line, select the `payment_benchmarks` row matching `cpt_code` + `modifier` + `payer`/`plan_type` whose `effective_start` ≤ `service_date` ≤ `effective_end`. Prefer the current commercial imaging schedule. **Reject** the stale `Legacy Imaging Export` (and any distractor schedule) → record it in `stale_source_rejected`.

**Per-line computation.**
- `correct_allowed_amount` = benchmark `allowed_amount` × `units`, rounded to two decimals.
- `disposition` ∈ `correct_upward` / `correct_downward` / `no_change` / `deny_line`: compare `correct_allowed_amount` to `paid_amount`; deny lines that are non-covered/ineligible (e.g., `denial_code` present).
- `recovery_amount` (line) = `correct_allowed_amount − paid_amount` when positive (underpayment); when overpaid, the recovery is the overpayment per the template's correction direction. Round to two decimals.
- `modifier` = line modifier, or `null` when none (never `""`).

**Totals.** `paid_total` = `claims.paid_total`. `correct_allowed_total` = sum of line `correct_allowed_amount` (two decimals). `recovery_amount` = `correct_allowed_total − paid_total` when corrected > paid (underpayment recovery); otherwise the overpayment amount. Two decimals.

**Routing / priority.** `resubmission_route` ∈ `payment_integrity_correction` / `provider_adjustment` / `appeal_reopen` / `no_resubmission`. `priority` ∈ `standard` / `expedited` / `urgent` / `monitor_only` (e.g., a stale-schedule underpayment flagged by the provider team is typically `payment_integrity_correction` at `standard` or `expedited`).

**Ordering.** `lines` sorted by claim-line order (`line_number`). Currency to cents; `null` for absent modifier.

**`source_precedence`:** `effective_benchmark_by_plan_modifier_and_date`. The benchmark effective for the service date and matching the plan modifier controls; the stale source is the exception and is rejected.

---

## D. Peer-to-peer final summary (cardiac imaging PET MPI)

**Trigger.** `requester_role` = peer-to-peer coordinator; target is a P2P case (`P2P-…`); `service_domain` = cardiac imaging; the P2P discussion is complete; asks for a final summary.

**Gather.** `p2p_events` (`outcome`, `final_status`, `new_information`, `provider_argument`, `reviewer`); `cases`; `request_lines` (requested CPT — `requested_cpt`); `policies` + `policy_criteria` (PET MPI criteria); `case_criteria` (result + gap per criterion); `documents` + `document_facts`; `authorizations`.

**Criteria map** (`criteria_results`, values ∈ `met` / `not_met` / `unclear` / `not_applicable`):
- `PET-IND` — PET MPI indication criteria met (e.g., prior equivocal/inconclusive SPECT, BMI limitation, attenuation artifact).
- `PET-FACTOR` — at least one PET-over-SPECT factor supported.

**P2P outcome.** `p2p_outcome` ∈ `not_applicable` / `overturn_to_approval` / `uphold_intended_adverse_decision`. If `p2p_events.new_information` supplied **new patient-specific information** that materially resolves a gap (e.g., documents a missing PET factor) → `overturn_to_approval` and `new_information_changed_review=true`; otherwise uphold → `new_information_changed_review=false`.

**`final_status`** ∈ `approved` / `pended` / `md_review_required` / `denied` / `partially_approved` / `appeal_overturned` / `appeal_upheld`, consistent with the P2P outcome.

**`unresolved_criteria`** — criterion IDs still `unclear`/`not_met` after the P2P, **ascending criterion ID**. Empty list `[]` only when no applicable criteria remain unresolved.

**`missing_pet_factors`** — the PET-over-SPECT factors still unsupported, in the fixed choices order: `prior_equivocal_spect`, `bmi_limitation`, `attenuation_artifact`. Include each that remains unsupported; omit those now supported by new P2P information.

**`letter_type`** ∈ `approval` / `denial` / `partial_denial` / `no_letter`. **`recommended_alternative`** ∈ `SPECT MPI` / `PET MPI` / `none` (e.g., when PET is denied but SPECT is appropriate, recommend `SPECT MPI`).

**`internal_appeal_deadline`** — when the final determination is **adverse**, compute `final adverse determination date + 180 days` (`YYYY-MM-DD`), using the plan's 180-day internal appeal window stated in the task memo. Use `null` when the result is not adverse (no deadline applies).

**`source_precedence`:** `new_patient_specific_p2p_information`. New patient-specific information from the P2P controls the overturn/uphold decision; pre-P2P gaps that remain unresolved are exceptions.

---

## E. UM-finance therapy margin queue

**Trigger.** `requester_role` = UM-finance operations analyst; target is a queue (`QUEUE-…`); `reporting_period` = `YYYY-MM`; asks for a margin-queue summary.

**Gather.** `service_margin` rows for **only** the `month_id` values listed in `task_context`'s memo `queue_row_ids`. Pull `payer_segment`, `service_domain`, `cpt_code`, `net_revenue`, `variable_cost`, `fixed_cost_allocated`, `charge_sensitive`, `period`.

**Per-row computation.**
- `total_cost` = `variable_cost + fixed_cost_allocated` (two decimals, USD).
- `margin` = `net_revenue − total_cost` (two decimals, USD).
- `revenue_to_cost_ratio` = `net_revenue / total_cost` (precision 4).
- `below_threshold` = `revenue_to_cost_ratio < threshold` (boolean). The threshold is the memo's `revenue_to_cost_threshold` (e.g., `1.2`).
- `charge_sensitive` = the stored flag (boolean).
- `recommended_action` ∈ `payer_contract_review` (below threshold) / `monitor_charge_sensitive` (charge-sensitive and not below threshold) / `monitor_no_action` (neither).

**`rows` ordering:** the same order as the memo's `queue_row_ids` — do not re-sort.

**Aggregates.**
- `below_threshold_segments` — distinct `payer_segment` values that are below threshold, **alphabetical by enum value**.
- `charge_sensitive_segments` — distinct `payer_segment` values flagged charge-sensitive, **alphabetical by enum value**. (Below-threshold and charge-sensitive are separate classifications; a segment can appear in both.)
- `top_issue` — the below-threshold row identified as the top issue, expressed as `segment + cpt` per the template's enum (e.g., `medicaid_97110` / `commercial_97530` / `workers_comp_97112` / `none`). Use `none` when no row is below threshold.
- `gap_to_120pct` — for the top below-threshold issue: `(threshold × total_cost) − net_revenue`, i.e., the dollars needed to reach 120% of cost (two decimals, USD). Use the memo's threshold value.

**Scope discipline.** Use **only** the listed `queue_row_ids`; explicitly separate below-threshold payer-service issues from rows merely flagged charge-sensitive.

**`source_precedence`:** `margin_threshold_then_charge_sensitivity`. The threshold (ratio vs 1.2) is evaluated first and drives `payer_contract_review`; charge-sensitivity is a secondary monitor classification.
