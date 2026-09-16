# Therapy Margin Queue Analysis

## Overview

Analyze a therapy service margin queue and classify payer-service rows for action.
The output matches the margin analysis answer template with required fields:
`case_id`, `period`, `threshold_revenue_to_cost_ratio`, `rows`,
`below_threshold_segments`, `charge_sensitive_segments`, `top_issue`,
`gap_to_120pct`, `basis_audit`.

## Workflow

### 1. Pull queue rows

Retrieve the margin queue rows from the environment using SQL. The task context
provides specific queue row IDs to include. Only process the listed rows.

Each row contains:

- `month_id`: the row identifier
- `payer_segment`: one of `medicaid`, `commercial`, `workers_comp`
- `service_domain`: one of `physical_therapy`, `speech_therapy`, `occupational_therapy`
- `cpt_code`: the therapy CPT code
- Revenue and cost fields needed to compute margin and ratio

### 2. Compute financial metrics

For each row:

```
total_cost = variable_cost + fixed_cost_allocated
margin = revenue - total_cost
revenue_to_cost_ratio = revenue / total_cost
```

Round total_cost and margin to two decimal places. Round revenue_to_cost_ratio to
four decimal places.

### 3. Classify rows

**Below threshold**: A row is `below_threshold` (`true`) when
`revenue_to_cost_ratio < threshold_revenue_to_cost_ratio` (typically 1.2).

**Charge sensitive**: A row is `charge_sensitive` (`true`) when its margin is
positive but the ratio suggests the payer contract pricing is notably above cost
(margin anomaly). The exact criteria come from the finance memo in the task context.

Rows that are not below threshold may still be charge sensitive.

### 4. Assign recommended actions

| Condition | recommended_action |
|-----------|-------------------|
| Below threshold | `payer_contract_review` |
| Charge sensitive (above threshold) | `monitor_charge_sensitive` |
| Neither below threshold nor charge sensitive | `monitor_no_action` |

### 5. Build segment lists

- `below_threshold_segments`: distinct payer segments from rows where
  `below_threshold` is `true`. Alphabetical order.
- `charge_sensitive_segments`: distinct payer segments from rows where
  `charge_sensitive` is `true`. Alphabetical order.

### 6. Identify the top issue

`top_issue` is a compound key `{payer_segment}_{cpt_code}` for the below-threshold
row with the lowest revenue-to-cost ratio (i.e., worst margin performance). If no
row is below threshold, use `"none"`.

Format: lowercase payer segment, underscore, CPT code. Example: `medicaid_97110`.

### 7. Compute gap to 120 percent

```
gap_to_120pct = (threshold_revenue_to_cost_ratio × total_cost) - revenue
```

for the top issue row. This is the dollar amount needed to bring revenue up to the
threshold ratio. Round to two decimal places.

### 8. Construct the basis_audit

Use `margin_threshold_then_charge_sensitivity`:

- `controlling_record_ids`: all queue row IDs, with below-threshold rows first
  (highest priority per the precedence rule)
- `exception_record_ids`: the below-threshold row ID(s) that drive the top issue
- `precedence_record_order`: below-threshold rows first, then charge-sensitive rows,
  then any remaining rows (matching the precedence rule name)

## Key Patterns from Training

- Rows in the output follow the same order as `task_context.finance_memo.queue_row_ids`.
- A row can be both below threshold AND charge sensitive if both conditions apply,
  but the recommended_action follows the below-threshold priority:
  `payer_contract_review` takes precedence over `monitor_charge_sensitive`.
- `gap_to_120pct` is always computed from the top issue row, not averaged or
  summed across rows.
- `charge_sensitive_segments` includes segments from rows flagged charge sensitive,
  even if those rows are also below threshold.
- The `top_issue` format is lowercase segment and CPT separated by underscore.
