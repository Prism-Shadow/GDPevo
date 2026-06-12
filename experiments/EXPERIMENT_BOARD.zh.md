# Experiment Board

语言：[English](EXPERIMENT_BOARD.md) | [中文](EXPERIMENT_BOARD.zh.md)

本看板汇总 GDPevo 公开 benchmark 运行的已发布评估结果。当前运行将无状态 `no_skill` baseline 与 `demonstration_skill`、`reflection_skill` 两种 skill-creation 方法进行对比，用于衡量 agent 经验是否能提升后续具有经济价值的业务任务。完整结构化 reports 存放在已发布实验目录下，例如 `codex_gpt5_5_xhigh/reports/`。

在已发布的 Codex GPT-5.5 xhigh 运行中，skill-based evolution 平均带来 18.21 个百分点的准确率提升，并让 token 成本平均下降 25.75%。

效率指标只统计 test solver agent 写答案的过程。计算时先对每个 test task 的 3 次 attempts 取平均，再对 5 个 test tasks 取平均。Skill 生成、环境启动、evaluator 执行和主 agent 汇总不计入这些指标。

看板中的 `avg@3` 以百分比展示，token 指标以 `k` 为单位展示。Cost 仍使用 report YAML 中的原始 token 数计算，并在看板中四舍五入到两位小数展示。

`cost USD avg@3` 是看板层面的派生字段，由 report 中的 token 指标和该运行使用的模型价格计算得到，不存放在正式 report YAML 文件中。

对于已发布的 `gpt-5.5, xhigh` 运行，本看板使用 GPT-5.5 标准 text-token 价格：

| Token 类型 | 价格 |
| --- | ---: |
| Input | $5.00 / 1M tokens |
| Cached input | $0.50 / 1M tokens |
| Output | $30.00 / 1M tokens |

看板层面的 cost 计算公式为：

```text
uncached_input_tokens_avg_3 = input_tokens_avg_3 - cached_input_tokens_avg_3

cost_USD_avg_3 =
  (uncached_input_tokens_avg_3 * 5.00
   + cached_input_tokens_avg_3 * 0.50
   + output_tokens_avg_3 * 30.00) / 1_000_000
```

| task_group_id | scenario_id | model | harness | mode | overall avg@3 (%) | cached tokens avg@3 (k) | input tokens avg@3 (k) | output tokens avg@3 (k) | cost USD avg@3 | seconds avg@3 | report |
| --- | --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| `task_group_001` | `SCN_001_crm_marketing_lead_capture` | `gpt-5.5, xhigh` | `codex` | `no_skill` | 44.43% | 403.2k | 457.0k | 14.2k | 0.90 | 309.779 | [task_group_001.yaml](codex_gpt5_5_xhigh/reports/task_group_001.yaml) |
| `task_group_001` | `SCN_001_crm_marketing_lead_capture` | `gpt-5.5, xhigh` | `codex` | `demonstration_skill` | 48.12% | 366.0k | 412.6k | 13.2k | 0.81 | 282.567 | [task_group_001.yaml](codex_gpt5_5_xhigh/reports/task_group_001.yaml) |
| `task_group_001` | `SCN_001_crm_marketing_lead_capture` | `gpt-5.5, xhigh` | `codex` | `reflection_skill` | 57.46% | 359.0k | 408.4k | 13.3k | 0.82 | 291.846 | [task_group_001.yaml](codex_gpt5_5_xhigh/reports/task_group_001.yaml) |
| `task_group_002` | `SCN_002_crm_b2b_quote_account_response` | `gpt-5.5, xhigh` | `codex` | `no_skill` | 41.62% | 281.3k | 329.8k | 7.7k | 0.62 | 176.821 | [task_group_002.yaml](codex_gpt5_5_xhigh/reports/task_group_002.yaml) |
| `task_group_002` | `SCN_002_crm_b2b_quote_account_response` | `gpt-5.5, xhigh` | `codex` | `demonstration_skill` | 51.17% | 190.9k | 225.5k | 7.1k | 0.48 | 156.808 | [task_group_002.yaml](codex_gpt5_5_xhigh/reports/task_group_002.yaml) |
| `task_group_002` | `SCN_002_crm_b2b_quote_account_response` | `gpt-5.5, xhigh` | `codex` | `reflection_skill` | 60.41% | 168.3k | 200.9k | 6.4k | 0.44 | 159.273 | [task_group_002.yaml](codex_gpt5_5_xhigh/reports/task_group_002.yaml) |
| `task_group_003` | `SCN_003_crm_service_ticket_resolution` | `gpt-5.5, xhigh` | `codex` | `no_skill` | 57.84% | 541.8k | 606.7k | 15.4k | 1.06 | 340.050 | [task_group_003.yaml](codex_gpt5_5_xhigh/reports/task_group_003.yaml) |
| `task_group_003` | `SCN_003_crm_service_ticket_resolution` | `gpt-5.5, xhigh` | `codex` | `demonstration_skill` | 78.11% | 380.2k | 440.2k | 13.1k | 0.88 | 322.110 | [task_group_003.yaml](codex_gpt5_5_xhigh/reports/task_group_003.yaml) |
| `task_group_003` | `SCN_003_crm_service_ticket_resolution` | `gpt-5.5, xhigh` | `codex` | `reflection_skill` | 71.69% | 354.2k | 400.6k | 12.6k | 0.79 | 273.740 | [task_group_003.yaml](codex_gpt5_5_xhigh/reports/task_group_003.yaml) |
| `task_group_004` | `SCN_004_crm_retention_churn_analytics` | `gpt-5.5, xhigh` | `codex` | `no_skill` | 31.73% | 766.4k | 859.9k | 18.5k | 1.40 | 431.142 | [task_group_004.yaml](codex_gpt5_5_xhigh/reports/task_group_004.yaml) |
| `task_group_004` | `SCN_004_crm_retention_churn_analytics` | `gpt-5.5, xhigh` | `codex` | `demonstration_skill` | 60.94% | 532.3k | 595.1k | 15.2k | 1.04 | 444.140 | [task_group_004.yaml](codex_gpt5_5_xhigh/reports/task_group_004.yaml) |
| `task_group_004` | `SCN_004_crm_retention_churn_analytics` | `gpt-5.5, xhigh` | `codex` | `reflection_skill` | 59.95% | 430.0k | 489.3k | 12.5k | 0.89 | 285.238 | [task_group_004.yaml](codex_gpt5_5_xhigh/reports/task_group_004.yaml) |
| `task_group_005` | `SCN_005_erp_finance_expense_control` | `gpt-5.5, xhigh` | `codex` | `no_skill` | 35.09% | 1760.8k | 1898.5k | 15.2k | 2.02 | 497.066 | [task_group_005.yaml](codex_gpt5_5_xhigh/reports/task_group_005.yaml) |
| `task_group_005` | `SCN_005_erp_finance_expense_control` | `gpt-5.5, xhigh` | `codex` | `demonstration_skill` | 52.45% | 812.0k | 889.1k | 12.3k | 1.16 | 385.155 | [task_group_005.yaml](codex_gpt5_5_xhigh/reports/task_group_005.yaml) |
| `task_group_005` | `SCN_005_erp_finance_expense_control` | `gpt-5.5, xhigh` | `codex` | `reflection_skill` | 46.51% | 825.1k | 895.9k | 11.2k | 1.10 | 288.502 | [task_group_005.yaml](codex_gpt5_5_xhigh/reports/task_group_005.yaml) |
| `task_group_006` | `SCN_006_erp_procurement_supplier_receiving` | `gpt-5.5, xhigh` | `codex` | `no_skill` | 66.28% | 320.6k | 376.5k | 8.3k | 0.69 | 190.860 | [task_group_006.yaml](codex_gpt5_5_xhigh/reports/task_group_006.yaml) |
| `task_group_006` | `SCN_006_erp_procurement_supplier_receiving` | `gpt-5.5, xhigh` | `codex` | `demonstration_skill` | 72.39% | 305.7k | 364.4k | 8.3k | 0.69 | 175.988 | [task_group_006.yaml](codex_gpt5_5_xhigh/reports/task_group_006.yaml) |
| `task_group_006` | `SCN_006_erp_procurement_supplier_receiving` | `gpt-5.5, xhigh` | `codex` | `reflection_skill` | 71.76% | 278.2k | 324.9k | 8.1k | 0.62 | 175.478 | [task_group_006.yaml](codex_gpt5_5_xhigh/reports/task_group_006.yaml) |
| `task_group_007` | `SCN_007_erp_inventory_order_fulfillment` | `gpt-5.5, xhigh` | `codex` | `no_skill` | 38.40% | 1299.2k | 1371.8k | 18.1k | 1.56 | 607.565 | [task_group_007.yaml](codex_gpt5_5_xhigh/reports/task_group_007.yaml) |
| `task_group_007` | `SCN_007_erp_inventory_order_fulfillment` | `gpt-5.5, xhigh` | `codex` | `demonstration_skill` | 54.31% | 699.0k | 774.3k | 16.1k | 1.21 | 433.929 | [task_group_007.yaml](codex_gpt5_5_xhigh/reports/task_group_007.yaml) |
| `task_group_007` | `SCN_007_erp_inventory_order_fulfillment` | `gpt-5.5, xhigh` | `codex` | `reflection_skill` | 54.49% | 823.3k | 896.3k | 16.6k | 1.28 | 479.444 | [task_group_007.yaml](codex_gpt5_5_xhigh/reports/task_group_007.yaml) |
| `task_group_008` | `SCN_008_personal_financial_advisory_tax_estate_planning` | `gpt-5.5, xhigh` | `codex` | `no_skill` | 70.57% | 200.8k | 232.4k | 11.5k | 0.60 | 370.470 | [task_group_008.yaml](codex_gpt5_5_xhigh/reports/task_group_008.yaml) |
| `task_group_008` | `SCN_008_personal_financial_advisory_tax_estate_planning` | `gpt-5.5, xhigh` | `codex` | `demonstration_skill` | 93.18% | 175.2k | 198.8k | 5.7k | 0.38 | 276.730 | [task_group_008.yaml](codex_gpt5_5_xhigh/reports/task_group_008.yaml) |
| `task_group_008` | `SCN_008_personal_financial_advisory_tax_estate_planning` | `gpt-5.5, xhigh` | `codex` | `reflection_skill` | 93.05% | 236.2k | 260.3k | 5.0k | 0.39 | 269.070 | [task_group_008.yaml](codex_gpt5_5_xhigh/reports/task_group_008.yaml) |
| `task_group_009` | `SCN_009_finance_operational_modeling_management_reporting` | `gpt-5.5, xhigh` | `codex` | `no_skill` | 42.76% | 503.7k | 564.8k | 12.6k | 0.94 | 461.765 | [task_group_009.yaml](codex_gpt5_5_xhigh/reports/task_group_009.yaml) |
| `task_group_009` | `SCN_009_finance_operational_modeling_management_reporting` | `gpt-5.5, xhigh` | `codex` | `demonstration_skill` | 92.47% | 354.0k | 400.9k | 7.3k | 0.63 | 322.609 | [task_group_009.yaml](codex_gpt5_5_xhigh/reports/task_group_009.yaml) |
| `task_group_009` | `SCN_009_finance_operational_modeling_management_reporting` | `gpt-5.5, xhigh` | `codex` | `reflection_skill` | 80.94% | 400.7k | 448.0k | 9.8k | 0.73 | 369.874 | [task_group_009.yaml](codex_gpt5_5_xhigh/reports/task_group_009.yaml) |
| `task_group_010` | `SCN_010_institutional_investment_strategy_portfolio_risk` | `gpt-5.5, xhigh` | `codex` | `no_skill` | 60.76% | 481.1k | 552.4k | 18.9k | 1.16 | 551.903 | [task_group_010.yaml](codex_gpt5_5_xhigh/reports/task_group_010.yaml) |
| `task_group_010` | `SCN_010_institutional_investment_strategy_portfolio_risk` | `gpt-5.5, xhigh` | `codex` | `demonstration_skill` | 71.05% | 405.8k | 465.8k | 14.6k | 0.94 | 443.150 | [task_group_010.yaml](codex_gpt5_5_xhigh/reports/task_group_010.yaml) |
| `task_group_010` | `SCN_010_institutional_investment_strategy_portfolio_risk` | `gpt-5.5, xhigh` | `codex` | `reflection_skill` | 73.77% | 370.6k | 426.0k | 15.3k | 0.92 | 455.498 | [task_group_010.yaml](codex_gpt5_5_xhigh/reports/task_group_010.yaml) |
| `task_group_011` | `SCN_011_bank_branch_credit_risk_lending_committee` | `gpt-5.5, xhigh` | `codex` | `no_skill` | 45.68% | 811.0k | 875.4k | 21.7k | 1.38 | 646.414 | [task_group_011.yaml](codex_gpt5_5_xhigh/reports/task_group_011.yaml) |
| `task_group_011` | `SCN_011_bank_branch_credit_risk_lending_committee` | `gpt-5.5, xhigh` | `codex` | `demonstration_skill` | 56.48% | 399.9k | 446.2k | 16.4k | 0.92 | 455.587 | [task_group_011.yaml](codex_gpt5_5_xhigh/reports/task_group_011.yaml) |
| `task_group_011` | `SCN_011_bank_branch_credit_risk_lending_committee` | `gpt-5.5, xhigh` | `codex` | `reflection_skill` | 65.41% | 411.0k | 457.6k | 15.9k | 0.91 | 468.705 | [task_group_011.yaml](codex_gpt5_5_xhigh/reports/task_group_011.yaml) |
| `task_group_012` | `SCN_012_erp_hr_employee_lifecycle` | `gpt-5.5, xhigh` | `codex` | `no_skill` | 45.08% | 336.4k | 384.7k | 7.6k | 0.64 | 179.588 | [task_group_012.yaml](codex_gpt5_5_xhigh/reports/task_group_012.yaml) |
| `task_group_012` | `SCN_012_erp_hr_employee_lifecycle` | `gpt-5.5, xhigh` | `codex` | `demonstration_skill` | 61.24% | 342.8k | 379.9k | 8.2k | 0.60 | 206.310 | [task_group_012.yaml](codex_gpt5_5_xhigh/reports/task_group_012.yaml) |
| `task_group_012` | `SCN_012_erp_hr_employee_lifecycle` | `gpt-5.5, xhigh` | `codex` | `reflection_skill` | 70.10% | 252.3k | 296.0k | 8.8k | 0.61 | 202.688 | [task_group_012.yaml](codex_gpt5_5_xhigh/reports/task_group_012.yaml) |
