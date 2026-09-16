# Basis Audit Trail

Every Northstar determination JSON must include a `basis_audit` object:

```json
{
  "source_precedence": "<rule>",
  "precedence_record_order": ["<id>", ...],
  "controlling_record_ids": ["<id>", ...],
  "exception_record_ids": ["<id>", ...]
}
```

## Source Precedence Rules

Choose exactly one rule based on the business domain:

| Rule | Domain | Description |
|------|--------|-------------|
| `current_clinical_records_over_stale_export` | UM nurse review (PT auth) | Use current clinical records; exclude stale exports. |
| `payer_appeal_before_manufacturer_assistance` | Pharmacy appeals | Process payer appeal evidence before manufacturer assistance screening. |
| `effective_benchmark_by_plan_modifier_and_date` | Payment integrity (claim repricing) | Select the benchmark source by effective date and plan modifier; reject stale schedules. |
| `new_patient_specific_p2p_information` | Peer-to-peer | Evaluate new patient-specific information from the P2P discussion first, then existing clinical evidence. |
| `margin_threshold_then_charge_sensitivity` | Margin queue | Classify rows: below-threshold rows first, then charge-sensitive rows. |
| `appeal_deadline_then_clinical_then_payment_integrity` | Multi-domain appeals crossing clinical and payment | Apply deadline analysis first, then clinical, then payment. |

## Record Ordering Conventions

### controlling_record_ids
Records that directly determine the result. Ordered by operational evidence priority -- the most impactful record first.

### exception_record_ids
Records that explain gaps, exclusions, denials, or missing information. Order using business gap/exception order: criteria or route gaps come before stale or excluded records when both are present.

### precedence_record_order
All controlling and exception records merged in source-precedence order, highest priority first.

## Domain Mapping

| Domain | Source Precedence | Typical Controlling Records | Typical Exception Records |
|--------|-------------------|---------------------------|--------------------------|
| UM nurse PT auth | `current_clinical_records_over_stale_export` | Current clinical docs (eval, POC) | Stale documents |
| Pharmacy appeals | `payer_appeal_before_manufacturer_assistance` | Appeal record, drug trial evidence | Failed/insufficient trials, missing fields |
| Payment integrity | `effective_benchmark_by_plan_modifier_and_date` | Current benchmark records, claim lines | Stale benchmark records |
| Peer-to-peer | `new_patient_specific_p2p_information` | P2P event record, clinical evidence | Unmet criteria IDs, missing PET factors |
| Margin queue | `margin_threshold_then_charge_sensitivity` | All queue rows (below-threshold first) | Below-threshold rows themselves (as exceptions) |

## General Rules

- Record IDs are string values from the environment (document IDs, claim line IDs, benchmark IDs, queue row IDs, criterion IDs, or domain-specific field identifiers).
- Do not invent record IDs -- use exactly the identifiers returned by the environment.
- `exception_record_ids` can include criteria IDs (like `PET-FACTOR`), missing-field identifiers (like `household_income_proof`), or specific gap labels when the environment does not provide a formal document ID for the gap.
- When no exceptions exist, use an empty list.
