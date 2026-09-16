# Basis Audit Rules

Every Northstar determination includes a `basis_audit` object with four required keys.

## Required Keys

| Key | Purpose |
|---|---|
| `source_precedence` | The business rule that governs which evidence takes priority. |
| `controlling_record_ids` | Environment record IDs that directly control the result (clinical docs, benchmarks, appeals, P2P events, margin rows). |
| `exception_record_ids` | Records that explain exclusions, denials, missing information, or route gaps. |
| `precedence_record_order` | All controlling and exception records listed in source-precedence order, highest priority first. |

## Source Precedence Values

Choose exactly one from the following enum:

| Value | When to Use |
|---|---|
| `current_clinical_records_over_stale_export` | UM nurse PT determination: current clinical documents control over stale exports. |
| `payer_appeal_before_manufacturer_assistance` | Pharmacy appeal: payer appeal evidence controls over manufacturer assistance screening. |
| `effective_benchmark_by_plan_modifier_and_date` | Payment integrity: the effective rate schedule (matched by plan modifier and date) controls over stale benchmarks. |
| `new_patient_specific_p2p_information` | P2P: new patient-specific information from the P2P event controls the determination. |
| `margin_threshold_then_charge_sensitivity` | Margin queue: classify below-threshold first; charge sensitivity is secondary. |
| `appeal_deadline_then_clinical_then_payment_integrity` | Complex multi-domain appeal: appeal deadline takes highest priority, then clinical records, then payment integrity. |

## Ordering Conventions for controlling_record_ids

- Use operational evidence order: the records that directly support the result, in the order relevant to the task's business logic.
- For PT determinations: current clinical documents in ascending document_id order.
- For payment integrity: claim lines first, then benchmarks mapped to each line, in claim-line order.
- For pharmacy appeals: appeal record first, then documented failure trials.
- For P2P: P2P event first, then clinical documents.
- For margin analysis: margin rows in the order given by the task context.

## Ordering Conventions for exception_record_ids

Business gap/exception order: criteria or route gaps before stale or excluded records when both appear.
- For PT: stale documents excluded from evidence.
- For pharmacy: undocumented failure trials, then missing packet fields.
- For payment integrity: rejected stale benchmarks.
- For P2P: unresolved criterion IDs, then missing PET factor enums.
- For margin: below-threshold row IDs that also appear as exceptions.

## Precedence Record Order

List controlling records first (in their operational order), then exception records (in gap/exception order). The combined list reflects the source-precedence priority, highest first.
