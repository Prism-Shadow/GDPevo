# basis_audit

Every answer ends with a `basis_audit` object. Its structure is **identical
across all answer templates** — only the values depend on the task. Build it
last, after the determination is computed.

## Required keys

```json
{
  "source_precedence": "<enum>",
  "precedence_record_order": ["..."],
  "controlling_record_ids": ["..."],
  "exception_record_ids": ["..."]
}
```

## Ordering rules (apply exactly as specified in the templates)

- **`controlling_record_ids`** — the environment record IDs that **directly
  control the result**, in **operational evidence order** (the order you relied
  on them). These are the records that drive the determination/repricing/queue
  result.
- **`exception_record_ids`** — the records that explain exclusions, denials,
  missing information, or route priority, in **business gap/exception order**:
  **criteria or route gaps first, then stale or excluded records** when both
  appear.
- **`precedence_record_order`** — the controlling **and** exception records
  listed together in **source-precedence order, highest priority first** (i.e.
  the controlling records in evidence order, followed by the exception records
  in gap/exception order). It is the merged, prioritized trail.

Use the **stable record IDs** the environment exposes (document_id, claim_line_id,
benchmark_id, month_id, appeal_id, trial_id, p2p_id, criterion_id, etc.). When an
exception is a missing item rather than a record (e.g. a missing packet field),
use the field/item identifier as the exception ID, in the same gap order.

## source_precedence decision table

Pick the value for the archetype (see `task_archetypes.md`). The enum is fixed
across templates; choose the one whose rule governs this task.

| source_precedence | Archetype | What controls vs. what is the exception |
|---|---|---|
| `current_clinical_records_over_stale_export` | UM prior-auth determination (A) | Current clinical records (`is_current=1`) control; stale export documents are excluded as exceptions. |
| `payer_appeal_before_manufacturer_assistance` | Pharmacy appeal & assistance intake (B) | Payer appeal pathway controls; assistance information gaps / undocumented failures are exceptions. |
| `effective_benchmark_by_plan_modifier_and_date` | Payment-integrity claim repricing (C) | Effective benchmark (plan_type/modifier/date) controls; stale/legacy benchmark source is rejected as an exception. |
| `new_patient_specific_p2p_information` | Peer-to-peer summary (D) | New patient-specific P2P information controls; unresolved criteria / remaining factor gaps are exceptions. |
| `margin_threshold_then_charge_sensitivity` | UM-finance margin queue (E) | Below-threshold (margin) rows control the top issue; charge-sensitive rows are monitored/exceptions. |
| `appeal_deadline_then_clinical_then_payment_integrity` | Combined routing/escalation (F, reserved) | Order the trail by appeal deadline, then clinical, then payment-integrity. |

If a task does not fit any archetype cleanly, choose the `source_precedence`
whose rule best matches which records control the result and which are gaps, and
follow the same ordering rules.
