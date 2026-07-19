# test_005 Notes - Vireo Labs Cross-System Remediation Dashboard

## English

### Data/source lineage

This task belongs to `task_group_017`, scenario `SCN_017_white_collar_investigation_production_review`, with source-example lineage from `E001`, `E002`, and `E003`. It implements the `test_005` design brief from `scratch/task_group_design.md`: a Vireo Labs SEC remediation dashboard for matter `MTR-VIREO-SEC`.

The task-builder ownership scope is `task_group/task_group_017/test_tasks/005/`. Solver-visible files are `input/prompt.txt`, `input/payloads/matter_context.json`, and `input/payloads/answer_template.json`. The substantive evidence is in the shared Investigation Review Hub at `<TASK_ENV_BASE_URL>`, using the public business endpoints and optional read-only SQL endpoint with `X-API-Key: review-key-017`. The solver-visible files do not contain answer facts, scoring weights, hidden notes, or a workflow checklist.

The decisive shared-environment records are `RET-VIREO-LAB-POST`, `SRC-VIREO-CHEN-PHONE`, `SRC-VIREO-ARCHIVE`, `DOC-VIREO-INVESTOR-MISCODE`, `PRIV-VIREO-LOG-GAP`, `PRIV-VIREO-THIRD-PARTY`, `QC-VIREO-MISCODED-PRIV`, and `RET-VIREO-AUDIT-MISSING`.

### Task definition and scenario fit

The business assignment is a realistic legal-operations request from outside counsel. Vireo Labs is responding to an SEC investigation involving lab-results records and investor disclosures. The solver must aggregate retention events, custodian-source status, document coding, privilege entries, QC findings, request-category coverage, retained or available sources, metrics, and remediation ownership into one structured dashboard.

This fits the scenario because it combines the recurring white-collar production review workflows from the source examples: government request category mapping, preservation and retention timing, source collection gaps, privilege-log completeness, waiver analysis, document responsiveness errors, and remediation planning. The task is a test task, so it reuses conventions inferable from the train tasks but uses a new matter, new category code family, new counts, and a dashboard-oriented output shape.

### Material map

`input/prompt.txt` gives the user-facing request, the target matter, the `<TASK_ENV_BASE_URL>` source constraint, the query-key header, and the required JSON-only deliverable.

`input/payloads/matter_context.json` gives matter context, endpoint names, and the query header. It is not a source of answer facts.

`input/payloads/answer_template.json` defines required top-level keys, stable ordering rules, numeric precision, and controlled enums for issue types, statuses, source states, production impacts, action types, owners, and priorities.

The shared hub records supply the answer basis:

- `RET-VIREO-LAB-POST`: three lab-results archive boxes destroyed on `2025-03-20`, after the `2025-02-03` hold, affecting `VL-B` and `VL-H`.
- `SRC-VIREO-CHEN-PHONE`: Mei Chen personal phone not collected, affecting `VL-D` and `VL-J`.
- `SRC-VIREO-ARCHIVE`: cloud mail archive available for purged custodian mail, affecting `VL-D` and `VL-E`.
- `DOC-VIREO-INVESTOR-MISCODE`: investor-results complaint email responsive to `VL-I`, coded nonresponsive, and not produced.
- `PRIV-VIREO-LOG-GAP`: 1755 withheld privileged documents, 702 logged, leaving 1053 unlogged documents.
- `PRIV-VIREO-THIRD-PARTY`: three privileged emails forwarded to an outside CRO, creating third-party waiver risk.
- `QC-VIREO-MISCODED-PRIV`: 29 privileged investigation documents coded non-privileged.
- `RET-VIREO-AUDIT-MISSING`: 2025 QA audit should exist under the retention rule but is missing, affecting `VL-C` and `VL-H`.

### Solution and evaluation basis

The standard answer ranks seven top risks: post-hold lab archive loss; third-party waiver; miscoded investor complaint email; incomplete privilege log; miscoded privileged documents; uncollected personal phone; and missing QA audit. The available cloud mail archive is not ranked as a loss, but it appears in `retained_or_available_sources` and in the action plan because it is a remediation path for purged custodian mail.

The category coverage rollup covers eight affected categories: `VL-B`, `VL-C`, `VL-D`, `VL-E`, `VL-G`, `VL-H`, `VL-I`, and `VL-J`. `VL-H` is mixed because both the lab archive destruction and missing QA audit affect it. `VL-I` is mixed because it includes responsiveness miscoding, third-party waiver, and miscoded privileged-document corrections.

The evaluator has ten whole-point scoring goals with raw weights totaling 24:

- `P01_lab_archive_post_hold_loss`, weight 3: post-hold lab archive destruction, 3 boxes, `VL-B` and `VL-H`, and disclosure action.
- `P02_personal_phone_gap`, weight 2: Mei Chen phone not collected, `VL-D` and `VL-J`, and collection action.
- `P03_cloud_archive_available`, weight 2: available cloud mail archive for purged custodian mail, `VL-D` and `VL-E`, and archive-search action.
- `P04_investor_complaint_miscoding`, weight 3: responsive investor complaint email miscoded nonresponsive and not produced, with recode-and-produce action.
- `P05_privilege_log_arithmetic`, weight 3: 1755 withheld minus 702 logged equals 1053 unlogged, with category `VL-G` and supplement-log action.
- `P06_third_party_waiver`, weight 2: three privileged emails forwarded to outside CRO, category `VL-I`, and waiver action.
- `P07_miscoded_privileged_docs`, weight 2: 29 privileged investigation documents coded non-privileged, with privilege recode/log action.
- `P08_missing_qa_audit`, weight 2: required 2025 QA audit missing, `VL-C` and `VL-H`, and locate-record action.
- `P09_category_coverage_and_metrics`, weight 2: correct category coverage rows and integer rollup metrics.
- `P10_top_risk_ranking_and_action_plan`, weight 3: correct top-risk ordering and ranked action plan across all remediation targets.

The scoring points cover distinct outcomes: preservation loss, source collection, archive availability, responsiveness correction, privilege-log arithmetic, waiver, privilege QC miscoding, missing retained records, category/metric aggregation, and operational prioritization. Each point is all-or-zero and deterministic. The evaluator normalizes ID casing for categories, enum casing, integer-like values, record reference sets, and rank fields; it does not score prose.

Likely model pitfalls include treating the cloud archive as another loss instead of an available source, missing the 1053 privilege-log arithmetic, merging waiver and miscoded privileged documents into one generic privilege item, omitting `VL-H` from either lab loss or audit coverage, failing to connect the personal phone to both `VL-D` and `VL-J`, and ranking the available archive above unresolved loss and privilege defects.

### Transfer design

This test task is anchored to all five train tasks:

- `train_001` anchors production category status reconstruction, responsive documents coded nonresponsive, personal-device risk, privilege-log arithmetic, and action-owner normalization.
- `train_002` anchors hold-date timing, post-hold loss treatment, missing required audit records, and available archive exceptions.
- `train_003` anchors personal-source collection gaps, third-party waiver, privilege QC defects, and priority treatment of source loss versus remediable sources.
- `train_004` anchors the separation of responsiveness miscoding, incomplete privilege logs, third-party waiver, and privileged-coded-nonprivileged QC defects.
- `train_005` anchors post-hold off-site destruction, personal messaging/source gaps, archive availability as a remediation path, zero or underproduction skepticism, and ranked remediation actions.

The transfer-dependent points are high value but not direct copies. Vireo uses a different matter, SEC request category family, lab-results/investor-disclosure context, different counts, and an aggregate dashboard output. Solvers must still explore the shared hub and aggregate task-specific evidence.

### Construction record

Author: Task-builder 10 / Codex. Created: 2026-07-18. Updated: 2026-07-18. Major changes: created the complete formal `test_005` task folder with solver-visible prompt and payloads, hidden standard answer, bilingual notes, rubric, and deterministic evaluator.

## 中文

### 数据来源与任务定位

本任务属于 `task_group_017`，场景为 `SCN_017_white_collar_investigation_production_review`，来源示例为 `E001`、`E002` 和 `E003`。它实现了 `scratch/task_group_design.md` 中的 `test_005` 设计：针对 `MTR-VIREO-SEC` 的 Vireo Labs SEC 补救仪表盘。

任务构建者只负责 `task_group/task_group_017/test_tasks/005/`。求解者可见文件为 `input/prompt.txt`、`input/payloads/matter_context.json` 和 `input/payloads/answer_template.json`。实质证据来自 `<TASK_ENV_BASE_URL>` 上的共享 Investigation Review Hub，包括公开业务端点，以及带有 `X-API-Key: review-key-017` 的只读 SQL 查询端点。求解者可见文件不包含答案事实、评分权重、隐藏说明或操作清单。

关键共享环境记录是 `RET-VIREO-LAB-POST`、`SRC-VIREO-CHEN-PHONE`、`SRC-VIREO-ARCHIVE`、`DOC-VIREO-INVESTOR-MISCODE`、`PRIV-VIREO-LOG-GAP`、`PRIV-VIREO-THIRD-PARTY`、`QC-VIREO-MISCODED-PRIV` 和 `RET-VIREO-AUDIT-MISSING`。

### 任务定义与场景契合

业务请求来自外部律师团队，目标是为 Vireo Labs 的 SEC 调查响应准备结构化补救仪表盘。事项涉及实验室结果记录和投资者披露。求解者需要把 retention event、custodian source 状态、文档编码、privilege entry、QC finding、请求类别覆盖、仍可用来源、数值指标和补救责任人整合到一个 JSON 结果中。

该任务符合本场景，因为它结合了源示例中的典型白领调查生产审查工作：政府请求类别映射、保全和保存时间判断、来源收集缺口、特权日志完整性、waiver 分析、文档响应性编码错误以及补救计划。本任务是测试任务，会复用训练任务可推断的惯例，但使用新的事项、新的类别代码、新的数量和仪表盘式输出结构。

### 材料地图

`input/prompt.txt` 给出面向求解者的业务请求、目标事项、只能使用 `<TASK_ENV_BASE_URL>` 的限制、查询 key header，以及仅输出 JSON 的要求。

`input/payloads/matter_context.json` 提供 matter 背景、端点名称和查询 header。它不是答案事实来源。

`input/payloads/answer_template.json` 定义顶层字段、稳定排序规则、数值精度，以及 issue type、status、source state、production impact、action type、owner 和 priority 的受控枚举。

共享 hub 中的关键事实如下：

- `RET-VIREO-LAB-POST`：3 箱 lab-results archive 于 `2025-03-20` 销毁，晚于 `2025-02-03` hold，影响 `VL-B` 和 `VL-H`。
- `SRC-VIREO-CHEN-PHONE`：Mei Chen 的个人手机未收集，影响 `VL-D` 和 `VL-J`。
- `SRC-VIREO-ARCHIVE`：cloud mail archive 可用于已清除的 custodian mail，影响 `VL-D` 和 `VL-E`。
- `DOC-VIREO-INVESTOR-MISCODE`：investor-results complaint email 响应 `VL-I`，但被编码为 nonresponsive，且未生产。
- `PRIV-VIREO-LOG-GAP`：1755 份 privileged documents 被 withheld，702 份已记入日志，因此 1053 份未记录。
- `PRIV-VIREO-THIRD-PARTY`：3 封 privileged emails 被转发给外部 CRO，产生 third-party waiver 风险。
- `QC-VIREO-MISCODED-PRIV`：29 份 privileged investigation documents 被编码为 non-privileged。
- `RET-VIREO-AUDIT-MISSING`：2025 QA audit 按保存要求应存在但缺失，影响 `VL-C` 和 `VL-H`。

### 解答和评估依据

标准答案按优先级列出七个 top risks：hold 后 lab archive 损失、third-party waiver、投资者投诉邮件误编码、privilege log 不完整、privileged documents 被误编码、个人手机未收集、QA audit 缺失。cloud mail archive 不是损失本身，因此不放入 top loss risk 中，但它作为可补救来源出现在 `retained_or_available_sources` 和 `action_plan` 中。

类别覆盖包括八个受影响类别：`VL-B`、`VL-C`、`VL-D`、`VL-E`、`VL-G`、`VL-H`、`VL-I` 和 `VL-J`。`VL-H` 同时受 lab archive 销毁和 QA audit 缺失影响，因此是混合缺口。`VL-I` 同时涉及响应性误编码、third-party waiver 和 privileged-document 编码修正。

评估器包含十个整点评分目标，原始权重合计 24：

- `P01_lab_archive_post_hold_loss`，权重 3：hold 后 lab archive 销毁、3 箱、`VL-B` 和 `VL-H`、披露行动。
- `P02_personal_phone_gap`，权重 2：Mei Chen 手机未收集、`VL-D` 和 `VL-J`、个人设备收集行动。
- `P03_cloud_archive_available`，权重 2：cloud mail archive 对 purged custodian mail 可用、`VL-D` 和 `VL-E`、搜索归档行动。
- `P04_investor_complaint_miscoding`，权重 3：投资者投诉邮件 responsive 但编码为 nonresponsive 且未生产，需要 recode and produce。
- `P05_privilege_log_arithmetic`，权重 3：1755 withheld 减 702 logged 等于 1053 unlogged，类别为 `VL-G`，行动为补充日志。
- `P06_third_party_waiver`，权重 2：3 封 privileged emails 转发给外部 CRO，类别 `VL-I`，需要 waiver 行动。
- `P07_miscoded_privileged_docs`，权重 2：29 份 privileged investigation documents 被编码为 non-privileged，需要 privilege recode and log。
- `P08_missing_qa_audit`，权重 2：2025 QA audit 是应存在但缺失的记录，影响 `VL-C` 和 `VL-H`，需要定位记录。
- `P09_category_coverage_and_metrics`，权重 2：正确的类别覆盖行和整数汇总指标。
- `P10_top_risk_ranking_and_action_plan`，权重 3：正确的 top risk 排序，以及覆盖所有补救目标的排序行动计划。

这些评分点覆盖不同业务结果：保全损失、来源收集、归档可用性、响应性修正、特权日志计算、waiver、特权 QC 编码错误、应保存记录缺失、类别与指标汇总以及操作优先级。每个评分点只能全得或不得分。评估器规范化类别大小写、枚举大小写、整数值、记录引用集合和排序字段，不评价自由文本。

常见错误包括把 cloud archive 当成另一个损失而不是可用来源，漏掉 1053 的 privilege log 计算，把 waiver 和 miscoded privileged documents 合并成泛化 privilege 问题，遗漏 `VL-H` 同时受 lab loss 和 audit missing 影响，未把个人手机同时关联到 `VL-D` 和 `VL-J`，以及把可用 archive 排在未解决损失和 privilege defect 之前。

### 迁移设计

本测试任务以五个训练任务为迁移锚点：

- `train_001` 锚定 production category status 重建、responsive 文档被编码为 nonresponsive、个人设备风险、privilege-log arithmetic 和 action-owner 规范化。
- `train_002` 锚定 hold date 时间判断、hold 后损失处理、应存在 audit 记录缺失和 archive exception。
- `train_003` 锚定个人来源收集缺口、third-party waiver、privilege QC 缺陷，以及来源损失与可补救来源之间的优先级区分。
- `train_004` 锚定响应性误编码、privilege log 不完整、third-party waiver、privileged-coded-nonprivileged QC 缺陷之间的区分。
- `train_005` 锚定 hold 后异地销毁、个人消息或设备来源缺口、archive availability 作为补救路径、对零生产或生产不足的审慎核对，以及补救行动排序。

这些迁移点对应高价值评分项，但不是简单复制。Vireo 使用不同的 matter、SEC 请求类别、lab-results 和 investor-disclosure 背景、不同计数，以及聚合 dashboard 输出。求解者仍然需要在共享 hub 中探索并汇总任务特定证据。

### 构建记录

作者：Task-builder 10 / Codex。创建日期：2026-07-18。更新日期：2026-07-18。主要变更：创建完整正式 `test_005` 任务文件夹，包括求解者可见 prompt 和 payload、隐藏标准答案、双语 notes、rubric 和确定性 evaluator。
