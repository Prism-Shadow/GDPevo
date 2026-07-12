# 数据看板

语言：[English](DATA_BOARD.md) | [中文](DATA_BOARD.zh.md)

本看板汇总当前公开的 GDPevo task groups：共 24 个 stateful benchmark 单元、240
个任务。每个 task group 包含一个共享业务环境、5 个 train tasks 和 5 个 held-out
test tasks，用于衡量由早期任务驱动的 self-evolution 是否能让同一环境下的后续任务获得提升。
完整定义见各 task group 目录下的 `task_group.yaml`。

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
| `task_group_013_healthcare_intake_transfer` | `SCN_013_healthcare_patient_intake_transfer` | 医疗运营 | 患者接收、转诊转入与服务准入 | 5 | 5 | [task_group_013_healthcare_intake_transfer](task_groups/task_group_013_healthcare_intake_transfer/) |
| `task_group_014_sql_payer_ops` | `SCN_014_healthcare_payer_authorization_appeals` | 医疗收入循环 | 医保授权、申诉、报销与收益分析 | 5 | 5 | [task_group_014_sql_payer_ops](task_groups/task_group_014_sql_payer_ops/) |
| `task_group_015_healthcare_ehr_quality_governance` | `SCN_015_healthcare_ehr_quality_governance` | 医疗数据运营 | 电子病历质量治理与临床记录核对 | 5 | 5 | [task_group_015_healthcare_ehr_quality_governance](task_groups/task_group_015_healthcare_ehr_quality_governance/) |
| `task_group_016_clinical_protocol_decision_support` | `SCN_016_healthcare_clinical_protocol_decision_support` | 医疗临床决策支持 | 基于临床规程的诊疗决策支持 | 5 | 5 | [task_group_016_clinical_protocol_decision_support](task_groups/task_group_016_clinical_protocol_decision_support/) |
| `task_group_017` | `SCN_017_white_collar_investigation_production_review` | 法律 | 调查材料提交、保全与补救审查 | 5 | 5 | [task_group_017](task_groups/task_group_017/) |
| `task_group_018` | `SCN_018_court_clerk_disposition_orders_and_financial_entries` | 法律 | 法院裁判结果与财务录入处理 | 5 | 5 | [task_group_018](task_groups/task_group_018/) |
| `task_group_019` | `SCN_019_regulatory_licensing_eligibility_and_compliance_review` | 法律 | 监管许可资格与合规审查 | 5 | 5 | [task_group_019](task_groups/task_group_019/) |
| `task_group_020` | `SCN_020_ma_transaction_contract_review_and_negotiation` | 法律 | 并购交易合同审查与谈判 | 5 | 5 | [task_group_020](task_groups/task_group_020/) |
| `task_group_021` | `SCN_021_data_cleaning_quality_pipeline` | 数据分析 | 数据清洗与质量管道审计 | 5 | 5 | [task_group_021](task_groups/task_group_021/) |
| `task_group_022` | `SCN_022_sql_database_analytics` | 数据分析 | SQL 数据库分析与安全修正流程 | 5 | 5 | [task_group_022](task_groups/task_group_022/) |
| `task_group_023` | `SCN_023_public_health_statistical_modeling_audit` | 公共卫生 | 公共卫生统计建模审计 | 5 | 5 | [task_group_023](task_groups/task_group_023/) |
| `task_group_024` | `SCN_024_engineering_portfolio_work_item_analytics` | 数据分析 | 工程项目组合、服务时限与发布就绪分析 | 5 | 5 | [task_group_024](task_groups/task_group_024/) |
