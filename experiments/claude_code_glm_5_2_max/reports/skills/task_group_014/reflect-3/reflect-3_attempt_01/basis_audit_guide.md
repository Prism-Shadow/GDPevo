# basis_audit Guide

Every Northstar task's `answer_template.json` requires a `basis_audit` object with the same four
keys. It is the audit trail that explains *which records controlled the result and why*.

```
{
  "source_precedence": "<one enum value>",
  "precedence_record_order": ["<id>", "..."],   // controlling then exception, highest priority first
  "controlling_record_ids": ["<id>", "..."],    // records that directly control the result
  "exception_record_ids": ["<id>", "..."]       // records that explain gaps/exclusions/staleness (may be [])
}
```

## Step 1 — Pick `source_precedence` (exactly one)

Choose the single rule that matches the task's controlling logic. The six choices:

| source_precedence | Use when the task is… | Controlling logic |
|---|---|---|
| `current_clinical_records_over_stale_export` | A UM nurse prior-auth determination where current clinical records override a stale/non-current export | Current (`is_current=1`) clinical documents drive the criteria; stale exports are excluded. |
| `payer_appeal_before_manufacturer_assistance` | A pharmacy appeal with a manufacturer-assistance track | The payer appeal (packet, criteria, drug-trial failures) takes priority over the assistance screen. |
| `effective_benchmark_by_plan_modifier_and_date` | Payment-integrity claim repricing | The effective rate schedule is selected by plan_type + modifier + service_date; stale schedules are rejected. |
| `new_patient_specific_p2p_information` | A peer-to-peer final summary | The review turns on whether the P2P supplied new patient-specific information that materially changed the review. |
| `margin_threshold_then_charge_sensitivity` | A therapy margin-queue summary | Below-threshold payer-service issues are separated from charge-sensitive rows. |
| `appeal_deadline_then_clinical_then_payment_integrity` | A routing-priority task weighing appeal deadline vs clinical vs payment-integrity | Route by deadline first, then clinical need, then payment integrity. |

## Step 2 — Identify controlling vs exception records

**`controlling_record_ids`** = the environment record IDs that **directly drive the result**.
These are the records that embody the chosen precedence rule and the evidence that produces the
answer. List them in **operational evidence order** — the order evidence is consumed for that
task type (e.g., clinical eval before plan of care; denial notice before member auth before
prescriber rationale; claim-line order; queue-row order).

What counts as controlling, by family:
- **UM PA:** the current clinical documents that support the met criteria (e.g., the eval and
  plan-of-care document IDs). Do **not** include the case ID or the authorization ID here.
- **Pharmacy appeal:** the appeal-packet document IDs plus the **documented** drug-trial IDs.
- **Claim repricing:** the **selected** benchmark IDs (one per repriced line), in line order.
- **P2P:** the **P2P event ID** plus the supporting clinical-evidence document ID(s).
- **Margin queue:** the queue row IDs (`month_id` values), in `task_context` row order.

**`exception_record_ids`** = the records that **explain a gap, exclusion, staleness, or missing
information** — i.e., why something was excluded, denied, pended, or routed differently. Order:
**criteria/route gaps before stale/excluded records** when both appear. Examples:
- A stale / `is_current=0` document (UM PA).
- An **undocumented** drug-trial ID whose missing fill record explains a `partial` criteria
  result (pharmacy appeal).
- A **stale/rejected** benchmark ID (claim repricing).
- A `document_facts` row whose value records an absent factor, e.g. `pet_over_spect_factor =
  "not documented"` (P2P).

**An empty list `[]` is valid** when every relevant record is controlling and nothing is
excluded or gapped (e.g., a margin queue where all listed rows are analyzed and none is
excluded). Do not pad it.

### Controlling vs exception — the test
- If a record **supports** the determination (it is *relied on*), it is **controlling**.
- If a record **explains a gap/exclusion/staleness/missing-info** (it is *rejected, excluded, or
  documents an absence*), it is an **exception**.
- A given record belongs to one list, not both. The container IDs (case_id, claim_id, appeal_id,
  queue_id) generally do **not** go in either list — use the evidence/decision record IDs
  instead. The one exception is the **P2P event ID** for a P2P task, which is controlling
  because the precedence rule is literally about the P2P's new information.

## Step 3 — Build `precedence_record_order`

Concatenate the controlling records (in operational evidence order) followed by the exception
records (in gap-before-stale order). This is the single ordered trail, highest priority first.
It equals `controlling_record_ids + exception_record_ids` in almost every case.

## Common mistakes
- Putting the case/claim/appeal/queue container ID into `controlling_record_ids`. Use the
  underlying evidence/decision record IDs instead.
- Forgetting the exception list when a gap exists (stale doc, undocumented trial, stale
  benchmark, absent-factor fact).
- Listing an exception record that is really just a controlling record (e.g., a fully
  documented trial is controlling, not an exception).
- Wrong order: `precedence_record_order` must be controlling-then-exception, and each sublist
  must follow its own ordering rule.
- Choosing the wrong `source_precedence` for the family — re-check the table above.
