# Basis Audit Trail

Every payer-operations answer must include a `basis_audit` object with four required keys:

```json
{
  "source_precedence": "...",
  "controlling_record_ids": [...],
  "exception_record_ids": [...],
  "precedence_record_order": [...]
}
```

## Source precedence rules

Choose exactly one of these six rules. Match the rule to the task domain:

| Rule | Domain | When to use |
|------|--------|------------|
| `current_clinical_records_over_stale_export` | Utilization management | Clinical documents exist alongside a stale export; the current clinical findings control the result |
| `payer_appeal_before_manufacturer_assistance` | Pharmacy appeals | An appeal record is primary; manufacturer assistance is secondary. Resolve payer-side qualification before checking assistance gaps |
| `effective_benchmark_by_plan_modifier_and_date` | Payment integrity | A current rate schedule controls over a stale one. Apply plan-appropriate, date-effective benchmark rates per CPT line |
| `new_patient_specific_p2p_information` | Peer-to-peer review | A completed P2P discussion may supply new clinical information that changes the review. Pre-P2P records still control when the P2P adds nothing material |
| `margin_threshold_then_charge_sensitivity` | Therapy margin finance | Below-threshold payer-service pairs control the top issue. Charge-sensitive rows are noted but do not override threshold priority |
| `appeal_deadline_then_clinical_then_payment_integrity` | Multi-domain appeals | Appeal deadline drives routing priority; clinical evidence drives determination; payment integrity drives financial correction |

## Construction rules

### `controlling_record_ids`

List the environment record IDs that directly determine the result. These are records whose content -- not their absence -- drives the outcome.

- For an approval: the clinical documents that satisfied each criterion
- For a denial: the policy criteria that were not met plus any clinical documents that support the negative finding
- For a claim repricing: the benchmark rows that produced the corrected amounts
- For a P2P: the P2P event record and the clinical documents that were evaluated
- For a finance queue: the queue rows themselves

Ordering: use the operational evidence order -- the records that most directly control the result first.

### `exception_record_ids`

List the records, criteria gaps, or information gaps that explain why the result is not a straightforward approval. This includes:

- Stale records that were rejected
- Criteria that were not met (use the criterion ID, not a document ID)
- Missing information or packet items
- Undocumented drug trial failures
- Gaps that caused escalation or denial

Ordering: put criteria and route gaps before stale or excluded records. When a gap is identified by a label (like `household_income_proof`) rather than a record ID, use that label.

### `precedence_record_order`

List all controlling and exception records in order from highest priority to lowest, following the chosen source precedence rule. This is the union of `controlling_record_ids` and `exception_record_ids`, sorted by business priority.

- For `current_clinical_records_over_stale_export`: current clinical records first, then stale records
- For `payer_appeal_before_manufacturer_assistance`: appeal record first, then clinical trial records, then assistance gaps
- For `effective_benchmark_by_plan_modifier_and_date`: benchmark rows first, then stale benchmark rows
- For `new_patient_specific_p2p_information`: P2P event first, then clinical records, then unresolved criteria
- For `margin_threshold_then_charge_sensitivity`: below-threshold rows first, then above-threshold rows
- For `appeal_deadline_then_clinical_then_payment_integrity`: deadline-driving item first, then clinical evidence, then financial records

## Separation rule

A record ID must never appear in both `controlling_record_ids` and `exception_record_ids`. Records either drive the result (controlling) or explain a gap/exception, not both.

## Identifier format

Use the exact record IDs as they appear in the environment. Do not transform or abbreviate them. If the environment uses IDs like `DOC-SAMPLE-EVAL`, `APL-SAMPLE`, or `BM-SAMPLE-CPT`, use those exact values.

## Common mistakes

- Using the wrong precedence rule for the task domain
- Placing a record in both controlling and exception lists
- Omitting the criterion IDs from exception records when criteria are not met
- Listing records in arbitrary order instead of following the precedence rule's priority
- Using `precedence_record_order` as a simple concatenation rather than a re-sorted priority list
