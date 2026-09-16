# Payment Integrity Claim Repricing

## Overview

Reprice a paid claim against the current benchmark rate schedule and produce a
correction packet. The output matches the payment integrity answer template with
required fields: `claim_id`, `case_id`, `auth_number`, `benchmark_source`,
`benchmark_version`, `stale_source_rejected`, `paid_total`, `correct_allowed_total`,
`recovery_amount`, `lines`, `resubmission_route`, `priority`, `basis_audit`.

## Workflow

### 1. Pull the claim

Retrieve the target claim from the environment. Use SQL to query claim headers and
claim lines. Identify:

- Claim ID and associated case ID
- Authorization number from the claim or payment record
- Every claim line with its line ID, CPT code, modifier, units, and paid amount

### 2. Pull rate schedules

Retrieve all available rate schedules via `GET /api/rate-schedules` or SQL.
A rate schedule is a set of per-CPT allowed amounts, typically versioned (e.g.,
`2026Q2`) and scoped to a plan/modifier combination.

Rate schedules available include:
- **Northstar Commercial Imaging Schedule**: The current, effective benchmark
- **Legacy Imaging Export**: A stale/outdated schedule that must not be used
- **Northstar Distractor Schedule**: A distractor schedule, also not applicable

### 3. Select the benchmark

Apply the rule: select the effective benchmark by matching plan modifier and
effective date. The current benchmark source (e.g., `Northstar Commercial Imaging
Schedule`) always takes precedence over legacy or distractor schedules.

Record the stale source in `stale_source_rejected`. If no stale source was
considered, use `"none"`.

Benchmark `source_precedence` rule: `effective_benchmark_by_plan_modifier_and_date`.

### 4. Reprice each line

For each claim line, compute the correct allowed amount by matching the line's
CPT code and optional modifier to the selected benchmark schedule.

```
correct_allowed_amount = benchmark_rate × units
recovery_amount = correct_allowed_amount - paid_amount
```

- Positive recovery: underpayment (correct > paid)
- Negative recovery: overpayment (correct < paid)
- Zero recovery: correct match

Disposition per line:

| Recovery | Disposition |
|----------|-------------|
| > 0 | `correct_upward` |
| < 0 | `correct_downward` |
| 0 | `no_change` |
| Line not covered | `deny_line` |

### 5. Compute totals

```
paid_total = sum of all line paid_amount values
correct_allowed_total = sum of all line correct_allowed_amount values
recovery_amount = correct_allowed_total - paid_total
```

Round every dollar value to two decimal places.

### 6. Determine route and priority

| Scenario | resubmission_route | priority |
|----------|-------------------|----------|
| Standard correction, non-urgent | `payment_integrity_correction` | `standard` |
| Provider-initiated correction | `provider_adjustment` | `standard` |
| Appeal-related correction | `appeal_reopen` | `expedited` |
| No correction needed | `no_resubmission` | `monitor_only` |
| Urgent financial impact | `payment_integrity_correction` | `urgent` |

### 7. Construct the basis_audit

Use `effective_benchmark_by_plan_modifier_and_date`:

- `controlling_record_ids`: claim line IDs and the effective benchmark record IDs
  that produced the correct rates
- `exception_record_ids`: the stale benchmark record ID(s) that were rejected
- `precedence_record_order`: effective benchmark records first, then stale records

Order benchmark records before claim line records in `precedence_record_order`.
Within each group, use ascending ID order.

## Key Patterns from Training

- The `benchmark_source` is the name of the effective schedule (e.g.,
  `Northstar Commercial Imaging Schedule`), not a record ID.
- `benchmark_version` is the version string (e.g., `2026Q2`).
- Benchmark record IDs (like `BM-TR-003-78452`) are per-CPT entries within the
  schedule.
- `modifier` is `null` (not empty string) when the claim line has no modifier.
- Lines list follows claim-line order from the source claim.
- Recovery amount at the claim level is the total; at the line level it is per-line.
