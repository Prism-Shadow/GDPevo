# Train 003 Notes: SEA_Q3_2026 Shipment Cost Integrity Audit

## English

Data/source lineage: This task belongs to `task_group_021`, scenario `SCN_021_data_cleaning_quality_pipeline`, using source examples `E001`, `E002`, and especially `E003` for CSV-style integrity auditing with duplicates, invalid rows, unit/currency normalization, and corrected closed-form aggregates. The shared generated environment is `task_group/task_group_021/env/`; the target data is in `env/data/asterops_data.json` and exposed through `/api/logistics/cost_events` and `/api/reference/quality_rules`. No task-local answer-bearing payloads are used.

Task definition: The solver is asked to audit logistics wave `SEA_Q3_2026` and return a single structured JSON result. The visible prompt points to the shared environment using `<TASK_ENV_BASE_URL>` and asks for effective event count, duplicate business-key count, invalid event IDs, corrected USD total, cost-type totals, top lane, unit counts, issue counts, and amended event IDs used. The prompt deliberately avoids listing the full reconstruction procedure.

Scenario fit: This is the event-integrity operation family from the group design. It mirrors the source scenario's data-cleaning work: analysts must find a target slice inside a larger generated dataset, distinguish invalid rows from ordinary advisory notes, suppress void/non-effective records, normalize currencies, and produce exact aggregate business results.

Material map: `/api/logistics/cost_events` provides the shipment cost event rows, including `wave_id`, `event_id`, `business_key`, `record_status`, `amends_event_id`, `amount`, `currency`, `event_type`, `lane`, `quantity`, `unit`, and `quality_notes`. `/api/reference/quality_rules` provides record-status, currency-rate, and unit enum references. `input/payloads/answer_template.json` gives the required output schema, precision rules, cost-type enums, unit enums, and issue-type enums without revealing the answer.

Solution and evaluation basis: The answer uses only rows where `wave_id == "SEA_Q3_2026"`. Rows with invalid issue notes, missing amount, negative amount, invalid currency, or invalid unit are excluded as invalid; void records are excluded as non-effective but not listed in `invalid_event_ids`. Amendment rows would replace their amended event, and duplicate business keys would be counted after exclusions and amendment handling. For this wave there are 54 source rows, invalid events `LC_BG_0000` and `LC_SEA_003`, four void records, no amendments used, and no duplicate effective business keys. The effective count is 48. Currency conversion uses environment rates USD 1.00, CAD 0.74, EUR 1.08, GBP 1.27. Each included event is converted to USD and rounded to cents before aggregation. The corrected total is 237277.31 USD. Cost-type totals are freight 59242.27, accessorial 64094.80, tax_fee 67632.77, and claim 46307.47. The top lane is Seattle-Denver at 57971.91 USD. Unit counts over included events are kg 11, lb 12, mile 8, shipment 11, and claim 6. Controlled issue counts are invalid_negative_amount 2, missing_amount 0, invalid_unit 1, invalid_currency 0, void_record 4, amended_record 0, duplicate_business_key 0, non_usd_currency 36, and advisory_note 1.

Evaluation: The evaluator has 8 scoring points with raw weights `[2, 2, 1, 3, 3, 2, 2, 2]`, total raw weight 17. It exact-matches: wave/effective count; invalid event IDs and issue types; duplicate/amendment outputs; corrected total; cost-type totals; top lane; unit counts; and issue-type counts. Monetary values are normalized to Decimal cents before comparison. `output/answer.json` scores full credit.

Transfer design: As a train task, this task exposes the event-integrity conventions that should be inferable only after attempting the task and comparing against the answer: effective-row reconstruction, void and invalid exclusion, amendment precedence, business-key duplicate grouping, deterministic currency conversion, line-level cent rounding, controlled enums, and aggregate precision. These conventions anchor later event-integrity test tasks such as `test_003` and `test_005`, where amendments and duplicate keys are more active.

Likely model pitfalls: Common errors include summing all rows in the wave, treating advisory `detention` as invalid, listing void rows as invalid, rounding only after aggregation, ignoring non-USD conversion, omitting zero-valued issue enums, or assuming that the named `LC_SEA_*` rows are the only rows in the wave.

Construction record: Created by task-builder subagent for `train_003` on 2026-07-07. Files created under `train_tasks/003/`: solver prompt, answer template, standard answer, evaluator, and bilingual notes. No shared environment, scratch, metadata, or other task folders were modified.

## 中文

数据来源：本任务属于 `task_group_021`，对应场景 `SCN_021_data_cleaning_quality_pipeline`，来源示例为 `E001`、`E002`、`E003`，其中主要承接 `E003` 的完整性审计模式。共享环境位于 `task_group/task_group_021/env/`，目标数据来自 `env/data/asterops_data.json`，并通过 `/api/logistics/cost_events` 和 `/api/reference/quality_rules` 暴露。任务本地没有额外的答案型数据。

任务定义：求解者需要审计物流成本波次 `SEA_Q3_2026`，输出一个结构化 JSON。可见提示只说明业务目标、环境入口和输出要求，不提供完整操作清单。输出包括有效事件数、重复业务键数、无效事件 ID、修正后的美元总额、成本类型汇总、最高成本航线、单位计数、问题类型计数以及使用的修订事件 ID。

场景契合度：该任务属于任务组中的事件完整性审计家族，要求在较大的生成数据集中定位目标切片，区分无效记录、作废记录和普通提示性备注，进行币种归一化，并产出可精确验证的业务汇总结果。

材料说明：`/api/logistics/cost_events` 提供成本事件字段，包括 `wave_id`、`event_id`、`business_key`、`record_status`、`amends_event_id`、`amount`、`currency`、`event_type`、`lane`、`quantity`、`unit` 和 `quality_notes`。`/api/reference/quality_rules` 提供状态、汇率和单位枚举。`input/payloads/answer_template.json` 规定输出结构、精度、成本类型枚举、单位枚举和问题类型枚举，但不泄露标准答案。

答案依据：标准答案只使用 `wave_id == "SEA_Q3_2026"` 的记录。带有无效问题备注、缺失金额、负金额、无效币种或无效单位的记录作为无效记录排除；作废记录作为非有效记录排除，但不放入 `invalid_event_ids`。若存在修订记录，则应使用修订记录替代原记录，并在排除和修订处理后统计重复业务键。本波次共有 54 条源记录，无效事件为 `LC_BG_0000` 和 `LC_SEA_003`，作废记录 4 条，没有使用的修订记录，也没有重复的有效业务键。有效记录数为 48。汇率为 USD 1.00、CAD 0.74、EUR 1.08、GBP 1.27。每条纳入记录先换算为美元并四舍五入到美分，再进行汇总。修正总额为 237277.31 美元；成本类型汇总为 freight 59242.27、accessorial 64094.80、tax_fee 67632.77、claim 46307.47；最高成本航线为 Seattle-Denver，金额 57971.91 美元。有效记录单位计数为 kg 11、lb 12、mile 8、shipment 11、claim 6。问题类型计数为 invalid_negative_amount 2、missing_amount 0、invalid_unit 1、invalid_currency 0、void_record 4、amended_record 0、duplicate_business_key 0、non_usd_currency 36、advisory_note 1。

评估方式：评估器包含 8 个评分点，原始权重为 `[2, 2, 1, 3, 3, 2, 2, 2]`，总权重 17。评分点分别精确匹配目标波次和有效数、无效事件和问题类型、重复与修订输出、修正总额、成本类型汇总、最高成本航线、单位计数和问题类型计数。金额比较会先归一化为 Decimal 美分。`output/answer.json` 可获得满分。

迁移设计：作为训练任务，本任务让模型通过尝试和对照答案学习事件完整性审计的可迁移规则：有效行重建、作废和无效排除、修订优先级、业务键重复分组、确定性汇率转换、逐行美分舍入、受控枚举和汇总精度。这些经验会迁移到后续 `test_003` 和 `test_005` 等事件审计任务，后者会更突出修订和重复业务键。

常见错误：常见失败包括把波次内所有记录都汇总、把 `detention` 这类提示性备注当作无效、把作废记录列为无效记录、只在最终总额处舍入、忽略非美元换算、漏掉值为 0 的问题类型枚举，或误以为只有 `LC_SEA_*` 记录属于该波次。

构造记录：由 `train_003` task-builder subagent 于 2026-07-07 创建。新增文件均位于 `train_tasks/003/` 下，包括求解提示、答案模板、标准答案、评估器和中英双语说明。未修改共享环境、scratch、元数据或其他任务目录。
## Rework addendum / 返工补充

English: After logistics calibration rework, the train answer includes `decision_audit` with concrete event evidence: void rows, amended rows, superseded rows, and a deterministic sample of non-USD events included in conversion. These lists anchor transfer to `test_003` and `test_005` while remaining recoverable from the shared ledger.

中文：物流类校准返工后，训练答案在 `decision_audit` 中加入了具体事件证据：作废行、修订行、被覆盖行，以及确定性的非美元换算事件样本。这些列表锚定到 `test_003` 和 `test_005` 的迁移，同时仍可从共享台账中恢复。
