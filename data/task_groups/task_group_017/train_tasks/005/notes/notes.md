# train_005 Notes: AlloyWorks Cross-System Remediation Dashboard

## English

### Data/source lineage

This task belongs to `task_group_017`, scenario `SCN_017_white_collar_investigation_production_review`, with source-example lineage from `E001`, `E002`, and `E003`. It is the formal train task `train_005` for the AlloyWorks DOJ antitrust subpoena matter `MTR-ALLOYWORKS-GJ`. The shared Investigation Review Hub contains the relevant matter, category, retention, custodian-source, document, privilege, QC, and remediation records.

The solver-visible materials are `input/prompt.txt`, `input/payloads/matter_context.json`, and `input/payloads/answer_template.json`. The substantive records must come from the hub at `<TASK_ENV_BASE_URL>`. No task-local payload contains the answer facts.

### Task definition and scenario fit

The business assignment asks for a cross-system remediation dashboard. The solver must rank material risks, summarize affected categories, identify retained or available remediation sources, report numeric metrics, and provide a ranked action plan. This fits the broader investigation-production workflow because it combines hold timing, privilege exceptions, source collection, archive availability, responsiveness coding, zero-production claim validation, and remediation ownership.

The output is normalized JSON with `matter_id`, `top_risks`, `category_coverage`, `retained_or_available_sources`, `metrics`, and `action_plan`. This structure was selected after calibration because it is the same output family used by later cross-system test tasks, while the underlying AlloyWorks facts remain a formal training problem.

### Material map

`input/prompt.txt` gives the user-facing matter request and requires use of the shared hub. `matter_context.json` gives the matter identifier, base URL placeholder, query key, and allowed endpoint inventory. `answer_template.json` defines controlled enum values, list ordering, whole-integer counts, stable identifier fields, and action-plan ranking.

The key environment records are `RET-ALLOY-BOX-POST`, `PRIV-ALLOYWORKS-001`, `PRIV-ALLOYWORKS-002`, `SRC-ALLOY-KLINE-SIGNAL`, `SRC-ALLOY-MORENO-SMS`, `SRC-ALLOY-TEAMS-ARCHIVE`, `QC-ALLOY-ZERO-CLAIM`, `DOC-ALLOY-BID-EMAIL-1`, and `DOC-ALLOY-BID-EMAIL-2`.

### Solution and evaluation basis

The standard answer ranks `RET-ALLOY-BOX-POST` first as a critical post-hold loss: six off-site bid-file boxes were destroyed after the hold, affecting categories `A`, `C`, and `F`, and requiring preservation-issue disclosure. The second risk is `PRIV-ALLOYWORKS-002`, a third-party waiver privilege entry in category `B` with 34 affected documents. The third risk is `QC-ALLOY-ZERO-CLAIM`, because two category `F` bid emails were responsive but coded nonresponsive and not produced, contradicting the zero-production claim and requiring recode and production. The fourth risk is `PRIV-ALLOYWORKS-001`, a privilege-log gap with 106 withheld documents, 34 logged documents, and 72 unlogged documents. The fifth and sixth risks are the uncollected personal messaging sources `SRC-ALLOY-KLINE-SIGNAL` and `SRC-ALLOY-MORENO-SMS`, both affecting `D` and `F`.

The retained remediation source is `SRC-ALLOY-TEAMS-ARCHIVE`, an available Teams archive for the deleted pricing channel affecting `D` and `E`. Category coverage rows summarize preservation loss for `A` and `C`, privilege corrections for `B`, source gap with archive availability for `D`, archive availability for `E`, and responsiveness underproduction for `F`. Required metrics include 6 top risks, 6 destroyed boxes, 1 post-hold loss event, 2 uncollected personal sources, 1 available archive, 2 miscoded responsive documents, 106 withheld privileged documents, 34 logged privilege documents, 72 unlogged privilege documents, 34 waiver documents, 0 missing required records, and 6 affected categories.

The evaluator has nine whole-point scoring goals with raw weights `[1, 3, 3, 2, 3, 2, 3, 2, 3]`: matter ID, post-hold loss, personal messaging risks, third-party waiver, privilege-log gap, Teams archive availability, zero-claim responsiveness miscoding, category coverage plus metrics, and action-plan order. Each point is all-or-nothing and checks structured IDs, enum values, category sets, counts, owners, ranks, and due-day limits.

### Transfer design

This task demonstrates transferable dashboard conventions without disclosing any later test answers. It anchors how to rank risks, keep available archives separate from open loss events, place privilege waiver and log remediation ahead of lower operational collection work, map each material issue to request categories, use stable hub IDs in both risk and action rows, and keep metric counts consistent with the issue ledger. Those conventions should transfer to unseen matters with different categories, record IDs, counts, and privilege issues.

### Likely model pitfalls

The main pitfalls are treating all source gaps as equal priority, missing the zero-production contradiction, counting the available archive as a top open risk, ignoring category coverage, treating waiver and log gaps as generic privilege noise, or copying owner/action text from remediation records without normalizing to the answer template.

### Construction record

Author: Task-builder 05 / Codex.

Created: 2026-07-18.

Updated: 2026-07-19.

Major changes: Converted the task from a narrower remediation-plan schema to a cross-system dashboard schema after formal calibration showed weak transfer to dashboard-style tests. Later calibration rework added real AlloyWorks privilege waiver and privilege-log issues so the train set includes a combined preservation, privilege, coding, personal-source, and archive dashboard.

## Chinese

### 数据来源与任务定位

本任务属于 `task_group_017`，场景为 `SCN_017_white_collar_investigation_production_review`，来源示例为 `E001`、`E002` 和 `E003`。这是 AlloyWorks DOJ 反垄断传票事项 `MTR-ALLOYWORKS-GJ` 的正式训练任务 `train_005`。共享 Investigation Review Hub 包含相关的事项、请求类别、留存、custodian source、文档、特权、QC 和补救记录。

求解器可见材料包括 `input/prompt.txt`、`input/payloads/matter_context.json` 和 `input/payloads/answer_template.json`。实体事实必须来自 `<TASK_ENV_BASE_URL>` 的 hub。任务本地 payload 不包含答案事实。

### 任务定义与场景契合

业务目标是生成一个跨系统 remediation dashboard。求解者需要排序 material risks，概括受影响类别，识别 retained or available remediation sources，报告数值指标，并给出排序后的行动计划。该任务契合调查生产审查流程，因为它结合了 hold 时间、特权例外、source collection、archive availability、responsiveness coding、zero-production claim validation 和 remediation ownership。

输出是规范化 JSON，包含 `matter_id`、`top_risks`、`category_coverage`、`retained_or_available_sources`、`metrics` 和 `action_plan`。这个结构是在校准后选定的，因为它与后续 cross-system 测试任务属于同一输出家族，同时 AlloyWorks 的实质事实仍保持正式训练问题。

### 材料地图

`input/prompt.txt` 给出面向求解者的事项请求，并要求使用共享 hub。`matter_context.json` 提供 matter 标识、base URL 占位符、查询密钥和允许端点清单。`answer_template.json` 定义受控枚举、列表排序、整数计数、稳定 ID 字段和 action-plan rank。

关键环境记录是 `RET-ALLOY-BOX-POST`、`PRIV-ALLOYWORKS-001`、`PRIV-ALLOYWORKS-002`、`SRC-ALLOY-KLINE-SIGNAL`、`SRC-ALLOY-MORENO-SMS`、`SRC-ALLOY-TEAMS-ARCHIVE`、`QC-ALLOY-ZERO-CLAIM`、`DOC-ALLOY-BID-EMAIL-1` 和 `DOC-ALLOY-BID-EMAIL-2`。

### 答案与评测依据

标准答案将 `RET-ALLOY-BOX-POST` 排在第一位，认定为 critical post-hold loss：6 箱异地投标文件在 hold 后被销毁，影响 `A`、`C`、`F`，需要披露 preservation issue。第二个风险是 `PRIV-ALLOYWORKS-002`，它是类别 `B` 中 34 份文件的 third-party waiver 特权条目。第三个风险是 `QC-ALLOY-ZERO-CLAIM`，因为两封类别 `F` 的 bid emails 实际 responsive，但被编码为 nonresponsive 且未生产，推翻了 zero-production claim，需要 recode and produce。第四个风险是 `PRIV-ALLOYWORKS-001`，它有 106 份 withheld 文件、34 份 logged 文件和 72 份 unlogged 文件。第五和第六个风险是未收集的个人消息来源 `SRC-ALLOY-KLINE-SIGNAL` 与 `SRC-ALLOY-MORENO-SMS`，都影响 `D` 和 `F`。

可用补救来源是 `SRC-ALLOY-TEAMS-ARCHIVE`，它是已删除 pricing Teams channel 的可用归档，影响 `D` 和 `E`。类别覆盖行分别概括 `A` 和 `C` 的 preservation loss，`B` 的 privilege corrections，`D` 的 source gap with archive availability，`E` 的 archive availability，以及 `F` 的 responsiveness underproduction。必需指标包括 6 个 top risks、6 箱被销毁、1 个 post-hold loss event、2 个 uncollected personal sources、1 个 available archive、2 份 miscoded responsive documents、106 份 withheld privileged documents、34 份 logged privilege documents、72 份 unlogged privilege documents、34 份 waiver documents、0 个 missing required records 和 6 个 affected categories。

评估器包含九个整点评分目标，原始权重为 `[1, 3, 3, 2, 3, 2, 3, 2, 3]`：matter ID、post-hold loss、personal messaging risks、third-party waiver、privilege-log gap、Teams archive availability、zero-claim responsiveness miscoding、category coverage plus metrics，以及 action-plan order。每个评分点只能全得或不得分，并检查结构化 ID、枚举、类别集合、计数、负责人、排序和 due-day 限制。

### 迁移设计

本任务展示 dashboard 类任务的可迁移惯例，但不披露任何后续测试答案。它锚定了如何排序风险、把 available archive 与 open loss event 分开、把 privilege waiver 和 log remediation 放在较低运营性 collection 工作之前、把每个 material issue 映射到请求类别、在 risk 和 action 行中使用稳定 hub ID，并保持指标计数与 issue ledger 一致。这些惯例应迁移到使用不同类别、记录 ID、计数和 privilege issues 的未知事项。

### 常见模型错误

常见错误包括把所有 source gaps 视为同等优先级，漏掉 zero-production contradiction，把 available archive 计为 top open risk，忽略 category coverage，把 waiver 和 log gap 当作普通 privilege 噪声，或者直接复制 remediation records 中的 owner/action 文本而不按 answer template 规范化。

### 构建记录

作者：Task-builder 05 / Codex。

创建时间：2026-07-18。

更新时间：2026-07-19。

主要变更：正式校准显示 dashboard 类测试迁移较弱后，将任务从较窄的 remediation-plan schema 改为 cross-system dashboard schema。后续校准返工加入真实 AlloyWorks privilege waiver 和 privilege-log issues，使训练集包含 preservation、privilege、coding、personal-source 和 archive 组合 dashboard。
