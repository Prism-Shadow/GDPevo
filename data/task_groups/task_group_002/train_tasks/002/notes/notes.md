# Notes / 说明

## English

- Task: `train_002` for `task_group_002`.
- Scenario: new NGO module-level EXW quote for RFQ `RFQ-TR-IEHK-204`, customer `CUST-NOVAID`, quote date `2026-06-01`.
- Main behavior being tested: quote requested IEHK modules only, not component composition.
- Required business controls: `EXW_ONLY`, freight excluded, `PREPAY_100`, 30-day validity, and WHO documentation required.
- Evaluation uses eight weighted checks: module line set, quantities, catalog unit prices, totals, shelf-life and lead-time fields, EXW/freight exclusion, new-client payment and validity, and WHO documentation flag.

## 中文

- 任务：`task_group_002` 的 `train_002`。
- 场景：为新 NGO 客户 `CUST-NOVAID` 的 RFQ `RFQ-TR-IEHK-204` 生成模块级 EXW 报价，报价日期为 `2026-06-01`。
- 重点考察：只报价客户请求的 IEHK 模块，不展开模块的组件明细。
- 必需业务控制：`EXW_ONLY`、不包含运费、`PREPAY_100`、报价有效期 30 天，以及需要 WHO 文件。
- 评估包含八个加权检查点：模块行集合、数量、目录单价、行合计和总计、保质期和交期字段、EXW 与运费排除、新客户付款和有效期控制、WHO 文件标记。
