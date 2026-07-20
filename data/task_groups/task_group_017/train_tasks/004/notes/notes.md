# Northbay Therapeutics Production-Readiness Review

## English Notes

Data/source lineage: This is `train_004` for `task_group_017`, derived from scenario `SCN_017_white_collar_investigation_production_review` and source examples `E001`, `E002`, and `E003`. The task follows the group design brief for a Northbay Therapeutics SEC production review in matter `MTR-NORTHBAY-SEC`. The shared Investigation Review Hub supplies matter records, request categories, production statistics, document metadata, privilege entries, QC findings, source records, retention records, and remediation actions.

Task definition: The solver receives a formal business request to decide whether Northbay's next SEC production is ready. The solver must use `<TASK_ENV_BASE_URL>` and the allowed environment endpoints only. The output is a normalized JSON object with `matter_id`, `readiness_statuses`, `issue_ledger`, `privilege_corrections`, `metrics`, and `priority_actions`.

Scenario fit: This task remains in the same white-collar investigation production-review family as the source examples. It requires cross-system review of responsive-document coding, privilege-log completeness, third-party waiver, privilege QC, category impacts, and remediation priority. It is not a tutorial task; it is a solved formal training example whose answer demonstrates conventions that can transfer to later unseen matters.

Material map: The solver-visible prompt gives the matter and source restrictions. `review_scope.json` provides the target matter and API access details without answer facts. `answer_template.json` defines the controlled JSON shape, enum values, ordering, and numeric precision. The material hub records are `DOC-NORTH-TRIAL-RISK`, `PRIV-NORTH-LOG-GAP`, `PRIV-NORTH-CC-BIZ`, `PRIV-NORTH-CONSULTANT`, and `QC-NORTH-MISCODED-PRIV`.

Solution basis: The standard answer marks `SEC-C` and `SEC-D` as not production-ready and sets `production_ready` to false. `DOC-NORTH-TRIAL-RISK` is a `SEC-C` clinical-risk email that is responsive but coded nonresponsive and not produced, so it requires recode and production. `PRIV-NORTH-LOG-GAP` has 840 withheld privileged documents and 365 logged documents, leaving 475 unlogged documents. `PRIV-NORTH-CONSULTANT` is a five-document third-party waiver involving a trial consultant. `PRIV-NORTH-CC-BIZ` is a 27-document over-designation correction, and `QC-NORTH-MISCODED-PRIV` is a 31-document privilege recoding/QC issue.

Evaluation basis: The evaluator uses seven deterministic whole-point checks with raw weights `[2, 3, 3, 2, 2, 1, 3]`. The points cover category readiness, responsive miscoding, privilege-log arithmetic, waiver, privilege cleanup, metrics, and prioritized actions. Each point is all-or-nothing, normalizes IDs and enum casing, and checks counts as exact integers.

Transfer design: This task was restructured after calibration to provide a closer anchor for the production-readiness output family used by later tests. The important transferable patterns are: category readiness rows should name blocking refs and action classes; responsive miscoding is both a document issue and a category readiness blocker; privilege-log arithmetic is withheld minus logged; waiver is separate from ordinary over-designation; and the final action plan should use stable IDs, owners, and priority ranks.

Likely model pitfalls: A solver may include noisy routine hub records, omit the readiness layer, treat over-designation and waiver as the same issue, miss the 840 minus 365 arithmetic, or list actions without stable target references.

Construction record: Created by Task-builder 04 on 2026-07-18. Updated on 2026-07-19 during calibration rework. Major update: converted the task from a narrower privilege/QC defect report to a production-readiness structure while preserving the original Northbay evidence and material facts.

## 中文说明

数据和来源：这是 `task_group_017` 的 `train_004`，来源场景为 `SCN_017_white_collar_investigation_production_review`，参考示例为 `E001`、`E002` 和 `E003`。任务对应 Northbay Therapeutics 的 SEC 生产审查事项 `MTR-NORTHBAY-SEC`。共享 Investigation Review Hub 提供事项、请求类别、生产统计、文档元数据、特权日志、QC 发现、来源记录、留存记录和补救行动。

任务定义：求解者需要判断 Northbay 的下一轮 SEC 生产是否 ready。求解者只能使用 `<TASK_ENV_BASE_URL>` 和允许的环境端点，不能使用本地环境文件或清单。输出是规范化 JSON，包含 `matter_id`、`readiness_statuses`、`issue_ledger`、`privilege_corrections`、`metrics` 和 `priority_actions`。

场景匹配：本任务仍属于白领调查生产审查工作族，需要跨系统核对响应性编码、特权日志完整性、第三方 waiver、特权 QC、类别影响和补救优先级。它不是教程任务，而是一个已解答的正式训练样本，用来让 fewshot skill 从输入和标准答案中推断可迁移惯例。

材料地图：求解器可见 prompt 给出事项和来源限制。`review_scope.json` 提供目标事项和 API 访问方式，但不包含答案事实。`answer_template.json` 定义受控 JSON 结构、枚举、排序和整数计数精度。关键 hub 记录是 `DOC-NORTH-TRIAL-RISK`、`PRIV-NORTH-LOG-GAP`、`PRIV-NORTH-CC-BIZ`、`PRIV-NORTH-CONSULTANT` 和 `QC-NORTH-MISCODED-PRIV`。

答案依据：标准答案将 `SEC-C` 和 `SEC-D` 标为尚未 production-ready，并将 `production_ready` 设为 false。`DOC-NORTH-TRIAL-RISK` 是响应 `SEC-C` 的 clinical-risk 邮件，但被编码为 nonresponsive 且未生产，因此需要 recode and produce。`PRIV-NORTH-LOG-GAP` 有 840 份 withheld 特权文件，其中 365 份已记录在日志中，未记录数量为 475。`PRIV-NORTH-CONSULTANT` 是 5 份发给 trial consultant 的第三方 waiver。`PRIV-NORTH-CC-BIZ` 是 27 份 over-designation 修正，`QC-NORTH-MISCODED-PRIV` 是 31 份特权文件误编码为非特权的 QC 问题。

评估依据：评估器使用七个确定性的整点评分项，原始权重为 `[2, 3, 3, 2, 2, 1, 3]`。评分点覆盖类别 readiness、响应性错误编码、特权日志计算、waiver、特权清理、指标和优先级行动。每个评分点只能全得或不得分，会规范化 ID 和枚举大小写，并要求整数计数精确。

迁移设计：本任务在校准后被重构，用来更好地锚定后续测试中的 production-readiness 输出族。可迁移模式包括：类别 readiness 行应包含 blocker refs 和 action classes；响应性错误编码既是文档问题也是类别 readiness blocker；特权日志计算是 withheld 减 logged；waiver 与 ordinary over-designation 不同；最终 action plan 应使用稳定 ID、负责人和优先级排序。

常见模型错误：模型可能纳入噪声 hub 记录，遗漏 readiness 层，把 over-designation 和 waiver 混为一类，漏算 840 减 365，或列出没有稳定 target refs 的行动。

构建记录：Task-builder 04 于 2026-07-18 创建。2026-07-19 校准返工时更新。主要更新：在保留 Northbay 原始证据和实质事实的前提下，将任务从较窄的 privilege/QC defect report 改为 production-readiness 结构。
