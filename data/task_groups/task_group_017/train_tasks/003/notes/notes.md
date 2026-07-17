# train_003 Notes

## English

### Data lineage and task source

This hidden notes file supports `task_group_017/train_tasks/003`. The task is derived from scenario `SCN_017_white_collar_investigation_production_review`, especially source example `E003`, the custodian production set review. The formal task is not a copy of the example; it uses the generated shared environment under `task_group/task_group_017/env/` and targets matter `M-GCF-088` with custodian `C-HL-033`.

The solver-visible files are:

- `input/prompt.txt`, which asks for a structured custodian production issue review.
- `input/payloads/answer_template.json`, which defines the required JSON shape, enums, integer-count precision, and ordering rules.

The answer and evaluator use generated environment records from:

- `env/data/generated/matters.json`
- `env/data/generated/custodians.json`
- `env/data/generated/subpoena_categories.json`
- `env/data/generated/production_logs.json`
- `env/data/generated/collection_events.json`
- `env/data/generated/destruction_events.json`
- `env/data/generated/privilege_logs.json`
- `env/data/generated/qc_events.json`
- `env/data/generated/documents.json`

### Task definition and expected work

The business request is a custodian-level production issue review for the Granite Crest Fund advisory-fee investigation. The solver must use the shared API to identify preservation, collection, privilege, QC, and processing issues for `C-HL-033`, then return normalized JSON instead of a memorandum. The key constraints are English-only solver-visible materials, no SOP checklist in the prompt, and exact integer counts for issue quantities.

Expected work includes reconciling matter metadata, subpoena categories, custodian records, collection events, destruction events, production logs, privilege logs, QC events, and document markers. The solver should ignore noisy same-matter records for other custodians and unrelated generated categories.

### Scenario fit

This task belongs to the custodian/QC/privilege review operation family described in `scratch/task_group_design.md`. It exercises the same real workflow as E003: post-hold loss analysis, incomplete source collection, privilege waiver, over-designation, first-pass privilege miscoding, attachment processing failures, and action ranking. The structured output converts a legal review memorandum into exact-match fields while preserving the long-horizon cross-source investigation.

### Material map

Matter record `M-GCF-088` supplies the hold date `2024-07-09`, subpoena date `2024-07-08`, agency, deadline, and issue summary.

Custodian record `C-HL-033` identifies H. Lang as Portfolio Operations Lead and lists relevant sources: work laptop, shared drive, Gmail, and email.

Subpoena categories `G-02`, `G-03`, `G-04`, `G-05`, and `G-06` define affected business areas: board/investor materials, shared-drive working files, personal email/external forwards, privilege/clawback review, and attachments/encrypted files.

Collection events `CE-0008`, `CE-0009`, and `CE-0010` are the primary source for laptop wipe, shared-drive recovery, and Gmail non-collection. Destruction events `DE-0004` and `DE-0005` corroborate the post-hold laptop wipe and shared-drive deletion.

Production logs `PL-0007`, `PL-0008`, and `PL-0009` provide category-level privilege, waiver, clawback, and attachment statuses.

Privilege log rows `PV-0003`, `PV-0004`, and `PV-0005` provide the three privileged emails forwarded externally, 12 business-only over-designations, and 45 privileged documents coded non-privileged.

QC events `QC-0002`, `QC-0003`, and `QC-0004` provide counts for 37 shared-drive deletions with 29 recovered and 8 unrecovered, 45 privileged miscoded documents, and 23 failed attachments. Document markers `DOC-GCF-SHARED-001`, `DOC-GCF-SHARED-008`, `DOC-GCF-PRIV-001`, `DOC-GCF-PRIV-045`, `DOC-GCF-ATT-014`, and `DOC-GCF-ATT-023` corroborate those counts and statuses.

### Solution and evaluation basis

The standard answer classifies the overall review as `needs_escalation` with `notice_recommended: true`. It includes seven issue findings:

- `laptop_wipe`: post-hold spoliation, critical, categories `G-02` and `G-03`, one unrecovered source, primary action `forensic_recovery`, secondary actions `custodian_declaration` and `regulator_notice`.
- `shared_drive_deletion`: post-hold spoliation, critical, category `G-03`, 37 affected files, 29 recovered, 8 unrecovered, primary action `regulator_notice`.
- `personal_email_gap`: uncollected source, high, category `G-04`, one missing Gmail source, primary action `supplemental_collection`.
- `privilege_waiver`: three privileged emails forwarded to an outside banker, high, category `G-04`, primary action `waiver_assessment`.
- `privilege_overdesignation`: 12 business-only records over-designated as privileged, medium, category `G-05`, primary action `privilege_review`.
- `privilege_miscoding`: 45 privileged documents first-pass coded non-privileged and produced, high, category `G-05`, primary action `clawback_check`.
- `attachment_failure`: 23 failed attachments, medium, category `G-06`, split into 14 password-protected and 9 corrupt, primary action `reprocess_qc`.

The evaluator has 9 exact-match scoring points with raw weights:

- SP001, weight 1: target matter/custodian, overall status, notice recommendation.
- SP002, weight 2: laptop wipe issue fields.
- SP003, weight 3: shared-drive deletion counts and action.
- SP004, weight 2: personal Gmail gap fields.
- SP005, weight 2: waiver issue and privilege action.
- SP006, weight 1: over-designation issue and privilege action.
- SP007, weight 3: miscoding/clawback issue and privilege action.
- SP008, weight 2: attachment failure issue and 14/9 split.
- SP009, weight 3: ranked escalation order and primary actions.

The evaluator normalizes `category_ids`, `secondary_actions`, and ranked rows where needed, but each scoring point is all-or-nothing. It ignores unscored narrative text and allows extra fields. The standard answer self-check must score 1.0.

Likely model pitfalls include relying only on production logs and missing collection/QC overrides, treating recovered shared-drive files as fully cured despite 8 unrecovered files, omitting personal Gmail because it is not in production counts, failing to distinguish waiver from over-designation, and ranking attachment processing failures above post-hold deletion.

### Transfer design

As a train task, this file should help a solver infer recurring task-group conventions after comparing attempts against the answer: collection and QC events can override production tracker completeness; post-hold device loss and unrecovered deleted files receive the highest escalation; uncollected personal sources are separate collection gaps; third-party forwarding is waiver risk; business-only privilege claims are over-designations; produced privileged documents require clawback review; and ranked escalations should prioritize preservation loss before privilege cleanup and attachment reprocessing. The answer also teaches field naming, enum use, issue ID style, category sorting, and rank ordering for the corresponding test custodian review family.

### Construction record

Author: Codex task-builder subagent for `task_group_017 train_003`.
Created: 2026-07-07.
Updated: 2026-07-07.
Major changes: Created prompt, answer template, hidden bilingual notes, standard answer, and exact-match evaluator under `train_tasks/003/`.

## 中文

### 数据来源与任务来源

本隐藏说明文件用于 `task_group_017/train_tasks/003`。任务来自场景 `SCN_017_white_collar_investigation_production_review`，主要对应源示例 `E003` 的 custodian production set review。正式任务不是简单复制原示例，而是使用 `task_group/task_group_017/env/` 中生成的共享环境，目标 matter 为 `M-GCF-088`，目标 custodian 为 `C-HL-033`。

求解器可见文件包括 `input/prompt.txt` 和 `input/payloads/answer_template.json`。前者提出结构化 custodian production issue review 请求，后者规定 JSON 结构、枚举、整数计数精度和排序规则。标准答案和评测基于共享环境中的 matters、custodians、subpoena categories、production logs、collection events、destruction events、privilege logs、QC events 和 documents 等 JSON 数据。

### 任务定义与预期工作

本任务要求对 Granite Crest Fund advisory-fee investigation 中 H. Lang 的 custodian production 风险进行结构化审查。求解器需要从共享 API 中交叉核对保全、收集、销毁、production、privilege、QC 和 document marker 记录，输出标准 JSON，而不是写备忘录。重要约束是求解器可见材料必须为英文，prompt 不能泄露答案或 SOP checklist，关键数量必须使用整数精确填写。

求解器需要识别并排除同一 matter 中其他 custodian 的噪声记录，以及生成数据中的无关类别和干扰项。

### 场景契合度

该任务属于 task group 设计中的 custodian/QC/privilege review 操作族。它复现 E003 的核心业务复杂度：hold 之后的设备或共享盘损失、个人邮箱未收集、privilege waiver、over-designation、first-pass privilege miscoding、附件处理失败，以及最终升级和行动排序。结构化输出将法律备忘录中的关键判断转化为可精确评测的字段。

### 材料映射

`M-GCF-088` matter 记录提供 hold date、subpoena date、监管机构、deadline 和 issue summary。`C-HL-033` custodian 记录说明 H. Lang 的角色及相关来源，包括 work laptop、shared drive、Gmail 和 email。

类别 `G-02`、`G-03`、`G-04`、`G-05`、`G-06` 分别对应 board/investor materials、shared-drive working files、personal email/external forwards、privilege/clawback review 和 attachments/encrypted files。

`CE-0008`、`CE-0009`、`CE-0010` 是 laptop wipe、shared-drive recovery 和 Gmail 未收集的主要 collection evidence。`DE-0004` 和 `DE-0005` 佐证 hold 之后 laptop wipe 与 shared-drive deletion。`PL-0007`、`PL-0008`、`PL-0009` 提供 category 级别的 waiver、clawback 和 attachment 状态。`PV-0003`、`PV-0004`、`PV-0005` 对应三封 privileged emails 转发给 outside banker、12 份 business-only over-designation、45 份 privileged documents 被 first-pass coded non-privileged。`QC-0002`、`QC-0003`、`QC-0004` 给出共享盘删除恢复、privilege miscoding 和附件失败的关键数量。

### 答案与评测依据

标准答案将 overall status 设为 `needs_escalation`，并设置 `notice_recommended: true`。七个 issue findings 分别为 laptop wipe、shared-drive deletion、personal email gap、privilege waiver、privilege overdesignation、privilege miscoding 和 attachment failure。

评测器包含 9 个 exact-match 评分点，原始权重为 1、2、3、2、2、1、3、2、3。重点评分事实包括：laptop 在 hold 后被 wipe；37 个 shared-drive 文件被删除，其中 29 个 recovered、8 个 unrecovered；personal Gmail 未收集；三封 privileged emails 被转发给 outside banker 并产生 waiver risk；12 份 business-only records 被 over-designated；45 份 privileged documents first-pass coded non-privileged 且需要 clawback check；23 个 failed attachments 分成 14 个 password-protected 和 9 个 corrupt；以及 ranked escalations/actions 的顺序。

评测器会规范化 category_ids、secondary_actions 和 ranking rows，但每个评分点内部仍是全有或全无。标准答案自检应得分 1.0。

### 迁移设计

作为 train task，本任务用于让求解器在对照答案后归纳 task group 内可迁移的做法：collection/QC 事件可以覆盖 production tracker 的表面完整性；hold 后的设备损失和未恢复删除文件优先级最高；未收集的个人来源应作为独立 collection gap；转发给第三方是 waiver risk；business-only 的 privilege claim 是 over-designation；已生产的 privileged documents 需要 clawback review；升级排序应先处理 preservation loss，再处理 privilege cleanup 和 attachment reprocessing。答案还提供 issue_id、枚举、类别排序和 ranking 字段的格式约定，可迁移到 test 中的 custodian review 任务。

### 构造记录

作者：Codex task-builder subagent for `task_group_017 train_003`。
创建日期：2026-07-07。
更新日期：2026-07-07。
主要变更：在 `train_tasks/003/` 下创建 prompt、answer template、隐藏双语 notes、standard answer 和 exact-match evaluator。
