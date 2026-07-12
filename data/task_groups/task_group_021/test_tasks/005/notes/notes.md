# Test 005 Notes: CLAIMS_SEP_2026 Claims Cost Integrity Audit

## English

Data/source lineage: This task belongs to `task_group_021`, scenario `SCN_021_data_cleaning_quality_pipeline`, using source examples `E001`, `E002`, and `E003`. Its primary lineage is the `E003` integrity-audit pattern, with category normalization pressure from the spreadsheet/category examples. The generated shared environment is `task_group/task_group_021/env/`; target rows are in `env/data/asterops_data.json` and exposed through `/api/logistics/cost_events`, `/api/reference/category_aliases`, and `/api/reference/quality_rules`. No task-local answer-bearing payload is used.

Task definition: The solver-visible request asks for a closed-form integrity audit of claims cost batch `CLAIMS_SEP_2026`. The expected output is one JSON object matching `input/payloads/answer_template.json`. The key business objects are cost events, event IDs, business keys, amendment links, event categories, lanes, currencies, units, and issue types. The prompt names the environment and output contract but does not provide a procedural checklist.

Scenario fit: This task is in the event-integrity and category-normalization operation families. It requires locating the target batch inside a larger cost-event ledger, reconstructing effective records, separating invalid records from void or superseded records, normalizing currency and category totals, and returning exact aggregate results.

Material map: `/api/logistics/cost_events` provides `wave_id`, `event_id`, `business_key`, `record_status`, `amends_event_id`, `amount`, `currency`, `event_type`, `lane`, `quantity`, `unit`, and `quality_notes`. `/api/reference/quality_rules` provides record-status enums, USD conversion rates, and valid logistics units. `/api/reference/category_aliases` provides the controlled category vocabulary used by the task group; for this claims batch, the retained `event_type` values are already in the controlled category set. `input/payloads/answer_template.json` specifies required keys, enums, ordering, and currency precision.

Solution and evaluation basis: The source slice contains 54 rows where `wave_id == "CLAIMS_SEP_2026"`. Non-void rows with invalid values are excluded and listed in `invalid_event_ids`: `LC_BG_0142` and `LC_CLM_002`, both with `missing_amount`. Void rows are excluded as non-effective but not listed as invalid. A target-batch row that is amended by a later event is also non-effective; `LC_BG_0220` is superseded by a later amendment elsewhere in the ledger. The combined `superseded_or_void_event_ids` list is `LC_BG_0016`, `LC_BG_0018`, `LC_BG_0118`, `LC_BG_0145`, `LC_BG_0173`, `LC_BG_0220`, and `LC_BG_0237`. Amendment row `LC_BG_0066` is retained as an effective claim-batch row. There are no duplicate retained business keys. The effective count is 45.

Currency conversion uses USD 1.00, EUR 1.08, GBP 1.27, and CAD 0.74. Each retained event is converted to USD and rounded to cents before aggregation. The corrected total is 191045.97 USD. Category totals are freight 59435.22, accessorial 51987.68, tax_fee 56197.16, and claim 23425.91. Effective category counts are freight 16, accessorial 12, tax_fee 11, and claim 6. The top lane is Seattle-Denver with 55021.64 USD. Unit counts are kg 7, lb 12, mile 10, shipment 5, and claim 11. Issue counts are invalid_negative_amount 0, missing_amount 2, invalid_unit 1, invalid_currency 0, void_record 6, superseded_record 1, amended_record 1, duplicate_business_key 0, non_usd_currency 35, and advisory_note 0. The invalid_unit count reflects the source-row issue note on void row `LC_BG_0237`; invalid event IDs still exclude that row because void status makes it non-effective before invalid-event reporting.

Evaluation: The evaluator has 10 scoring points with raw weights `[1, 1, 2, 1, 2, 1, 1, 3, 1, 1]`, total raw weight 14. It exact-matches: target identifiers and effective count; invalid IDs and issue types; duplicate, superseded/void, amendment outputs, and audit evidence; corrected total; category totals and counts; top lane; unit counts; raw invalid-unit issue taxonomy count; non-USD issue-count scope; and the remaining controlled issue-type counts. Monetary values are normalized to Decimal cents before comparison. `output/answer.json` scores full credit.

Transfer design: This test task is anchored in `train_003` and `train_005`. From `train_003`, solvers should transfer effective-row reconstruction, invalid versus void treatment, amendment precedence, duplicate business-key grouping, currency conversion, line-level cent rounding, and controlled issue enums. From `train_005`, solvers should transfer category alias mapping and controlled review/category summary habits. Transfer-dependent scoring points are SP001, SP002, SP003, SP004, SP005, SP008, SP009, and SP010, with SP008 isolating the easy-to-miss rule that a void row can still contribute issue taxonomy evidence while remaining excluded from effective totals. Task-specific exploration comes from the claims batch's cross-wave amendment edge, claim-specific category mix, source units, and non-USD currency combinations.

Likely model pitfalls: Common errors include summing all rows in the batch, including void rows, listing void rows as invalid, missing the superseded `LC_BG_0220` edge, dropping retained amendment `LC_BG_0066`, rounding only after aggregation, ignoring non-USD conversion, treating `event_type` strings as free text instead of controlled categories, or omitting zero-valued issue enums.

Construction record: Created by task-builder subagent for `test_005` on 2026-07-07. Files created under `test_tasks/005/`: solver prompt, answer template, standard answer, evaluator, and bilingual notes. No shared environment, scratch files, task metadata, or other task folders were modified.

## 中文

数据来源：本任务属于 `task_group_021`，对应场景 `SCN_021_data_cleaning_quality_pipeline`，来源示例为 `E001`、`E002`、`E003`。主要承接 `E003` 的完整性审计模式，同时结合类别归一化任务中的别名和受控类别要求。共享环境位于 `task_group/task_group_021/env/`；目标记录来自 `env/data/asterops_data.json`，并通过 `/api/logistics/cost_events`、`/api/reference/category_aliases` 和 `/api/reference/quality_rules` 暴露。任务本地没有额外的答案型数据。

任务定义：求解者需要对理赔成本批次 `CLAIMS_SEP_2026` 做封闭式完整性审计，并输出一个符合 `input/payloads/answer_template.json` 的 JSON 对象。关键业务对象包括成本事件、事件 ID、业务键、修订链接、事件类别、路线、币种、单位和问题类型。可见提示只提供环境入口和输出合同，不提供完整操作清单。

场景契合度：该任务属于事件完整性审计和类别归一化两个操作家族。它要求在较大的成本事件台账中定位目标批次，重建有效记录，区分无效记录、作废记录和被修订覆盖的记录，进行币种和类别汇总归一化，并产出可精确验证的聚合结果。

材料说明：`/api/logistics/cost_events` 提供 `wave_id`、`event_id`、`business_key`、`record_status`、`amends_event_id`、`amount`、`currency`、`event_type`、`lane`、`quantity`、`unit` 和 `quality_notes`。`/api/reference/quality_rules` 提供记录状态枚举、美元汇率和有效物流单位。`/api/reference/category_aliases` 提供任务组使用的受控类别词表；在本理赔批次中，保留记录的 `event_type` 已经属于受控类别。`input/payloads/answer_template.json` 规定必需字段、枚举、排序和货币精度。

答案依据：源切片中共有 54 条 `wave_id == "CLAIMS_SEP_2026"` 的记录。非作废且存在无效值的记录需要排除并列入 `invalid_event_ids`：`LC_BG_0142` 和 `LC_CLM_002`，二者的问题类型都是 `missing_amount`。作废记录作为非有效记录排除，但不列为无效事件。若目标批次记录已被后续修订事件覆盖，也应视为非有效；`LC_BG_0220` 被台账中的后续修订覆盖。`superseded_or_void_event_ids` 因此为 `LC_BG_0016`、`LC_BG_0018`、`LC_BG_0118`、`LC_BG_0145`、`LC_BG_0173`、`LC_BG_0220`、`LC_BG_0237`。修订记录 `LC_BG_0066` 作为本批次有效记录保留。保留后的业务键没有重复。有效记录数为 45。

汇率为 USD 1.00、EUR 1.08、GBP 1.27、CAD 0.74。每条保留记录先换算为美元并四舍五入到美分，再进行汇总。修正总额为 191045.97 美元。类别汇总为 freight 59435.22、accessorial 51987.68、tax_fee 56197.16、claim 23425.91。有效类别计数为 freight 16、accessorial 12、tax_fee 11、claim 6。最高成本路线为 Seattle-Denver，金额 55021.64 美元。单位计数为 kg 7、lb 12、mile 10、shipment 5、claim 11。问题计数为 invalid_negative_amount 0、missing_amount 2、invalid_unit 1、invalid_currency 0、void_record 6、superseded_record 1、amended_record 1、duplicate_business_key 0、non_usd_currency 35、advisory_note 0。其中 invalid_unit 来自作废记录 `LC_BG_0237` 的源数据问题备注；但无效事件 ID 列表仍不包含该记录，因为作废状态使其在无效事件报告前已被排除为非有效记录。

评估方式：评估器包含 10 个评分点，原始权重为 `[1, 1, 2, 1, 2, 1, 1, 3, 1, 1]`，总权重 14。评分点分别精确匹配目标标识和有效数、无效事件和问题类型、重复/作废或覆盖/修订输出及审计证据、修正总额、类别金额和计数、最高成本路线、单位计数、原始无效单位问题分类计数、非美元问题计数范围，以及其余受控问题类型计数。金额比较会先归一化为 Decimal 美分。`output/answer.json` 可获得满分。

迁移设计：本测试任务锚定 `train_003` 和 `train_005`。从 `train_003` 可迁移有效行重建、无效与作废区分、修订优先级、业务键重复分组、汇率转换、逐行美分舍入和受控问题枚举。从 `train_005` 可迁移类别别名映射和受控类别汇总习惯。依赖迁移的评分点包括 SP001、SP002、SP003、SP004、SP005、SP008、SP009 和 SP010，其中 SP008 单独检验“作废行仍可能贡献问题分类证据、但不进入有效汇总”的易错规则。任务特有探索难点来自理赔批次中的跨波次修订边界、理赔类别组合、源单位和非美元币种组合。

常见错误：常见失败包括把批次中所有记录直接求和、纳入作废记录、把作废记录列为无效事件、漏掉被覆盖的 `LC_BG_0220`、错误丢弃有效修订记录 `LC_BG_0066`、只在最终总额处舍入、忽略非美元换算、把 `event_type` 当作自由文本而非受控类别，或遗漏值为 0 的问题类型枚举。

构造记录：由 `test_005` task-builder subagent 于 2026-07-07 创建。新增文件均位于 `test_tasks/005/` 下，包括求解提示、答案模板、标准答案、评估器和中英双语说明。未修改共享环境、scratch 文件、任务元数据或其他任务目录。
## Rework addendum / 返工补充

English: The logistics/claims rework added `decision_audit` event evidence for void rows, amended rows, superseded rows, and a non-USD conversion sample. These fields transfer from `train_003`, while category totals and claim-specific invalid IDs remain task-specific exploration points.

中文：物流/索赔返工在 `decision_audit` 中加入了作废行、修订行、被覆盖行和非美元换算样本等事件证据。这些字段从 `train_003` 迁移，而类别金额汇总和索赔特有异常 ID 仍属于本任务的数据探索点。
