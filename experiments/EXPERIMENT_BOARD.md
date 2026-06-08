# Experiment Board

Languages: [English](EXPERIMENT_BOARD.md) | [Chinese](EXPERIMENT_BOARD.zh.md)

This board summarizes the released evaluation results for the public benchmark runs.
Full structured reports are stored under released experiment directories, such
as `codex_gpt5_5_xhigh/reports/`.

Efficiency metrics only count test solver subagent answer-writing. They are averaged across the 3 attempts for each test task first, then averaged across the 5 test tasks. Skill generation, environment startup, evaluator execution, and main-agent aggregation are outside these metrics.

`cost USD avg@3` is a board-level derived field calculated from report token metrics and the model price used for the run. It is not stored inside the formal report YAML files.

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

| task_group_id | scenario_id | model | harness | mode | overall avg@3 | cached tokens avg@3 | input tokens avg@3 | output tokens avg@3 | cost USD avg@3 | seconds avg@3 | report |
| --- | --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| `task_group_001` | `SCN_001_crm_marketing_lead_capture` | `gpt-5.5, xhigh` | `codex` | `no_skill` | 0.4443 | 403242.67 | 456965.60 | 14219.33 | 0.896816 | 309.779 | [task_group_001.yaml](codex_gpt5_5_xhigh/reports/task_group_001.yaml) |
| `task_group_001` | `SCN_001_crm_marketing_lead_capture` | `gpt-5.5, xhigh` | `codex` | `demonstration_skill` | 0.4812 | 366020.27 | 412637.73 | 13239.67 | 0.813288 | 282.567 | [task_group_001.yaml](codex_gpt5_5_xhigh/reports/task_group_001.yaml) |
| `task_group_001` | `SCN_001_crm_marketing_lead_capture` | `gpt-5.5, xhigh` | `codex` | `reflection_skill` | 0.5746 | 358997.33 | 408413.60 | 13280.27 | 0.824988 | 291.846 | [task_group_001.yaml](codex_gpt5_5_xhigh/reports/task_group_001.yaml) |
| `task_group_002` | `SCN_002_crm_b2b_quote_account_response` | `gpt-5.5, xhigh` | `codex` | `no_skill` | 0.4162 | 281301.33 | 329825.40 | 7731.13 | 0.615205 | 176.821 | [task_group_002.yaml](codex_gpt5_5_xhigh/reports/task_group_002.yaml) |
| `task_group_002` | `SCN_002_crm_b2b_quote_account_response` | `gpt-5.5, xhigh` | `codex` | `demonstration_skill` | 0.5117 | 190873.60 | 225481.40 | 7094.00 | 0.481296 | 156.808 | [task_group_002.yaml](codex_gpt5_5_xhigh/reports/task_group_002.yaml) |
| `task_group_002` | `SCN_002_crm_b2b_quote_account_response` | `gpt-5.5, xhigh` | `codex` | `reflection_skill` | 0.6041 | 168337.06 | 200899.93 | 6396.47 | 0.438877 | 159.273 | [task_group_002.yaml](codex_gpt5_5_xhigh/reports/task_group_002.yaml) |
| `task_group_003` | `SCN_003_crm_service_ticket_resolution` | `gpt-5.5, xhigh` | `codex` | `no_skill` | 0.5784 | 541764.27 | 606650.73 | 15427.27 | 1.058133 | 340.050 | [task_group_003.yaml](codex_gpt5_5_xhigh/reports/task_group_003.yaml) |
| `task_group_003` | `SCN_003_crm_service_ticket_resolution` | `gpt-5.5, xhigh` | `codex` | `demonstration_skill` | 0.7811 | 380185.60 | 440217.67 | 13091.60 | 0.883001 | 322.110 | [task_group_003.yaml](codex_gpt5_5_xhigh/reports/task_group_003.yaml) |
| `task_group_003` | `SCN_003_crm_service_ticket_resolution` | `gpt-5.5, xhigh` | `codex` | `reflection_skill` | 0.7169 | 354218.67 | 400569.13 | 12645.87 | 0.788238 | 273.740 | [task_group_003.yaml](codex_gpt5_5_xhigh/reports/task_group_003.yaml) |
| `task_group_004` | `SCN_004_crm_retention_churn_analytics` | `gpt-5.5, xhigh` | `codex` | `no_skill` | 0.3173 | 766429.87 | 859865.40 | 18469.80 | 1.404487 | 431.142 | [task_group_004.yaml](codex_gpt5_5_xhigh/reports/task_group_004.yaml) |
| `task_group_004` | `SCN_004_crm_retention_churn_analytics` | `gpt-5.5, xhigh` | `codex` | `demonstration_skill` | 0.6094 | 532275.20 | 595131.47 | 15153.73 | 1.035031 | 444.140 | [task_group_004.yaml](codex_gpt5_5_xhigh/reports/task_group_004.yaml) |
| `task_group_004` | `SCN_004_crm_retention_churn_analytics` | `gpt-5.5, xhigh` | `codex` | `reflection_skill` | 0.5995 | 429986.13 | 489274.80 | 12457.40 | 0.885158 | 285.238 | [task_group_004.yaml](codex_gpt5_5_xhigh/reports/task_group_004.yaml) |
| `task_group_005` | `SCN_005_erp_finance_expense_control` | `gpt-5.5, xhigh` | `codex` | `no_skill` | 0.3509 | 1760844.800 | 1898498.400 | 15163.600 | 2.023598 | 497.066 | [task_group_005.yaml](codex_gpt5_5_xhigh/reports/task_group_005.yaml) |
| `task_group_005` | `SCN_005_erp_finance_expense_control` | `gpt-5.5, xhigh` | `codex` | `demonstration_skill` | 0.5245 | 812049.067 | 889106.467 | 12293.400 | 1.160114 | 385.155 | [task_group_005.yaml](codex_gpt5_5_xhigh/reports/task_group_005.yaml) |
| `task_group_005` | `SCN_005_erp_finance_expense_control` | `gpt-5.5, xhigh` | `codex` | `reflection_skill` | 0.4651 | 825105.067 | 895917.800 | 11191.133 | 1.102350 | 288.502 | [task_group_005.yaml](codex_gpt5_5_xhigh/reports/task_group_005.yaml) |
| `task_group_006` | `SCN_006_erp_procurement_supplier_receiving` | `gpt-5.5, xhigh` | `codex` | `no_skill` | 0.6628 | 320640.000 | 376502.600 | 8295.133 | 0.688487 | 190.860 | [task_group_006.yaml](codex_gpt5_5_xhigh/reports/task_group_006.yaml) |
| `task_group_006` | `SCN_006_erp_procurement_supplier_receiving` | `gpt-5.5, xhigh` | `codex` | `demonstration_skill` | 0.7239 | 305749.333 | 364423.067 | 8284.600 | 0.694781 | 175.988 | [task_group_006.yaml](codex_gpt5_5_xhigh/reports/task_group_006.yaml) |
| `task_group_006` | `SCN_006_erp_procurement_supplier_receiving` | `gpt-5.5, xhigh` | `codex` | `reflection_skill` | 0.7176 | 278203.733 | 324909.533 | 8116.733 | 0.616133 | 175.478 | [task_group_006.yaml](codex_gpt5_5_xhigh/reports/task_group_006.yaml) |
| `task_group_007` | `SCN_007_erp_inventory_order_fulfillment` | `gpt-5.5, xhigh` | `codex` | `no_skill` | 0.3840 | 1299191.467 | 1371844.467 | 18125.533 | 1.556627 | 607.565 | [task_group_007.yaml](codex_gpt5_5_xhigh/reports/task_group_007.yaml) |
| `task_group_007` | `SCN_007_erp_inventory_order_fulfillment` | `gpt-5.5, xhigh` | `codex` | `demonstration_skill` | 0.5431 | 698982.400 | 774339.933 | 16075.400 | 1.208541 | 433.929 | [task_group_007.yaml](codex_gpt5_5_xhigh/reports/task_group_007.yaml) |
| `task_group_007` | `SCN_007_erp_inventory_order_fulfillment` | `gpt-5.5, xhigh` | `codex` | `reflection_skill` | 0.5449 | 823296.000 | 896349.800 | 16612.867 | 1.275303 | 479.444 | [task_group_007.yaml](codex_gpt5_5_xhigh/reports/task_group_007.yaml) |
| `task_group_008` | `SCN_008_personal_financial_advisory_tax_estate_planning` | `gpt-5.5, xhigh` | `codex` | `no_skill` | 0.7057 | 200797.87 | 232406.40 | 11526.13 | 0.604225 | 370.470 | [task_group_008.yaml](codex_gpt5_5_xhigh/reports/task_group_008.yaml) |
| `task_group_008` | `SCN_008_personal_financial_advisory_tax_estate_planning` | `gpt-5.5, xhigh` | `codex` | `demonstration_skill` | 0.9318 | 175155.20 | 198751.60 | 5718.40 | 0.377112 | 276.730 | [task_group_008.yaml](codex_gpt5_5_xhigh/reports/task_group_008.yaml) |
| `task_group_008` | `SCN_008_personal_financial_advisory_tax_estate_planning` | `gpt-5.5, xhigh` | `codex` | `reflection_skill` | 0.9305 | 236236.80 | 260255.87 | 5045.87 | 0.389590 | 269.070 | [task_group_008.yaml](codex_gpt5_5_xhigh/reports/task_group_008.yaml) |
| `task_group_009` | `SCN_009_finance_operational_modeling_management_reporting` | `gpt-5.5, xhigh` | `codex` | `no_skill` | 0.4276 | 503697.07 | 564793.93 | 12609.80 | 0.935627 | 461.765 | [task_group_009.yaml](codex_gpt5_5_xhigh/reports/task_group_009.yaml) |
| `task_group_009` | `SCN_009_finance_operational_modeling_management_reporting` | `gpt-5.5, xhigh` | `codex` | `demonstration_skill` | 0.9247 | 354030.93 | 400931.47 | 7279.73 | 0.629910 | 322.609 | [task_group_009.yaml](codex_gpt5_5_xhigh/reports/task_group_009.yaml) |
| `task_group_009` | `SCN_009_finance_operational_modeling_management_reporting` | `gpt-5.5, xhigh` | `codex` | `reflection_skill` | 0.8094 | 400674.13 | 448003.67 | 9814.07 | 0.731407 | 369.874 | [task_group_009.yaml](codex_gpt5_5_xhigh/reports/task_group_009.yaml) |
| `task_group_010` | `SCN_010_institutional_investment_strategy_portfolio_risk` | `gpt-5.5, xhigh` | `codex` | `no_skill` | 0.6076 | 481134.93 | 552425.13 | 18894.13 | 1.163842 | 551.903 | [task_group_010.yaml](codex_gpt5_5_xhigh/reports/task_group_010.yaml) |
| `task_group_010` | `SCN_010_institutional_investment_strategy_portfolio_risk` | `gpt-5.5, xhigh` | `codex` | `demonstration_skill` | 0.7105 | 405819.73 | 465838.20 | 14622.53 | 0.941678 | 443.150 | [task_group_010.yaml](codex_gpt5_5_xhigh/reports/task_group_010.yaml) |
| `task_group_010` | `SCN_010_institutional_investment_strategy_portfolio_risk` | `gpt-5.5, xhigh` | `codex` | `reflection_skill` | 0.7377 | 370636.80 | 426022.47 | 15270.93 | 0.920375 | 455.498 | [task_group_010.yaml](codex_gpt5_5_xhigh/reports/task_group_010.yaml) |
| `task_group_011` | `SCN_011_bank_branch_credit_risk_lending_committee` | `gpt-5.5, xhigh` | `codex` | `no_skill` | 0.4568 | 811033.60 | 875385.27 | 21693.27 | 1.378073 | 646.414 | [task_group_011.yaml](codex_gpt5_5_xhigh/reports/task_group_011.yaml) |
| `task_group_011` | `SCN_011_bank_branch_credit_risk_lending_committee` | `gpt-5.5, xhigh` | `codex` | `demonstration_skill` | 0.5648 | 399940.27 | 446151.73 | 16418.00 | 0.923567 | 455.587 | [task_group_011.yaml](codex_gpt5_5_xhigh/reports/task_group_011.yaml) |
| `task_group_011` | `SCN_011_bank_branch_credit_risk_lending_committee` | `gpt-5.5, xhigh` | `codex` | `reflection_skill` | 0.6541 | 411016.53 | 457633.07 | 15867.60 | 0.914619 | 468.705 | [task_group_011.yaml](codex_gpt5_5_xhigh/reports/task_group_011.yaml) |
| `task_group_012` | `SCN_012_erp_hr_employee_lifecycle` | `gpt-5.5, xhigh` | `codex` | `no_skill` | 0.4508 | 336366.933 | 384656.200 | 7550.267 | 0.636138 | 179.588 | [task_group_012.yaml](codex_gpt5_5_xhigh/reports/task_group_012.yaml) |
| `task_group_012` | `SCN_012_erp_hr_employee_lifecycle` | `gpt-5.5, xhigh` | `codex` | `demonstration_skill` | 0.6124 | 342818.133 | 379934.067 | 8172.267 | 0.602157 | 206.310 | [task_group_012.yaml](codex_gpt5_5_xhigh/reports/task_group_012.yaml) |
| `task_group_012` | `SCN_012_erp_hr_employee_lifecycle` | `gpt-5.5, xhigh` | `codex` | `reflection_skill` | 0.7010 | 252330.667 | 296039.467 | 8816.933 | 0.609217 | 202.688 | [task_group_012.yaml](codex_gpt5_5_xhigh/reports/task_group_012.yaml) |
