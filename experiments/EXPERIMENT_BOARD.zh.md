# Experiment Board

语言：[English](EXPERIMENT_BOARD.md) | [中文](EXPERIMENT_BOARD.zh.md)

本看板汇总 GDPevo 公开 benchmark 运行的已发布评估结果。已发布运行将无状态 `base` baseline 与进化模式进行对比。Codex、Claude Code 和 Panofy 运行均报告 `fewshot`、`self` 和 `reflect-3`。完整结构化 reports 存放在已发布实验目录下，例如 `codex_gpt5_5_xhigh/reports/`、`claude_code_opus_4_8_xhigh/reports/`、`panofy_claude_opus_4_6_high/reports/` 和 `claude_code_glm_5_2_max/reports/`。

在已发布的 Codex GPT-5.5 xhigh 运行中，三个 Codex 进化模式平均带来 +12.39 个百分点的准确率提升，token 成本平均变化 -29.05%。

效率指标只统计 test solver agent 写答案的过程。计算时先对每个 test task 的 3 次 attempts 取平均，再对 5 个 test tasks 取平均。Artifact 生成、环境启动、evaluator 执行和主 agent 汇总不计入这些指标。

看板中的 `acc@3` 和 population `std@3` 均以百分比展示，token 指标以 `k` 为单位展示。Cost 仍使用 report YAML 中的原始 token 数计算，并在看板中四舍五入到两位小数展示。

`cost USD avg@3` 是看板层面的派生字段，由 report 中的 token 指标和该运行使用的模型价格计算得到；看板中展示为两位小数。

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

| task_group_id | scenario_id | model | harness | mode | overall acc@3 (%) | overall std@3 (%) | cached tokens avg@3 (k) | input tokens avg@3 (k) | output tokens avg@3 (k) | cost USD avg@3 | report |
| --- | --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| `task_group_001` | `SCN_001_crm_marketing_lead_capture` | `gpt-5.5, xhigh` | `codex` | `base` | 44.43% | 2.63% | 403.2k | 457.0k | 14.2k | 0.90 | [task_group_001.yaml](codex_gpt5_5_xhigh/reports/task_group_001.yaml) |
| `task_group_001` | `SCN_001_crm_marketing_lead_capture` | `gpt-5.5, xhigh` | `codex` | `fewshot` | 48.12% | 7.59% | 366.0k | 412.6k | 13.2k | 0.81 | [task_group_001.yaml](codex_gpt5_5_xhigh/reports/task_group_001.yaml) |
| `task_group_001` | `SCN_001_crm_marketing_lead_capture` | `gpt-5.5, xhigh` | `codex` | `self` | 71.06% | 1.17% | 320.8k | 391.4k | 12.2k | 0.88 | [task_group_001.yaml](codex_gpt5_5_xhigh/reports/task_group_001.yaml) |
| `task_group_001` | `SCN_001_crm_marketing_lead_capture` | `gpt-5.5, xhigh` | `codex` | `reflect-3` | 68.34% | 9.77% | 381.7k | 445.0k | 12.8k | 0.89 | [task_group_001.yaml](codex_gpt5_5_xhigh/reports/task_group_001.yaml) |
| `task_group_002` | `SCN_002_crm_b2b_quote_account_response` | `gpt-5.5, xhigh` | `codex` | `base` | 41.62% | 1.57% | 281.3k | 329.8k | 7.7k | 0.62 | [task_group_002.yaml](codex_gpt5_5_xhigh/reports/task_group_002.yaml) |
| `task_group_002` | `SCN_002_crm_b2b_quote_account_response` | `gpt-5.5, xhigh` | `codex` | `fewshot` | 51.17% | 1.22% | 190.9k | 225.5k | 7.1k | 0.48 | [task_group_002.yaml](codex_gpt5_5_xhigh/reports/task_group_002.yaml) |
| `task_group_002` | `SCN_002_crm_b2b_quote_account_response` | `gpt-5.5, xhigh` | `codex` | `self` | 45.36% | 3.14% | 155.9k | 188.1k | 6.3k | 0.43 | [task_group_002.yaml](codex_gpt5_5_xhigh/reports/task_group_002.yaml) |
| `task_group_002` | `SCN_002_crm_b2b_quote_account_response` | `gpt-5.5, xhigh` | `codex` | `reflect-3` | 44.24% | 5.59% | 160.0k | 203.4k | 7.1k | 0.51 | [task_group_002.yaml](codex_gpt5_5_xhigh/reports/task_group_002.yaml) |
| `task_group_003` | `SCN_003_crm_service_ticket_resolution` | `gpt-5.5, xhigh` | `codex` | `base` | 57.84% | 5.41% | 541.8k | 606.7k | 15.4k | 1.06 | [task_group_003.yaml](codex_gpt5_5_xhigh/reports/task_group_003.yaml) |
| `task_group_003` | `SCN_003_crm_service_ticket_resolution` | `gpt-5.5, xhigh` | `codex` | `fewshot` | 78.11% | 10.15% | 380.2k | 440.2k | 13.1k | 0.88 | [task_group_003.yaml](codex_gpt5_5_xhigh/reports/task_group_003.yaml) |
| `task_group_003` | `SCN_003_crm_service_ticket_resolution` | `gpt-5.5, xhigh` | `codex` | `self` | 62.91% | 12.19% | 455.2k | 537.0k | 14.5k | 1.07 | [task_group_003.yaml](codex_gpt5_5_xhigh/reports/task_group_003.yaml) |
| `task_group_003` | `SCN_003_crm_service_ticket_resolution` | `gpt-5.5, xhigh` | `codex` | `reflect-3` | 57.76% | 11.14% | 564.8k | 639.7k | 15.5k | 1.12 | [task_group_003.yaml](codex_gpt5_5_xhigh/reports/task_group_003.yaml) |
| `task_group_004` | `SCN_004_crm_retention_churn_analytics` | `gpt-5.5, xhigh` | `codex` | `base` | 31.73% | 4.20% | 766.4k | 859.9k | 18.5k | 1.40 | [task_group_004.yaml](codex_gpt5_5_xhigh/reports/task_group_004.yaml) |
| `task_group_004` | `SCN_004_crm_retention_churn_analytics` | `gpt-5.5, xhigh` | `codex` | `fewshot` | 60.94% | 1.18% | 532.3k | 595.1k | 15.2k | 1.04 | [task_group_004.yaml](codex_gpt5_5_xhigh/reports/task_group_004.yaml) |
| `task_group_004` | `SCN_004_crm_retention_churn_analytics` | `gpt-5.5, xhigh` | `codex` | `self` | 25.74% | 8.17% | 364.7k | 427.7k | 10.6k | 0.82 | [task_group_004.yaml](codex_gpt5_5_xhigh/reports/task_group_004.yaml) |
| `task_group_004` | `SCN_004_crm_retention_churn_analytics` | `gpt-5.5, xhigh` | `codex` | `reflect-3` | 25.01% | 6.00% | 575.3k | 652.9k | 12.6k | 1.05 | [task_group_004.yaml](codex_gpt5_5_xhigh/reports/task_group_004.yaml) |
| `task_group_005` | `SCN_005_erp_finance_expense_control` | `gpt-5.5, xhigh` | `codex` | `base` | 35.09% | 11.38% | 1760.8k | 1898.5k | 15.2k | 2.02 | [task_group_005.yaml](codex_gpt5_5_xhigh/reports/task_group_005.yaml) |
| `task_group_005` | `SCN_005_erp_finance_expense_control` | `gpt-5.5, xhigh` | `codex` | `fewshot` | 52.45% | 15.59% | 812.0k | 889.1k | 12.3k | 1.16 | [task_group_005.yaml](codex_gpt5_5_xhigh/reports/task_group_005.yaml) |
| `task_group_005` | `SCN_005_erp_finance_expense_control` | `gpt-5.5, xhigh` | `codex` | `self` | 58.86% | 7.72% | 314.0k | 377.2k | 12.1k | 0.84 | [task_group_005.yaml](codex_gpt5_5_xhigh/reports/task_group_005.yaml) |
| `task_group_005` | `SCN_005_erp_finance_expense_control` | `gpt-5.5, xhigh` | `codex` | `reflect-3` | 59.51% | 9.21% | 327.3k | 408.7k | 13.0k | 0.96 | [task_group_005.yaml](codex_gpt5_5_xhigh/reports/task_group_005.yaml) |
| `task_group_006` | `SCN_006_erp_procurement_supplier_receiving` | `gpt-5.5, xhigh` | `codex` | `base` | 66.28% | 0.79% | 320.6k | 376.5k | 8.3k | 0.69 | [task_group_006.yaml](codex_gpt5_5_xhigh/reports/task_group_006.yaml) |
| `task_group_006` | `SCN_006_erp_procurement_supplier_receiving` | `gpt-5.5, xhigh` | `codex` | `fewshot` | 72.39% | 3.62% | 305.7k | 364.4k | 8.3k | 0.69 | [task_group_006.yaml](codex_gpt5_5_xhigh/reports/task_group_006.yaml) |
| `task_group_006` | `SCN_006_erp_procurement_supplier_receiving` | `gpt-5.5, xhigh` | `codex` | `self` | 70.46% | 4.98% | 233.5k | 294.3k | 13.2k | 0.82 | [task_group_006.yaml](codex_gpt5_5_xhigh/reports/task_group_006.yaml) |
| `task_group_006` | `SCN_006_erp_procurement_supplier_receiving` | `gpt-5.5, xhigh` | `codex` | `reflect-3` | 72.87% | 2.62% | 213.1k | 263.9k | 12.8k | 0.74 | [task_group_006.yaml](codex_gpt5_5_xhigh/reports/task_group_006.yaml) |
| `task_group_007` | `SCN_007_erp_inventory_order_fulfillment` | `gpt-5.5, xhigh` | `codex` | `base` | 38.40% | 2.67% | 1299.2k | 1371.8k | 18.1k | 1.56 | [task_group_007.yaml](codex_gpt5_5_xhigh/reports/task_group_007.yaml) |
| `task_group_007` | `SCN_007_erp_inventory_order_fulfillment` | `gpt-5.5, xhigh` | `codex` | `fewshot` | 54.31% | 5.95% | 699.0k | 774.3k | 16.1k | 1.21 | [task_group_007.yaml](codex_gpt5_5_xhigh/reports/task_group_007.yaml) |
| `task_group_007` | `SCN_007_erp_inventory_order_fulfillment` | `gpt-5.5, xhigh` | `codex` | `self` | 28.48% | 16.35% | 351.4k | 435.7k | 15.1k | 1.05 | [task_group_007.yaml](codex_gpt5_5_xhigh/reports/task_group_007.yaml) |
| `task_group_007` | `SCN_007_erp_inventory_order_fulfillment` | `gpt-5.5, xhigh` | `codex` | `reflect-3` | 43.44% | 9.41% | 437.1k | 513.7k | 15.9k | 1.08 | [task_group_007.yaml](codex_gpt5_5_xhigh/reports/task_group_007.yaml) |
| `task_group_008` | `SCN_008_personal_financial_advisory_tax_estate_planning` | `gpt-5.5, xhigh` | `codex` | `base` | 43.47% | 14.34% | 983.9k | 1155.8k | 18.4k | 1.90 | [task_group_008.yaml](codex_gpt5_5_xhigh/reports/task_group_008.yaml) |
| `task_group_008` | `SCN_008_personal_financial_advisory_tax_estate_planning` | `gpt-5.5, xhigh` | `codex` | `fewshot` | 95.55% | 2.76% | 159.5k | 190.6k | 5.5k | 0.40 | [task_group_008.yaml](codex_gpt5_5_xhigh/reports/task_group_008.yaml) |
| `task_group_008` | `SCN_008_personal_financial_advisory_tax_estate_planning` | `gpt-5.5, xhigh` | `codex` | `self` | 62.44% | 6.88% | 171.8k | 203.4k | 6.4k | 0.44 | [task_group_008.yaml](codex_gpt5_5_xhigh/reports/task_group_008.yaml) |
| `task_group_008` | `SCN_008_personal_financial_advisory_tax_estate_planning` | `gpt-5.5, xhigh` | `codex` | `reflect-3` | 72.68% | 7.01% | 142.6k | 176.6k | 6.9k | 0.45 | [task_group_008.yaml](codex_gpt5_5_xhigh/reports/task_group_008.yaml) |
| `task_group_009` | `SCN_009_finance_operational_modeling_management_reporting` | `gpt-5.5, xhigh` | `codex` | `base` | 41.87% | 7.32% | 378.2k | 453.7k | 11.8k | 0.92 | [task_group_009.yaml](codex_gpt5_5_xhigh/reports/task_group_009.yaml) |
| `task_group_009` | `SCN_009_finance_operational_modeling_management_reporting` | `gpt-5.5, xhigh` | `codex` | `fewshot` | 69.79% | 11.21% | 305.7k | 360.4k | 9.3k | 0.71 | [task_group_009.yaml](codex_gpt5_5_xhigh/reports/task_group_009.yaml) |
| `task_group_009` | `SCN_009_finance_operational_modeling_management_reporting` | `gpt-5.5, xhigh` | `codex` | `self` | 52.30% | 17.25% | 201.0k | 243.0k | 8.0k | 0.55 | [task_group_009.yaml](codex_gpt5_5_xhigh/reports/task_group_009.yaml) |
| `task_group_009` | `SCN_009_finance_operational_modeling_management_reporting` | `gpt-5.5, xhigh` | `codex` | `reflect-3` | 68.33% | 7.92% | 215.4k | 281.2k | 9.8k | 0.73 | [task_group_009.yaml](codex_gpt5_5_xhigh/reports/task_group_009.yaml) |
| `task_group_010` | `SCN_010_institutional_investment_strategy_portfolio_risk` | `gpt-5.5, xhigh` | `codex` | `base` | 63.15% | 10.15% | 349.4k | 436.1k | 14.7k | 1.05 | [task_group_010.yaml](codex_gpt5_5_xhigh/reports/task_group_010.yaml) |
| `task_group_010` | `SCN_010_institutional_investment_strategy_portfolio_risk` | `gpt-5.5, xhigh` | `codex` | `fewshot` | 71.44% | 2.80% | 316.8k | 377.4k | 14.6k | 0.90 | [task_group_010.yaml](codex_gpt5_5_xhigh/reports/task_group_010.yaml) |
| `task_group_010` | `SCN_010_institutional_investment_strategy_portfolio_risk` | `gpt-5.5, xhigh` | `codex` | `self` | 68.99% | 10.37% | 290.2k | 360.7k | 15.5k | 0.96 | [task_group_010.yaml](codex_gpt5_5_xhigh/reports/task_group_010.yaml) |
| `task_group_010` | `SCN_010_institutional_investment_strategy_portfolio_risk` | `gpt-5.5, xhigh` | `codex` | `reflect-3` | 68.77% | 9.33% | 378.5k | 448.3k | 18.3k | 1.09 | [task_group_010.yaml](codex_gpt5_5_xhigh/reports/task_group_010.yaml) |
| `task_group_011` | `SCN_011_bank_branch_credit_risk_lending_committee` | `gpt-5.5, xhigh` | `codex` | `base` | 51.68% | 1.11% | 259.0k | 329.6k | 13.7k | 0.89 | [task_group_011.yaml](codex_gpt5_5_xhigh/reports/task_group_011.yaml) |
| `task_group_011` | `SCN_011_bank_branch_credit_risk_lending_committee` | `gpt-5.5, xhigh` | `codex` | `fewshot` | 63.38% | 3.41% | 219.1k | 274.9k | 12.7k | 0.77 | [task_group_011.yaml](codex_gpt5_5_xhigh/reports/task_group_011.yaml) |
| `task_group_011` | `SCN_011_bank_branch_credit_risk_lending_committee` | `gpt-5.5, xhigh` | `codex` | `self` | 50.23% | 3.70% | 179.7k | 227.3k | 14.1k | 0.75 | [task_group_011.yaml](codex_gpt5_5_xhigh/reports/task_group_011.yaml) |
| `task_group_011` | `SCN_011_bank_branch_credit_risk_lending_committee` | `gpt-5.5, xhigh` | `codex` | `reflect-3` | 47.61% | 3.71% | 207.1k | 248.5k | 15.3k | 0.77 | [task_group_011.yaml](codex_gpt5_5_xhigh/reports/task_group_011.yaml) |
| `task_group_012` | `SCN_012_erp_hr_employee_lifecycle` | `gpt-5.5, xhigh` | `codex` | `base` | 45.08% | 0.00% | 336.4k | 384.7k | 7.6k | 0.64 | [task_group_012.yaml](codex_gpt5_5_xhigh/reports/task_group_012.yaml) |
| `task_group_012` | `SCN_012_erp_hr_employee_lifecycle` | `gpt-5.5, xhigh` | `codex` | `fewshot` | 61.24% | 10.84% | 342.8k | 379.9k | 8.2k | 0.60 | [task_group_012.yaml](codex_gpt5_5_xhigh/reports/task_group_012.yaml) |
| `task_group_012` | `SCN_012_erp_hr_employee_lifecycle` | `gpt-5.5, xhigh` | `codex` | `self` | 63.01% | 12.79% | 262.0k | 308.3k | 9.7k | 0.66 | [task_group_012.yaml](codex_gpt5_5_xhigh/reports/task_group_012.yaml) |
| `task_group_012` | `SCN_012_erp_hr_employee_lifecycle` | `gpt-5.5, xhigh` | `codex` | `reflect-3` | 60.78% | 9.79% | 310.2k | 359.5k | 11.1k | 0.73 | [task_group_012.yaml](codex_gpt5_5_xhigh/reports/task_group_012.yaml) |


---

## Claude Code (Opus 4.8, xhigh)

在已发布的 Claude Code Opus 4.8 xhigh 运行中，三个 Claude Code 进化模式平均带来 +14.55 个百分点的准确率提升，token 成本平均变化 -3.14%。

对于已发布的 `claude-opus-4-8, xhigh` 运行，本看板使用 Claude Opus 4.8 价格：

| Token 类型 | 价格 |
| --- | ---: |
| Input（未缓存） | $5.00 / 1M tokens |
| Cache write（写缓存） | $6.25 / 1M tokens |
| Cache read（读缓存） | $0.50 / 1M tokens |
| Output | $25.00 / 1M tokens |

看板层面的 cost 计算公式为：

```text
cost_USD_avg_3 =
  (input_tokens_avg_3        * 5.00
   + cache_creation_tokens_avg_3 * 6.25
   + cache_read_tokens_avg_3     * 0.50
   + output_tokens_avg_3         * 25.00) / 1_000_000
```

Claude Code 的 token 列是 Anthropic 的四个 usage 桶（未缓存 input、写缓存、读缓存、output）。

| task_group_id | scenario_id | model | harness | mode | overall acc@3 (%) | overall std@3 (%) | input(uncached) tokens avg@3 (k) | cache write tokens avg@3 (k) | cache read tokens avg@3 (k) | output tokens avg@3 (k) | cost USD avg@3 | report |
| --- | --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| `task_group_001` | `SCN_001_crm_marketing_lead_capture` | `claude-opus-4-8, xhigh` | `claude_code` | `base` | 48.75% | 7.28% | 2.8k | 29.4k | 205.0k | 10.0k | 0.55 | [task_group_001.yaml](claude_code_opus_4_8_xhigh/reports/task_group_001.yaml) |
| `task_group_001` | `SCN_001_crm_marketing_lead_capture` | `claude-opus-4-8, xhigh` | `claude_code` | `fewshot` | 81.96% | 9.32% | 2.8k | 28.1k | 138.1k | 5.1k | 0.39 | [task_group_001.yaml](claude_code_opus_4_8_xhigh/reports/task_group_001.yaml) |
| `task_group_001` | `SCN_001_crm_marketing_lead_capture` | `claude-opus-4-8, xhigh` | `claude_code` | `self` | 77.11% | 13.70% | 3.2k | 31.3k | 241.7k | 5.8k | 0.48 | [task_group_001.yaml](claude_code_opus_4_8_xhigh/reports/task_group_001.yaml) |
| `task_group_001` | `SCN_001_crm_marketing_lead_capture` | `claude-opus-4-8, xhigh` | `claude_code` | `reflect-3` | 71.84% | 6.38% | 3.3k | 32.0k | 291.1k | 7.5k | 0.55 | [task_group_001.yaml](claude_code_opus_4_8_xhigh/reports/task_group_001.yaml) |
| `task_group_002` | `SCN_002_crm_b2b_quote_account_response` | `claude-opus-4-8, xhigh` | `claude_code` | `base` | 42.74% | 0.00% | 2.8k | 19.4k | 125.6k | 3.2k | 0.28 | [task_group_002.yaml](claude_code_opus_4_8_xhigh/reports/task_group_002.yaml) |
| `task_group_002` | `SCN_002_crm_b2b_quote_account_response` | `claude-opus-4-8, xhigh` | `claude_code` | `fewshot` | 58.48% | 1.22% | 2.8k | 27.2k | 108.7k | 2.5k | 0.30 | [task_group_002.yaml](claude_code_opus_4_8_xhigh/reports/task_group_002.yaml) |
| `task_group_002` | `SCN_002_crm_b2b_quote_account_response` | `claude-opus-4-8, xhigh` | `claude_code` | `self` | 49.84% | 7.68% | 2.9k | 22.1k | 142.8k | 3.1k | 0.30 | [task_group_002.yaml](claude_code_opus_4_8_xhigh/reports/task_group_002.yaml) |
| `task_group_002` | `SCN_002_crm_b2b_quote_account_response` | `claude-opus-4-8, xhigh` | `claude_code` | `reflect-3` | 58.79% | 1.43% | 2.9k | 20.8k | 127.5k | 2.7k | 0.28 | [task_group_002.yaml](claude_code_opus_4_8_xhigh/reports/task_group_002.yaml) |
| `task_group_003` | `SCN_003_crm_service_ticket_resolution` | `claude-opus-4-8, xhigh` | `claude_code` | `base` | 46.69% | 2.05% | 2.8k | 45.7k | 638.2k | 12.3k | 0.93 | [task_group_003.yaml](claude_code_opus_4_8_xhigh/reports/task_group_003.yaml) |
| `task_group_003` | `SCN_003_crm_service_ticket_resolution` | `claude-opus-4-8, xhigh` | `claude_code` | `fewshot` | 70.89% | 9.52% | 2.8k | 38.7k | 375.7k | 6.4k | 0.60 | [task_group_003.yaml](claude_code_opus_4_8_xhigh/reports/task_group_003.yaml) |
| `task_group_003` | `SCN_003_crm_service_ticket_resolution` | `claude-opus-4-8, xhigh` | `claude_code` | `self` | 57.21% | 7.92% | 3.7k | 45.7k | 618.7k | 10.9k | 0.89 | [task_group_003.yaml](claude_code_opus_4_8_xhigh/reports/task_group_003.yaml) |
| `task_group_003` | `SCN_003_crm_service_ticket_resolution` | `claude-opus-4-8, xhigh` | `claude_code` | `reflect-3` | 56.48% | 11.79% | 3.6k | 43.9k | 552.1k | 10.6k | 0.83 | [task_group_003.yaml](claude_code_opus_4_8_xhigh/reports/task_group_003.yaml) |
| `task_group_004` | `SCN_004_crm_retention_churn_analytics` | `claude-opus-4-8, xhigh` | `claude_code` | `base` | 25.24% | 5.65% | 2.8k | 40.1k | 611.2k | 13.5k | 0.91 | [task_group_004.yaml](claude_code_opus_4_8_xhigh/reports/task_group_004.yaml) |
| `task_group_004` | `SCN_004_crm_retention_churn_analytics` | `claude-opus-4-8, xhigh` | `claude_code` | `fewshot` | 54.55% | 3.98% | 2.8k | 34.4k | 366.6k | 8.7k | 0.63 | [task_group_004.yaml](claude_code_opus_4_8_xhigh/reports/task_group_004.yaml) |
| `task_group_004` | `SCN_004_crm_retention_churn_analytics` | `claude-opus-4-8, xhigh` | `claude_code` | `self` | 38.35% | 10.57% | 2.9k | 39.2k | 557.8k | 8.4k | 0.75 | [task_group_004.yaml](claude_code_opus_4_8_xhigh/reports/task_group_004.yaml) |
| `task_group_004` | `SCN_004_crm_retention_churn_analytics` | `claude-opus-4-8, xhigh` | `claude_code` | `reflect-3` | 45.50% | 5.52% | 2.7k | 41.4k | 501.2k | 8.2k | 0.73 | [task_group_004.yaml](claude_code_opus_4_8_xhigh/reports/task_group_004.yaml) |
| `task_group_005` | `SCN_005_erp_finance_expense_control` | `claude-opus-4-8, xhigh` | `claude_code` | `base` | 51.15% | 6.37% | 2.8k | 34.3k | 386.8k | 10.1k | 0.67 | [task_group_005.yaml](claude_code_opus_4_8_xhigh/reports/task_group_005.yaml) |
| `task_group_005` | `SCN_005_erp_finance_expense_control` | `claude-opus-4-8, xhigh` | `claude_code` | `fewshot` | 57.96% | 17.30% | 2.8k | 30.2k | 246.4k | 7.3k | 0.51 | [task_group_005.yaml](claude_code_opus_4_8_xhigh/reports/task_group_005.yaml) |
| `task_group_005` | `SCN_005_erp_finance_expense_control` | `claude-opus-4-8, xhigh` | `claude_code` | `self` | 45.35% | 6.66% | 3.6k | 38.6k | 461.1k | 10.1k | 0.74 | [task_group_005.yaml](claude_code_opus_4_8_xhigh/reports/task_group_005.yaml) |
| `task_group_005` | `SCN_005_erp_finance_expense_control` | `claude-opus-4-8, xhigh` | `claude_code` | `reflect-3` | 58.97% | 12.80% | 3.8k | 33.8k | 396.1k | 8.6k | 0.64 | [task_group_005.yaml](claude_code_opus_4_8_xhigh/reports/task_group_005.yaml) |
| `task_group_006` | `SCN_006_erp_procurement_supplier_receiving` | `claude-opus-4-8, xhigh` | `claude_code` | `base` | 67.98% | 2.49% | 2.8k | 28.6k | 284.6k | 9.3k | 0.57 | [task_group_006.yaml](claude_code_opus_4_8_xhigh/reports/task_group_006.yaml) |
| `task_group_006` | `SCN_006_erp_procurement_supplier_receiving` | `claude-opus-4-8, xhigh` | `claude_code` | `fewshot` | 72.98% | 1.31% | 2.8k | 38.6k | 356.5k | 8.7k | 0.65 | [task_group_006.yaml](claude_code_opus_4_8_xhigh/reports/task_group_006.yaml) |
| `task_group_006` | `SCN_006_erp_procurement_supplier_receiving` | `claude-opus-4-8, xhigh` | `claude_code` | `self` | 74.72% | 0.00% | 3.4k | 32.0k | 355.6k | 7.9k | 0.59 | [task_group_006.yaml](claude_code_opus_4_8_xhigh/reports/task_group_006.yaml) |
| `task_group_006` | `SCN_006_erp_procurement_supplier_receiving` | `claude-opus-4-8, xhigh` | `claude_code` | `reflect-3` | 73.52% | 5.89% | 3.7k | 32.6k | 346.5k | 8.2k | 0.60 | [task_group_006.yaml](claude_code_opus_4_8_xhigh/reports/task_group_006.yaml) |
| `task_group_007` | `SCN_007_erp_inventory_order_fulfillment` | `claude-opus-4-8, xhigh` | `claude_code` | `base` | 39.54% | 2.23% | 2.8k | 35.7k | 337.8k | 10.1k | 0.66 | [task_group_007.yaml](claude_code_opus_4_8_xhigh/reports/task_group_007.yaml) |
| `task_group_007` | `SCN_007_erp_inventory_order_fulfillment` | `claude-opus-4-8, xhigh` | `claude_code` | `fewshot` | 55.76% | 6.25% | 2.8k | 43.3k | 356.0k | 8.6k | 0.68 | [task_group_007.yaml](claude_code_opus_4_8_xhigh/reports/task_group_007.yaml) |
| `task_group_007` | `SCN_007_erp_inventory_order_fulfillment` | `claude-opus-4-8, xhigh` | `claude_code` | `self` | 37.38% | 5.32% | 3.5k | 44.0k | 524.2k | 9.2k | 0.79 | [task_group_007.yaml](claude_code_opus_4_8_xhigh/reports/task_group_007.yaml) |
| `task_group_007` | `SCN_007_erp_inventory_order_fulfillment` | `claude-opus-4-8, xhigh` | `claude_code` | `reflect-3` | 51.45% | 7.75% | 3.6k | 39.5k | 547.0k | 8.9k | 0.76 | [task_group_007.yaml](claude_code_opus_4_8_xhigh/reports/task_group_007.yaml) |
| `task_group_008` | `SCN_008_personal_financial_advisory_tax_estate_planning` | `claude-opus-4-8, xhigh` | `claude_code` | `base` | 66.89% | 5.58% | 2.8k | 13.8k | 106.2k | 5.3k | 0.29 | [task_group_008.yaml](claude_code_opus_4_8_xhigh/reports/task_group_008.yaml) |
| `task_group_008` | `SCN_008_personal_financial_advisory_tax_estate_planning` | `claude-opus-4-8, xhigh` | `claude_code` | `fewshot` | 93.60% | 2.76% | 2.8k | 32.0k | 241.7k | 3.6k | 0.43 | [task_group_008.yaml](claude_code_opus_4_8_xhigh/reports/task_group_008.yaml) |
| `task_group_008` | `SCN_008_personal_financial_advisory_tax_estate_planning` | `claude-opus-4-8, xhigh` | `claude_code` | `self` | 68.93% | 10.77% | 3.1k | 21.8k | 115.7k | 2.6k | 0.27 | [task_group_008.yaml](claude_code_opus_4_8_xhigh/reports/task_group_008.yaml) |
| `task_group_008` | `SCN_008_personal_financial_advisory_tax_estate_planning` | `claude-opus-4-8, xhigh` | `claude_code` | `reflect-3` | 78.58% | 4.42% | 3.1k | 20.9k | 136.8k | 3.5k | 0.30 | [task_group_008.yaml](claude_code_opus_4_8_xhigh/reports/task_group_008.yaml) |
| `task_group_009` | `SCN_009_finance_operational_modeling_management_reporting` | `claude-opus-4-8, xhigh` | `claude_code` | `base` | 51.76% | 11.95% | 2.8k | 25.4k | 162.7k | 4.9k | 0.38 | [task_group_009.yaml](claude_code_opus_4_8_xhigh/reports/task_group_009.yaml) |
| `task_group_009` | `SCN_009_finance_operational_modeling_management_reporting` | `claude-opus-4-8, xhigh` | `claude_code` | `fewshot` | 100.00% | 0.00% | 2.8k | 29.3k | 205.2k | 3.8k | 0.39 | [task_group_009.yaml](claude_code_opus_4_8_xhigh/reports/task_group_009.yaml) |
| `task_group_009` | `SCN_009_finance_operational_modeling_management_reporting` | `claude-opus-4-8, xhigh` | `claude_code` | `self` | 58.07% | 2.37% | 3.8k | 26.6k | 257.6k | 4.6k | 0.43 | [task_group_009.yaml](claude_code_opus_4_8_xhigh/reports/task_group_009.yaml) |
| `task_group_009` | `SCN_009_finance_operational_modeling_management_reporting` | `claude-opus-4-8, xhigh` | `claude_code` | `reflect-3` | 76.68% | 4.42% | 3.2k | 24.8k | 253.2k | 5.0k | 0.42 | [task_group_009.yaml](claude_code_opus_4_8_xhigh/reports/task_group_009.yaml) |
| `task_group_010` | `SCN_010_institutional_investment_strategy_portfolio_risk` | `claude-opus-4-8, xhigh` | `claude_code` | `base` | 58.60% | 9.86% | 2.8k | 41.8k | 445.6k | 10.9k | 0.77 | [task_group_010.yaml](claude_code_opus_4_8_xhigh/reports/task_group_010.yaml) |
| `task_group_010` | `SCN_010_institutional_investment_strategy_portfolio_risk` | `claude-opus-4-8, xhigh` | `claude_code` | `fewshot` | 63.45% | 10.44% | 2.8k | 46.7k | 500.8k | 10.5k | 0.82 | [task_group_010.yaml](claude_code_opus_4_8_xhigh/reports/task_group_010.yaml) |
| `task_group_010` | `SCN_010_institutional_investment_strategy_portfolio_risk` | `claude-opus-4-8, xhigh` | `claude_code` | `self` | 60.67% | 7.32% | 3.6k | 50.9k | 690.1k | 11.2k | 0.96 | [task_group_010.yaml](claude_code_opus_4_8_xhigh/reports/task_group_010.yaml) |
| `task_group_010` | `SCN_010_institutional_investment_strategy_portfolio_risk` | `claude-opus-4-8, xhigh` | `claude_code` | `reflect-3` | 58.16% | 8.93% | 3.6k | 49.1k | 699.6k | 12.3k | 0.98 | [task_group_010.yaml](claude_code_opus_4_8_xhigh/reports/task_group_010.yaml) |
| `task_group_011` | `SCN_011_bank_branch_credit_risk_lending_committee` | `claude-opus-4-8, xhigh` | `claude_code` | `base` | 41.56% | 4.83% | 2.8k | 45.3k | 703.5k | 15.5k | 1.04 | [task_group_011.yaml](claude_code_opus_4_8_xhigh/reports/task_group_011.yaml) |
| `task_group_011` | `SCN_011_bank_branch_credit_risk_lending_committee` | `claude-opus-4-8, xhigh` | `claude_code` | `fewshot` | 63.48% | 8.06% | 2.8k | 50.2k | 586.2k | 9.6k | 0.86 | [task_group_011.yaml](claude_code_opus_4_8_xhigh/reports/task_group_011.yaml) |
| `task_group_011` | `SCN_011_bank_branch_credit_risk_lending_committee` | `claude-opus-4-8, xhigh` | `claude_code` | `self` | 47.32% | 6.55% | 3.5k | 41.8k | 539.6k | 11.2k | 0.83 | [task_group_011.yaml](claude_code_opus_4_8_xhigh/reports/task_group_011.yaml) |
| `task_group_011` | `SCN_011_bank_branch_credit_risk_lending_committee` | `claude-opus-4-8, xhigh` | `claude_code` | `reflect-3` | 48.03% | 7.12% | 3.6k | 41.8k | 649.6k | 9.6k | 0.84 | [task_group_011.yaml](claude_code_opus_4_8_xhigh/reports/task_group_011.yaml) |
| `task_group_012` | `SCN_012_erp_hr_employee_lifecycle` | `claude-opus-4-8, xhigh` | `claude_code` | `base` | 48.41% | 4.71% | 2.8k | 17.6k | 103.3k | 3.0k | 0.25 | [task_group_012.yaml](claude_code_opus_4_8_xhigh/reports/task_group_012.yaml) |
| `task_group_012` | `SCN_012_erp_hr_employee_lifecycle` | `claude-opus-4-8, xhigh` | `claude_code` | `fewshot` | 77.66% | 6.37% | 2.8k | 25.2k | 149.8k | 3.0k | 0.32 | [task_group_012.yaml](claude_code_opus_4_8_xhigh/reports/task_group_012.yaml) |
| `task_group_012` | `SCN_012_erp_hr_employee_lifecycle` | `claude-opus-4-8, xhigh` | `claude_code` | `self` | 73.48% | 2.62% | 3.1k | 21.1k | 158.2k | 2.9k | 0.30 | [task_group_012.yaml](claude_code_opus_4_8_xhigh/reports/task_group_012.yaml) |
| `task_group_012` | `SCN_012_erp_hr_employee_lifecycle` | `claude-opus-4-8, xhigh` | `claude_code` | `reflect-3` | 74.70% | 3.75% | 3.1k | 21.1k | 170.1k | 3.2k | 0.31 | [task_group_012.yaml](claude_code_opus_4_8_xhigh/reports/task_group_012.yaml) |

---

## Panofy (Claude Opus 4.6, high)

在已发布的 Panofy Claude Opus 4.6 high 运行中，三个已报告的进化模式在 12 个 task group 上平均带来 +12.82 个百分点 的准确率提升，token 成本平均变化 +1.42%。其中 `fewshot`、`self` 和 `reflect-3` 的准确率提升分别为 +21.07 个百分点、+7.99 个百分点 和 +9.41 个百分点。

对于已发布的 `claude-opus-4-6, high` 运行，本看板使用 Claude Opus 4.6 价格，并按 Panofy 暴露的三类 token 桶计算：

| Token 类型 | 价格 |
| --- | ---: |
| 5m Cache Writes | $6.25 / 1M tokens |
| Cache Hits | $0.50 / 1M tokens |
| Output Tokens | $25.00 / 1M tokens |

看板层面和 report 层面的 cost 计算公式为：

```text
cost_USD_avg_3 =
  (cache_write_tokens_avg_3 * 6.25
   + cache_read_tokens_avg_3  * 0.50
   + output_tokens_avg_3      * 25.00) / 1_000_000
```

Panofy 的 token 列是 harness 返回的三个 Anthropic usage 桶：5 分钟 cache write、cache hit 和 output tokens。

| task_group_id | scenario_id | model | harness | mode | overall acc@3 (%) | overall std@3 (%) | 5m cache write tokens avg@3 (k) | cache hit tokens avg@3 (k) | output tokens avg@3 (k) | cost USD avg@3 | report |
| --- | --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| `task_group_001` | `SCN_001_crm_marketing_lead_capture` | `claude-opus-4-6, high` | `panofy` | `base` | 63.93% | 15.55% | 36.6k | 199.9k | 13.9k | 0.68 | [task_group_001.yaml](panofy_claude_opus_4_6_high/reports/task_group_001.yaml) |
| `task_group_001` | `SCN_001_crm_marketing_lead_capture` | `claude-opus-4-6, high` | `panofy` | `fewshot` | 90.12% | 3.20% | 33.6k | 209.4k | 12.6k | 0.63 | [task_group_001.yaml](panofy_claude_opus_4_6_high/reports/task_group_001.yaml) |
| `task_group_001` | `SCN_001_crm_marketing_lead_capture` | `claude-opus-4-6, high` | `panofy` | `self` | 76.98% | 6.58% | 30.7k | 250.2k | 11.0k | 0.59 | [task_group_001.yaml](panofy_claude_opus_4_6_high/reports/task_group_001.yaml) |
| `task_group_001` | `SCN_001_crm_marketing_lead_capture` | `claude-opus-4-6, high` | `panofy` | `reflect-3` | 76.59% | 5.08% | 32.2k | 210.1k | 13.3k | 0.64 | [task_group_001.yaml](panofy_claude_opus_4_6_high/reports/task_group_001.yaml) |
| `task_group_002` | `SCN_002_crm_b2b_quote_account_response` | `claude-opus-4-6, high` | `panofy` | `base` | 43.55% | 2.86% | 19.3k | 125.2k | 5.8k | 0.33 | [task_group_002.yaml](panofy_claude_opus_4_6_high/reports/task_group_002.yaml) |
| `task_group_002` | `SCN_002_crm_b2b_quote_account_response` | `claude-opus-4-6, high` | `panofy` | `fewshot` | 60.03% | 5.89% | 21.9k | 210.9k | 6.7k | 0.41 | [task_group_002.yaml](panofy_claude_opus_4_6_high/reports/task_group_002.yaml) |
| `task_group_002` | `SCN_002_crm_b2b_quote_account_response` | `claude-opus-4-6, high` | `panofy` | `self` | 48.72% | 2.73% | 23.5k | 243.8k | 7.4k | 0.46 | [task_group_002.yaml](panofy_claude_opus_4_6_high/reports/task_group_002.yaml) |
| `task_group_002` | `SCN_002_crm_b2b_quote_account_response` | `claude-opus-4-6, high` | `panofy` | `reflect-3` | 51.08% | 6.09% | 24.4k | 239.4k | 8.0k | 0.47 | [task_group_002.yaml](panofy_claude_opus_4_6_high/reports/task_group_002.yaml) |
| `task_group_003` | `SCN_003_crm_service_ticket_resolution` | `claude-opus-4-6, high` | `panofy` | `base` | 55.16% | 6.63% | 42.3k | 348.1k | 13.8k | 0.78 | [task_group_003.yaml](panofy_claude_opus_4_6_high/reports/task_group_003.yaml) |
| `task_group_003` | `SCN_003_crm_service_ticket_resolution` | `claude-opus-4-6, high` | `panofy` | `fewshot` | 72.33% | 5.41% | 44.9k | 478.5k | 13.2k | 0.85 | [task_group_003.yaml](panofy_claude_opus_4_6_high/reports/task_group_003.yaml) |
| `task_group_003` | `SCN_003_crm_service_ticket_resolution` | `claude-opus-4-6, high` | `panofy` | `self` | 55.71% | 9.50% | 41.3k | 417.2k | 11.8k | 0.76 | [task_group_003.yaml](panofy_claude_opus_4_6_high/reports/task_group_003.yaml) |
| `task_group_003` | `SCN_003_crm_service_ticket_resolution` | `claude-opus-4-6, high` | `panofy` | `reflect-3` | 47.47% | 8.39% | 39.9k | 495.9k | 12.8k | 0.82 | [task_group_003.yaml](panofy_claude_opus_4_6_high/reports/task_group_003.yaml) |
| `task_group_004` | `SCN_004_crm_retention_churn_analytics` | `claude-opus-4-6, high` | `panofy` | `base` | 16.00% | 3.95% | 36.7k | 262.4k | 13.6k | 0.70 | [task_group_004.yaml](panofy_claude_opus_4_6_high/reports/task_group_004.yaml) |
| `task_group_004` | `SCN_004_crm_retention_churn_analytics` | `claude-opus-4-6, high` | `panofy` | `fewshot` | 57.95% | 7.17% | 59.0k | 466.1k | 24.3k | 1.21 | [task_group_004.yaml](panofy_claude_opus_4_6_high/reports/task_group_004.yaml) |
| `task_group_004` | `SCN_004_crm_retention_churn_analytics` | `claude-opus-4-6, high` | `panofy` | `self` | 19.24% | 2.22% | 45.0k | 410.1k | 18.1k | 0.94 | [task_group_004.yaml](panofy_claude_opus_4_6_high/reports/task_group_004.yaml) |
| `task_group_004` | `SCN_004_crm_retention_churn_analytics` | `claude-opus-4-6, high` | `panofy` | `reflect-3` | 30.95% | 12.98% | 43.8k | 402.8k | 17.4k | 0.91 | [task_group_004.yaml](panofy_claude_opus_4_6_high/reports/task_group_004.yaml) |
| `task_group_005` | `SCN_005_erp_finance_expense_control` | `claude-opus-4-6, high` | `panofy` | `base` | 47.84% | 14.63% | 38.0k | 278.8k | 18.5k | 0.84 | [task_group_005.yaml](panofy_claude_opus_4_6_high/reports/task_group_005.yaml) |
| `task_group_005` | `SCN_005_erp_finance_expense_control` | `claude-opus-4-6, high` | `panofy` | `fewshot` | 58.40% | 11.91% | 38.8k | 294.9k | 16.2k | 0.79 | [task_group_005.yaml](panofy_claude_opus_4_6_high/reports/task_group_005.yaml) |
| `task_group_005` | `SCN_005_erp_finance_expense_control` | `claude-opus-4-6, high` | `panofy` | `self` | 46.18% | 14.23% | 40.1k | 278.5k | 17.8k | 0.84 | [task_group_005.yaml](panofy_claude_opus_4_6_high/reports/task_group_005.yaml) |
| `task_group_005` | `SCN_005_erp_finance_expense_control` | `claude-opus-4-6, high` | `panofy` | `reflect-3` | 44.23% | 13.40% | 44.4k | 552.1k | 19.0k | 1.03 | [task_group_005.yaml](panofy_claude_opus_4_6_high/reports/task_group_005.yaml) |
| `task_group_006` | `SCN_006_erp_procurement_supplier_receiving` | `claude-opus-4-6, high` | `panofy` | `base` | 68.91% | 2.17% | 30.9k | 218.7k | 12.1k | 0.60 | [task_group_006.yaml](panofy_claude_opus_4_6_high/reports/task_group_006.yaml) |
| `task_group_006` | `SCN_006_erp_procurement_supplier_receiving` | `claude-opus-4-6, high` | `panofy` | `fewshot` | 67.05% | 3.93% | 58.9k | 434.7k | 16.1k | 0.99 | [task_group_006.yaml](panofy_claude_opus_4_6_high/reports/task_group_006.yaml) |
| `task_group_006` | `SCN_006_erp_procurement_supplier_receiving` | `claude-opus-4-6, high` | `panofy` | `self` | 70.76% | 3.65% | 34.1k | 245.9k | 11.9k | 0.63 | [task_group_006.yaml](panofy_claude_opus_4_6_high/reports/task_group_006.yaml) |
| `task_group_006` | `SCN_006_erp_procurement_supplier_receiving` | `claude-opus-4-6, high` | `panofy` | `reflect-3` | 71.31% | 4.88% | 51.8k | 424.0k | 15.1k | 0.91 | [task_group_006.yaml](panofy_claude_opus_4_6_high/reports/task_group_006.yaml) |
| `task_group_007` | `SCN_007_erp_inventory_order_fulfillment` | `claude-opus-4-6, high` | `panofy` | `base` | 35.56% | 2.36% | 51.0k | 373.3k | 18.9k | 0.98 | [task_group_007.yaml](panofy_claude_opus_4_6_high/reports/task_group_007.yaml) |
| `task_group_007` | `SCN_007_erp_inventory_order_fulfillment` | `claude-opus-4-6, high` | `panofy` | `fewshot` | 56.18% | 7.54% | 58.9k | 479.8k | 22.0k | 1.16 | [task_group_007.yaml](panofy_claude_opus_4_6_high/reports/task_group_007.yaml) |
| `task_group_007` | `SCN_007_erp_inventory_order_fulfillment` | `claude-opus-4-6, high` | `panofy` | `self` | 42.59% | 6.46% | 57.0k | 431.7k | 19.2k | 1.05 | [task_group_007.yaml](panofy_claude_opus_4_6_high/reports/task_group_007.yaml) |
| `task_group_007` | `SCN_007_erp_inventory_order_fulfillment` | `claude-opus-4-6, high` | `panofy` | `reflect-3` | 43.94% | 11.66% | 58.4k | 470.2k | 21.0k | 1.13 | [task_group_007.yaml](panofy_claude_opus_4_6_high/reports/task_group_007.yaml) |
| `task_group_008` | `SCN_008_personal_financial_advisory_tax_estate_planning` | `claude-opus-4-6, high` | `panofy` | `base` | 63.12% | 8.97% | 21.8k | 133.7k | 9.0k | 0.43 | [task_group_008.yaml](panofy_claude_opus_4_6_high/reports/task_group_008.yaml) |
| `task_group_008` | `SCN_008_personal_financial_advisory_tax_estate_planning` | `claude-opus-4-6, high` | `panofy` | `fewshot` | 90.94% | 0.99% | 18.3k | 174.6k | 5.7k | 0.34 | [task_group_008.yaml](panofy_claude_opus_4_6_high/reports/task_group_008.yaml) |
| `task_group_008` | `SCN_008_personal_financial_advisory_tax_estate_planning` | `claude-opus-4-6, high` | `panofy` | `self` | 65.34% | 6.49% | 11.5k | 139.9k | 4.2k | 0.25 | [task_group_008.yaml](panofy_claude_opus_4_6_high/reports/task_group_008.yaml) |
| `task_group_008` | `SCN_008_personal_financial_advisory_tax_estate_planning` | `claude-opus-4-6, high` | `panofy` | `reflect-3` | 71.54% | 4.91% | 16.5k | 169.3k | 5.9k | 0.33 | [task_group_008.yaml](panofy_claude_opus_4_6_high/reports/task_group_008.yaml) |
| `task_group_009` | `SCN_009_finance_operational_modeling_management_reporting` | `claude-opus-4-6, high` | `panofy` | `base` | 60.78% | 14.12% | 28.6k | 163.8k | 11.8k | 0.56 | [task_group_009.yaml](panofy_claude_opus_4_6_high/reports/task_group_009.yaml) |
| `task_group_009` | `SCN_009_finance_operational_modeling_management_reporting` | `claude-opus-4-6, high` | `panofy` | `fewshot` | 90.90% | 1.11% | 27.2k | 188.0k | 10.0k | 0.51 | [task_group_009.yaml](panofy_claude_opus_4_6_high/reports/task_group_009.yaml) |
| `task_group_009` | `SCN_009_finance_operational_modeling_management_reporting` | `claude-opus-4-6, high` | `panofy` | `self` | 73.22% | 2.20% | 26.0k | 193.1k | 9.1k | 0.49 | [task_group_009.yaml](panofy_claude_opus_4_6_high/reports/task_group_009.yaml) |
| `task_group_009` | `SCN_009_finance_operational_modeling_management_reporting` | `claude-opus-4-6, high` | `panofy` | `reflect-3` | 76.78% | 0.94% | 33.3k | 237.3k | 12.6k | 0.64 | [task_group_009.yaml](panofy_claude_opus_4_6_high/reports/task_group_009.yaml) |
| `task_group_010` | `SCN_010_institutional_investment_strategy_portfolio_risk` | `claude-opus-4-6, high` | `panofy` | `base` | 53.11% | 5.60% | 47.1k | 272.2k | 16.3k | 0.84 | [task_group_010.yaml](panofy_claude_opus_4_6_high/reports/task_group_010.yaml) |
| `task_group_010` | `SCN_010_institutional_investment_strategy_portfolio_risk` | `claude-opus-4-6, high` | `panofy` | `fewshot` | 70.29% | 4.60% | 52.7k | 355.5k | 19.3k | 0.99 | [task_group_010.yaml](panofy_claude_opus_4_6_high/reports/task_group_010.yaml) |
| `task_group_010` | `SCN_010_institutional_investment_strategy_portfolio_risk` | `claude-opus-4-6, high` | `panofy` | `self` | 72.01% | 5.25% | 58.8k | 330.7k | 20.5k | 1.04 | [task_group_010.yaml](panofy_claude_opus_4_6_high/reports/task_group_010.yaml) |
| `task_group_010` | `SCN_010_institutional_investment_strategy_portfolio_risk` | `claude-opus-4-6, high` | `panofy` | `reflect-3` | 69.78% | 6.94% | 53.5k | 356.9k | 18.1k | 0.97 | [task_group_010.yaml](panofy_claude_opus_4_6_high/reports/task_group_010.yaml) |
| `task_group_011` | `SCN_011_bank_branch_credit_risk_lending_committee` | `claude-opus-4-6, high` | `panofy` | `base` | 49.55% | 7.05% | 73.8k | 1310.3k | 29.6k | 1.86 | [task_group_011.yaml](panofy_claude_opus_4_6_high/reports/task_group_011.yaml) |
| `task_group_011` | `SCN_011_bank_branch_credit_risk_lending_committee` | `claude-opus-4-6, high` | `panofy` | `fewshot` | 55.86% | 6.34% | 85.4k | 503.9k | 34.9k | 1.66 | [task_group_011.yaml](panofy_claude_opus_4_6_high/reports/task_group_011.yaml) |
| `task_group_011` | `SCN_011_bank_branch_credit_risk_lending_committee` | `claude-opus-4-6, high` | `panofy` | `self` | 45.01% | 3.23% | 63.1k | 415.9k | 24.1k | 1.20 | [task_group_011.yaml](panofy_claude_opus_4_6_high/reports/task_group_011.yaml) |
| `task_group_011` | `SCN_011_bank_branch_credit_risk_lending_committee` | `claude-opus-4-6, high` | `panofy` | `reflect-3` | 50.89% | 7.14% | 56.3k | 413.7k | 21.9k | 1.11 | [task_group_011.yaml](panofy_claude_opus_4_6_high/reports/task_group_011.yaml) |
| `task_group_012` | `SCN_012_erp_hr_employee_lifecycle` | `claude-opus-4-6, high` | `panofy` | `base` | 47.30% | 0.00% | 25.5k | 243.7k | 6.4k | 0.44 | [task_group_012.yaml](panofy_claude_opus_4_6_high/reports/task_group_012.yaml) |
| `task_group_012` | `SCN_012_erp_hr_employee_lifecycle` | `claude-opus-4-6, high` | `panofy` | `fewshot` | 87.58% | 1.05% | 11.7k | 134.7k | 3.5k | 0.23 | [task_group_012.yaml](panofy_claude_opus_4_6_high/reports/task_group_012.yaml) |
| `task_group_012` | `SCN_012_erp_hr_employee_lifecycle` | `claude-opus-4-6, high` | `panofy` | `self` | 84.91% | 6.35% | 10.8k | 144.1k | 3.6k | 0.23 | [task_group_012.yaml](panofy_claude_opus_4_6_high/reports/task_group_012.yaml) |
| `task_group_012` | `SCN_012_erp_hr_employee_lifecycle` | `claude-opus-4-6, high` | `panofy` | `reflect-3` | 83.23% | 5.31% | 13.3k | 128.9k | 4.2k | 0.25 | [task_group_012.yaml](panofy_claude_opus_4_6_high/reports/task_group_012.yaml) |

---

## Claude Code (GLM-5.2, max)

在已发布的 Claude Code GLM-5.2 max 运行中，三个进化模式在 12 个 task group 上平均带来 +15.21 个百分点的准确率提升，token 成本平均变化 -13.00%。其中 `fewshot`、`self` 和 `reflect-3` 的准确率提升分别为 +21.83 个百分点、+8.18 个百分点 和 +15.62 个百分点。

对于已发布的 `glm-5.2, max` 运行，本看板使用 Z.AI GLM-5.2 价格：

| Token 类型 | 价格 |
| --- | ---: |
| Input | $1.40 / 1M tokens |
| Cached input | $0.26 / 1M tokens |
| Cached input storage（缓存存储） | $0.00 / 1M tokens（限时免费） |
| Output | $4.40 / 1M tokens |

看板层面和 report 层面的 cost 计算公式为：

```text
cost_USD_avg_3 =
  (input_tokens_avg_3          * 1.40
   + cache_creation_tokens_avg_3 * 0.00
   + cache_read_tokens_avg_3     * 0.26
   + output_tokens_avg_3         * 4.40) / 1_000_000
```

GLM 的 token 列使用从 Claude Code run metadata 归一化后的四个 usage bucket：input、cached input storage、cached input 和 output。`cache_creation_tokens_avg_3` 对应 cached input storage，目前价格为 0.00。

| task_group_id | scenario_id | model | harness | mode | overall acc@3 (%) | overall std@3 (%) | input tokens avg@3 (k) | cached input storage tokens avg@3 (k) | cached input tokens avg@3 (k) | output tokens avg@3 (k) | cost USD avg@3 | report |
| --- | --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| `task_group_001` | `SCN_001_crm_marketing_lead_capture` | `glm-5.2, max` | `claude_code` | `base` | 42.94% | 4.65% | 56.5k | 0.0k | 532.5k | 32.1k | 0.36 | [task_group_001.yaml](claude_code_glm_5_2_max/reports/task_group_001.yaml) |
| `task_group_001` | `SCN_001_crm_marketing_lead_capture` | `glm-5.2, max` | `claude_code` | `fewshot` | 81.65% | 7.09% | 45.0k | 0.0k | 507.6k | 20.7k | 0.29 | [task_group_001.yaml](claude_code_glm_5_2_max/reports/task_group_001.yaml) |
| `task_group_001` | `SCN_001_crm_marketing_lead_capture` | `glm-5.2, max` | `claude_code` | `self` | 61.77% | 6.16% | 49.1k | 0.0k | 522.3k | 26.6k | 0.32 | [task_group_001.yaml](claude_code_glm_5_2_max/reports/task_group_001.yaml) |
| `task_group_001` | `SCN_001_crm_marketing_lead_capture` | `glm-5.2, max` | `claude_code` | `reflect-3` | 78.38% | 13.71% | 38.6k | 0.0k | 429.6k | 21.5k | 0.26 | [task_group_001.yaml](claude_code_glm_5_2_max/reports/task_group_001.yaml) |
| `task_group_002` | `SCN_002_crm_b2b_quote_account_response` | `glm-5.2, max` | `claude_code` | `base` | 40.92% | 0.00% | 27.1k | 0.0k | 302.1k | 14.7k | 0.18 | [task_group_002.yaml](claude_code_glm_5_2_max/reports/task_group_002.yaml) |
| `task_group_002` | `SCN_002_crm_b2b_quote_account_response` | `glm-5.2, max` | `claude_code` | `fewshot` | 56.27% | 7.00% | 34.6k | 0.0k | 329.8k | 15.3k | 0.20 | [task_group_002.yaml](claude_code_glm_5_2_max/reports/task_group_002.yaml) |
| `task_group_002` | `SCN_002_crm_b2b_quote_account_response` | `glm-5.2, max` | `claude_code` | `self` | 42.43% | 2.01% | 35.1k | 0.0k | 339.8k | 15.4k | 0.21 | [task_group_002.yaml](claude_code_glm_5_2_max/reports/task_group_002.yaml) |
| `task_group_002` | `SCN_002_crm_b2b_quote_account_response` | `glm-5.2, max` | `claude_code` | `reflect-3` | 47.71% | 7.28% | 29.1k | 0.0k | 325.0k | 11.8k | 0.18 | [task_group_002.yaml](claude_code_glm_5_2_max/reports/task_group_002.yaml) |
| `task_group_003` | `SCN_003_crm_service_ticket_resolution` | `glm-5.2, max` | `claude_code` | `base` | 61.56% | 7.81% | 59.4k | 0.0k | 459.8k | 34.7k | 0.36 | [task_group_003.yaml](claude_code_glm_5_2_max/reports/task_group_003.yaml) |
| `task_group_003` | `SCN_003_crm_service_ticket_resolution` | `glm-5.2, max` | `claude_code` | `fewshot` | 74.90% | 10.36% | 55.5k | 0.0k | 468.1k | 25.4k | 0.31 | [task_group_003.yaml](claude_code_glm_5_2_max/reports/task_group_003.yaml) |
| `task_group_003` | `SCN_003_crm_service_ticket_resolution` | `glm-5.2, max` | `claude_code` | `self` | 65.65% | 9.87% | 57.6k | 0.0k | 527.9k | 28.2k | 0.34 | [task_group_003.yaml](claude_code_glm_5_2_max/reports/task_group_003.yaml) |
| `task_group_003` | `SCN_003_crm_service_ticket_resolution` | `glm-5.2, max` | `claude_code` | `reflect-3` | 63.15% | 4.72% | 53.5k | 0.0k | 452.7k | 30.4k | 0.33 | [task_group_003.yaml](claude_code_glm_5_2_max/reports/task_group_003.yaml) |
| `task_group_004` | `SCN_004_crm_retention_churn_analytics` | `glm-5.2, max` | `claude_code` | `base` | 19.68% | 3.19% | 71.8k | 0.0k | 663.1k | 50.7k | 0.50 | [task_group_004.yaml](claude_code_glm_5_2_max/reports/task_group_004.yaml) |
| `task_group_004` | `SCN_004_crm_retention_churn_analytics` | `glm-5.2, max` | `claude_code` | `fewshot` | 60.15% | 3.83% | 65.5k | 0.0k | 636.3k | 40.4k | 0.43 | [task_group_004.yaml](claude_code_glm_5_2_max/reports/task_group_004.yaml) |
| `task_group_004` | `SCN_004_crm_retention_churn_analytics` | `glm-5.2, max` | `claude_code` | `self` | 28.61% | 7.26% | 49.2k | 0.0k | 460.2k | 26.5k | 0.31 | [task_group_004.yaml](claude_code_glm_5_2_max/reports/task_group_004.yaml) |
| `task_group_004` | `SCN_004_crm_retention_churn_analytics` | `glm-5.2, max` | `claude_code` | `reflect-3` | 42.93% | 18.53% | 47.7k | 0.0k | 378.4k | 27.5k | 0.29 | [task_group_004.yaml](claude_code_glm_5_2_max/reports/task_group_004.yaml) |
| `task_group_005` | `SCN_005_erp_finance_expense_control` | `glm-5.2, max` | `claude_code` | `base` | 48.07% | 2.25% | 58.2k | 0.0k | 435.4k | 39.9k | 0.37 | [task_group_005.yaml](claude_code_glm_5_2_max/reports/task_group_005.yaml) |
| `task_group_005` | `SCN_005_erp_finance_expense_control` | `glm-5.2, max` | `claude_code` | `fewshot` | 62.44% | 12.04% | 57.7k | 0.0k | 434.7k | 36.8k | 0.36 | [task_group_005.yaml](claude_code_glm_5_2_max/reports/task_group_005.yaml) |
| `task_group_005` | `SCN_005_erp_finance_expense_control` | `glm-5.2, max` | `claude_code` | `self` | 54.97% | 15.52% | 52.5k | 0.0k | 448.6k | 31.2k | 0.33 | [task_group_005.yaml](claude_code_glm_5_2_max/reports/task_group_005.yaml) |
| `task_group_005` | `SCN_005_erp_finance_expense_control` | `glm-5.2, max` | `claude_code` | `reflect-3` | 59.38% | 4.27% | 53.4k | 0.0k | 444.3k | 37.5k | 0.36 | [task_group_005.yaml](claude_code_glm_5_2_max/reports/task_group_005.yaml) |
| `task_group_006` | `SCN_006_erp_procurement_supplier_receiving` | `glm-5.2, max` | `claude_code` | `base` | 58.37% | 7.34% | 67.0k | 0.0k | 499.2k | 41.7k | 0.41 | [task_group_006.yaml](claude_code_glm_5_2_max/reports/task_group_006.yaml) |
| `task_group_006` | `SCN_006_erp_procurement_supplier_receiving` | `glm-5.2, max` | `claude_code` | `fewshot` | 70.41% | 7.11% | 57.9k | 0.0k | 446.9k | 34.6k | 0.35 | [task_group_006.yaml](claude_code_glm_5_2_max/reports/task_group_006.yaml) |
| `task_group_006` | `SCN_006_erp_procurement_supplier_receiving` | `glm-5.2, max` | `claude_code` | `self` | 61.15% | 5.14% | 64.8k | 0.0k | 469.7k | 35.4k | 0.37 | [task_group_006.yaml](claude_code_glm_5_2_max/reports/task_group_006.yaml) |
| `task_group_006` | `SCN_006_erp_procurement_supplier_receiving` | `glm-5.2, max` | `claude_code` | `reflect-3` | 62.07% | 6.69% | 56.4k | 0.0k | 499.0k | 32.5k | 0.35 | [task_group_006.yaml](claude_code_glm_5_2_max/reports/task_group_006.yaml) |
| `task_group_007` | `SCN_007_erp_inventory_order_fulfillment` | `glm-5.2, max` | `claude_code` | `base` | 33.36% | 5.65% | 64.5k | 0.0k | 613.7k | 46.1k | 0.45 | [task_group_007.yaml](claude_code_glm_5_2_max/reports/task_group_007.yaml) |
| `task_group_007` | `SCN_007_erp_inventory_order_fulfillment` | `glm-5.2, max` | `claude_code` | `fewshot` | 55.84% | 5.84% | 60.1k | 0.0k | 585.4k | 35.1k | 0.39 | [task_group_007.yaml](claude_code_glm_5_2_max/reports/task_group_007.yaml) |
| `task_group_007` | `SCN_007_erp_inventory_order_fulfillment` | `glm-5.2, max` | `claude_code` | `self` | 35.21% | 5.39% | 64.5k | 0.0k | 732.2k | 35.7k | 0.44 | [task_group_007.yaml](claude_code_glm_5_2_max/reports/task_group_007.yaml) |
| `task_group_007` | `SCN_007_erp_inventory_order_fulfillment` | `glm-5.2, max` | `claude_code` | `reflect-3` | 55.03% | 8.67% | 62.6k | 0.0k | 679.7k | 37.2k | 0.43 | [task_group_007.yaml](claude_code_glm_5_2_max/reports/task_group_007.yaml) |
| `task_group_008` | `SCN_008_personal_financial_advisory_tax_estate_planning` | `glm-5.2, max` | `claude_code` | `base` | 56.27% | 7.53% | 48.6k | 0.0k | 356.7k | 35.0k | 0.31 | [task_group_008.yaml](claude_code_glm_5_2_max/reports/task_group_008.yaml) |
| `task_group_008` | `SCN_008_personal_financial_advisory_tax_estate_planning` | `glm-5.2, max` | `claude_code` | `fewshot` | 77.94% | 19.38% | 31.8k | 0.0k | 284.1k | 15.0k | 0.18 | [task_group_008.yaml](claude_code_glm_5_2_max/reports/task_group_008.yaml) |
| `task_group_008` | `SCN_008_personal_financial_advisory_tax_estate_planning` | `glm-5.2, max` | `claude_code` | `self` | 63.09% | 10.98% | 31.2k | 0.0k | 301.8k | 12.6k | 0.18 | [task_group_008.yaml](claude_code_glm_5_2_max/reports/task_group_008.yaml) |
| `task_group_008` | `SCN_008_personal_financial_advisory_tax_estate_planning` | `glm-5.2, max` | `claude_code` | `reflect-3` | 76.41% | 4.94% | 28.6k | 0.0k | 296.8k | 9.7k | 0.16 | [task_group_008.yaml](claude_code_glm_5_2_max/reports/task_group_008.yaml) |
| `task_group_009` | `SCN_009_finance_operational_modeling_management_reporting` | `glm-5.2, max` | `claude_code` | `base` | 55.10% | 7.41% | 44.1k | 0.0k | 310.0k | 31.8k | 0.28 | [task_group_009.yaml](claude_code_glm_5_2_max/reports/task_group_009.yaml) |
| `task_group_009` | `SCN_009_finance_operational_modeling_management_reporting` | `glm-5.2, max` | `claude_code` | `fewshot` | 88.31% | 8.26% | 40.1k | 0.0k | 358.0k | 20.8k | 0.24 | [task_group_009.yaml](claude_code_glm_5_2_max/reports/task_group_009.yaml) |
| `task_group_009` | `SCN_009_finance_operational_modeling_management_reporting` | `glm-5.2, max` | `claude_code` | `self` | 63.45% | 10.95% | 40.5k | 0.0k | 367.3k | 18.3k | 0.23 | [task_group_009.yaml](claude_code_glm_5_2_max/reports/task_group_009.yaml) |
| `task_group_009` | `SCN_009_finance_operational_modeling_management_reporting` | `glm-5.2, max` | `claude_code` | `reflect-3` | 78.35% | 2.05% | 37.3k | 0.0k | 287.7k | 18.4k | 0.21 | [task_group_009.yaml](claude_code_glm_5_2_max/reports/task_group_009.yaml) |
| `task_group_010` | `SCN_010_institutional_investment_strategy_portfolio_risk` | `glm-5.2, max` | `claude_code` | `base` | 61.54% | 8.58% | 72.4k | 0.0k | 541.0k | 46.4k | 0.45 | [task_group_010.yaml](claude_code_glm_5_2_max/reports/task_group_010.yaml) |
| `task_group_010` | `SCN_010_institutional_investment_strategy_portfolio_risk` | `glm-5.2, max` | `claude_code` | `fewshot` | 72.11% | 9.69% | 66.6k | 0.0k | 525.7k | 35.6k | 0.39 | [task_group_010.yaml](claude_code_glm_5_2_max/reports/task_group_010.yaml) |
| `task_group_010` | `SCN_010_institutional_investment_strategy_portfolio_risk` | `glm-5.2, max` | `claude_code` | `self` | 69.60% | 6.15% | 68.0k | 0.0k | 602.9k | 39.6k | 0.43 | [task_group_010.yaml](claude_code_glm_5_2_max/reports/task_group_010.yaml) |
| `task_group_010` | `SCN_010_institutional_investment_strategy_portfolio_risk` | `glm-5.2, max` | `claude_code` | `reflect-3` | 64.61% | 7.13% | 68.9k | 0.0k | 528.3k | 41.3k | 0.42 | [task_group_010.yaml](claude_code_glm_5_2_max/reports/task_group_010.yaml) |
| `task_group_011` | `SCN_011_bank_branch_credit_risk_lending_committee` | `glm-5.2, max` | `claude_code` | `base` | 47.59% | 8.16% | 74.5k | 0.0k | 574.3k | 51.7k | 0.48 | [task_group_011.yaml](claude_code_glm_5_2_max/reports/task_group_011.yaml) |
| `task_group_011` | `SCN_011_bank_branch_credit_risk_lending_committee` | `glm-5.2, max` | `claude_code` | `fewshot` | 54.40% | 8.41% | 71.4k | 0.0k | 595.0k | 44.0k | 0.45 | [task_group_011.yaml](claude_code_glm_5_2_max/reports/task_group_011.yaml) |
| `task_group_011` | `SCN_011_bank_branch_credit_risk_lending_committee` | `glm-5.2, max` | `claude_code` | `self` | 46.38% | 7.08% | 72.9k | 0.0k | 603.3k | 45.4k | 0.46 | [task_group_011.yaml](claude_code_glm_5_2_max/reports/task_group_011.yaml) |
| `task_group_011` | `SCN_011_bank_branch_credit_risk_lending_committee` | `glm-5.2, max` | `claude_code` | `reflect-3` | 52.00% | 4.10% | 69.5k | 0.0k | 552.1k | 41.2k | 0.42 | [task_group_011.yaml](claude_code_glm_5_2_max/reports/task_group_011.yaml) |
| `task_group_012` | `SCN_012_erp_hr_employee_lifecycle` | `glm-5.2, max` | `claude_code` | `base` | 47.30% | 0.00% | 101.3k | 0.0k | 1125.4k | 16.4k | 0.51 | [task_group_012.yaml](claude_code_glm_5_2_max/reports/task_group_012.yaml) |
| `task_group_012` | `SCN_012_erp_hr_employee_lifecycle` | `glm-5.2, max` | `claude_code` | `fewshot` | 80.21% | 7.20% | 104.0k | 0.0k | 1074.7k | 15.1k | 0.49 | [task_group_012.yaml](claude_code_glm_5_2_max/reports/task_group_012.yaml) |
| `task_group_012` | `SCN_012_erp_hr_employee_lifecycle` | `glm-5.2, max` | `claude_code` | `self` | 78.58% | 7.61% | 122.6k | 0.0k | 1198.3k | 20.5k | 0.57 | [task_group_012.yaml](claude_code_glm_5_2_max/reports/task_group_012.yaml) |
| `task_group_012` | `SCN_012_erp_hr_employee_lifecycle` | `glm-5.2, max` | `claude_code` | `reflect-3` | 80.16% | 8.00% | 109.1k | 0.0k | 1015.8k | 17.5k | 0.49 | [task_group_012.yaml](claude_code_glm_5_2_max/reports/task_group_012.yaml) |


