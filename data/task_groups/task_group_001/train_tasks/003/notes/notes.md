# train_003 Hidden Notes

## English

This task belongs to source scenario `SCN_001_crm_marketing_lead_capture`, using source examples `E001`, `E002`, and especially `E003` for contact-data hygiene. It implements the task-group design brief for `train_003`: clean and summarize the HarborCRM raw campaign batch `fall_webinar_import` for CRM import. The shared environment data is in `task_group/task_group_001/env/data/harborcrm_data.json`; public solver access is through the HarborCRM API endpoints for import batches, raw contacts, suppression, CRM accounts, CRM contacts, and policies. The only task-local solver payload is `input/payloads/answer_template.json`.

The solver-visible task asks for a CRM-ready JSON summary, not a mutation of the CRM. The expected output includes batch metadata, surviving cleaned contacts, duplicate metadata, removal metadata, action totals, and the campaign member count. The visible prompt deliberately avoids a procedural SOP list; solvers must inspect the public policy endpoint and reconcile the raw batch with CRM and suppression data.

The important source records are raw rows `fw_001` through `fw_008`. `fw_002` wins over `fw_001` for Dana Ruiz because the normalized email matches and `fw_002` is more recent. `fw_008` wins over `fw_003` for Evan Blake because the normalized email and timestamp match, and `partner_upload` outranks `webinar_form` in source priority. `fw_005` survives as an email-only contact. `fw_006` is unusable because it lacks both normalized email and normalized phone. `fw_004` and `fw_007` are suppressed: `fw_004` also matches an opted-out existing CRM contact, and `fw_007` appears in the suppression list. HelioWare already exists as CRM account `acct_helio_ware`, so Dana Ruiz is an `update_existing` import action with no existing contact id. Monarch Foods and Quartz Foods have no matching CRM account and use `create_account`.

The material map is:

- `GET /api/import_batches` identifies campaign code `WEB-FALL-2026` for `fall_webinar_import`.
- `GET /api/import_batches/fall_webinar_import/raw_contacts` provides the raw rows to normalize, suppress, dedupe, and import.
- `GET /api/import_batches/fall_webinar_import/suppression` provides suppression matches by normalized email or phone.
- `GET /api/crm/accounts` determines whether a surviving contact maps to an existing account.
- `GET /api/crm/contacts` identifies opted-out existing contacts and possible existing contact matches.
- `GET /api/policies` exposes the general normalization, dedupe, and source-priority conventions.

The standard answer in `output/answer.json` has three clean contacts sorted by row id: `fw_002`, `fw_005`, and `fw_008`. Email values are lowercase and trimmed. Phone values are digits-only, preserving a leading country digit when present in the winning row. Duplicate removal count is `2`, with duplicate keys `email:dana.ruiz@helioware.example` and `email:evan.blake@quartzfoods.example`. Removal counts are one unusable row and two suppressed rows. Import action totals are `create_account: 2`, `update_existing: 1`, `no_import: 3`, and `suppress: 2`. Campaign member import count is `3`.

The evaluator has seven scoring points, matching the design:

- SP001, weight 3: exact ordered surviving cleaned contact IDs.
- SP002, weight 2: normalized email values by survivor id.
- SP003, weight 2: normalized phone values by survivor id.
- SP004, weight 2: duplicate removal count and duplicate keys with winner and removed row ids.
- SP005, weight 2: unusable and suppressed removal counts with the relevant removed rows.
- SP006, weight 2: import action totals.
- SP007, weight 1: campaign member import count.

Likely pitfalls include keeping both duplicate rows, picking the webinar form over the partner upload on equal timestamp, dropping Kenji Sato because the phone is blank, treating suppressed rows as ordinary `no_import` rather than `suppress`, normalizing Evan Blake from the losing row instead of the winning row, and assuming HelioWare requires account creation even though it exists in CRM.

As a train task, this should teach transfer habits for `test_003`: read public policies, normalize before matching, suppress before final import, handle existing opted-out contacts, dedupe by normalized email before phone-company keys, and prefer the most recent/highest-priority source record. The train-derived skill should capture the shape of the hygiene workflow without memorizing these row ids.

Construction record: created by Codex task-builder for `train_003` on 2026-06-01. Initial version created `prompt.txt`, `answer_template.json`, `answer.json`, `eval.sh`, `evaluator.py`, and these bilingual notes.

## 中文

本任务属于源场景 `SCN_001_crm_marketing_lead_capture`，参考了源示例 `E001`、`E002`，并主要继承 `E003` 的联系人数据清洗主题。它实现了任务组设计中的 `train_003`：为 HarborCRM 的原始营销批次 `fall_webinar_import` 清洗并汇总 CRM 导入结果。共享环境数据位于 `task_group/task_group_001/env/data/harborcrm_data.json`；求解器通过 HarborCRM API 读取导入批次、原始联系人、抑制名单、CRM 账户、CRM 联系人和策略。任务本地对求解器可见的载荷只有 `input/payloads/answer_template.json`。

求解器可见任务要求输出一个可导入 CRM 的 JSON 摘要，而不是修改 CRM 系统。期望输出包括批次元数据、保留下来的清洗联系人、重复行信息、移除行信息、导入动作汇总和 campaign member 数量。可见提示刻意不列出操作 SOP；求解器需要查看公开策略接口，并把原始批次与 CRM、抑制名单数据进行核对。

关键源记录是 `fw_001` 到 `fw_008`。Dana Ruiz 的 `fw_002` 胜过 `fw_001`，因为标准化邮箱相同且 `fw_002` 更新时间更晚。Evan Blake 的 `fw_008` 胜过 `fw_003`，因为标准化邮箱和时间戳相同，但 `partner_upload` 的优先级高于 `webinar_form`。`fw_005` 作为只有邮箱的联系人保留。`fw_006` 因没有标准化邮箱也没有标准化电话而不可用。`fw_004` 和 `fw_007` 被抑制：`fw_004` 同时匹配已有的 opt-out CRM 联系人，`fw_007` 出现在抑制名单中。HelioWare 已经有 CRM 账户 `acct_helio_ware`，所以 Dana Ruiz 的导入动作为 `update_existing`，但没有已有联系人 id。Monarch Foods 和 Quartz Foods 没有匹配的 CRM 账户，所以动作为 `create_account`。

材料映射如下：

- `GET /api/import_batches` 用于确认 `fall_webinar_import` 的 campaign code 是 `WEB-FALL-2026`。
- `GET /api/import_batches/fall_webinar_import/raw_contacts` 提供需要标准化、抑制、去重和导入的原始行。
- `GET /api/import_batches/fall_webinar_import/suppression` 提供按标准化邮箱或电话匹配的抑制记录。
- `GET /api/crm/accounts` 用于判断保留联系人是否属于已有账户。
- `GET /api/crm/contacts` 用于识别已有 opt-out 联系人以及可能的已有联系人匹配。
- `GET /api/policies` 暴露通用的标准化、去重和来源优先级规则。

标准答案 `output/answer.json` 中有三个按行 id 排序的清洗联系人：`fw_002`、`fw_005` 和 `fw_008`。邮箱转为小写并去除首尾空格。电话只保留数字，并按获胜行保留开头的国家码数字。重复移除数量是 `2`，重复 key 为 `email:dana.ruiz@helioware.example` 和 `email:evan.blake@quartzfoods.example`。移除统计中有一个不可用行和两个抑制行。导入动作汇总为 `create_account: 2`、`update_existing: 1`、`no_import: 3`、`suppress: 2`。Campaign member 导入数量是 `3`。

评估器包含七个评分点，与设计一致：

- SP001，权重 3：保留清洗联系人 id 的精确顺序。
- SP002，权重 2：按保留 id 检查标准化邮箱。
- SP003，权重 2：按保留 id 检查标准化电话。
- SP004，权重 2：重复移除数量、重复 key、获胜行和被移除行。
- SP005，权重 2：不可用和抑制移除数量，以及相关移除行。
- SP006，权重 2：导入动作汇总。
- SP007，权重 1：campaign member 导入数量。

常见错误包括保留重复行、在相同时间戳时选择 webinar form 而不是 partner upload、因为 Kenji Sato 电话为空而错误删除、把抑制行当成普通 `no_import` 而不是 `suppress`、用失败行而不是获胜行来标准化 Evan Blake 的电话，以及忽略 HelioWare 已经在 CRM 中存在而错误创建新账户。

作为训练任务，它应帮助 `test_003` 迁移以下习惯：读取公开策略，先标准化再匹配，在最终导入前处理抑制名单，识别已有 opt-out 联系人，优先按标准化邮箱去重，再按电话加公司去重，并选择最近或更高优先级来源的记录。训练技能应总结这种清洗工作流，而不是记忆本任务的具体行 id。

构建记录：由 Codex task-builder 于 2026-06-01 为 `train_003` 创建。初版创建了 `prompt.txt`、`answer_template.json`、`answer.json`、`eval.sh`、`evaluator.py` 和本双语 notes。
