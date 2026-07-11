# Test 003 Notes: AIR_Q4_2026 Shipment Cost Integrity Audit

## English

Data/source lineage: This task belongs to `task_group_021`, scenario `SCN_021_data_cleaning_quality_pipeline`, using source examples `E001`, `E002`, and especially `E003` for data-integrity auditing with duplicate keys, invalid values, currency normalization, and exact aggregate reporting. The shared generated environment is `task_group/task_group_021/env/`; the target data is in `env/data/asterops_data.json` and exposed through `/api/logistics/cost_events`, `/api/reference/quality_rules`, and `/downloads/logistics_cost_events_export.csv`. No task-local answer-bearing payload is used.

Task definition: The solver-visible prompt asks for a structured integrity audit of shipment cost wave `AIR_Q4_2026`. The required answer fields are `wave_id`, `effective_event_count`, `duplicate_business_key_count`, `invalid_event_ids`, `invalid_event_issue_types`, `corrected_total_usd`, `cost_type_totals_usd`, `top_lane_by_cost`, `unit_correction_counts`, `issue_type_counts`, and `amended_event_ids_used`. The visible prompt names the environment and output schema but does not reveal the reconstruction checklist or expected values.

Scenario fit: This is the event-integrity operation family from the task group. It matches the source scenario's business-data cleanup pattern: locate a target slice in a larger operational dataset, reconstruct effective records, separate invalid data from ordinary non-effective records, normalize currencies, and produce exact closed-form business totals.

Material map: `/api/logistics/cost_events?wave_id=AIR_Q4_2026` provides the cost-event rows. Important fields are `event_id`, `business_key`, `record_status`, `amends_event_id`, `amount`, `currency`, `event_type`, `lane`, `unit`, and `quality_notes`. `/api/reference/quality_rules` provides the deterministic USD rates and controlled unit/status values. The CSV download is a bulk copy of the same logistics table. `input/payloads/answer_template.json` defines the output structure, enums, ordering, and cent precision without exposing the answer.

Solution and evaluation basis: The AIR wave contains 63 source rows. The standard answer excludes four void rows, two invalid negative-amount rows as invalid data issues, the original `LC_AIR_002` superseded by `LC_AIR_003`, and the lower-precedence duplicate business-key candidate `LC_BG_0247`; `LC_BG_0134` is listed as invalid because it has an invalid negative amount even though it is also void. Valid amended rows retained in the effective set are `LC_AIR_003` and `LC_BG_0221`. The duplicate business-key count is 1 for `LOG-0123`. The effective count is 56.

Currency conversion uses the environment rates USD 1.00, CAD 0.74, EUR 1.08, and GBP 1.27. Each included event is converted to USD and rounded to cents before aggregation. The corrected total is 294773.68 USD. Cost-type totals are freight 90338.98, accessorial 71097.64, tax_fee 45943.15, and claim 87393.91. The top lane is Frankfurt-Atlanta at 78361.46 USD. Effective source-unit counts are kg 11, lb 9, mile 12, shipment 11, and claim 13. Controlled issue counts are invalid_negative_amount 2, missing_amount 0, invalid_unit 0, invalid_currency 0, void_record 4, amended_record 2, duplicate_business_key 1, non_usd_currency 39, and advisory_note 0.

Evaluation: The evaluator has 8 scoring points with raw weights `[2, 2, 3, 3, 3, 2, 2, 3]`, total raw weight 20. It exact-matches: wave/effective count; invalid event IDs and issue types; duplicate count, amended event IDs, and audit evidence; corrected total; cost-type totals; top lane; unit counts; and issue-type counts with audit evidence. Monetary values are normalized to Decimal cents before comparison. `output/answer.json` scores full credit.

Transfer design: This test task is anchored by `train_003` and `train_005`. `train_003` transfers effective-row reconstruction for logistics cost events, line-level USD cent rounding, invalid-row exclusion, non-USD handling, cost-type totals, top-lane aggregation, and controlled issue counts. `train_005` reinforces amendment precedence and non-effective record handling in a spend-reporting context. Transfer-dependent scoring points include effective count, amended row precedence, duplicate business-key count, invalid event exclusion, unit/currency correction, and cost-type totals. Task-specific exploration comes from the AIR lanes, a larger surcharge/accessorial mix, mixed currencies, the `LOG-0123` duplicate, and the amended rows present in this wave.

Likely model pitfalls: Common errors include filtering only the hand-seeded `LC_AIR_*` rows, summing all AIR rows including voids and invalid records, keeping both `LC_AIR_002` and `LC_AIR_003`, dropping all amended rows, failing to suppress the lower-precedence `LOG-0123` duplicate, rounding only after aggregation, omitting zero-valued issue enums, or treating every quality note as an invalid issue.

Construction record: Created by task-builder subagent for `test_003` on 2026-07-07. Files created only under `task_group/task_group_021/test_tasks/003/`: solver prompt, answer template, standard answer, evaluator, and bilingual notes. No shared environment, scratch files, metadata, or other task folders were modified.

## 中文

数据来源：本任务属于 `task_group_021`，对应场景 `SCN_021_data_cleaning_quality_pipeline`，来源示例为 `E001`、`E002`、`E003`，其中主要承接 `E003` 的数据完整性审计模式，包括重复键、无效值、币种归一化和精确汇总。共享环境位于 `task_group/task_group_021/env/`，目标数据来自 `env/data/asterops_data.json`，并通过 `/api/logistics/cost_events`、`/api/reference/quality_rules` 和 `/downloads/logistics_cost_events_export.csv` 暴露。任务本地没有答案型载荷。

任务定义：可见提示要求求解者审计物流成本波次 `AIR_Q4_2026`，输出结构化 JSON。答案字段包括 `wave_id`、`effective_event_count`、`duplicate_business_key_count`、`invalid_event_ids`、`invalid_event_issue_types`、`corrected_total_usd`、`cost_type_totals_usd`、`top_lane_by_cost`、`unit_correction_counts`、`issue_type_counts` 和 `amended_event_ids_used`。可见提示只说明环境入口和输出结构，不泄露重建步骤或标准值。

场景契合度：该任务属于任务组中的事件完整性审计家族，符合源场景的数据清洗工作：在较大的运营数据中定位目标切片，重建有效记录，区分无效数据和普通非有效记录，归一化币种，并产出可精确验证的业务汇总结果。

材料说明：`/api/logistics/cost_events?wave_id=AIR_Q4_2026` 提供成本事件行，关键字段包括 `event_id`、`business_key`、`record_status`、`amends_event_id`、`amount`、`currency`、`event_type`、`lane`、`unit` 和 `quality_notes`。`/api/reference/quality_rules` 提供确定性美元汇率以及受控单位和状态值。CSV 下载是同一物流表的批量副本。`input/payloads/answer_template.json` 规定输出结构、枚举、排序和美分精度，但不暴露答案。

答案依据：AIR 波次共有 63 条源记录。标准答案排除 4 条 void 记录、2 条负金额无效数据记录、被 `LC_AIR_003` 取代的原始记录 `LC_AIR_002`，以及较低优先级的重复业务键候选 `LC_BG_0247`；`LC_BG_0134` 虽然也是 void，但因为带有负金额无效问题，所以列入无效事件。保留在有效集合中的修订记录是 `LC_AIR_003` 和 `LC_BG_0221`。重复业务键数为 1，对应 `LOG-0123`。有效记录数为 56。

币种换算使用环境中的汇率：USD 1.00、CAD 0.74、EUR 1.08、GBP 1.27。每条纳入记录先换算为美元并四舍五入到美分，再进行汇总。修正总额为 294773.68 美元。成本类型汇总为 freight 90338.98、accessorial 71097.64、tax_fee 45943.15、claim 87393.91。最高成本航线为 Frankfurt-Atlanta，金额 78361.46 美元。有效记录的源单位计数为 kg 11、lb 9、mile 12、shipment 11、claim 13。问题类型计数为 invalid_negative_amount 2、missing_amount 0、invalid_unit 0、invalid_currency 0、void_record 4、amended_record 2、duplicate_business_key 1、non_usd_currency 39、advisory_note 0。

评估方式：评估器包含 8 个评分点，原始权重为 `[2, 2, 3, 3, 3, 2, 2, 3]`，总权重 20。评分点分别精确匹配目标波次和有效数、无效事件和问题类型、重复数、修订事件 ID 与审计证据、修正总额、成本类型汇总、最高成本航线、单位计数，以及带审计证据的问题类型计数。金额比较会先归一化为 Decimal 美分。`output/answer.json` 可获得满分。

迁移设计：本测试任务锚定 `train_003` 和 `train_005`。`train_003` 迁移物流成本事件中的有效行重建、逐行美元美分舍入、无效行排除、非美元处理、成本类型汇总、最高航线聚合和受控问题计数。`train_005` 强化支出报表场景中的修订优先级和非有效记录处理。依赖迁移的评分点包括有效数、修订记录优先级、重复业务键数、无效事件排除、单位和币种修正以及成本类型汇总。任务特有探索来自航空航线、更多 surcharge/accessorial 记录、混合币种、`LOG-0123` 重复键以及本波次中的修订记录。

常见错误：常见失败包括只筛选手工种子 `LC_AIR_*` 行，把 void 和无效记录一起汇总，同时保留 `LC_AIR_002` 与 `LC_AIR_003`，删除所有 amended 行，没有抑制低优先级的 `LOG-0123` 重复记录，只在最终汇总后四舍五入，漏掉值为 0 的问题枚举，或把所有 quality note 都当作无效问题。

构造记录：由 `test_003` task-builder subagent 于 2026-07-07 创建。新增文件均位于 `task_group/task_group_021/test_tasks/003/` 下，包括求解提示、答案模板、标准答案、评估器和中英双语说明。未修改共享环境、scratch 文件、元数据或其他任务目录。
## Rework addendum / 返工补充

English: The logistics rework added `decision_audit` event evidence for void rows, amended rows, superseded rows, and a non-USD conversion sample. These fields transfer from `train_003`, while lane totals and unit counts still require task-specific data exploration.

中文：物流返工在 `decision_audit` 中加入了作废行、修订行、被覆盖行和非美元换算样本等事件证据。这些字段从 `train_003` 迁移；同时航线金额和单位计数仍需要针对本任务的数据探索。
