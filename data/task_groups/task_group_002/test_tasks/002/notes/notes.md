# Notes / 说明

## English

- Task: `test_002` for `task_group_002`.
- Scenario: new NGO cholera response module EXW quote for RFQ `RFQ-TE-CHOL-882`, customer `CUST-RELIEFPOINT`, quote date `2026-06-01`.
- Main behavior being tested: normalize the noisy RFQ to the requested cholera module lines only, without duplicate commercial lines or component-level expansion.
- Required business controls: `EXW_ONLY`, freight excluded, `PREPAY_100`, 30-day offer validity, `duplicate_rfq_normalized` true, module-line granularity, component exclusion, new-client policy source, indicative EXW scope, and catalog-line-sum total basis.
- Evaluation uses eight weighted checks totaling 18 points: module-only line set, quantities, catalog prices and line totals, grand total, shelf-life and lead-time fields, commercial scope controls, granularity/component controls, and policy-source controls.

## 中文

- 任务：`task_group_002` 的 `test_002`。
- 场景：为新 NGO 客户 `CUST-RELIEFPOINT` 的 RFQ `RFQ-TE-CHOL-882` 生成霍乱响应模块级 EXW 报价，报价日期为 `2026-06-01`。
- 重点考察：将有噪声和重复叙述的 RFQ 归一化为客户请求的霍乱模块报价行，不产生重复商业行，也不展开为组件级明细。
- 必需业务控制：`EXW_ONLY`、不包含运费、`PREPAY_100`、报价有效期 30 天、`duplicate_rfq_normalized` 为 true、模块级行粒度、排除组件报价、新客户政策来源、指示性 EXW 范围，以及目录行合计作为总额基础。
- 评估包含八个加权检查点，总分 18 分：仅模块级行集合、数量、目录价格和行合计、总计、保质期和交期字段、商业范围控制、粒度/组件控制，以及政策来源控制。
