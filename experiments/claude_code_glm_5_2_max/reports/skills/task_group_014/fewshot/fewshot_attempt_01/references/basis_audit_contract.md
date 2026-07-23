# basis_audit Contract

Every Northstar payer-ops answer carries a `basis_audit` object that documents
*why* the result is what it is. It has four required keys. This file defines
each key, the six precedence rules, and the ordering/curation logic.

The structure and the six rule strings are part of the published template
contract (they appear identically in every `answer_template.json`). The
specific record IDs populated for any given case are derived from the
environment — never copied from another case.

## Required keys

### `source_precedence`
A single enum value naming the precedence rule that governed the result. Choose
from the six rules below based on the work type. The rule determines how
conflicting records are reconciled and how `precedence_record_order` is sorted.

### `controlling_record_ids`
The environment record IDs that **directly control** the result — the
authoritative sources the determination rests on.

- Ordering: **operational evidence order** — the order records are encountered
  in the environment's operational flow (e.g., claim lines in line order
  followed by their benchmark records; an evaluation before its plan-of-care;
  a clinical record before the P2P event that revisits it).
- This is the complete list of controlling records.

### `exception_record_ids`
Records that explain a gap, exclusion, denial, missing information, or route
priority — i.e., records that shape the outcome without being authoritative
evidence.

- Ordering: **business gap/exception order** — criteria or route gaps first,
  then stale or excluded records when both appear.
- This is the complete list of exception records.

### `precedence_record_order`
The controlling and exception records listed in **source-precedence order,
highest priority first**. This is the audit trail a reviewer reads top-down to
understand the decision.

- It is **not** a plain concatenation of `controlling_record_ids` then
  `exception_record_ids`. It is a **curated, de-duplicated trail of the records
  that drive the precedence decision**.
- **Curated:** include the records that the precedence rule actually operates
  on — the authoritative sources and the key exception/gap that decides the
  outcome. Omit records that are mere operands or supporting evidence rather
  than precedence-driving sources (for example, the claim lines being repriced
  are operands, not precedence drivers, so they may be omitted while the
  benchmark-schedule records that set the price are kept).
- **De-duplicated:** if a record appears in both the controlling and exception
  roles, list it once, at the position its precedence dictates.
- **Reordered:** sort by the precedence rule, not by the controlling/exception
  list orders. A higher-precedence record (e.g., new P2P information) sorts
  above a lower-precedence record (e.g., the prior clinical record) even if the
  clinical record was encountered first.

`controlling_record_ids` and `exception_record_ids` stay complete; only
`precedence_record_order` is the curated, ordered trail.

## The six source-precedence rules

These are the only allowed `source_precedence` values. Each names a
reconciliation policy and the work context it governs.

1. **`current_clinical_records_over_stale_export`** — A current clinical record
   (e.g., a current evaluation or plan-of-care) controls over a stale or
   superseded exported record; the stale export is excluded. Governs clinical
   prior-authorization / UM-nurse determinations.

2. **`payer_appeal_before_manufacturer_assistance`** — The payer coverage-appeal
   process and its evidence (denial notice, formulary-failure/trial evidence,
   prescriber rationale) take precedence over manufacturer-assistance intake;
   assistance eligibility is screened, but the appeal disposition controls the
   result. Governs pharmacy coverage appeal + assistance intake dispositions.

3. **`effective_benchmark_by_plan_modifier_and_date`** — For claim repricing the
   effective rate-schedule benchmark is selected by the plan's modifier and the
   service/effective date; stale or inapplicable schedules are rejected and
   named as the excluded source. Governs payment-integrity claim repricing.

4. **`new_patient_specific_p2p_information`** — New patient-specific information
   surfaced in a completed peer-to-peer discussion can materially change the
   review; the P2P event and the new information it supplies take precedence
   over the prior record when material. Governs peer-to-peer final summaries.

5. **`margin_threshold_then_charge_sensitivity`** — In the margin queue, first
   separate segments below the revenue-to-cost threshold (action: contract
   review) from segments at/above threshold but flagged charge-sensitive
   (action: monitor); a threshold breach takes precedence over charge
   sensitivity for prioritization. Governs UM-finance margin-queue summaries.

6. **`appeal_deadline_then_clinical_then_payment_integrity`** — When routing an
   appeal or disposition, prioritize by appeal deadline first, then clinical
   merit, then payment-integrity concerns. Use for deadline-driven appeal
   routing where the deadline governs the route/owner choice.

## How to choose the rule

Match the rule to the **work type**, not to a remembered answer:

| Work type (from task_context / prompt) | source_precedence |
|---|---|
| UM-nurse prior-authorization determination (clinical/therapy auth) | `current_clinical_records_over_stale_export` |
| Pharmacy coverage appeal + manufacturer-assistance intake | `payer_appeal_before_manufacturer_assistance` |
| Payment-integrity claim repricing / benchmark correction | `effective_benchmark_by_plan_modifier_and_date` |
| Peer-to-peer final summary | `new_patient_specific_p2p_information` |
| UM-finance margin queue | `margin_threshold_then_charge_sensitivity` |
| Deadline-governed appeal routing | `appeal_deadline_then_clinical_then_payment_integrity` |

If a task blends work types, pick the rule whose reconciliation policy actually
decides the contested field, and document the choice in the trail.
