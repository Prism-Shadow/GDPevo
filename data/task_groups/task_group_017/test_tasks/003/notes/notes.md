# BriarGate SEC Custodian Production Issue Packet Notes

## English

Task ID: `test_003`

Author: Task-builder 08

Created: 2026-07-18

Updated: 2026-07-18

Source scenario: `SCN_017_white_collar_investigation_production_review`

Source examples: `E001`, `E002`, `E003`, with strongest lineage to `E003` because this task is an SEC custodian production, privilege, QC, and valuation-red-flag review.

This task asks a solver to prepare a structured production-issue packet for `MTR-BRIARGATE-SEC`. Solver-visible material is limited to `input/prompt.txt`, `input/payloads/review_scope.json`, `input/payloads/answer_template.json`, and the shared Investigation Review Hub at `<TASK_ENV_BASE_URL>`. The prompt is written as a realistic outside-counsel work request and intentionally avoids a workflow checklist, scoring criteria, transfer notes, and answer-like facts. The small `review_scope.json` identifies the matter, audience, allowed source class, and API key header for the read-only query endpoint without exposing the issue IDs.

The expected work process is cross-system review of custodian source status, retention/deletion records, document metadata, privilege entries, QC findings, and remediation action candidates. The solver should use shared environment endpoints only and should not read `env/` source files, SQLite files, hidden notes, or standard answers directly.

Scenario fit:

This task belongs to the white-collar investigation production-review scenario because it requires the same operational judgment as the source examples: reconstructing a production issue packet from scattered review-hub records, separating preservation and collection gaps from privilege defects, and escalating substantive investigation documents without turning the deliverable into a narrative memo. The task uses the fund-valuation SEC matter family and repeats the custodian-source, synchronized-folder loss, personal account, waiver, over-designation, miscoded-privilege, and valuation-red-flag patterns.

Material map:

- `input/prompt.txt` is the solver-facing work request.
- `input/payloads/review_scope.json` provides matter scope, the base URL placeholder, and the read-only query header.
- `input/payloads/answer_template.json` defines the required JSON shape, allowed enums, list-ordering rules, and integer-count precision.
- `GET /api/custodian-sources` and `POST /api/query` can expose `SRC-BRIAR-LIN-LAPTOP` and `SRC-BRIAR-LIN-PMAIL`.
- `GET /api/retention-events` can expose `RET-BRIAR-CLOUD-DEL` and its deletion/recovery counts.
- `GET /api/documents/search` can expose unrecovered files `DOC-BRIAR-SOLARIS-MODEL` and `DOC-BRIAR-NOVA-WATERFALL`, plus valuation red flags `DOC-BRIAR-NOVA-BACKSOLVE` and `DOC-BRIAR-SOLARIS-OVERRIDE`.
- `GET /api/privilege-log` can expose `PRIV-BRIAR-ADVISER-WAIVER` and `PRIV-BRIAR-OVERDESIG`.
- `GET /api/qc-findings` can expose `QC-BRIAR-MISCODED-PRIV`.
- `GET /api/remediation-actions` may help confirm that issue records have remediation candidates, but the standard action package uses task-level normalized action enums.

Standard answer basis:

- `SRC-BRIAR-LIN-LAPTOP`: Evelyn Lin's laptop was wiped after the hold on `2024-04-12`; status is `lost`; affected categories are `SEC-A` and `SEC-D`; this is a `post_hold_preservation_failure` requiring SEC disclosure assessment and forensic work.
- `RET-BRIAR-CLOUD-DEL`: 24 synchronized folder files were deleted after the hold; 17 were recovered and 7 remain unrecovered; affected categories are `SEC-B` and `SEC-C`.
- `DOC-BRIAR-SOLARIS-MODEL` and `DOC-BRIAR-NOVA-WATERFALL`: investigation-relevant unrecovered file IDs linked to the synchronized-folder deletion event.
- `SRC-BRIAR-LIN-PMAIL`: Evelyn Lin's ProtonMail source is uncollected; affected categories are `SEC-A` and `SEC-C`; it is a personal account collection gap.
- `PRIV-BRIAR-ADVISER-WAIVER`: four privileged emails were forwarded to an outside placement adviser; this is `third_party_waiver`.
- `PRIV-BRIAR-OVERDESIG`: 15 logistics emails were over-designated as privileged.
- `QC-BRIAR-MISCODED-PRIV`: 38 privileged documents were coded non-privileged.
- `DOC-BRIAR-NOVA-BACKSOLVE` and `DOC-BRIAR-SOLARIS-OVERRIDE`: substantive valuation red flags. The former is classified as `valuation_back_into`; the latter is classified as `unsupported_valuation_mark`.

The output schema uses normalized JSON fields and controlled enums for statuses, classifications, priorities, actions, and owners. Counts are integers. Lists are evaluated as stable ID sets unless the action-ranking point specifically checks rank placement.

Rubric, whole-point pass/fail:

| Point | Weight | Business outcome |
| --- | ---: | --- |
| `SP001` | 3 | Correct Lin laptop preservation failure with source ID, status, wipe date, impacts, priority, and action. |
| `SP002` | 3 | Correct synchronized-folder deletion event ID, deleted/recovered/unrecovered counts, and impacted categories. |
| `SP003` | 2 | Correct unrecovered investigation-relevant file IDs linked to the recovery gap. |
| `SP004` | 2 | Correct Lin ProtonMail collection gap, impacts, priority, and action. |
| `SP005` | 2 | Correct outside-placement-adviser third-party waiver classification, count, third party, priority, and action. |
| `SP006` | 1 | Correct over-designation defect, count, and cleanup action. |
| `SP007` | 2 | Correct miscoded privileged document QC defect, count, priority, and recode/clawback action. |
| `SP008` | 2 | Correct valuation red-flag document IDs and red-flag classifications. |
| `SP009` | 2 | Correct prioritized remediation package across preservation, collection, privilege, and valuation escalation targets. |

The nine scoring points cover at least four distinct outcomes: preservation/source risk, deletion recovery metrics, file-level unrecovered evidence, personal-account collection, privilege waiver, over-designation, QC miscoding, substantive valuation evidence, and action prioritization. The evaluator awards each point all-or-zero using deterministic normalized JSON checks and does not score prose quality.

Transfer design:

This is a test task anchored mainly to `train_003` and `train_004`. `train_003` anchors post-hold laptop loss, shared-drive or synchronized-folder deletion recovery, personal account collection gaps, separate unrecovered files and valuation red flags, and the shape of a custodian issue packet. `train_004` reinforces privilege/QC distinctions, especially the need to separate third-party waiver, over-designation, and privileged documents coded non-privileged. These anchors should help a fewshot solver recognize that the BriarGate laptop and cloud deletion are preservation/recovery issues, that ProtonMail is a source gap tied to request categories, that waiver and over-designation are not interchangeable, and that valuation red-flag document IDs must be surfaced separately from unrecovered file IDs.

Task-specific exploration remains necessary because all matter IDs, source IDs, document IDs, counts, dates, categories, and third-party descriptions differ from the train tasks. The prompt does not mention the transfer anchors or answer path, so the solver must infer the workflow from train examples and rediscover the BriarGate facts through the shared environment.

Likely model pitfalls include treating the laptop wipe as ordinary IT replacement, missing the 24/17/7 synchronized-folder counts, listing only unrecovered file IDs without the recovery event, merging waiver and over-designation into a generic privilege issue, using the privilege entry ID instead of `QC-BRIAR-MISCODED-PRIV` for the miscoding defect, omitting ProtonMail because it is outside company systems, and confusing unrecovered files with produced valuation red flags.

Construction record:

- 2026-07-18: Created complete `test_003` task-local prompt, scope payload, answer template, standard answer, rubric, deterministic evaluator, and bilingual notes.

## 中文

任务 ID：`test_003`

作者：Task-builder 08

创建日期：2026-07-18

更新日期：2026-07-18

来源场景：`SCN_017_white_collar_investigation_production_review`

来源示例：`E001`、`E002`、`E003`，其中与 `E003` 的关系最强，因为本任务同样是 SEC custodian production、privilege、QC 和 valuation red flag 审查。

本任务要求求解者为 `MTR-BRIARGATE-SEC` 准备结构化 production issue packet。求解者可见材料仅包括 `input/prompt.txt`、`input/payloads/review_scope.json`、`input/payloads/answer_template.json` 以及 `<TASK_ENV_BASE_URL>` 上的共享 Investigation Review Hub。提示词以真实外部律师工作请求的形式撰写，刻意不暴露操作清单、评分规则、迁移说明或答案事实。小型 `review_scope.json` 只提供 matter 范围、base URL 占位符和只读查询接口 header，不暴露问题 ID。

预期工作流程是跨系统审查 custodian source status、retention/deletion records、document metadata、privilege entries、QC findings 和 remediation action candidates。求解者只能使用共享环境端点，不应直接读取 `env/` 源文件、SQLite 文件、隐藏 notes 或标准答案。

场景契合度：

该任务属于 white-collar investigation production-review 场景，因为它要求与来源示例相同的运营判断：从分散的 review hub 记录重建 production issue packet，区分 preservation/collection gap 与 privilege defect，并将实质性调查文件升级处理，同时保持结构化 JSON 输出而非叙事备忘录。任务使用基金估值 SEC matter 家族，并复用 custodian source、synchronized-folder loss、personal account、waiver、over-designation、miscoded privilege 和 valuation red flag 等模式。

材料地图：

- `input/prompt.txt` 是求解者可见的工作请求。
- `input/payloads/review_scope.json` 提供 matter 范围、base URL 占位符和只读查询 header。
- `input/payloads/answer_template.json` 定义 JSON 形状、允许枚举、列表排序规则和整数精度。
- `GET /api/custodian-sources` 与 `POST /api/query` 可用于发现 `SRC-BRIAR-LIN-LAPTOP` 和 `SRC-BRIAR-LIN-PMAIL`。
- `GET /api/retention-events` 可用于发现 `RET-BRIAR-CLOUD-DEL` 以及删除、恢复、未恢复数量。
- `GET /api/documents/search` 可用于发现未恢复文件 `DOC-BRIAR-SOLARIS-MODEL`、`DOC-BRIAR-NOVA-WATERFALL`，以及估值红旗 `DOC-BRIAR-NOVA-BACKSOLVE`、`DOC-BRIAR-SOLARIS-OVERRIDE`。
- `GET /api/privilege-log` 可用于发现 `PRIV-BRIAR-ADVISER-WAIVER` 和 `PRIV-BRIAR-OVERDESIG`。
- `GET /api/qc-findings` 可用于发现 `QC-BRIAR-MISCODED-PRIV`。
- `GET /api/remediation-actions` 可辅助确认问题记录存在 remediation candidates，但标准行动包使用任务层面的规范化 action enums。

标准答案依据：

- `SRC-BRIAR-LIN-LAPTOP`：Evelyn Lin 的笔记本在 hold 之后于 `2024-04-12` 被擦除；状态为 `lost`；影响 `SEC-A` 和 `SEC-D`；这是 `post_hold_preservation_failure`，需要 SEC 披露评估和取证工作。
- `RET-BRIAR-CLOUD-DEL`：hold 之后删除了 24 个同步文件夹文件，其中 17 个已恢复，7 个未恢复；影响 `SEC-B` 和 `SEC-C`。
- `DOC-BRIAR-SOLARIS-MODEL` 与 `DOC-BRIAR-NOVA-WATERFALL`：与调查相关且未恢复的文件 ID，关联到同步文件夹删除事件。
- `SRC-BRIAR-LIN-PMAIL`：Evelyn Lin 的 ProtonMail 来源未收集；影响 `SEC-A` 和 `SEC-C`；这是个人账户收集缺口。
- `PRIV-BRIAR-ADVISER-WAIVER`：四封 privileged emails 被转发给 outside placement adviser；分类为 `third_party_waiver`。
- `PRIV-BRIAR-OVERDESIG`：15 封 logistics emails 被过度标记为 privileged。
- `QC-BRIAR-MISCODED-PRIV`：38 份 privileged documents 被编码为 non-privileged。
- `DOC-BRIAR-NOVA-BACKSOLVE` 与 `DOC-BRIAR-SOLARIS-OVERRIDE`：实质性估值红旗文件。前者分类为 `valuation_back_into`，后者分类为 `unsupported_valuation_mark`。

输出 schema 使用结构化 JSON 和受控枚举来表示 status、classification、priority、action 与 owner。数量字段均为整数。除 action ranking 评分点外，列表按稳定 ID 集合进行归一化评估。

评分规则为整点通过或失败：

| Point | Weight | 业务结果 |
| --- | ---: | --- |
| `SP001` | 3 | 正确识别 Lin laptop preservation failure，包括来源 ID、状态、擦除日期、影响类别、优先级和动作。 |
| `SP002` | 3 | 正确报告 synchronized-folder 删除事件 ID、删除/恢复/未恢复数量和影响类别。 |
| `SP003` | 2 | 正确识别未恢复且与调查相关的文件 ID，并关联到恢复缺口。 |
| `SP004` | 2 | 正确识别 Lin ProtonMail 收集缺口、影响类别、优先级和动作。 |
| `SP005` | 2 | 正确识别 outside-placement-adviser third-party waiver，包括数量、第三方、优先级和动作。 |
| `SP006` | 1 | 正确识别 over-designation 缺陷、数量和清理动作。 |
| `SP007` | 2 | 正确识别 privileged documents 被误编码的 QC 缺陷、数量、优先级和 recode/clawback 动作。 |
| `SP008` | 2 | 正确识别估值红旗 document IDs 和红旗分类。 |
| `SP009` | 2 | 正确给出覆盖 preservation、collection、privilege 和 valuation escalation 的优先 remediation package。 |

九个评分点覆盖至少四个不同业务结果：preservation/source risk、删除恢复指标、未恢复证据文件、个人账户收集、privilege waiver、over-designation、QC miscoding、估值实质证据和行动优先级。评估器使用确定性的 JSON 归一化检查，每个评分点整点通过或失败，不评价文字风格。

迁移设计：

本任务是 test task，主要锚定 `train_003` 和 `train_004`。`train_003` 锚定 hold 后 laptop loss、shared-drive 或 synchronized-folder deletion recovery、personal account collection gap、未恢复文件与估值红旗分离，以及 custodian issue packet 的输出形状。`train_004` 强化 privilege/QC 区分，尤其是第三方 waiver、over-designation 和 privileged documents coded non-privileged 需要分开处理。通过这些锚点，fewshot 求解者应能识别 BriarGate 的 laptop 和 cloud deletion 是 preservation/recovery 问题，ProtonMail 是与请求类别相关的 source gap，waiver 与 over-designation 不能互换，valuation red-flag document IDs 必须与 unrecovered file IDs 分开呈现。

任务仍需要特定探索，因为 matter IDs、source IDs、document IDs、数量、日期、类别和第三方描述都不同于训练任务。提示词不提及迁移锚点或答案路径，因此求解者必须从训练示例中推断工作方式，并通过共享环境重新发现 BriarGate 事实。

常见错误包括：把 laptop wipe 当成普通 IT replacement；漏掉 24/17/7 的同步文件夹数量；只列文件 ID 而不关联恢复事件；把 waiver 和 over-designation 合并成泛化 privilege issue；用 privilege entry ID 代替 `QC-BRIAR-MISCODED-PRIV` 作为 miscoding defect；因为 ProtonMail 不属于公司系统而漏掉个人账户缺口；以及混淆未恢复文件与已生产的估值红旗文件。

构建记录：

- 2026-07-18：创建完整 `test_003` 任务目录，包括提示词、scope payload、answer template、标准答案、rubric、确定性评估器和双语 notes。
