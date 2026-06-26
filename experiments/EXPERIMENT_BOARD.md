# Experiment Board

Languages: [English](EXPERIMENT_BOARD.md) | [Chinese](EXPERIMENT_BOARD.zh.md)

This board summarizes the released evaluation results for GDPevo's public
benchmark runs. Released runs compare a stateless `base` baseline with
evolution modes. The Codex and Claude Code runs report `fewshot`, `self`, and
`reflect-3`; Panofy reports `fewshot`. Full structured reports
are stored under released experiment directories, such as
`codex_gpt5_5_xhigh/reports/`, `claude_code_opus_4_8_xhigh/reports/`,
and `panofy_claude_opus_4_6_high/reports/`.

In the released Codex GPT-5.5 xhigh run, the three Codex evolution modes improve
accuracy by +12.39 pp on average and change token cost by
-29.05% on average.

Efficiency metrics only count test solver subagent answer-writing. They are averaged across the 3 attempts for each test task first, then averaged across the 5 test tasks. Artifact generation, environment startup, evaluator execution, and main-agent aggregation are outside these metrics.

This board displays `acc@3` as a percentage and token metrics in thousands (`k`). Cost is calculated from the raw token counts in the report YAML files, then rounded to two decimals for display.

`cost USD avg@3` is calculated from report token metrics and the model price used for the run. Some report YAMLs store the calculated field directly; the board rounds it to two decimals for display.

For the released `gpt-5.5, xhigh` run, this board uses the standard GPT-5.5
text-token prices:

| Token type | Price |
| --- | ---: |
| Input | $5.00 / 1M tokens |
| Cached input | $0.50 / 1M tokens |
| Output | $30.00 / 1M tokens |

The board-level cost formula is:

```text
uncached_input_tokens_avg_3 = input_tokens_avg_3 - cached_input_tokens_avg_3

cost_USD_avg_3 =
  (uncached_input_tokens_avg_3 * 5.00
   + cached_input_tokens_avg_3 * 0.50
   + output_tokens_avg_3 * 30.00) / 1_000_000
```

| task_group_id | scenario_id | model | harness | mode | overall acc@3 (%) | cached tokens avg@3 (k) | input tokens avg@3 (k) | output tokens avg@3 (k) | cost USD avg@3 | report |
| --- | --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | --- |
| `task_group_001` | `SCN_001_crm_marketing_lead_capture` | `gpt-5.5, xhigh` | `codex` | `base` | 44.43% | 403.2k | 457.0k | 14.2k | 0.90 | [task_group_001.yaml](codex_gpt5_5_xhigh/reports/task_group_001.yaml) |
| `task_group_001` | `SCN_001_crm_marketing_lead_capture` | `gpt-5.5, xhigh` | `codex` | `fewshot` | 48.12% | 366.0k | 412.6k | 13.2k | 0.81 | [task_group_001.yaml](codex_gpt5_5_xhigh/reports/task_group_001.yaml) |
| `task_group_001` | `SCN_001_crm_marketing_lead_capture` | `gpt-5.5, xhigh` | `codex` | `self` | 71.06% | 320.8k | 391.4k | 12.2k | 0.88 | [task_group_001.yaml](codex_gpt5_5_xhigh/reports/task_group_001.yaml) |
| `task_group_001` | `SCN_001_crm_marketing_lead_capture` | `gpt-5.5, xhigh` | `codex` | `reflect-3` | 68.34% | 381.7k | 445.0k | 12.8k | 0.89 | [task_group_001.yaml](codex_gpt5_5_xhigh/reports/task_group_001.yaml) |
| `task_group_002` | `SCN_002_crm_b2b_quote_account_response` | `gpt-5.5, xhigh` | `codex` | `base` | 41.62% | 281.3k | 329.8k | 7.7k | 0.62 | [task_group_002.yaml](codex_gpt5_5_xhigh/reports/task_group_002.yaml) |
| `task_group_002` | `SCN_002_crm_b2b_quote_account_response` | `gpt-5.5, xhigh` | `codex` | `fewshot` | 51.17% | 190.9k | 225.5k | 7.1k | 0.48 | [task_group_002.yaml](codex_gpt5_5_xhigh/reports/task_group_002.yaml) |
| `task_group_002` | `SCN_002_crm_b2b_quote_account_response` | `gpt-5.5, xhigh` | `codex` | `self` | 45.36% | 155.9k | 188.1k | 6.3k | 0.43 | [task_group_002.yaml](codex_gpt5_5_xhigh/reports/task_group_002.yaml) |
| `task_group_002` | `SCN_002_crm_b2b_quote_account_response` | `gpt-5.5, xhigh` | `codex` | `reflect-3` | 44.24% | 160.0k | 203.4k | 7.1k | 0.51 | [task_group_002.yaml](codex_gpt5_5_xhigh/reports/task_group_002.yaml) |
| `task_group_003` | `SCN_003_crm_service_ticket_resolution` | `gpt-5.5, xhigh` | `codex` | `base` | 57.84% | 541.8k | 606.7k | 15.4k | 1.06 | [task_group_003.yaml](codex_gpt5_5_xhigh/reports/task_group_003.yaml) |
| `task_group_003` | `SCN_003_crm_service_ticket_resolution` | `gpt-5.5, xhigh` | `codex` | `fewshot` | 78.11% | 380.2k | 440.2k | 13.1k | 0.88 | [task_group_003.yaml](codex_gpt5_5_xhigh/reports/task_group_003.yaml) |
| `task_group_003` | `SCN_003_crm_service_ticket_resolution` | `gpt-5.5, xhigh` | `codex` | `self` | 62.91% | 455.2k | 537.0k | 14.5k | 1.07 | [task_group_003.yaml](codex_gpt5_5_xhigh/reports/task_group_003.yaml) |
| `task_group_003` | `SCN_003_crm_service_ticket_resolution` | `gpt-5.5, xhigh` | `codex` | `reflect-3` | 57.76% | 564.8k | 639.7k | 15.5k | 1.12 | [task_group_003.yaml](codex_gpt5_5_xhigh/reports/task_group_003.yaml) |
| `task_group_004` | `SCN_004_crm_retention_churn_analytics` | `gpt-5.5, xhigh` | `codex` | `base` | 31.73% | 766.4k | 859.9k | 18.5k | 1.40 | [task_group_004.yaml](codex_gpt5_5_xhigh/reports/task_group_004.yaml) |
| `task_group_004` | `SCN_004_crm_retention_churn_analytics` | `gpt-5.5, xhigh` | `codex` | `fewshot` | 60.94% | 532.3k | 595.1k | 15.2k | 1.04 | [task_group_004.yaml](codex_gpt5_5_xhigh/reports/task_group_004.yaml) |
| `task_group_004` | `SCN_004_crm_retention_churn_analytics` | `gpt-5.5, xhigh` | `codex` | `self` | 25.74% | 364.7k | 427.7k | 10.6k | 0.82 | [task_group_004.yaml](codex_gpt5_5_xhigh/reports/task_group_004.yaml) |
| `task_group_004` | `SCN_004_crm_retention_churn_analytics` | `gpt-5.5, xhigh` | `codex` | `reflect-3` | 25.01% | 575.3k | 652.9k | 12.6k | 1.05 | [task_group_004.yaml](codex_gpt5_5_xhigh/reports/task_group_004.yaml) |
| `task_group_005` | `SCN_005_erp_finance_expense_control` | `gpt-5.5, xhigh` | `codex` | `base` | 35.09% | 1760.8k | 1898.5k | 15.2k | 2.02 | [task_group_005.yaml](codex_gpt5_5_xhigh/reports/task_group_005.yaml) |
| `task_group_005` | `SCN_005_erp_finance_expense_control` | `gpt-5.5, xhigh` | `codex` | `fewshot` | 52.45% | 812.0k | 889.1k | 12.3k | 1.16 | [task_group_005.yaml](codex_gpt5_5_xhigh/reports/task_group_005.yaml) |
| `task_group_005` | `SCN_005_erp_finance_expense_control` | `gpt-5.5, xhigh` | `codex` | `self` | 58.86% | 314.0k | 377.2k | 12.1k | 0.84 | [task_group_005.yaml](codex_gpt5_5_xhigh/reports/task_group_005.yaml) |
| `task_group_005` | `SCN_005_erp_finance_expense_control` | `gpt-5.5, xhigh` | `codex` | `reflect-3` | 59.51% | 327.3k | 408.7k | 13.0k | 0.96 | [task_group_005.yaml](codex_gpt5_5_xhigh/reports/task_group_005.yaml) |
| `task_group_006` | `SCN_006_erp_procurement_supplier_receiving` | `gpt-5.5, xhigh` | `codex` | `base` | 66.28% | 320.6k | 376.5k | 8.3k | 0.69 | [task_group_006.yaml](codex_gpt5_5_xhigh/reports/task_group_006.yaml) |
| `task_group_006` | `SCN_006_erp_procurement_supplier_receiving` | `gpt-5.5, xhigh` | `codex` | `fewshot` | 72.39% | 305.7k | 364.4k | 8.3k | 0.69 | [task_group_006.yaml](codex_gpt5_5_xhigh/reports/task_group_006.yaml) |
| `task_group_006` | `SCN_006_erp_procurement_supplier_receiving` | `gpt-5.5, xhigh` | `codex` | `self` | 70.46% | 233.5k | 294.3k | 13.2k | 0.82 | [task_group_006.yaml](codex_gpt5_5_xhigh/reports/task_group_006.yaml) |
| `task_group_006` | `SCN_006_erp_procurement_supplier_receiving` | `gpt-5.5, xhigh` | `codex` | `reflect-3` | 72.87% | 213.1k | 263.9k | 12.8k | 0.74 | [task_group_006.yaml](codex_gpt5_5_xhigh/reports/task_group_006.yaml) |
| `task_group_007` | `SCN_007_erp_inventory_order_fulfillment` | `gpt-5.5, xhigh` | `codex` | `base` | 38.40% | 1299.2k | 1371.8k | 18.1k | 1.56 | [task_group_007.yaml](codex_gpt5_5_xhigh/reports/task_group_007.yaml) |
| `task_group_007` | `SCN_007_erp_inventory_order_fulfillment` | `gpt-5.5, xhigh` | `codex` | `fewshot` | 54.31% | 699.0k | 774.3k | 16.1k | 1.21 | [task_group_007.yaml](codex_gpt5_5_xhigh/reports/task_group_007.yaml) |
| `task_group_007` | `SCN_007_erp_inventory_order_fulfillment` | `gpt-5.5, xhigh` | `codex` | `self` | 28.48% | 351.4k | 435.7k | 15.1k | 1.05 | [task_group_007.yaml](codex_gpt5_5_xhigh/reports/task_group_007.yaml) |
| `task_group_007` | `SCN_007_erp_inventory_order_fulfillment` | `gpt-5.5, xhigh` | `codex` | `reflect-3` | 43.44% | 437.1k | 513.7k | 15.9k | 1.08 | [task_group_007.yaml](codex_gpt5_5_xhigh/reports/task_group_007.yaml) |
| `task_group_008` | `SCN_008_personal_financial_advisory_tax_estate_planning` | `gpt-5.5, xhigh` | `codex` | `base` | 43.47% | 983.9k | 1155.8k | 18.4k | 1.90 | [task_group_008.yaml](codex_gpt5_5_xhigh/reports/task_group_008.yaml) |
| `task_group_008` | `SCN_008_personal_financial_advisory_tax_estate_planning` | `gpt-5.5, xhigh` | `codex` | `fewshot` | 95.55% | 159.5k | 190.6k | 5.5k | 0.40 | [task_group_008.yaml](codex_gpt5_5_xhigh/reports/task_group_008.yaml) |
| `task_group_008` | `SCN_008_personal_financial_advisory_tax_estate_planning` | `gpt-5.5, xhigh` | `codex` | `self` | 62.44% | 171.8k | 203.4k | 6.4k | 0.44 | [task_group_008.yaml](codex_gpt5_5_xhigh/reports/task_group_008.yaml) |
| `task_group_008` | `SCN_008_personal_financial_advisory_tax_estate_planning` | `gpt-5.5, xhigh` | `codex` | `reflect-3` | 72.68% | 142.6k | 176.6k | 6.9k | 0.45 | [task_group_008.yaml](codex_gpt5_5_xhigh/reports/task_group_008.yaml) |
| `task_group_009` | `SCN_009_finance_operational_modeling_management_reporting` | `gpt-5.5, xhigh` | `codex` | `base` | 41.87% | 378.2k | 453.7k | 11.8k | 0.92 | [task_group_009.yaml](codex_gpt5_5_xhigh/reports/task_group_009.yaml) |
| `task_group_009` | `SCN_009_finance_operational_modeling_management_reporting` | `gpt-5.5, xhigh` | `codex` | `fewshot` | 69.79% | 305.7k | 360.4k | 9.3k | 0.71 | [task_group_009.yaml](codex_gpt5_5_xhigh/reports/task_group_009.yaml) |
| `task_group_009` | `SCN_009_finance_operational_modeling_management_reporting` | `gpt-5.5, xhigh` | `codex` | `self` | 52.30% | 201.0k | 243.0k | 8.0k | 0.55 | [task_group_009.yaml](codex_gpt5_5_xhigh/reports/task_group_009.yaml) |
| `task_group_009` | `SCN_009_finance_operational_modeling_management_reporting` | `gpt-5.5, xhigh` | `codex` | `reflect-3` | 68.33% | 215.4k | 281.2k | 9.8k | 0.73 | [task_group_009.yaml](codex_gpt5_5_xhigh/reports/task_group_009.yaml) |
| `task_group_010` | `SCN_010_institutional_investment_strategy_portfolio_risk` | `gpt-5.5, xhigh` | `codex` | `base` | 63.15% | 349.4k | 436.1k | 14.7k | 1.05 | [task_group_010.yaml](codex_gpt5_5_xhigh/reports/task_group_010.yaml) |
| `task_group_010` | `SCN_010_institutional_investment_strategy_portfolio_risk` | `gpt-5.5, xhigh` | `codex` | `fewshot` | 71.44% | 316.8k | 377.4k | 14.6k | 0.90 | [task_group_010.yaml](codex_gpt5_5_xhigh/reports/task_group_010.yaml) |
| `task_group_010` | `SCN_010_institutional_investment_strategy_portfolio_risk` | `gpt-5.5, xhigh` | `codex` | `self` | 68.99% | 290.2k | 360.7k | 15.5k | 0.96 | [task_group_010.yaml](codex_gpt5_5_xhigh/reports/task_group_010.yaml) |
| `task_group_010` | `SCN_010_institutional_investment_strategy_portfolio_risk` | `gpt-5.5, xhigh` | `codex` | `reflect-3` | 68.77% | 378.5k | 448.3k | 18.3k | 1.09 | [task_group_010.yaml](codex_gpt5_5_xhigh/reports/task_group_010.yaml) |
| `task_group_011` | `SCN_011_bank_branch_credit_risk_lending_committee` | `gpt-5.5, xhigh` | `codex` | `base` | 51.68% | 259.0k | 329.6k | 13.7k | 0.89 | [task_group_011.yaml](codex_gpt5_5_xhigh/reports/task_group_011.yaml) |
| `task_group_011` | `SCN_011_bank_branch_credit_risk_lending_committee` | `gpt-5.5, xhigh` | `codex` | `fewshot` | 63.38% | 219.1k | 274.9k | 12.7k | 0.77 | [task_group_011.yaml](codex_gpt5_5_xhigh/reports/task_group_011.yaml) |
| `task_group_011` | `SCN_011_bank_branch_credit_risk_lending_committee` | `gpt-5.5, xhigh` | `codex` | `self` | 50.23% | 179.7k | 227.3k | 14.1k | 0.75 | [task_group_011.yaml](codex_gpt5_5_xhigh/reports/task_group_011.yaml) |
| `task_group_011` | `SCN_011_bank_branch_credit_risk_lending_committee` | `gpt-5.5, xhigh` | `codex` | `reflect-3` | 47.61% | 207.1k | 248.5k | 15.3k | 0.77 | [task_group_011.yaml](codex_gpt5_5_xhigh/reports/task_group_011.yaml) |
| `task_group_012` | `SCN_012_erp_hr_employee_lifecycle` | `gpt-5.5, xhigh` | `codex` | `base` | 45.08% | 336.4k | 384.7k | 7.6k | 0.64 | [task_group_012.yaml](codex_gpt5_5_xhigh/reports/task_group_012.yaml) |
| `task_group_012` | `SCN_012_erp_hr_employee_lifecycle` | `gpt-5.5, xhigh` | `codex` | `fewshot` | 61.24% | 342.8k | 379.9k | 8.2k | 0.60 | [task_group_012.yaml](codex_gpt5_5_xhigh/reports/task_group_012.yaml) |
| `task_group_012` | `SCN_012_erp_hr_employee_lifecycle` | `gpt-5.5, xhigh` | `codex` | `self` | 63.01% | 262.0k | 308.3k | 9.7k | 0.66 | [task_group_012.yaml](codex_gpt5_5_xhigh/reports/task_group_012.yaml) |
| `task_group_012` | `SCN_012_erp_hr_employee_lifecycle` | `gpt-5.5, xhigh` | `codex` | `reflect-3` | 60.78% | 310.2k | 359.5k | 11.1k | 0.73 | [task_group_012.yaml](codex_gpt5_5_xhigh/reports/task_group_012.yaml) |

---

## Claude Code (Opus 4.8, xhigh)

In the released Claude Code Opus 4.8 xhigh run, the three Claude Code evolution
modes improve accuracy by +14.55 percentage points on average and change token
cost by -3.14% on average.

For the released `claude-opus-4-8, xhigh` run, this board uses the Claude Opus 4.8 prices:

| Token type | Price |
| --- | ---: |
| Input (uncached) | $5.00 / 1M tokens |
| Cache write | $6.25 / 1M tokens |
| Cache read | $0.50 / 1M tokens |
| Output | $25.00 / 1M tokens |

The board-level cost formula is:

```text
cost_USD_avg_3 =
  (input_tokens_avg_3        * 5.00
   + cache_creation_tokens_avg_3 * 6.25
   + cache_read_tokens_avg_3     * 0.50
   + output_tokens_avg_3         * 25.00) / 1_000_000
```

The Claude Code token columns are the four Anthropic usage buckets (uncached input, cache write, cache read, output).

| task_group_id | scenario_id | model | harness | mode | overall acc@3 (%) | input(uncached) tokens avg@3 (k) | cache write tokens avg@3 (k) | cache read tokens avg@3 (k) | output tokens avg@3 (k) | cost USD avg@3 | report |
| --- | --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| `task_group_001` | `SCN_001_crm_marketing_lead_capture` | `claude-opus-4-8, xhigh` | `claude_code` | `base` | 48.75% | 2.8k | 29.4k | 205.0k | 10.0k | 0.55 | [task_group_001.yaml](claude_code_opus_4_8_xhigh/reports/task_group_001.yaml) |
| `task_group_001` | `SCN_001_crm_marketing_lead_capture` | `claude-opus-4-8, xhigh` | `claude_code` | `fewshot` | 81.96% | 2.8k | 28.1k | 138.1k | 5.1k | 0.39 | [task_group_001.yaml](claude_code_opus_4_8_xhigh/reports/task_group_001.yaml) |
| `task_group_001` | `SCN_001_crm_marketing_lead_capture` | `claude-opus-4-8, xhigh` | `claude_code` | `self` | 77.11% | 3.2k | 31.3k | 241.7k | 5.8k | 0.48 | [task_group_001.yaml](claude_code_opus_4_8_xhigh/reports/task_group_001.yaml) |
| `task_group_001` | `SCN_001_crm_marketing_lead_capture` | `claude-opus-4-8, xhigh` | `claude_code` | `reflect-3` | 71.84% | 3.3k | 32.0k | 291.1k | 7.5k | 0.55 | [task_group_001.yaml](claude_code_opus_4_8_xhigh/reports/task_group_001.yaml) |
| `task_group_002` | `SCN_002_crm_b2b_quote_account_response` | `claude-opus-4-8, xhigh` | `claude_code` | `base` | 42.74% | 2.8k | 19.4k | 125.6k | 3.2k | 0.28 | [task_group_002.yaml](claude_code_opus_4_8_xhigh/reports/task_group_002.yaml) |
| `task_group_002` | `SCN_002_crm_b2b_quote_account_response` | `claude-opus-4-8, xhigh` | `claude_code` | `fewshot` | 58.48% | 2.8k | 27.2k | 108.7k | 2.5k | 0.30 | [task_group_002.yaml](claude_code_opus_4_8_xhigh/reports/task_group_002.yaml) |
| `task_group_002` | `SCN_002_crm_b2b_quote_account_response` | `claude-opus-4-8, xhigh` | `claude_code` | `self` | 49.84% | 2.9k | 22.1k | 142.8k | 3.1k | 0.30 | [task_group_002.yaml](claude_code_opus_4_8_xhigh/reports/task_group_002.yaml) |
| `task_group_002` | `SCN_002_crm_b2b_quote_account_response` | `claude-opus-4-8, xhigh` | `claude_code` | `reflect-3` | 58.79% | 2.9k | 20.8k | 127.5k | 2.7k | 0.28 | [task_group_002.yaml](claude_code_opus_4_8_xhigh/reports/task_group_002.yaml) |
| `task_group_003` | `SCN_003_crm_service_ticket_resolution` | `claude-opus-4-8, xhigh` | `claude_code` | `base` | 46.69% | 2.8k | 45.7k | 638.2k | 12.3k | 0.93 | [task_group_003.yaml](claude_code_opus_4_8_xhigh/reports/task_group_003.yaml) |
| `task_group_003` | `SCN_003_crm_service_ticket_resolution` | `claude-opus-4-8, xhigh` | `claude_code` | `fewshot` | 70.89% | 2.8k | 38.7k | 375.7k | 6.4k | 0.60 | [task_group_003.yaml](claude_code_opus_4_8_xhigh/reports/task_group_003.yaml) |
| `task_group_003` | `SCN_003_crm_service_ticket_resolution` | `claude-opus-4-8, xhigh` | `claude_code` | `self` | 57.21% | 3.7k | 45.7k | 618.7k | 10.9k | 0.89 | [task_group_003.yaml](claude_code_opus_4_8_xhigh/reports/task_group_003.yaml) |
| `task_group_003` | `SCN_003_crm_service_ticket_resolution` | `claude-opus-4-8, xhigh` | `claude_code` | `reflect-3` | 56.48% | 3.6k | 43.9k | 552.1k | 10.6k | 0.83 | [task_group_003.yaml](claude_code_opus_4_8_xhigh/reports/task_group_003.yaml) |
| `task_group_004` | `SCN_004_crm_retention_churn_analytics` | `claude-opus-4-8, xhigh` | `claude_code` | `base` | 25.24% | 2.8k | 40.1k | 611.2k | 13.5k | 0.91 | [task_group_004.yaml](claude_code_opus_4_8_xhigh/reports/task_group_004.yaml) |
| `task_group_004` | `SCN_004_crm_retention_churn_analytics` | `claude-opus-4-8, xhigh` | `claude_code` | `fewshot` | 54.55% | 2.8k | 34.4k | 366.6k | 8.7k | 0.63 | [task_group_004.yaml](claude_code_opus_4_8_xhigh/reports/task_group_004.yaml) |
| `task_group_004` | `SCN_004_crm_retention_churn_analytics` | `claude-opus-4-8, xhigh` | `claude_code` | `self` | 38.35% | 2.9k | 39.2k | 557.8k | 8.4k | 0.75 | [task_group_004.yaml](claude_code_opus_4_8_xhigh/reports/task_group_004.yaml) |
| `task_group_004` | `SCN_004_crm_retention_churn_analytics` | `claude-opus-4-8, xhigh` | `claude_code` | `reflect-3` | 45.50% | 2.7k | 41.4k | 501.2k | 8.2k | 0.73 | [task_group_004.yaml](claude_code_opus_4_8_xhigh/reports/task_group_004.yaml) |
| `task_group_005` | `SCN_005_erp_finance_expense_control` | `claude-opus-4-8, xhigh` | `claude_code` | `base` | 51.15% | 2.8k | 34.3k | 386.8k | 10.1k | 0.67 | [task_group_005.yaml](claude_code_opus_4_8_xhigh/reports/task_group_005.yaml) |
| `task_group_005` | `SCN_005_erp_finance_expense_control` | `claude-opus-4-8, xhigh` | `claude_code` | `fewshot` | 57.96% | 2.8k | 30.2k | 246.4k | 7.3k | 0.51 | [task_group_005.yaml](claude_code_opus_4_8_xhigh/reports/task_group_005.yaml) |
| `task_group_005` | `SCN_005_erp_finance_expense_control` | `claude-opus-4-8, xhigh` | `claude_code` | `self` | 45.35% | 3.6k | 38.6k | 461.1k | 10.1k | 0.74 | [task_group_005.yaml](claude_code_opus_4_8_xhigh/reports/task_group_005.yaml) |
| `task_group_005` | `SCN_005_erp_finance_expense_control` | `claude-opus-4-8, xhigh` | `claude_code` | `reflect-3` | 58.97% | 3.8k | 33.8k | 396.1k | 8.6k | 0.64 | [task_group_005.yaml](claude_code_opus_4_8_xhigh/reports/task_group_005.yaml) |
| `task_group_006` | `SCN_006_erp_procurement_supplier_receiving` | `claude-opus-4-8, xhigh` | `claude_code` | `base` | 67.98% | 2.8k | 28.6k | 284.6k | 9.3k | 0.57 | [task_group_006.yaml](claude_code_opus_4_8_xhigh/reports/task_group_006.yaml) |
| `task_group_006` | `SCN_006_erp_procurement_supplier_receiving` | `claude-opus-4-8, xhigh` | `claude_code` | `fewshot` | 72.98% | 2.8k | 38.6k | 356.5k | 8.7k | 0.65 | [task_group_006.yaml](claude_code_opus_4_8_xhigh/reports/task_group_006.yaml) |
| `task_group_006` | `SCN_006_erp_procurement_supplier_receiving` | `claude-opus-4-8, xhigh` | `claude_code` | `self` | 74.72% | 3.4k | 32.0k | 355.6k | 7.9k | 0.59 | [task_group_006.yaml](claude_code_opus_4_8_xhigh/reports/task_group_006.yaml) |
| `task_group_006` | `SCN_006_erp_procurement_supplier_receiving` | `claude-opus-4-8, xhigh` | `claude_code` | `reflect-3` | 73.52% | 3.7k | 32.6k | 346.5k | 8.2k | 0.60 | [task_group_006.yaml](claude_code_opus_4_8_xhigh/reports/task_group_006.yaml) |
| `task_group_007` | `SCN_007_erp_inventory_order_fulfillment` | `claude-opus-4-8, xhigh` | `claude_code` | `base` | 39.54% | 2.8k | 35.7k | 337.8k | 10.1k | 0.66 | [task_group_007.yaml](claude_code_opus_4_8_xhigh/reports/task_group_007.yaml) |
| `task_group_007` | `SCN_007_erp_inventory_order_fulfillment` | `claude-opus-4-8, xhigh` | `claude_code` | `fewshot` | 55.76% | 2.8k | 43.3k | 356.0k | 8.6k | 0.68 | [task_group_007.yaml](claude_code_opus_4_8_xhigh/reports/task_group_007.yaml) |
| `task_group_007` | `SCN_007_erp_inventory_order_fulfillment` | `claude-opus-4-8, xhigh` | `claude_code` | `self` | 37.38% | 3.5k | 44.0k | 524.2k | 9.2k | 0.79 | [task_group_007.yaml](claude_code_opus_4_8_xhigh/reports/task_group_007.yaml) |
| `task_group_007` | `SCN_007_erp_inventory_order_fulfillment` | `claude-opus-4-8, xhigh` | `claude_code` | `reflect-3` | 51.45% | 3.6k | 39.5k | 547.0k | 8.9k | 0.76 | [task_group_007.yaml](claude_code_opus_4_8_xhigh/reports/task_group_007.yaml) |
| `task_group_008` | `SCN_008_personal_financial_advisory_tax_estate_planning` | `claude-opus-4-8, xhigh` | `claude_code` | `base` | 66.89% | 2.8k | 13.8k | 106.2k | 5.3k | 0.29 | [task_group_008.yaml](claude_code_opus_4_8_xhigh/reports/task_group_008.yaml) |
| `task_group_008` | `SCN_008_personal_financial_advisory_tax_estate_planning` | `claude-opus-4-8, xhigh` | `claude_code` | `fewshot` | 93.60% | 2.8k | 32.0k | 241.7k | 3.6k | 0.43 | [task_group_008.yaml](claude_code_opus_4_8_xhigh/reports/task_group_008.yaml) |
| `task_group_008` | `SCN_008_personal_financial_advisory_tax_estate_planning` | `claude-opus-4-8, xhigh` | `claude_code` | `self` | 68.93% | 3.1k | 21.8k | 115.7k | 2.6k | 0.27 | [task_group_008.yaml](claude_code_opus_4_8_xhigh/reports/task_group_008.yaml) |
| `task_group_008` | `SCN_008_personal_financial_advisory_tax_estate_planning` | `claude-opus-4-8, xhigh` | `claude_code` | `reflect-3` | 78.58% | 3.1k | 20.9k | 136.8k | 3.5k | 0.30 | [task_group_008.yaml](claude_code_opus_4_8_xhigh/reports/task_group_008.yaml) |
| `task_group_009` | `SCN_009_finance_operational_modeling_management_reporting` | `claude-opus-4-8, xhigh` | `claude_code` | `base` | 51.76% | 2.8k | 25.4k | 162.7k | 4.9k | 0.38 | [task_group_009.yaml](claude_code_opus_4_8_xhigh/reports/task_group_009.yaml) |
| `task_group_009` | `SCN_009_finance_operational_modeling_management_reporting` | `claude-opus-4-8, xhigh` | `claude_code` | `fewshot` | 100.00% | 2.8k | 29.3k | 205.2k | 3.8k | 0.39 | [task_group_009.yaml](claude_code_opus_4_8_xhigh/reports/task_group_009.yaml) |
| `task_group_009` | `SCN_009_finance_operational_modeling_management_reporting` | `claude-opus-4-8, xhigh` | `claude_code` | `self` | 58.07% | 3.8k | 26.6k | 257.6k | 4.6k | 0.43 | [task_group_009.yaml](claude_code_opus_4_8_xhigh/reports/task_group_009.yaml) |
| `task_group_009` | `SCN_009_finance_operational_modeling_management_reporting` | `claude-opus-4-8, xhigh` | `claude_code` | `reflect-3` | 76.68% | 3.2k | 24.8k | 253.2k | 5.0k | 0.42 | [task_group_009.yaml](claude_code_opus_4_8_xhigh/reports/task_group_009.yaml) |
| `task_group_010` | `SCN_010_institutional_investment_strategy_portfolio_risk` | `claude-opus-4-8, xhigh` | `claude_code` | `base` | 58.60% | 2.8k | 41.8k | 445.6k | 10.9k | 0.77 | [task_group_010.yaml](claude_code_opus_4_8_xhigh/reports/task_group_010.yaml) |
| `task_group_010` | `SCN_010_institutional_investment_strategy_portfolio_risk` | `claude-opus-4-8, xhigh` | `claude_code` | `fewshot` | 63.45% | 2.8k | 46.7k | 500.8k | 10.5k | 0.82 | [task_group_010.yaml](claude_code_opus_4_8_xhigh/reports/task_group_010.yaml) |
| `task_group_010` | `SCN_010_institutional_investment_strategy_portfolio_risk` | `claude-opus-4-8, xhigh` | `claude_code` | `self` | 60.67% | 3.6k | 50.9k | 690.1k | 11.2k | 0.96 | [task_group_010.yaml](claude_code_opus_4_8_xhigh/reports/task_group_010.yaml) |
| `task_group_010` | `SCN_010_institutional_investment_strategy_portfolio_risk` | `claude-opus-4-8, xhigh` | `claude_code` | `reflect-3` | 58.16% | 3.6k | 49.1k | 699.6k | 12.3k | 0.98 | [task_group_010.yaml](claude_code_opus_4_8_xhigh/reports/task_group_010.yaml) |
| `task_group_011` | `SCN_011_bank_branch_credit_risk_lending_committee` | `claude-opus-4-8, xhigh` | `claude_code` | `base` | 41.56% | 2.8k | 45.3k | 703.5k | 15.5k | 1.04 | [task_group_011.yaml](claude_code_opus_4_8_xhigh/reports/task_group_011.yaml) |
| `task_group_011` | `SCN_011_bank_branch_credit_risk_lending_committee` | `claude-opus-4-8, xhigh` | `claude_code` | `fewshot` | 63.48% | 2.8k | 50.2k | 586.2k | 9.6k | 0.86 | [task_group_011.yaml](claude_code_opus_4_8_xhigh/reports/task_group_011.yaml) |
| `task_group_011` | `SCN_011_bank_branch_credit_risk_lending_committee` | `claude-opus-4-8, xhigh` | `claude_code` | `self` | 47.32% | 3.5k | 41.8k | 539.6k | 11.2k | 0.83 | [task_group_011.yaml](claude_code_opus_4_8_xhigh/reports/task_group_011.yaml) |
| `task_group_011` | `SCN_011_bank_branch_credit_risk_lending_committee` | `claude-opus-4-8, xhigh` | `claude_code` | `reflect-3` | 48.03% | 3.6k | 41.8k | 649.6k | 9.6k | 0.84 | [task_group_011.yaml](claude_code_opus_4_8_xhigh/reports/task_group_011.yaml) |
| `task_group_012` | `SCN_012_erp_hr_employee_lifecycle` | `claude-opus-4-8, xhigh` | `claude_code` | `base` | 48.41% | 2.8k | 17.6k | 103.3k | 3.0k | 0.25 | [task_group_012.yaml](claude_code_opus_4_8_xhigh/reports/task_group_012.yaml) |
| `task_group_012` | `SCN_012_erp_hr_employee_lifecycle` | `claude-opus-4-8, xhigh` | `claude_code` | `fewshot` | 77.66% | 2.8k | 25.2k | 149.8k | 3.0k | 0.32 | [task_group_012.yaml](claude_code_opus_4_8_xhigh/reports/task_group_012.yaml) |
| `task_group_012` | `SCN_012_erp_hr_employee_lifecycle` | `claude-opus-4-8, xhigh` | `claude_code` | `self` | 73.48% | 3.1k | 21.1k | 158.2k | 2.9k | 0.30 | [task_group_012.yaml](claude_code_opus_4_8_xhigh/reports/task_group_012.yaml) |
| `task_group_012` | `SCN_012_erp_hr_employee_lifecycle` | `claude-opus-4-8, xhigh` | `claude_code` | `reflect-3` | 74.70% | 3.1k | 21.1k | 170.1k | 3.2k | 0.31 | [task_group_012.yaml](claude_code_opus_4_8_xhigh/reports/task_group_012.yaml) |

---

## Panofy (Claude Opus 4.6, high)

In the released Panofy Claude Opus 4.6 high run, the reported fewshot mode improves accuracy by +18.07 percentage points and changes token cost by +11.05% on average across the 12 task groups.

For the released `claude-opus-4-6, high` run, this board uses the Claude Opus 4.6 prices for the three token buckets exposed by Panofy:

| Token type | Price |
| --- | ---: |
| 5m Cache Writes | $6.25 / 1M tokens |
| Cache Hits | $0.50 / 1M tokens |
| Output Tokens | $25.00 / 1M tokens |

The board-level and report-level cost formula is:

```text
cost_USD_avg_3 =
  (cache_write_tokens_avg_3 * 6.25
   + cache_read_tokens_avg_3  * 0.50
   + output_tokens_avg_3      * 25.00) / 1_000_000
```

The Panofy token columns are the three available Anthropic usage buckets returned by the harness: 5-minute cache writes, cache hits, and output tokens.

| task_group_id | scenario_id | model | harness | mode | overall acc@3 (%) | 5m cache write tokens avg@3 (k) | cache hit tokens avg@3 (k) | output tokens avg@3 (k) | cost USD avg@3 | report |
| --- | --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | --- |
| `task_group_001` | `SCN_001_crm_marketing_lead_capture` | `claude-opus-4-6, high` | `panofy` | `base` | 63.74% | 23.8k | 155.1k | 11.9k | 0.52 | [task_group_001.yaml](panofy_claude_opus_4_6_high/reports/task_group_001.yaml) |
| `task_group_001` | `SCN_001_crm_marketing_lead_capture` | `claude-opus-4-6, high` | `panofy` | `fewshot` | 85.28% | 27.4k | 209.2k | 11.5k | 0.56 | [task_group_001.yaml](panofy_claude_opus_4_6_high/reports/task_group_001.yaml) |
| `task_group_002` | `SCN_002_crm_b2b_quote_account_response` | `claude-opus-4-6, high` | `panofy` | `base` | 43.85% | 18.5k | 148.6k | 5.8k | 0.34 | [task_group_002.yaml](panofy_claude_opus_4_6_high/reports/task_group_002.yaml) |
| `task_group_002` | `SCN_002_crm_b2b_quote_account_response` | `claude-opus-4-6, high` | `panofy` | `fewshot` | 58.93% | 21.4k | 218.5k | 6.8k | 0.41 | [task_group_002.yaml](panofy_claude_opus_4_6_high/reports/task_group_002.yaml) |
| `task_group_003` | `SCN_003_crm_service_ticket_resolution` | `claude-opus-4-6, high` | `panofy` | `base` | 58.58% | 36.9k | 472.6k | 13.7k | 0.81 | [task_group_003.yaml](panofy_claude_opus_4_6_high/reports/task_group_003.yaml) |
| `task_group_003` | `SCN_003_crm_service_ticket_resolution` | `claude-opus-4-6, high` | `panofy` | `fewshot` | 73.41% | 45.5k | 625.3k | 16.3k | 1.00 | [task_group_003.yaml](panofy_claude_opus_4_6_high/reports/task_group_003.yaml) |
| `task_group_004` | `SCN_004_crm_retention_churn_analytics` | `claude-opus-4-6, high` | `panofy` | `base` | 18.82% | 42.0k | 456.8k | 19.3k | 0.97 | [task_group_004.yaml](panofy_claude_opus_4_6_high/reports/task_group_004.yaml) |
| `task_group_004` | `SCN_004_crm_retention_churn_analytics` | `claude-opus-4-6, high` | `panofy` | `fewshot` | 59.53% | 40.0k | 445.5k | 17.8k | 0.92 | [task_group_004.yaml](panofy_claude_opus_4_6_high/reports/task_group_004.yaml) |
| `task_group_005` | `SCN_005_erp_finance_expense_control` | `claude-opus-4-6, high` | `panofy` | `base` | 41.05% | 31.0k | 242.0k | 17.8k | 0.76 | [task_group_005.yaml](panofy_claude_opus_4_6_high/reports/task_group_005.yaml) |
| `task_group_005` | `SCN_005_erp_finance_expense_control` | `claude-opus-4-6, high` | `panofy` | `fewshot` | 60.51% | 33.1k | 317.4k | 17.8k | 0.81 | [task_group_005.yaml](panofy_claude_opus_4_6_high/reports/task_group_005.yaml) |
| `task_group_006` | `SCN_006_erp_procurement_supplier_receiving` | `claude-opus-4-6, high` | `panofy` | `base` | 64.83% | 33.0k | 239.9k | 12.2k | 0.63 | [task_group_006.yaml](panofy_claude_opus_4_6_high/reports/task_group_006.yaml) |
| `task_group_006` | `SCN_006_erp_procurement_supplier_receiving` | `claude-opus-4-6, high` | `panofy` | `fewshot` | 72.24% | 40.4k | 352.1k | 14.3k | 0.79 | [task_group_006.yaml](panofy_claude_opus_4_6_high/reports/task_group_006.yaml) |
| `task_group_007` | `SCN_007_erp_inventory_order_fulfillment` | `claude-opus-4-6, high` | `panofy` | `base` | 36.39% | 48.6k | 446.2k | 20.2k | 1.03 | [task_group_007.yaml](panofy_claude_opus_4_6_high/reports/task_group_007.yaml) |
| `task_group_007` | `SCN_007_erp_inventory_order_fulfillment` | `claude-opus-4-6, high` | `panofy` | `fewshot` | 41.88% | 56.8k | 522.9k | 25.8k | 1.26 | [task_group_007.yaml](panofy_claude_opus_4_6_high/reports/task_group_007.yaml) |
| `task_group_008` | `SCN_008_personal_financial_advisory_tax_estate_planning` | `claude-opus-4-6, high` | `panofy` | `base` | 49.18% | 20.5k | 189.2k | 10.9k | 0.49 | [task_group_008.yaml](panofy_claude_opus_4_6_high/reports/task_group_008.yaml) |
| `task_group_008` | `SCN_008_personal_financial_advisory_tax_estate_planning` | `claude-opus-4-6, high` | `panofy` | `fewshot` | 73.36% | 25.9k | 268.5k | 16.2k | 0.70 | [task_group_008.yaml](panofy_claude_opus_4_6_high/reports/task_group_008.yaml) |
| `task_group_009` | `SCN_009_finance_operational_modeling_management_reporting` | `claude-opus-4-6, high` | `panofy` | `base` | 62.39% | 23.8k | 155.3k | 11.7k | 0.52 | [task_group_009.yaml](panofy_claude_opus_4_6_high/reports/task_group_009.yaml) |
| `task_group_009` | `SCN_009_finance_operational_modeling_management_reporting` | `claude-opus-4-6, high` | `panofy` | `fewshot` | 89.73% | 26.2k | 234.6k | 14.4k | 0.64 | [task_group_009.yaml](panofy_claude_opus_4_6_high/reports/task_group_009.yaml) |
| `task_group_010` | `SCN_010_institutional_investment_strategy_portfolio_risk` | `claude-opus-4-6, high` | `panofy` | `base` | 50.73% | 49.7k | 471.3k | 21.3k | 1.08 | [task_group_010.yaml](panofy_claude_opus_4_6_high/reports/task_group_010.yaml) |
| `task_group_010` | `SCN_010_institutional_investment_strategy_portfolio_risk` | `claude-opus-4-6, high` | `panofy` | `fewshot` | 65.18% | 52.0k | 491.3k | 21.1k | 1.10 | [task_group_010.yaml](panofy_claude_opus_4_6_high/reports/task_group_010.yaml) |
| `task_group_011` | `SCN_011_bank_branch_credit_risk_lending_committee` | `claude-opus-4-6, high` | `panofy` | `base` | 48.91% | 58.4k | 304.3k | 25.5k | 1.15 | [task_group_011.yaml](panofy_claude_opus_4_6_high/reports/task_group_011.yaml) |
| `task_group_011` | `SCN_011_bank_branch_credit_risk_lending_committee` | `claude-opus-4-6, high` | `panofy` | `fewshot` | 56.38% | 51.9k | 331.3k | 24.1k | 1.09 | [task_group_011.yaml](panofy_claude_opus_4_6_high/reports/task_group_011.yaml) |
| `task_group_012` | `SCN_012_erp_hr_employee_lifecycle` | `claude-opus-4-6, high` | `panofy` | `base` | 63.59% | 18.9k | 140.1k | 5.8k | 0.33 | [task_group_012.yaml](panofy_claude_opus_4_6_high/reports/task_group_012.yaml) |
| `task_group_012` | `SCN_012_erp_hr_employee_lifecycle` | `claude-opus-4-6, high` | `panofy` | `fewshot` | 82.43% | 18.0k | 146.9k | 4.9k | 0.31 | [task_group_012.yaml](panofy_claude_opus_4_6_high/reports/task_group_012.yaml) |
