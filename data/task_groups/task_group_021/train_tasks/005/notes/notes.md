# train_005 Notes

## English

This task belongs to `task_group_021`, scenario `SCN_021_data_cleaning_quality_pipeline`, using source examples `E001`, `E002`, and `E003`. The task design brief is the train task for product/category normalization plus event integrity audit: clean August 2026 west facilities maintenance vendor charges before spend reporting.

Visible solver inputs are `input/prompt.txt` and `input/payloads/answer_template.json`. The shared environment provides the actual records through `<TASK_ENV_BASE_URL>`, especially `/api/catalog`, `/api/facilities/charges?scope=facilities_west&period=2026-08`, `/api/reference/category_aliases`, `/api/reference/quality_rules`, and `/downloads/facilities_charges_export.csv`. The hidden standard answer is `output/answer.json`; the evaluator is under `eval/`.

The target slice contains 11 facilities charge rows with `scope=facilities_west` and August 2026 charge dates. The effective spend set has 10 rows. `FC_W_003` is both invalid for reporting because it is `record_status=void` and superseded by amended row `FC_W_004` through `amends_charge_id=FC_W_003`. All retained target rows are USD with positive amounts.

Category normalization for the standard answer uses the charge `raw_category` matched to `reference_category_aliases` after case and whitespace normalization. Description aliases are not allowed to silently recategorize spend, but they are used to identify `source_conflict` review reasons when the best non-unknown description alias maps to a different category than the raw category. Unknown raw category aliases produce `ambiguous_alias`. This yields category counts `fuel=1`, `maintenance=5`, `freight=0`, `accessorial=3`, `claim=0`, `tax_fee=0`, and `unknown=1`. Spend by category is fuel `740.50`, maintenance `10335.93`, freight `0.00`, accessorial `9275.45`, claim `0.00`, tax_fee `0.00`, and unknown `4477.45`. The top adjusted-spend vendor is Bay Maintenance with `10062.18` across `FC_BG_0031`, `FC_BG_0110`, `FC_W_001`, and `FC_W_004`.

Review reason counts are exact controlled enum counts: `duplicate=0`, `invalid_amount=0`, `invalid_unit=0`, `missing_contact_channel=0`, `suppressed_contact=0`, `ambiguous_alias=1`, `superseded=1`, and `source_conflict=4`. The canonical sample records demonstrate the amended west work order, controlled category enums, and the generated unknown-category charge `FC_BG_0000`.

Scoring has 8 points with raw weights totaling 17:

- SP001, weight 2: exact `scope` and `effective_charge_count`.
- SP002, weight 2: exact `invalid_charge_ids` and `superseded_charge_ids`.
- SP003, weight 2: exact `category_counts` across all controlled category keys.
- SP004, weight 3: exact `spend_by_category_usd` to cents.
- SP005, weight 2: exact `top_vendor_by_adjusted_spend`.
- SP006, weight 2: exact `review_reason_counts` across all controlled review reasons.
- SP007, weight 3: exact canonical sample rows for `FC_W_001`, `FC_W_002`, `FC_W_004`, and `FC_W_005`.
- SP008, weight 1: exact ambiguous generated sample row `FC_BG_0000`.

Likely model pitfalls are filtering only the hand-seeded `FC_W_*` rows and missing generated August distractors, counting the void row as effective spend, treating the amended row as an extra duplicate instead of the replacement, using description text to rewrite spend categories, or omitting zero-valued category/reason keys. This train task reinforces transferable habits from the task group: use the environment rather than a stale extract, reconstruct effective records before aggregation, normalize aliases to controlled enums, preserve currency precision to cents, and separate spend classification from review flags.

Construction record: created by task-builder subagent for `train_005` on 2026-07-07. Files created under `task_group/task_group_021/train_tasks/005/` only.

## 中文

本任务属于 `task_group_021`，场景为 `SCN_021_data_cleaning_quality_pipeline`，来源示例为 `E001`、`E002`、`E003`。任务设计定位是训练任务中的“产品/类别归一化 + 事件有效记录审计”：在支出报表前清洗 2026 年 8 月西区设施维护供应商费用。

求解器可见输入只有 `input/prompt.txt` 和 `input/payloads/answer_template.json`。共享环境通过 `<TASK_ENV_BASE_URL>` 提供真实记录，关键入口包括 `/api/catalog`、`/api/facilities/charges?scope=facilities_west&period=2026-08`、`/api/reference/category_aliases`、`/api/reference/quality_rules` 和 `/downloads/facilities_charges_export.csv`。隐藏标准答案是 `output/answer.json`，评分器位于 `eval/`。

目标切片包含 11 条 `scope=facilities_west` 且费用日期在 2026 年 8 月的设施费用记录。有效支出集合包含 10 条记录。`FC_W_003` 因 `record_status=void` 不能进入报表，同时又被修订记录 `FC_W_004` 通过 `amends_charge_id=FC_W_003` 取代。所有保留的目标记录都是美元且金额为正。

标准答案的类别归一化使用费用记录的 `raw_category`，经过大小写和空白规范化后匹配 `reference_category_aliases`。描述字段中的别名不会直接改写支出类别，但会用于发现 `source_conflict`：当描述中最佳的非 unknown 别名映射到与 raw category 不同的类别时计为来源冲突。无法识别的 raw category 计为 `ambiguous_alias`。因此类别计数为 `fuel=1`、`maintenance=5`、`freight=0`、`accessorial=3`、`claim=0`、`tax_fee=0`、`unknown=1`。按类别支出为 fuel `740.50`、maintenance `10335.93`、freight `0.00`、accessorial `9275.45`、claim `0.00`、tax_fee `0.00`、unknown `4477.45`。调整后支出最高的供应商是 Bay Maintenance，金额 `10062.18`，对应 `FC_BG_0031`、`FC_BG_0110`、`FC_W_001` 和 `FC_W_004`。

复核原因计数使用受控枚举精确计数：`duplicate=0`、`invalid_amount=0`、`invalid_unit=0`、`missing_contact_channel=0`、`suppressed_contact=0`、`ambiguous_alias=1`、`superseded=1`、`source_conflict=4`。规范费用样本覆盖修订后的 west 工单、受控类别枚举，以及生成数据中的未知类别费用 `FC_BG_0000`。

评分共 8 个点，原始权重合计 17：

- SP001，权重 2：`scope` 和 `effective_charge_count` 精确匹配。
- SP002，权重 2：`invalid_charge_ids` 和 `superseded_charge_ids` 精确匹配。
- SP003，权重 2：所有受控类别键上的 `category_counts` 精确匹配。
- SP004，权重 3：`spend_by_category_usd` 精确到美分。
- SP005，权重 2：`top_vendor_by_adjusted_spend` 精确匹配。
- SP006，权重 2：所有受控复核原因上的 `review_reason_counts` 精确匹配。
- SP007，权重 3：`FC_W_001`、`FC_W_002`、`FC_W_004`、`FC_W_005` 的规范样本行精确匹配。
- SP008，权重 1：未知类别生成样本 `FC_BG_0000` 精确匹配。

常见模型错误包括只筛选手工种子 `FC_W_*` 记录而漏掉 8 月生成的干扰记录，把 void 行计入有效支出，把 amended 行当作额外重复而不是替代记录，用描述文本直接改写支出类别，或省略值为 0 的类别和复核原因键。该训练任务强化本任务组中的可迁移经验：使用共享环境而不是旧摘录，先重建有效记录再汇总，使用受控枚举做别名归一化，金额精确到美分，并区分支出分类与复核标记。

构建记录：由 `train_005` task-builder subagent 于 2026-07-07 创建。只在 `task_group/task_group_021/train_tasks/005/` 范围内创建文件。
