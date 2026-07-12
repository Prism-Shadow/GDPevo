# Data Board

Languages: [English](DATA_BOARD.md) | [Chinese](DATA_BOARD.zh.md)

This board summarizes the released GDPevo task groups: 240 tasks across 24
stateful benchmark units. Each task group has one shared business environment,
five train tasks, and five held-out test tasks, allowing the benchmark to
measure whether self-evolution from earlier tasks improves later work in the
same environment. Full definitions are available in each task group's
`task_group.yaml`.

| task_group_id | scenario_id | domain | focus | train | test | path |
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
| `task_group_013_healthcare_intake_transfer` | `SCN_013_healthcare_patient_intake_transfer` | Healthcare Operations | Healthcare intake, transfer, and referral readiness | 5 | 5 | [task_group_013_healthcare_intake_transfer](task_groups/task_group_013_healthcare_intake_transfer/) |
| `task_group_014_sql_payer_ops` | `SCN_014_healthcare_payer_authorization_appeals` | Healthcare Revenue Cycle | Payer authorization, appeals, reimbursement, and profitability | 5 | 5 | [task_group_014_sql_payer_ops](task_groups/task_group_014_sql_payer_ops/) |
| `task_group_015_healthcare_ehr_quality_governance` | `SCN_015_healthcare_ehr_quality_governance` | Healthcare Data Operations | EHR quality governance and clinical-record reconciliation | 5 | 5 | [task_group_015_healthcare_ehr_quality_governance](task_groups/task_group_015_healthcare_ehr_quality_governance/) |
| `task_group_016_clinical_protocol_decision_support` | `SCN_016_healthcare_clinical_protocol_decision_support` | Healthcare Clinical Decision Support | Protocol-bound clinical decision support | 5 | 5 | [task_group_016_clinical_protocol_decision_support](task_groups/task_group_016_clinical_protocol_decision_support/) |
| `task_group_017` | `SCN_017_white_collar_investigation_production_review` | Legal | Investigation production, preservation, and remediation review | 5 | 5 | [task_group_017](task_groups/task_group_017/) |
| `task_group_018` | `SCN_018_court_clerk_disposition_orders_and_financial_entries` | Legal | Court disposition and financial-entry operations | 5 | 5 | [task_group_018](task_groups/task_group_018/) |
| `task_group_019` | `SCN_019_regulatory_licensing_eligibility_and_compliance_review` | Legal | Regulatory licensing eligibility and compliance review | 5 | 5 | [task_group_019](task_groups/task_group_019/) |
| `task_group_020` | `SCN_020_ma_transaction_contract_review_and_negotiation` | Legal | M&A contract review and negotiation | 5 | 5 | [task_group_020](task_groups/task_group_020/) |
| `task_group_021` | `SCN_021_data_cleaning_quality_pipeline` | Data Analysis | Data cleaning and quality-pipeline audits | 5 | 5 | [task_group_021](task_groups/task_group_021/) |
| `task_group_022` | `SCN_022_sql_database_analytics` | Data Analysis | SQL database analytics and safe correction workflows | 5 | 5 | [task_group_022](task_groups/task_group_022/) |
| `task_group_023` | `SCN_023_public_health_statistical_modeling_audit` | Public Health | Public-health statistical modeling audits | 5 | 5 | [task_group_023](task_groups/task_group_023/) |
| `task_group_024` | `SCN_024_engineering_portfolio_work_item_analytics` | Data Analysis | Engineering portfolio, SLA, and release-readiness analytics | 5 | 5 | [task_group_024](task_groups/task_group_024/) |
