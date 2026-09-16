# Basis Audit Trail

Every Northstar payer-operations determination requires a `basis_audit` object
with four keys. This reference defines how to construct them for each domain.

## Required Keys

| Key | Purpose |
|-----|---------|
| `source_precedence` | The dominant decision rule for this task domain. |
| `controlling_record_ids` | Environment record IDs that directly support the result. |
| `exception_record_ids` | Records excluded (stale, gap, or missing) plus criteria gaps. |
| `precedence_record_order` | All record IDs in source-precedence priority, highest first. |

## Source Precedence Rules

Select the rule that matches the task domain. Each rule captures the principle
by which the determination resolves conflicting or competing records.

| Rule | Domain | Meaning |
|------|--------|---------|
| `current_clinical_records_over_stale_export` | UM clinical review | Active, in-range clinical documents control over expired or stale exports. |
| `payer_appeal_before_manufacturer_assistance` | Pharmacy appeals | Payer-side appeal and trial records determine medical necessity; manufacturer assistance is secondary. |
| `effective_benchmark_by_plan_modifier_and_date` | Payment integrity | The rate schedule effective for the plan modifier and service date controls over legacy or mismatched schedules. |
| `new_patient_specific_p2p_information` | Peer-to-peer | New information from the P2P discussion controls over the original authorization file records. |
| `margin_threshold_then_charge_sensitivity` | Margin analysis | Rows failing the margin threshold take priority over rows flagged only for charge sensitivity. |

## Constructing Record Lists

### controlling_record_ids

List the environment record IDs that directly substantiate the result. These
are the records whose values were used to satisfy criteria, compute allowed
amounts, or establish routing decisions. Include:

- Case, appeal, or authorization identifiers.
- Clinical documents relied on for criteria evaluation.
- Drug trial or fill-history records supporting documented failures.
- Claim lines and benchmark rate records used for repricing.
- P2P event records that supplied the final determination.
- Margin row IDs that produced the below-threshold or charge-sensitive results.

Order by operational evidence priority: records that most directly control the
determination appear first. For claims, list claim lines before rate benchmarks.
For appeals, the appeal record itself precedes supporting clinical or trial
records.

### exception_record_ids

List records and gaps that explain why the determination is not a simple
approval or why records were excluded. Include:

- Stale or out-of-range documents rejected during collection.
- Criteria IDs that could not be met (unresolved criteria).
- Missing packet items or missing assistance fields (use the field identifier,
  not a record ID, for fields with no record in the environment).
- Unsupported PET-over-SPECT factors when PET is denied.
- Rate schedule records that were examined but rejected as stale.

Order by business gap/exception order: criteria or route gaps before stale or
excluded records when both appear. Unresolved criteria IDs precede stale
document IDs.

### precedence_record_order

The ordered union of controlling and exception records, sorted by the priority
defined by the source-precedence rule. Highest-priority records come first.

- For `current_clinical_records_over_stale_export`: current clinical records
  first, then stale records.
- For `payer_appeal_before_manufacturer_assistance`: appeal records first,
  then trial records, then assistance-relevant gaps.
- For `effective_benchmark_by_plan_modifier_and_date`: rate benchmarks first
  (in CPT order), then the stale benchmark record.
- For `new_patient_specific_p2p_information`: P2P event record first, then
  the controlling clinical document, then unresolved criteria.
- For `margin_threshold_then_charge_sensitivity`: below-threshold rows first
  (in queue row order), then charge-sensitive rows, then any remaining rows.

## Cross-Cutting Rules

- Use the exact record identifiers returned by the environment. Do not
  fabricate IDs.
- A gap identifier (like a missing field name or criterion ID) may appear as
  an exception record when no environment record exists for it.
- When a record serves both controlling and exception roles (for example, a
  trial record that documents one failure but also highlights a gap), list it
  only in controlling; the gap appears separately as an exception.
