# test_004 Notes

## English

Data lineage: This test task derives from `E005` and is anchored by `train_004`. It uses `PAT-L-X001`, ESR Observations with code `4537-7`, and `FHIR_LAB_RETRIEVAL_2026`.

Task definition: The solver must determine whether final ESR Observations exist in June 2026 and return matched ids, count, first/last dates, excluded ids, resource type, and checked code.

Scenario fit and material map: `/api/observations` exposes June final ESR records, a cancelled June record, a panel header, and a July boundary record. The protocol defines final-only status, panel exclusion, and month-window inclusion.

Solution and evaluation basis: The matched final June ids are `OBS-L-X001-ESR-JUN-A` and `OBS-L-X001-ESR-JUN-B`, count 2. The cancelled, panel, and July records are excluded. The evaluator has 6 exact-match scoring points.

Transfer design: Anchor is `train_004`. Transfer-dependent points are exact patient/code/month matching, matched id set, and first/last date derivation. The changed difficulty is a different lab code and a new set of boundary and panel distractors.

Construction record: Author Codex; created 2026-07-07; updated after final environment reconciliation.

## 中文

数据来源：本测试任务来自 `E005`，由 `train_004` 锚定。它使用 `PAT-L-X001`、代码 `4537-7` 的 ESR Observation 和 `FHIR_LAB_RETRIEVAL_2026`。

任务定义：求解者需要判断 2026 年 6 月是否存在 final 状态 ESR Observation，并返回匹配 ID、数量、首末日期、排除 ID、资源类型和检查代码。

场景匹配与材料图：`/api/observations` 提供 6 月 final ESR 记录、6 月 cancelled 记录、panel header 和 7 月边界记录。协议定义 final-only、panel 排除和月份窗口。

解法与评估依据：正确匹配 ID 为 `OBS-L-X001-ESR-JUN-A` 和 `OBS-L-X001-ESR-JUN-B`，数量为 2；cancelled、panel 和 7 月记录应排除。评估包含 6 个精确匹配评分点。

迁移设计：锚点为 `train_004`。迁移点是精确患者、代码、月份和状态过滤，以及首末日期推导；变化是实验室代码和干扰记录不同。

构建记录：作者 Codex；创建于 2026-07-07；最终环境对齐后更新。
