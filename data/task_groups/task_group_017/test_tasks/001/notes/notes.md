# test_001 Notes

## English

### Data and source lineage

This task belongs to `task_group_017`, scenario `SCN_017_white_collar_investigation_production_review`. It is the Meridian Devices test task for matter `MTR-MERIDIAN-GJ`, designed from the task group brief for a grand jury rolling-production gap and coding-risk report. The source scenario examples are `E001`, `E002`, and `E003`, with the strongest operational transfer from `train_001` and `train_004`.

Solver-visible inputs are `input/prompt.txt`, `input/payloads/request_context.json`, and `input/payloads/answer_template.json`. Business evidence is meant to come from the shared Investigation Review Hub at `<TASK_ENV_BASE_URL>` through its public endpoints or the read-only query endpoint, not from local environment files or manifests.

The hidden construction facts used for the standard answer are:

- `SRC-MER-CARROW-PHONE`: Leo Carrow's phone was remote-erased after the subpoena, has source status `lost`, and affects `MD-15` and `MD-09`.
- `DOC-MER-DEALER-SAFETY`: dealer safety escalation document responsive to `MD-09`, coded nonresponsive, and not produced.
- `QC-MER-MD09-NR`: QC finding for one complaint/safety document miscoded nonresponsive.
- `PRIV-MER-LOG-GAP`: 2260 withheld privileged documents, 910 logged, leaving 1350 unlogged; the generated hub record is tied to `MD-11`.
- `SRC-MER-BOARD-ROOM`: board portal not collected, affecting `MD-07`, `MD-08`, and `MD-09`.

### Task definition and material map

The prompt asks for a structured legal operations report rather than a prose memorandum. The expected answer is a single JSON object with `matter_id`, `critical_findings`, `category_statuses`, `metrics`, and `priority_actions`. The answer template gives enum choices, field types, count precision, and ordering rules without exposing the target facts, scoring weights, endpoint call order, or review SOP.

The review hub endpoints provide matter metadata, request categories, production statistics, custodian-source records, review documents, privilege entries, QC findings, and remediation action candidates. The task-local `request_context.json` scopes the work to the Meridian matter and provides the read-only query header. It does not contain answer facts.

### Solution and evaluation basis

The standard answer has four root findings. Leo Carrow's phone erasure is a post-subpoena preservation failure because the source is lost after the subpoena/hold period; it affects `MD-09` and `MD-15` and requires government disclosure assessment plus forensic recovery. `DOC-MER-DEALER-SAFETY` and `QC-MER-MD09-NR` create an `MD-09` responsiveness miscoding gap because the responsive safety escalation was coded nonresponsive and not produced. `PRIV-MER-LOG-GAP` is an incomplete privilege-log issue for `MD-11`: 2260 withheld minus 910 logged equals 1350 unlogged privileged documents. `SRC-MER-BOARD-ROOM` is an uncollected board portal source affecting `MD-07`, `MD-08`, and `MD-09`.

The seven whole-point scoring goals are:

- `P1_phone_preservation`, weight 3: phone preservation failure, lost source status, `MD-09/MD-15` impacts, and disclosure or forensic remediation.
- `P2_md09_miscoded_safety_document`, weight 3: responsive safety document, QC reference, `MD-09`, not-produced impact, one document, and recode-and-produce action.
- `P3_privilege_log_gap`, weight 3: `MD-11`, 2260 withheld, 910 logged, 1350 unlogged, and protocol noncompliance.
- `P4_board_portal_gap`, weight 2: uncollected board portal, `MD-07/MD-08/MD-09`, source-missing impact, and collect-source action.
- `P5_category_status_matrix`, weight 2: correct category status rows for `MD-07`, `MD-08`, `MD-09`, `MD-11`, and `MD-15`.
- `P6_metrics_and_readiness`, weight 1: correct rollup metrics and `rolling_production_ready: false`.
- `P7_priority_action_set`, weight 3: required action set with action type, owner, target IDs, category impacts, and unique priority ranks.

The evaluator is deterministic. It normalizes ID and enum casing, treats arrays as sets for category and reference checks, requires exact integer counts, and awards each scoring point all-or-nothing. It does not score prose quality or incidental formatting beyond JSON parseability.

### Transfer design

This is a test task. The main transfer anchors are `train_001` and `train_004`. From `train_001`, a solver can infer the recurring treatment of a post-subpoena personal-device erasure as a preservation failure, the need to connect personal-source gaps to request categories, the handling of a responsive complaint/safety document coded nonresponsive, privilege-log arithmetic, board-source collection gaps, and action-owner-target conventions. From `train_004`, a solver can reinforce the responsiveness miscoding convention and the incomplete privilege-log calculation and status treatment.

Transfer-dependent scoring points are `P1`, `P2`, `P3`, `P4`, `P5`, and `P7`. `P6` also benefits from the same conventions but mainly checks aggregation consistency. Task-specific exploration remains necessary because the matter ID, category codes, source IDs, document IDs, counts, and board/source labels are different from the train tasks.

Likely model pitfalls include treating the phone erasure as only an uncollected source rather than a preservation failure, omitting one of the phone's category impacts, finding the safety document but not linking the QC row or production status, reporting 910 as the privilege gap instead of calculating 1350, leaving the board portal as a generic note without category impact, and providing free-form actions instead of controlled enum actions with owners and target IDs.

### Construction record

Author: Task-builder 06, Codex.

Created: 2026-07-18.

Updated: 2026-07-18.

Major changes: Created the complete formal `test_001` task folder with solver input, task-local context payload, answer template, standard answer, bilingual notes, rubric, and deterministic evaluator.

## 中文

### 数据与来源

本任务属于 `task_group_017`，场景为 `SCN_017_white_collar_investigation_production_review`。这是 Meridian Devices 的测试任务，事项编号为 `MTR-MERIDIAN-GJ`，按照任务组设计中的 grand jury rolling-production gap and coding-risk report 构建。源场景示例为 `E001`、`E002` 和 `E003`，最主要的迁移锚点来自 `train_001` 和 `train_004`。

求解者可见输入包括 `input/prompt.txt`、`input/payloads/request_context.json` 和 `input/payloads/answer_template.json`。业务证据应通过 `<TASK_ENV_BASE_URL>` 上的共享 Investigation Review Hub 获取，可以使用公开端点或只读查询端点，不能读取本地环境文件或清单。

标准答案使用的隐藏构造事实如下：

- `SRC-MER-CARROW-PHONE`：Leo Carrow 的手机在 subpoena 之后被远程擦除，source status 为 `lost`，影响 `MD-15` 和 `MD-09`。
- `DOC-MER-DEALER-SAFETY`：dealer safety escalation 文件响应 `MD-09`，但被编码为 nonresponsive，且未生产。
- `QC-MER-MD09-NR`：QC 记录显示一份 complaint/safety 文件被错误编码为 nonresponsive。
- `PRIV-MER-LOG-GAP`：2260 份特权文件被 withheld，其中 910 份已记录在日志中，因此有 1350 份未记录；生成环境中的该记录关联 `MD-11`。
- `SRC-MER-BOARD-ROOM`：board portal 未收集，影响 `MD-07`、`MD-08` 和 `MD-09`。

### 任务定义与材料映射

提示要求输出结构化 legal operations report，而不是普通散文式备忘录。预期答案是单个 JSON 对象，包含 `matter_id`、`critical_findings`、`category_statuses`、`metrics` 和 `priority_actions`。答案模板提供枚举选项、字段类型、整数精度和排序规则，但不暴露目标事实、评分权重、端点调用顺序或审查 SOP。

Review Hub 端点提供 matter metadata、request categories、production statistics、custodian-source records、review documents、privilege entries、QC findings 和 remediation action candidates。任务本地的 `request_context.json` 只限定 Meridian 事项并提供只读查询头，不包含答案事实。

### 解答和评估依据

标准答案有四个根问题。Leo Carrow 的手机在 subpoena/hold 期间之后被擦除，且 source 已 lost，因此属于 subpoena 后的 preservation failure；影响 `MD-09` 和 `MD-15`，需要进行政府披露评估并尝试 forensic recovery。`DOC-MER-DEALER-SAFETY` 和 `QC-MER-MD09-NR` 形成 `MD-09` 的 responsiveness miscoding gap，因为响应性的安全升级文件被编码为 nonresponsive 且未生产。`PRIV-MER-LOG-GAP` 是 `MD-11` 的 privilege log 不完整问题：2260 withheld 减去 910 logged 等于 1350 unlogged privileged documents。`SRC-MER-BOARD-ROOM` 是未收集的 board portal source，影响 `MD-07`、`MD-08` 和 `MD-09`。

七个整点评分目标为：

- `P1_phone_preservation`，权重 3：手机保全失败、lost source status、`MD-09/MD-15` 影响，以及 disclosure 或 forensic remediation。
- `P2_md09_miscoded_safety_document`，权重 3：响应性 safety document、QC reference、`MD-09`、not-produced impact、一份文件，以及 recode-and-produce action。
- `P3_privilege_log_gap`，权重 3：`MD-11`、2260 withheld、910 logged、1350 unlogged，以及 protocol noncompliance。
- `P4_board_portal_gap`，权重 2：未收集的 board portal、`MD-07/MD-08/MD-09`、source-missing impact，以及 collect-source action。
- `P5_category_status_matrix`，权重 2：`MD-07`、`MD-08`、`MD-09`、`MD-11` 和 `MD-15` 的正确 category status rows。
- `P6_metrics_and_readiness`，权重 1：正确汇总指标和 `rolling_production_ready: false`。
- `P7_priority_action_set`，权重 3：必要行动集合，包括 action type、owner、target IDs、category impacts 和唯一 priority ranks。

评估器是确定性的。它会规范化 ID 和枚举大小写，将 category 和 reference 数组按集合检查，整数计数必须精确匹配，每个评分点只能全得或不得分。它不评价自由文本质量，也不把无关格式差异作为独立评分点。

### 迁移设计

这是测试任务。主要迁移锚点是 `train_001` 和 `train_004`。从 `train_001` 中，求解者可以推断出：subpoena 后个人设备被擦除应作为 preservation failure 处理；个人来源缺口必须连接到请求类别；响应性 complaint/safety 文件被编码为 nonresponsive 时应作为生产缺口处理；privilege log 需要做差额计算；board source 未收集会形成类别层面的 collection gap；补救措施应使用 action-owner-target 的受控 JSON 结构。从 `train_004` 中，求解者可以进一步巩固 responsiveness miscoding 规则，以及 incomplete privilege log 的计算和状态处理。

依赖迁移的评分点是 `P1`、`P2`、`P3`、`P4`、`P5` 和 `P7`。`P6` 也受益于相同约定，但主要检查汇总一致性。任务本身仍需要新的探索，因为 matter ID、category codes、source IDs、document IDs、counts 和 board/source labels 都不同于训练任务。

常见模型错误包括：把手机擦除只当作未收集来源，而不是 preservation failure；遗漏手机影响类别之一；找到 safety document 但没有关联 QC 记录或生产状态；把 910 误当成 privilege gap，而不是计算 1350；把 board portal 写成泛泛备注而不映射到类别影响；使用自由文本行动而不是带 owner 和 target IDs 的受控枚举行动。

### 构建记录

作者：Task-builder 06，Codex。

创建日期：2026-07-18。

更新日期：2026-07-18。

主要变更：创建完整的 `test_001` 正式任务目录，包括求解者输入、任务本地 context payload、答案模板、标准答案、双语 notes、rubric 和确定性评估器。
