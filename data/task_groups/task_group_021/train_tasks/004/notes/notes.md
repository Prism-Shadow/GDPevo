# train_004 Notes

## English

### Data lineage and task definition

This task belongs to `task_group_021`, scenario `SCN_021_data_cleaning_quality_pipeline`, source examples `E001`, `E002`, and `E003`. It is the CRM/contact reconciliation train task for the campaign member list `renewal_webinar_q3`.

Solver-visible input is `input/prompt.txt` plus `input/payloads/answer_template.json`. The prompt points to `<TASK_ENV_BASE_URL>` and the shared AsterOps workbench. The relevant environment records are:

- `/api/crm/campaign_members?campaign_id=renewal_webinar_q3`
- `/api/crm/contact_rows?batch_id=renewal_webinar_q3`
- `/api/reference/quality_rules?domain=crm`
- `/downloads/campaign_members_export.csv`
- `/downloads/crm_contact_rows_export.csv`

The business request is to reconcile the campaign members into a reachable qualified audience summary. The output must identify the campaign, count unique retained people, list hard-blocked/suppressed member IDs, list duplicate/review member IDs, count retained domains and segments, identify duplicate person keys, and provide a canonical retained-member sample.

### Solution basis

Campaign member rows for `renewal_webinar_q3` are `CM_REN_001` through `CM_REN_005`. Reachable qualified members must have a qualified campaign status (`registered` or `attended`), a usable canonical CRM contact, no hard blocking campaign status, no `do_not_contact` effective contact status, no revoked consent, and no suppression note on the effective retained contact. Duplicate campaign rows for the same `person_key` are resolved to one retained canonical member; the noncanonical duplicate member row is sent to manual review.

For `P_REN_001`, `CM_REN_001` is retained. The canonical contact is `CR_REN_025`: email `opted@example.com`, phone digits `3125550144`, domain `example.com`, segment `enterprise_renewal`.

For `P_REN_004`, campaign rows `CM_REN_002` and `CM_REN_005` are duplicates. `CM_REN_005` is retained because it is the attended duplicate with the higher score and the latest steward-corrected contact `CR_REN_032`; `CM_REN_002` needs manual review as the noncanonical duplicate member row. The retained email is `case@example.com`, phone digits `13125550166`, domain `example.com`, segment `enterprise_renewal`.

`CM_REN_003` is hard-blocked because the campaign status is `bounced` and the matching CRM person has revoked consent. `CM_REN_004` is hard-blocked because the campaign status is `unsubscribed`.

The standard answer therefore has:

- `qualified_reachable_count`: `2`
- `blocked_or_suppressed_ids`: `["CM_REN_003", "CM_REN_004"]`
- `needs_manual_review_ids`: `["CM_REN_002"]`
- `domain_counts`: `{"example.com": 2}`
- `segment_counts`: `enterprise_renewal = 2`, all other controlled segments = `0`
- `duplicate_person_keys`: `["P_REN_004"]`
- `canonical_member_sample`: retained members `P_REN_001` and `P_REN_004` ordered by `person_key`

### Evaluation

The evaluator has 8 scoring points, all exact-match business results:

1. Correct `campaign_id`, weight 1.
2. Correct `qualified_reachable_count`, weight 2.
3. Correct `blocked_or_suppressed_ids`, weight 2.
4. Correct `needs_manual_review_ids`, weight 2.
5. Correct `domain_counts`, weight 1.
6. Correct `segment_counts`, weight 1.
7. Correct `duplicate_person_keys`, weight 2.
8. Correct `canonical_member_sample`, weight 3.

List fields for blocked IDs, review IDs, and duplicate person keys are normalized as sets by sorting. The canonical sample is order-sensitive and should be ordered by `person_key`.

Likely model pitfalls include counting campaign member rows instead of unique people, treating `CM_REN_002` and `CM_REN_005` as two reachable members, ignoring the unsubscribed and bounced statuses, using stale contact row `CR_REN_028` instead of the latest steward-corrected `CR_REN_032`, retaining revoked-consent contacts, and counting domains or segments for blocked/review rows.

### Transfer design

As a train task, this teaches by answer comparison rather than by prompt instruction. Solvers can infer CRM contact reconciliation habits that transfer to later tasks: use environment APIs and downloads together, group duplicate people by `person_key`, normalize email domains and phone digits, separate hard suppression from manual review, and count only retained canonical records in aggregate summaries.

### Construction record

Author: task-builder subagent for `train_004`.
Created: 2026-07-07.
Updated: 2026-07-07.
Major changes: created prompt, answer template, standard answer, evaluator, and notes for `renewal_webinar_q3`.

## 中文

### 数据来源与任务定义

本任务属于 `task_group_021`，场景为 `SCN_021_data_cleaning_quality_pipeline`，来源样例为 `E001`、`E002`、`E003`。这是一个 CRM/联系人清洗训练任务，目标活动成员列表为 `renewal_webinar_q3`。

求解者可见输入包括 `input/prompt.txt` 和 `input/payloads/answer_template.json`。提示词使用 `<TASK_ENV_BASE_URL>` 指向共享 AsterOps 工作台。相关环境数据包括：

- `/api/crm/campaign_members?campaign_id=renewal_webinar_q3`
- `/api/crm/contact_rows?batch_id=renewal_webinar_q3`
- `/api/reference/quality_rules?domain=crm`
- `/downloads/campaign_members_export.csv`
- `/downloads/crm_contact_rows_export.csv`

业务目标是把活动成员整理成可触达且合格的受众汇总。输出需要包含活动 ID、唯一保留人数、硬性阻止或抑制的成员 ID、需要人工复核的成员 ID、保留成员的域名和分段计数、重复人员键，以及规范化后的保留成员样本。

### 标准答案依据

`renewal_webinar_q3` 的活动成员是 `CM_REN_001` 到 `CM_REN_005`。可触达合格成员必须具备合格活动状态（`registered` 或 `attended`）、可用的规范化 CRM 联系人、没有硬性阻止状态、有效联系人状态不是 `do_not_contact`、同意状态不是 `revoked`，且有效保留联系人没有 suppression 标记。同一 `person_key` 的重复活动成员只保留一个规范成员，未保留的重复成员进入人工复核。

`P_REN_001` 保留 `CM_REN_001`，规范联系人为 `CR_REN_025`，邮箱为 `opted@example.com`，电话数字为 `3125550144`，域名为 `example.com`，分段为 `enterprise_renewal`。

`P_REN_004` 有重复活动成员 `CM_REN_002` 和 `CM_REN_005`。保留 `CM_REN_005`，因为它是 attended 状态、分数更高，并且匹配最新 steward 修正联系人 `CR_REN_032`；`CM_REN_002` 是未保留的重复成员，需要人工复核。保留邮箱为 `case@example.com`，电话数字为 `13125550166`，域名为 `example.com`，分段为 `enterprise_renewal`。

`CM_REN_003` 被硬性阻止，因为活动状态为 `bounced`，并且匹配 CRM 人员同意状态为 revoked。`CM_REN_004` 被硬性阻止，因为活动状态为 `unsubscribed`。

因此标准答案为：

- `qualified_reachable_count`: `2`
- `blocked_or_suppressed_ids`: `["CM_REN_003", "CM_REN_004"]`
- `needs_manual_review_ids`: `["CM_REN_002"]`
- `domain_counts`: `{"example.com": 2}`
- `segment_counts`: `enterprise_renewal = 2`，其他受控分段均为 `0`
- `duplicate_person_keys`: `["P_REN_004"]`
- `canonical_member_sample`: 按 `person_key` 排序的 `P_REN_001` 和 `P_REN_004`

### 评估方式

评估器包含 8 个精确匹配评分点：

1. `campaign_id` 正确，权重 1。
2. `qualified_reachable_count` 正确，权重 2。
3. `blocked_or_suppressed_ids` 正确，权重 2。
4. `needs_manual_review_ids` 正确，权重 2。
5. `domain_counts` 正确，权重 1。
6. `segment_counts` 正确，权重 1。
7. `duplicate_person_keys` 正确，权重 2。
8. `canonical_member_sample` 正确，权重 3。

阻止 ID、复核 ID、重复人员键按集合处理并排序比较；规范成员样本要求按 `person_key` 排序，顺序敏感。

常见错误包括按活动成员行数而不是唯一人员计数、把 `CM_REN_002` 和 `CM_REN_005` 都计入可触达成员、忽略 unsubscribed 和 bounced 状态、使用旧的 `CR_REN_028` 而不是最新 steward 修正的 `CR_REN_032`、保留 revoked consent 联系人，以及把被阻止或复核的行计入域名和分段汇总。

### 迁移设计

作为训练任务，本任务通过标准答案对比让求解者归纳方法，而不是在提示词中教学。可迁移经验包括：结合环境 API 和下载文件、按 `person_key` 分组重复人员、规范化邮箱域名和电话数字、区分硬性抑制与人工复核、只用保留的规范记录做汇总。这些经验会迁移到后续 CRM 联系人和合作伙伴名单任务。

### 构建记录

作者：`train_004` task-builder subagent。
创建日期：2026-07-07。
更新日期：2026-07-07。
主要变更：为 `renewal_webinar_q3` 创建提示词、答案模板、标准答案、评估器和说明文件。
## Rework addendum / 返工补充

English: After calibration rework, the train answer includes `decision_audit` with business evidence for CRM/audience handling: source-precedence override person keys, duplicate campaign members requiring manual review, and suppressed or bounced member IDs. This records transfer from the CRM train task as recoverable source-row evidence.

中文：校准返工后，训练答案在 `decision_audit` 中加入了 CRM/受众处理的业务证据：来源优先级覆盖的人员键、需要人工复核的重复活动成员，以及被抑制或退信的成员 ID。该字段以可恢复的来源行证据记录从 CRM 训练任务迁移来的处理习惯。
