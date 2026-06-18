# 数据看板

语言：[English](DATA_BOARD.md) | [中文](DATA_BOARD.zh.md)

本看板汇总当前公开的 GDPevo task groups：共 12 个 stateful benchmark 单元、120 个任务。每个 task group 包含一个共享业务环境、5 个 train tasks 和 5 个 test tasks，用于衡量早期任务经验是否能让同一环境下的后续任务获得提升。完整定义见各 task group 目录下的 `task_group.yaml`。

| task_group_id | scenario_id | 领域 | 任务侧重点 | train | test | 路径 |
| --- | --- | --- | --- | ---: | ---: | --- |
| `task_group_001` | `SCN_001_crm_marketing_lead_capture` | CRM | CRM marketing lead capture | 5 | 5 | [task_group_001](task_groups/task_group_001/) |
| `task_group_002` | `SCN_002_crm_b2b_quote_account_response` | CRM | B2B quote and account response | 5 | 5 | [task_group_002](task_groups/task_group_002/) |
| `task_group_003` | `SCN_003_crm_service_ticket_resolution` | CRM | Service ticket resolution | 5 | 5 | [task_group_003](task_groups/task_group_003/) |
| `task_group_004` | `SCN_004_crm_retention_churn_analytics` | CRM | Retention and churn analytics | 5 | 5 | [task_group_004](task_groups/task_group_004/) |
| `task_group_005` | `SCN_005_erp_finance_expense_control` | ERP | Finance expense control and accounting close | 5 | 5 | [task_group_005](task_groups/task_group_005/) |
| `task_group_006` | `SCN_006_erp_procurement_supplier_receiving` | ERP | Procurement, supplier, and receiving control | 5 | 5 | [task_group_006](task_groups/task_group_006/) |
| `task_group_007` | `SCN_007_erp_inventory_order_fulfillment` | ERP | Inventory and order fulfillment | 5 | 5 | [task_group_007](task_groups/task_group_007/) |
| `task_group_008` | `SCN_008_personal_financial_advisory_tax_estate_planning` | Finance | Personal financial advisory, tax, and estate planning | 5 | 5 | [task_group_008](task_groups/task_group_008/) |
| `task_group_009` | `SCN_009_finance_operational_modeling_management_reporting` | Finance | Operational modeling and management reporting | 5 | 5 | [task_group_009](task_groups/task_group_009/) |
| `task_group_010` | `SCN_010_institutional_investment_strategy_portfolio_risk` | Finance | Institutional investment strategy and portfolio risk | 5 | 5 | [task_group_010](task_groups/task_group_010/) |
| `task_group_011` | `SCN_011_bank_branch_credit_risk_lending_committee` | Finance | Bank branch credit risk and lending committee | 5 | 5 | [task_group_011](task_groups/task_group_011/) |
| `task_group_012` | `SCN_012_erp_hr_employee_lifecycle` | ERP | HR employee lifecycle and policy operations | 5 | 5 | [task_group_012](task_groups/task_group_012/) |
