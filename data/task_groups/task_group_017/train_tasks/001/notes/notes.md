# train_001 Notes

## English

### Data and source lineage

This task belongs to `task_group_017`, scenario `SCN_017_white_collar_investigation_production_review`. It is anchored mainly in source example `E001` and also uses recurring issue types from `E002` and `E003`: production gap analysis, preservation loss, privilege-log defects, custodian-source gaps, and responsiveness coding errors.

The formal task is the Sentinel Medical first rolling production gap analysis for matter `MTR-SENTINEL-GJ`. Solver-visible inputs are `input/prompt.txt`, `input/payloads/request_context.json`, and `input/payloads/answer_template.json`. The business evidence is intended to be discovered through the shared Investigation Review Hub at `<TASK_ENV_BASE_URL>`, not through local environment files.

The hidden construction facts used for the standard answer are the injected environment records for `MTR-SENTINEL-GJ`:

- `SRC-SENT-ALDEN-PHONE`: Nora Alden's personal iPhone was erased on 2025-02-04 after the 2025-01-27 subpoena, status `lost`, affecting `R15` and `R09`.
- `DOC-SENT-ALDEN-DEALER-ESC`: dealer complaint email dated 2024-10-18, responsive to `R09`, coded nonresponsive and not produced.
- `QC-SENT-R09-NR`: QC finding for one complaint email miscoded nonresponsive for `R09`, severity high.
- `PRIV-SENT-LOG-GAP`: `R11`, 3180 documents withheld, 1410 logged, so 1770 withheld documents are unlogged and the privilege log is incomplete.
- `SRC-SENT-BOARD-SP`: board SharePoint site not collected, affecting `R07`, `R08`, and `R09`.

### Task definition and material map

The prompt asks for a structured legal operations escalation packet rather than a prose memo. The expected answer is JSON with `matter_id`, `critical_findings`, `category_statuses`, `metrics`, and `priority_actions`. The template provides enum choices and ordering rules but does not disclose the answers, endpoint call sequence, scoring weights, or hidden SOP.

The review hub tables and endpoints supply the matter, request categories, production statistics, source status records, document metadata, privilege summary, QC findings, and remediation candidates. The task-local `request_context.json` only scopes the request to Sentinel Medical and the first rolling production workstream.

### Solution and evaluation basis

The standard answer has four root findings. The phone wipe is a preservation failure because it occurred after the subpoena and the source status is lost; it affects the personal-device and complaint communications categories `R15` and `R09`. The dealer complaint email and matching QC row create a responsiveness miscoding gap for `R09`; the document must be recoded and produced. The privilege-log issue is a protocol defect for `R11`: 3180 withheld minus 1410 logged equals 1770 unlogged documents. The board SharePoint source is a collection gap affecting `R07`, `R08`, and `R09`.

The seven whole-point scoring goals are:

- `P1_phone_preservation`, weight 3: phone preservation failure, lost status, `R09/R15` category impacts, and a disclosure or forensic action.
- `P2_r09_miscoded_complaint`, weight 3: complaint document and QC reference, `R09`, not produced impact, one document, and recode-and-produce action.
- `P3_privilege_log_gap`, weight 3: `R11`, 3180 withheld, 1410 logged, 1770 unlogged, and protocol noncompliance.
- `P4_board_sharepoint_gap`, weight 2: uncollected board SharePoint source, `R07/R08/R09`, source-missing impact, and collect-source action.
- `P5_category_status_matrix`, weight 2: correct category status rows for `R07`, `R08`, `R09`, `R11`, and `R15`.
- `P6_metrics_and_readiness`, weight 1: correct rollup metrics and `rolling_production_ready: false`.
- `P7_priority_action_set`, weight 3: required action set with action type, owner, target IDs, category impacts, and unique priority ranks.

The evaluator is deterministic and structured. It normalizes list ordering and string casing for enums and IDs, but each scoring point is all-or-nothing. It does not evaluate prose quality.

Likely model pitfalls include treating the phone wipe as a generic collection note rather than a post-subpoena preservation problem, finding the dealer complaint email but missing that it was coded nonresponsive and not produced, using the privilege `logged_count` as the gap rather than calculating 3180 minus 1410, and listing the board SharePoint source without mapping it to all three impacted categories.

### Transfer design

As a train task, this is not a tutorial. It is a solved example from which a fewshot skill generator can infer recurring task-group conventions: use the review hub rather than local files, map source and document defects to request categories, distinguish preservation failure from ordinary collection incompleteness, treat responsive nonresponsive-coded documents as production gaps, compute privilege-log arithmetic explicitly, and express remediation as controlled action-owner-target JSON.

The transfer value is intended for later unseen tasks, especially `test_001`, `test_004`, and `test_005`. Those tasks reuse the same business reasoning but change matter IDs, category codes, custodians, source systems, counts, and document facts.

### Construction record

Author: Task-builder 01, Codex.

Created: 2026-07-18.

Updated: 2026-07-18.

Major changes: Created the formal `train_001` task folder with solver input, answer template, request context payload, standard answer, bilingual notes, and deterministic evaluator.

## 中文

### 数据与来源

本任务属于 `task_group_017`，场景为 `SCN_017_white_collar_investigation_production_review`。它主要锚定源示例 `E001`，同时复用 `E002` 和 `E003` 中的常见问题类型：生产缺口分析、保全损失、特权日志缺陷、custodian source 缺口和 responsiveness 编码错误。

正式任务是 Sentinel Medical 在 `MTR-SENTINEL-GJ` 事项中的第一轮 rolling production gap analysis。求解者可见材料包括 `input/prompt.txt`、`input/payloads/request_context.json` 和 `input/payloads/answer_template.json`。业务证据应通过 `<TASK_ENV_BASE_URL>` 上的共享 Investigation Review Hub 查询，而不是读取本地环境文件。

标准答案使用的隐藏构造事实如下：

- `SRC-SENT-ALDEN-PHONE`：Nora Alden 的个人 iPhone 在 2025-02-04 被擦除，晚于 2025-01-27 的 subpoena；source status 为 `lost`，影响 `R15` 和 `R09`。
- `DOC-SENT-ALDEN-DEALER-ESC`：2024-10-18 的 dealer complaint email，响应 `R09`，但被编码为 nonresponsive，且未生产。
- `QC-SENT-R09-NR`：QC 记录显示一封 `R09` complaint email 被错误编码为 nonresponsive，严重性为 high。
- `PRIV-SENT-LOG-GAP`：`R11` 下 3180 份文件被 withheld，只有 1410 份进入 privilege log，因此有 1770 份 withheld 文件未记录，privilege log 不完整。
- `SRC-SENT-BOARD-SP`：board SharePoint site 未收集，影响 `R07`、`R08` 和 `R09`。

### 任务定义与材料映射

提示要求输出结构化的 legal operations escalation packet，而不是普通备忘录。预期答案是 JSON，包含 `matter_id`、`critical_findings`、`category_statuses`、`metrics` 和 `priority_actions`。模板给出 enum 选项和排序规则，但不暴露答案、端点调用顺序、评分权重或隐藏 SOP。

Review Hub 的表和端点提供 matter、request categories、production statistics、source status、document metadata、privilege summary、QC findings 和 remediation candidates。任务本地的 `request_context.json` 只用于限定 Sentinel Medical 和第一轮 production 工作流。

### 解法与评估依据

标准答案包含四个根问题。手机擦除发生在 subpoena 之后，且 source status 为 lost，因此属于 preservation failure，影响个人设备和 complaint communications 类别 `R15` 和 `R09`。Dealer complaint email 与对应 QC 记录构成 `R09` 的 responsiveness miscoding gap，需要 recode and produce。Privilege log 问题是 `R11` 的 protocol defect：3180 withheld 减去 1410 logged 等于 1770 unlogged。Board SharePoint source 未收集，构成 collection gap，影响 `R07`、`R08` 和 `R09`。

七个整点评分目标为：

- `P1_phone_preservation`，权重 3：手机保全失败、lost 状态、`R09/R15` 类别影响，以及 disclosure 或 forensic 行动。
- `P2_r09_miscoded_complaint`，权重 3：complaint document 和 QC reference、`R09`、not produced 影响、一份文件，以及 recode-and-produce 行动。
- `P3_privilege_log_gap`，权重 3：`R11`、3180 withheld、1410 logged、1770 unlogged，以及 protocol noncompliance。
- `P4_board_sharepoint_gap`，权重 2：未收集的 board SharePoint source、`R07/R08/R09`、source-missing 影响，以及 collect-source 行动。
- `P5_category_status_matrix`，权重 2：`R07`、`R08`、`R09`、`R11` 和 `R15` 的正确 category status rows。
- `P6_metrics_and_readiness`，权重 1：正确汇总指标和 `rolling_production_ready: false`。
- `P7_priority_action_set`，权重 3：必要行动集合，包括 action type、owner、target IDs、category impacts 和唯一 priority ranks。

评估器是确定性的结构化评分。它会规范化列表顺序以及 enum 和 ID 的大小写，但每个评分点只能全得或不得分。评估器不评价自由文本质量。

模型容易失败的地方包括：把手机擦除当作普通 collection note，而不是 subpoena 后的保全问题；找到 dealer complaint email 但遗漏它被编码为 nonresponsive 且未生产；把 privilege 的 `logged_count` 误当作缺口，而不是计算 3180 减 1410；列出 board SharePoint source 但没有映射到全部三个受影响类别。

### 迁移设计

作为训练任务，本任务不是教程。fewshot skill generator 可以通过该真实任务和标准答案推断出 task group 的可迁移约定：使用 review hub 而不是本地文件；把 source 和 document defect 映射到 request categories；区分 preservation failure 和普通 collection incompleteness；把 responsive 但 nonresponsive-coded 的文件视为生产缺口；显式计算 privilege-log arithmetic；并用受控的 action-owner-target JSON 表达补救措施。

迁移价值主要面向后续未见任务，尤其是 `test_001`、`test_004` 和 `test_005`。这些任务复用相同业务推理，但会改变 matter IDs、category codes、custodians、source systems、counts 和 document facts。

### 构造记录

作者：Task-builder 01，Codex。

创建日期：2026-07-18。

更新日期：2026-07-18。

主要变更：创建完整的 `train_001` 正式任务目录，包括求解者输入、答案模板、请求上下文 payload、标准答案、双语 notes 和确定性评估器。
