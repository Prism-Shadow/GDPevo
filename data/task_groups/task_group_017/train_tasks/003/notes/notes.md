# Graycliff SEC Cross-System Remediation Dashboard Notes

## English

Task ID: `train_003`

Author: Task-builder 03; reworked by main agent during calibration rework.

Created: 2026-07-18

Updated: 2026-07-19

Source scenario: `SCN_017_white_collar_investigation_production_review`

This train task now asks for a cross-system remediation dashboard for `MTR-GRAYCLIFF-SEC`. The visible task material remains formal: the solver sees the prompt, `review_scope.json`, `answer_template.json`, and the shared Investigation Review Hub only. The prompt does not expose an answer procedure or scoring criteria.

The rework keeps the same Graycliff matter and real hub evidence, but changes the output from a one-off valuation packet to the same dashboard family used by other production-readiness tasks. This gives fewshot skill generation a second solved example for top-risk ranking, category coverage, waiver and privilege-miscoding separation, and rollup metrics.

Key answer facts:

- `RET-GRAY-SHARE-DEL`: post-hold shared-drive deletion with 37 deleted files, 29 recovered files, and 8 unrecovered files. The material unrecovered valuation documents are `DOC-GRAY-CASCADE-V3` and `DOC-GRAY-ORION-DRAFT`.
- `SRC-GRAY-HALE-LAPTOP`: Marcus Hale laptop was replaced and wiped after the hold, so it is a post-hold source loss affecting `SEC-1` and `SEC-4`.
- `SRC-GRAY-HALE-GMAIL`: personal Gmail source not collected, affecting `SEC-1` and `SEC-3`.
- `PRIV-GRAY-WINSLOW`: three privileged emails forwarded to Derek Winslow; this is a third-party waiver and is counted separately from incomplete-log metrics.
- `QC-GRAY-MISCODED-PRIV`: 45 privileged documents were initially coded nonprivileged and require privilege recoding.

The standard answer intentionally sets incomplete-log metrics to zero while separately reporting `third_party_waiver_doc_count = 3` and `miscoded_privileged_doc_count = 45`. This reinforces the transferable distinction between log-gap arithmetic and other privilege exposure counts.

Rubric, whole-point pass/fail:

| Point | Weight | Business outcome |
| --- | ---: | --- |
| `matter_id` | 1 | Correct Graycliff matter. |
| `shared_drive_post_hold_loss` | 3 | Correct shared-drive post-hold loss, unrecovered document refs, and volume. |
| `laptop_post_hold_loss` | 2 | Correct Hale laptop post-hold source loss. |
| `third_party_waiver` | 2 | Correct Winslow waiver count, third party, and action. |
| `miscoded_privileged_docs` | 2 | Correct 45-document privilege-miscoding QC finding. |
| `personal_email_source_gap` | 2 | Correct personal Gmail source gap. |
| `category_coverage_and_metrics` | 3 | Correct category rows and dashboard metrics. |
| `action_plan_order` | 3 | Correct action order for disclosure, waiver review, privilege recoding, and personal-source collection. |

Likely model pitfalls include summing waiver counts into incomplete-log metrics, treating the retained/recovered portion of the shared-drive event as eliminating the unrecovered loss, including routine Graycliff noise rows, and following raw hub action priority instead of the normalized legal-risk action plan required by the schema.

## 中文

任务 ID：`train_003`

作者：Task-builder 03；校准返工阶段由主 agent 重构。

创建日期：2026-07-18

更新日期：2026-07-19

来源场景：`SCN_017_white_collar_investigation_production_review`

本训练任务现在要求为 `MTR-GRAYCLIFF-SEC` 生成 cross-system remediation dashboard。求解者可见材料仍然是正式任务材料：prompt、`review_scope.json`、`answer_template.json` 和共享 Investigation Review Hub。提示词不暴露解题步骤或评分标准。

这次返工保留 Graycliff matter 及其真实 hub 证据，但把输出从一次性的 valuation packet 改为与其他 production-readiness 任务一致的 dashboard family。这样 fewshot skill 生成器能看到第二个 solved example，用来学习 top-risk 排序、category coverage、waiver 与 privilege miscoding 分离、以及 rollup metrics。

关键答案事实：

- `RET-GRAY-SHARE-DEL`：hold 后共享盘删除事件，37 个文件被删除，29 个恢复，8 个未恢复；重要未恢复估值文件是 `DOC-GRAY-CASCADE-V3` 与 `DOC-GRAY-ORION-DRAFT`。
- `SRC-GRAY-HALE-LAPTOP`：Marcus Hale 笔记本在 hold 后被替换并擦除，因此是影响 `SEC-1` 与 `SEC-4` 的 post-hold source loss。
- `SRC-GRAY-HALE-GMAIL`：个人 Gmail 未收集，影响 `SEC-1` 与 `SEC-3`。
- `PRIV-GRAY-WINSLOW`：三封 privileged emails 被转发给 Derek Winslow；这是 third-party waiver，应与 incomplete-log metrics 分开计数。
- `QC-GRAY-MISCODED-PRIV`：45 份 privileged documents 最初被编码为 nonprivileged，需要 privilege recoding。

标准答案故意把 incomplete-log metrics 设为 0，同时单独报告 `third_party_waiver_doc_count = 3` 和 `miscoded_privileged_doc_count = 45`。这强化了可迁移规则：log-gap arithmetic 与其他 privilege exposure counts 不能混算。

评分点均为整点通过或失败：

| Point | Weight | 业务结果 |
| --- | ---: | --- |
| `matter_id` | 1 | 正确识别 Graycliff matter。 |
| `shared_drive_post_hold_loss` | 3 | 正确识别共享盘 post-hold loss、未恢复文档引用和数量。 |
| `laptop_post_hold_loss` | 2 | 正确识别 Hale laptop post-hold source loss。 |
| `third_party_waiver` | 2 | 正确识别 Winslow waiver、数量、第三方和动作。 |
| `miscoded_privileged_docs` | 2 | 正确识别 45 份 privilege-miscoding QC finding。 |
| `personal_email_source_gap` | 2 | 正确识别 personal Gmail source gap。 |
| `category_coverage_and_metrics` | 3 | 正确给出 category rows 和 dashboard metrics。 |
| `action_plan_order` | 3 | 正确排序 disclosure、waiver review、privilege recoding 和 personal-source collection。 |

常见错误包括：把 waiver 数量加进 incomplete-log metrics；认为共享盘事件中已恢复的部分消除了未恢复损失；纳入 Graycliff routine noise rows；以及照抄 hub 原始 action priority，而不是按 schema 要求的 normalized legal-risk action plan 排序。
