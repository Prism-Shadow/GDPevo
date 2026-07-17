# test_003 Notes

## English

### Data lineage and task source

This hidden notes file supports `task_group_017/test_tasks/003`. The task is derived from scenario `SCN_017_white_collar_investigation_production_review`, especially source example `E003`, and from the `task_group_017` design brief for the custodian/QC/privilege review family. The formal test task targets matter `M-LYN-322` and custodian `C-MR-118` in the generated shared environment under `task_group/task_group_017/env/`.

The solver-visible files are `input/prompt.txt` and `input/payloads/answer_template.json`. They are English-only and do not expose the SOP checklist or answer facts. The standard answer and evaluator use generated environment records from `matters.json`, `custodians.json`, `subpoena_categories.json`, `production_logs.json`, `collection_events.json`, `destruction_events.json`, `privilege_logs.json`, `qc_events.json`, and `documents.json`.

### Task definition and expected work

The business request is a custodian-level production issue review for the Lynxion Consulting Payments Investigation. The solver must use the shared API to identify preservation, collection, privilege, QC, and processing issues for `C-MR-118`, then return normalized JSON rather than a memorandum. The expected output follows the same broad schema family as `train_tasks/003`: overall status, issue findings, privilege actions, attachment failures, and ranked escalations.

The key constraints are exact integer counts, controlled enum values, sorted lists where the template says to sort, and no unstructured narrative answer. The target matter contains noisy same-matter categories and generated distractor records, so the intended work process is to reconcile the matter, custodian, category, collection, destruction, privilege, QC, production, and document-marker records rather than relying on a single table.

### Scenario fit

This task belongs to the white-collar investigation production-review scenario because it simulates a legal production team triaging a single custodian's preservation, collection, privilege, and processing issues before making supplemental production and notice decisions. It matches the `test_003` row in `scratch/task_group_design.md`: laptop wipe, shared-folder deletions, failed attachments, third-party forwarding, and first-pass privilege errors.

### Material map

Matter `M-LYN-322` supplies the DOJ Fraud Section context, subpoena date `2024-08-20`, hold date `2024-08-22`, deadline `2025-01-24`, production protocol flag, and regulator notice flag. Custodian `C-MR-118` identifies M. Rivas as Consulting Payments Director and lists the relevant sources: laptop, shared folder, personal Outlook, and email.

Subpoena categories `L-02`, `L-03`, `L-04`, `L-05`, and `L-06` are the scored affected categories. `L-02` covers the laptop and local files, `L-03` covers shared-folder payment files, `L-04` covers personal Outlook, `L-05` covers consultant communications and forwards, and `L-06` covers privilege coding and attachments.

Collection events `CE-0024`, `CE-0025`, and `CE-0026` provide the laptop wipe, shared-folder partial recovery, and uncollected personal Outlook evidence. Destruction events `DE-0006` and `DE-0007` corroborate the post-hold laptop wipe and shared-folder deletion. Production logs `PL-0028` through `PL-0032` summarize the affected category states. Privilege rows `PV-0010`, `PV-0011`, and `PV-0012` support waiver, over-designation, and miscoding findings. QC events `QC-0009`, `QC-0010`, and `QC-0011` provide the key counts for shared-folder recovery, privilege miscoding, and failed attachments. Document markers include `DOC-LYN-SHARED-001`, `DOC-LYN-SHARED-052`, `DOC-LYN-PRIV-001`, `DOC-LYN-PRIV-039`, `DOC-LYN-ATT-017`, and `DOC-LYN-ATT-031`.

### Solution and evaluation basis

The standard answer classifies the overall status as `needs_escalation` with `notice_recommended: true`. It contains seven present issue findings:

- `laptop_wipe`: post-hold spoliation, critical, category `L-02`, one affected and unrecovered laptop source, primary action `forensic_recovery`, secondary actions `custodian_declaration` and `regulator_notice`.
- `shared_drive_deletion`: post-hold spoliation, critical, category `L-03`, 52 deleted shared-folder files, 41 recovered, 11 unrecovered, primary action `regulator_notice`.
- `personal_email_gap`: uncollected source, high, category `L-04`, one uncollected personal Outlook source, primary action `supplemental_collection`.
- `privilege_waiver`: four legal-advice emails forwarded to outside consultant K. Sato, high, category `L-05`, primary action `waiver_assessment`.
- `privilege_overdesignation`: 18 business-only scheduling/logistics emails over-designated as privileged, medium, category `L-06`, primary action `privilege_review`.
- `privilege_miscoding`: 39 privileged investigation emails first-pass coded non-privileged and produced, high, category `L-06`, primary action `clawback_check`.
- `attachment_failure`: 31 failed attachments, medium, category `L-06`, split into 17 password-protected and 14 corrupt, primary action `reprocess_qc`.

The evaluator has 9 exact-match scoring points with raw weights `1, 2, 3, 2, 2, 1, 3, 2, 3`. It normalizes `category_ids`, `secondary_actions`, and ranked rows but otherwise treats each scoring point as all-or-nothing. The points cover target identity and status, laptop wipe after hold, shared-folder deletion and recovery counts, uncollected personal Outlook, four forwarded privileged emails and waiver risk, 18 over-designations, 39 privilege miscoding records and clawback, 31 failed attachments split 17/14, and the ranked escalation/action order. The standard answer must score 1.0.

Likely model pitfalls include using noisy `LY-N...` categories instead of the core `L-..` categories, treating partial shared-folder recovery as cured, missing the personal Outlook source because produced email exists elsewhere, confusing waiver with over-designation, missing that miscoded privileged records were produced and require clawback review, and ranking attachment reprocessing above post-hold preservation loss.

### Transfer design

The main train anchors are `train_tasks/003` and `train_tasks/004`, with secondary support from `train_tasks/005`. `train_003` anchors the custodian issue schema, the post-hold device loss and shared-drive deletion pattern, personal email collection gaps, third-party waiver analysis, attachment failure handling, and escalation ranking. `train_004` anchors privilege review conventions for business-only over-designation, first-pass privileged/non-privileged miscoding, privilege-log correction, and clawback checks. `train_005` reinforces that uncollected personal sources and hold-related collection gaps must be escalated even when other sources were collected.

The transfer-dependent difficulty is recognizing the recurring issue taxonomy and action order without a solver-visible checklist. The task-specific exploration difficulty is finding the `M-LYN-322` and `C-MR-118` records among noisy generated records and mapping the new category IDs and counts. High-value scoring goals that rely on transfer include the post-hold spoliation classification, waiver versus over-designation separation, clawback treatment for produced privileged records, and preservation-first escalation ranking.

### Construction record

Author: Codex task-builder subagent for `task_group_017 test_003`.
Created: 2026-07-07.
Updated: 2026-07-07.
Major changes: Created prompt, answer template, hidden bilingual notes, standard answer, and exact-match evaluator under `test_tasks/003/`.

## 中文

### 数据来源与任务来源

本隐藏说明文件用于 `task_group_017/test_tasks/003`。任务来自场景 `SCN_017_white_collar_investigation_production_review`，主要承接源示例 `E003` 的 custodian production set review，并依据 `task_group_017` 设计文档中的 custodian/QC/privilege review 测试任务。正式测试任务使用 `task_group/task_group_017/env/` 中的生成环境，目标 matter 是 `M-LYN-322`，目标 custodian 是 `C-MR-118`。

求解器可见文件为 `input/prompt.txt` 和 `input/payloads/answer_template.json`，均为英文，不泄露 SOP checklist 或答案事实。标准答案与评测器基于共享环境中的 matters、custodians、subpoena categories、production logs、collection events、destruction events、privilege logs、QC events 和 documents 等 JSON 数据。

### 任务定义与预期工作

本任务要求对 Lynxion Consulting Payments Investigation 中 M. Rivas 的 custodian production 风险进行结构化审查。求解器需要通过共享 API 识别保全、收集、privilege、QC 和处理失败问题，并输出符合模板的 JSON，而不是写叙述性备忘录。输出结构延续 `train_tasks/003` 的同一任务族，包括 overall status、issue findings、privilege actions、attachment failures 和 ranked escalations。

关键约束包括使用整数精确计数、控制枚举值、按模板要求排序列表、不得输出非结构化 memo。目标 matter 中存在同一 matter 的噪声类别和干扰记录，因此正确解题需要交叉核对 matter、custodian、category、collection、destruction、privilege、QC、production 和 document marker 记录，而不是只看单一表格。

### 场景契合度

该任务符合白领调查中的生产审查场景，模拟法律生产团队在补充生产和通知决策前，对单个 custodian 的保全、收集、privilege 和处理问题进行 triage。它对应 `scratch/task_group_design.md` 中的 `test_003`：laptop wipe、shared-folder deletions、failed attachments、third-party forwarding 和 first-pass privilege errors。

### 材料映射

`M-LYN-322` matter 记录提供 DOJ Fraud Section 背景、subpoena date `2024-08-20`、hold date `2024-08-22`、deadline `2025-01-24`、production protocol flag 和 regulator notice flag。`C-MR-118` custodian 记录表明 M. Rivas 是 Consulting Payments Director，相关来源包括 laptop、shared folder、personal Outlook 和 email。

评分相关类别为 `L-02`、`L-03`、`L-04`、`L-05` 和 `L-06`。`L-02` 对应 laptop and local files，`L-03` 对应 shared-folder payment files，`L-04` 对应 personal Outlook，`L-05` 对应 consultant communications and forwards，`L-06` 对应 privilege coding and attachments。

`CE-0024`、`CE-0025` 和 `CE-0026` 分别提供 laptop wipe、shared-folder 部分恢复和 personal Outlook 未收集的 collection evidence。`DE-0006` 和 `DE-0007` 佐证 hold 之后 laptop wipe 与 shared-folder deletion。`PL-0028` 至 `PL-0032` 提供各类别状态摘要。`PV-0010`、`PV-0011` 和 `PV-0012` 分别支撑 waiver、over-designation 和 miscoding 发现。`QC-0009`、`QC-0010` 和 `QC-0011` 给出 shared-folder recovery、privilege miscoding 和 failed attachments 的关键数量。

### 答案与评测依据

标准答案将 overall status 设为 `needs_escalation`，并设置 `notice_recommended: true`。七个 present issue findings 为：`laptop_wipe`、`shared_drive_deletion`、`personal_email_gap`、`privilege_waiver`、`privilege_overdesignation`、`privilege_miscoding` 和 `attachment_failure`。

核心评分事实包括：laptop 在 hold 后的 `2024-09-18` 被 wipe；52 个 shared-folder 文件被删除，其中 41 个 recovered、11 个 unrecovered；personal Outlook 被 produced emails 引用但未收集；4 封 legal-advice emails 转发给 consultant K. Sato 并产生 waiver risk；18 封 business-only scheduling/logistics emails 被 over-designated；39 封 privileged investigation emails 被 first-pass coded non-privileged 且已经 produced，需要 clawback check；31 个 failed attachments 分为 17 个 password-protected 和 14 个 corrupt；以及 escalation/action 的优先级排序。

评测器包含 9 个 exact-match 评分点，原始权重为 `1, 2, 3, 2, 2, 1, 3, 2, 3`。评测器会规范化 `category_ids`、`secondary_actions` 和 ranked rows，但每个评分点内部仍然是全有或全无。标准答案自检必须得到 1.0。

常见错误包括误用噪声 `LY-N...` 类别而不是核心 `L-..` 类别，将 shared-folder 部分恢复误认为完全修复，因为已有 produced email 而忽略 personal Outlook，混淆 waiver 与 over-designation，未识别已生产 privileged records 需要 clawback review，以及把 attachment reprocessing 排在 post-hold preservation loss 之前。

### 迁移设计

主要 train anchors 是 `train_tasks/003` 和 `train_tasks/004`，次要锚点为 `train_tasks/005`。`train_003` 锚定 custodian issue schema、hold 后 device loss 与 shared-drive deletion 模式、personal email collection gap、third-party waiver、attachment failure 处理和 escalation ranking。`train_004` 锚定 business-only over-designation、first-pass privileged/non-privileged miscoding、privilege-log correction 和 clawback check 的 privilege review 约定。`train_005` 强化 personal source 未收集和 hold-related collection gap 即使存在其他 collected sources 也需要升级处理。

迁移依赖的难点在于求解器需要从训练任务中归纳 issue taxonomy 和 action order，而 prompt 中不会给出 checklist。任务本地探索难点在于需要在噪声生成数据中找到 `M-LYN-322` 和 `C-MR-118` 的记录，并映射新的 category IDs 和 counts。高度依赖迁移的评分点包括 post-hold spoliation classification、waiver 与 over-designation 的区分、produced privileged records 的 clawback 处理，以及 preservation-first 的 escalation ranking。

### 构造记录

作者：Codex task-builder subagent for `task_group_017 test_003`。
创建日期：2026-07-07。
更新日期：2026-07-07。
主要变更：在 `test_tasks/003/` 下创建 prompt、answer template、隐藏双语 notes、standard answer 和 exact-match evaluator。
