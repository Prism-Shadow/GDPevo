# test_003 Hidden Notes

## English

This task belongs to source scenario `SCN_001_crm_marketing_lead_capture`, using source examples `E001`, `E002`, and especially `E003` for CRM contact-import hygiene. It implements the task-group design brief for `test_003`: prepare the HarborCRM raw import batch `q1_partner_import` for CRM import while respecting existing CRM records and suppression. The shared environment data is in `task_group/task_group_001/env/data/harborcrm_data.json`; public solver access is through the HarborCRM API endpoints for import batches, raw contacts, suppression, CRM accounts, CRM contacts, and policies. The only task-local solver payload is `input/payloads/answer_template.json`.

The solver-visible task asks for a structured CRM-ready JSON summary, not a CRM mutation. The expected output includes batch metadata, surviving cleaned contacts, duplicate metadata, removal metadata, import action totals, and the campaign-member import count plus source label. The visible prompt is intentionally compact and does not expose the contact-hygiene SOP as a step list; solvers are expected to infer and apply the public policies and train-derived conventions.

The important source records are raw rows `q1_001` through `q1_008`. `q1_002` wins over `q1_001` for Hana Park because the normalized email matches and `q1_002` is more recent, even though its source priority is lower. `q1_008` wins over `q1_007` for Miles Chen because the normalized email matches and `q1_008` is later and comes from `badge_scan`. `q1_003` survives as an existing LakeHealth account contact with no existing contact id. `q1_004` survives as a phone-only new account. `q1_005` is unusable because it has neither normalized email nor normalized phone. `q1_006` is suppressed through the batch suppression list. Riverbend Chemical already exists as CRM account `acct_riverbend_chem`, and Hana Park matches existing contact `cont_hana_park`; LakeHealth Robotics already exists as `acct_lakehealth`, but Pia Norberg has no existing contact. DeltaForge Tools and Cascadia Steel are new account creates.

The material map is:

- `GET /api/import_batches` identifies campaign code `PARTNER-Q1-2027` and source label `partner_and_manual_upload` for `q1_partner_import`.
- `GET /api/import_batches/q1_partner_import/raw_contacts` provides rows `q1_001` through `q1_008` to normalize, suppress, dedupe, and import.
- `GET /api/import_batches/q1_partner_import/suppression` identifies the suppressed Lia Foster row via `lia.foster@crownassembly.example` and phone `13135550104`.
- `GET /api/crm/accounts` determines existing account updates for Riverbend Chemical and LakeHealth Robotics.
- `GET /api/crm/contacts` identifies `cont_hana_park` as an existing stale Riverbend contact and confirms that Pia Norberg, Noah Kim, and Miles Chen are not existing contacts.
- `GET /api/policies` exposes the normalization, source-priority, and dedupe conventions needed to resolve the batch.

The standard answer in `output/answer.json` has four clean contacts sorted by row id: `q1_002`, `q1_003`, `q1_004`, and `q1_008`. Email values are lowercase and trimmed. Phone values are digits-only from the winning row, so Hana Park's winning row has `7135550138` rather than the country-prefixed phone from the losing row. Duplicate removal count is `2`, with duplicate keys `email:hana.park@riverbendchem.example` and `email:miles.chen@cascadiasteel.example`. Removal counts are one unusable row and one suppressed row. Import action totals are `create_account: 2`, `update_existing: 2`, `no_import: 3`, and `suppress: 1`. Campaign member import is count `4` with source label `partner_and_manual_upload`.

The evaluator has six scoring points, matching the design:

- SP001, weight 3: exact ordered surviving cleaned contact IDs.
- SP002, weight 3: normalized email and phone values by survivor id.
- SP003, weight 2: duplicate resolution winners and removed row ids.
- SP004, weight 2: unusable and suppressed removal counts with the relevant removed rows.
- SP005, weight 2: create/update/no-import/suppress action totals.
- SP006, weight 1: campaign member count and source label.

Likely pitfalls include choosing the higher-priority but older `q1_001` over `q1_002`, mixing the winning Hana row's email with the losing row's phone, keeping the suppressed Lia Foster row because it does not match the existing TerraLens opt-out contact exactly, dropping phone-only `q1_004`, treating LakeHealth Robotics as a new account despite existing CRM account `acct_lakehealth`, and counting duplicate removals as suppressions rather than `no_import`.

Transfer anchors: SP001 through SP004 are anchored by `train_003` and `train_004`. The relevant transferable knowledge is to normalize before matching, dedupe by normalized email before phone-company keys, prefer the most recent source record with source priority as the tie-breaker, preserve contacts with either email or phone, and remove suppressed or opted-out contacts before final import. SP005 and SP006 also benefit from `train_003` because that task establishes the import action counting convention, but they require task-local exploration of q1-specific existing accounts and the new source label. This test keeps the same contact-hygiene operation family while changing the batch, duplicate conflicts, existing-contact overlap, and suppression pattern.

Construction record: created by Codex task-builder for `test_003` on 2026-06-01. Initial version created `prompt.txt`, `answer_template.json`, `answer.json`, `eval.sh`, `evaluator.py`, and these bilingual notes.

## 中文

本任务属于源场景 `SCN_001_crm_marketing_lead_capture`，参考了源示例 `E001`、`E002`，并主要继承 `E003` 的 CRM 联系人导入清洗主题。它实现了任务组设计中的 `test_003`：为 HarborCRM 的原始导入批次 `q1_partner_import` 准备 CRM 导入结果，同时尊重已有 CRM 记录和抑制名单。共享环境数据位于 `task_group/task_group_001/env/data/harborcrm_data.json`；求解器通过 HarborCRM API 读取导入批次、原始联系人、抑制名单、CRM 账户、CRM 联系人和策略。任务本地对求解器可见的载荷只有 `input/payloads/answer_template.json`。

求解器可见任务要求输出结构化的 CRM 导入 JSON 摘要，而不是修改 CRM 系统。期望输出包括批次元数据、保留下来的清洗联系人、重复行信息、移除行信息、导入动作汇总，以及 campaign member 导入数量和来源标签。可见提示刻意保持简洁，不把联系人清洗 SOP 写成步骤列表；求解器需要结合公开策略和从训练任务中归纳出的约定来完成。

关键源记录是 `q1_001` 到 `q1_008`。Hana Park 的 `q1_002` 胜过 `q1_001`，因为标准化邮箱相同且 `q1_002` 更新时间更晚，虽然它的来源优先级更低。Miles Chen 的 `q1_008` 胜过 `q1_007`，因为标准化邮箱相同，而且 `q1_008` 时间更晚并来自 `badge_scan`。`q1_003` 作为 LakeHealth 已有账户的新联系人保留，但没有已有联系人 id。`q1_004` 作为只有电话的新账户保留。`q1_005` 因没有标准化邮箱也没有标准化电话而不可用。`q1_006` 通过批次抑制名单被移除。Riverbend Chemical 已有 CRM 账户 `acct_riverbend_chem`，Hana Park 匹配已有联系人 `cont_hana_park`；LakeHealth Robotics 已有账户 `acct_lakehealth`，但 Pia Norberg 没有已有联系人。DeltaForge Tools 和 Cascadia Steel 是新建账户。

材料映射如下：

- `GET /api/import_batches` 用于确认 `q1_partner_import` 的 campaign code 是 `PARTNER-Q1-2027`，来源标签是 `partner_and_manual_upload`。
- `GET /api/import_batches/q1_partner_import/raw_contacts` 提供 `q1_001` 到 `q1_008`，这些行需要标准化、抑制、去重和导入判断。
- `GET /api/import_batches/q1_partner_import/suppression` 通过 `lia.foster@crownassembly.example` 和电话 `13135550104` 标识被抑制的 Lia Foster 行。
- `GET /api/crm/accounts` 用于确认 Riverbend Chemical 和 LakeHealth Robotics 是已有账户更新。
- `GET /api/crm/contacts` 用于确认 `cont_hana_park` 是 Riverbend 的已有旧联系人，并确认 Pia Norberg、Noah Kim 和 Miles Chen 不是已有联系人。
- `GET /api/policies` 暴露完成本批次所需的标准化、来源优先级和去重约定。

标准答案 `output/answer.json` 中有四个按行 id 排序的清洗联系人：`q1_002`、`q1_003`、`q1_004` 和 `q1_008`。邮箱转为小写并去除首尾空格。电话只保留获胜行中的数字，因此 Hana Park 的获胜行电话是 `7135550138`，而不是失败行中带国家码的号码。重复移除数量是 `2`，重复 key 为 `email:hana.park@riverbendchem.example` 和 `email:miles.chen@cascadiasteel.example`。移除统计中有一个不可用行和一个抑制行。导入动作汇总为 `create_account: 2`、`update_existing: 2`、`no_import: 3`、`suppress: 1`。Campaign member 导入数量是 `4`，来源标签是 `partner_and_manual_upload`。

评估器包含六个评分点，与设计一致：

- SP001，权重 3：保留清洗联系人 id 的精确顺序。
- SP002，权重 3：按保留 id 检查标准化邮箱和电话。
- SP003，权重 2：重复解析的获胜行和被移除行。
- SP004，权重 2：不可用和抑制移除数量，以及相关移除行。
- SP005，权重 2：create、update、no-import 和 suppress 动作汇总。
- SP006，权重 1：campaign member 数量和来源标签。

常见错误包括因为来源优先级更高而错误选择较旧的 `q1_001`、把 Hana 获胜行的邮箱和失败行的电话混用、因为 Lia Foster 没有精确匹配 TerraLens 的已有 opt-out 联系人而保留她、误删只有电话的 `q1_004`、忽略 `acct_lakehealth` 而把 LakeHealth Robotics 当作新账户，以及把重复移除计为 suppress 而不是 `no_import`。

迁移锚点：SP001 到 SP004 由 `train_003` 和 `train_004` 锚定。需要迁移的知识包括先标准化再匹配、优先按标准化邮箱去重再按电话加公司去重、优先选择最新来源记录并在时间相同才用来源优先级打破平局、只要有邮箱或电话就可保留联系人，以及在最终导入前移除抑制或 opt-out 联系人。SP005 和 SP006 也受益于 `train_003`，因为该训练任务建立了导入动作计数约定，但它们还需要探索本任务特有的已有账户和新的来源标签。本测试保持相同的联系人清洗操作族，同时更换批次、重复冲突、已有联系人重叠和抑制模式。

构建记录：由 Codex task-builder 于 2026-06-01 为 `test_003` 创建。初版创建了 `prompt.txt`、`answer_template.json`、`answer.json`、`eval.sh`、`evaluator.py` 和本双语 notes。
