# train_004 Notes: EdgeAI Field Day 2026 Reconciliation

## English

This hidden construction note covers `train_004` for `task_group_001`, based on source scenario `SCN_001_crm_marketing_lead_capture` and source examples `E001`, `E002`, and `E003`. The task follows the task-group design brief for `EdgeAI Field Day 2026` / `edgeai_field_2026`, combining event-to-CRM reconciliation with contact hygiene. Solver-visible files are `input/prompt.txt` and `input/payloads/answer_template.json`; the shared public environment is HarborCRM under `task_group_001/env/`.

The task asks the solver to reconcile badge scans, sponsor packages/orders, finance invoices, existing CRM accounts/contacts/opportunities, and campaign members. The expected answer is a structured handoff with sponsor statuses, badge-level inclusion/exclusion decisions, campaign member actions, opportunity rollups for non-sponsor leads, unpaid sponsor follow-up targets, normalized badge-only contacts, and exclusion counts. The prompt deliberately names the business outcome and API entry point without revealing a step-by-step SOP.

Material map: `env/data/harborcrm_data.json` contains the deterministic source records. The relevant public API endpoints are `/api/events/edgeai_field_2026`, `/api/events/edgeai_field_2026/orders`, `/api/events/edgeai_field_2026/badges`, `/api/finance/invoices?event_id=edgeai_field_2026`, `/api/crm/accounts`, `/api/crm/contacts`, `/api/crm/opportunities?event_id=edgeai_field_2026`, `/api/crm/campaign_members?event_id=edgeai_field_2026`, and `/api/policies`. The answer template describes the required JSON shape, allowed enums, ordering rules, integer USD precision, and date format.

Solution basis: the event ends on `2026-11-05`, has `lead_opportunity_amount` `36000`, `followup_days_after_end` `5`, and `sponsor_followup_days_after_end` `2`. Active sponsor packages are Rivet AI Labs, SignalForge Industrial, and VectorQuay Automation. Rivet has a paid/deferred invoice for `32000`; SignalForge has an open invoice for `21000`; VectorQuay has only a proposal-order package for `9000`. Badge scans include sponsor attendees Sofia Meyer and Lena Ortiz, qualified non-sponsor leads Marta Novak at Tundra Port Systems and Amir Qureshi at Glassfield Power, and excluded press attendee Sam Lee at Open Press Wire. Qualified non-sponsor pipeline is `2 * 36000 = 72000`.

Campaign member basis: Sofia Meyer already has `attended_sponsor`, so no action is needed. Owen Grant already has `registered_sponsor`; there is no badge scan requiring an attended update, so no action is needed. Marta Novak and Amir Qureshi need created attended campaign members, and Lena Ortiz needs a created sponsor campaign member because VectorQuay has no existing campaign member/contact. Badge-only contact normalization uses lowercase trimmed email and digit-only phone: Marta Novak `marta.novak@tundraport.example` / `19075550108`; Amir Qureshi empty email / `15125550121`; Lena Ortiz `lena.ortiz@vectorquay.example` / `2125550166`.

Evaluation uses seven exact scoring points with raw weights `[3, 2, 2, 2, 2, 1, 1]`: SP001 sponsor statuses and badge classifications; SP002 campaign member actions; SP003 non-sponsor opportunity summary; SP004 unpaid sponsor follow-up set, amount, and due date; SP005 normalized badge-only contacts; SP006 event lead follow-up date; SP007 exclusion counts. The evaluator ignores incidental extra fields but requires exact normalized business results for each point. Likely pitfalls include treating sponsor badge scans as ordinary leads, missing proposal-only sponsor follow-up, not creating the VectorQuay sponsor campaign member, dropping the phone-only Glassfield lead, or using the audit date instead of the event-derived due dates.

Transfer design: this is a real train task, not a tutorial. It reinforces sponsor/attendee separation from event tasks, finance-aware sponsor status, CRM campaign member create/no-action decisions, lead opportunity rollups from event values, follow-up date conventions, and contact normalization from badge scans. These conventions are intended to transfer to later event-reconciliation and hygiene tasks, especially test tasks involving sponsor attendees, unpaid sponsor follow-up, and badge-only contact creation.

Construction record: authored by Codex on 2026-06-01. Created `prompt.txt`, `answer_template.json`, `answer.json`, `eval/eval.sh`, `eval/evaluate.py`, and these notes for `train_004`.

## 中文

本隐藏说明用于 `task_group_001` 的 `train_004`，来源场景是 `SCN_001_crm_marketing_lead_capture`，参考样例为 `E001`、`E002`、`E003`。该任务按照任务组设计中的 `EdgeAI Field Day 2026` / `edgeai_field_2026` 简报构建，结合活动到 CRM 的对账和联系人清洗。求解者可见文件只有 `input/prompt.txt` 与 `input/payloads/answer_template.json`；共享公开环境是 `task_group_001/env/` 下的 HarborCRM。

任务要求求解者核对胸卡扫描、赞助订单、财务发票、现有 CRM 账号/联系人/机会以及 campaign member。标准答案是结构化交接结果，包括赞助状态、每条胸卡的纳入或排除判断、campaign member 动作、非赞助线索机会汇总、未付款赞助跟进对象、仅来自胸卡的联系人标准化信息以及排除原因计数。可见 prompt 只说明业务目标和 API 入口，不泄露逐步 SOP。

材料地图：`env/data/harborcrm_data.json` 包含确定性生成的源数据。相关公开 API 包括 `/api/events/edgeai_field_2026`、`/api/events/edgeai_field_2026/orders`、`/api/events/edgeai_field_2026/badges`、`/api/finance/invoices?event_id=edgeai_field_2026`、`/api/crm/accounts`、`/api/crm/contacts`、`/api/crm/opportunities?event_id=edgeai_field_2026`、`/api/crm/campaign_members?event_id=edgeai_field_2026` 和 `/api/policies`。答案模板规定了 JSON 结构、枚举值、排序规则、整数美元精度和日期格式。

解题依据：活动结束日期是 `2026-11-05`，`lead_opportunity_amount` 为 `36000`，普通线索跟进天数为 `5`，赞助财务跟进天数为 `2`。活跃赞助包来自 Rivet AI Labs、SignalForge Industrial 和 VectorQuay Automation。Rivet 有 `32000` 的已支付递延发票；SignalForge 有 `21000` 的未结发票；VectorQuay 只有 `9000` 的 proposal-only 赞助订单。胸卡扫描中，Sofia Meyer 和 Lena Ortiz 是赞助参会者，Tundra Port Systems 的 Marta Novak 与 Glassfield Power 的 Amir Qureshi 是合格非赞助线索，Open Press Wire 的 Sam Lee 是媒体/新闻人员，应排除。合格非赞助机会金额为 `2 * 36000 = 72000`。

Campaign member 判断依据：Sofia Meyer 已经是 `attended_sponsor`，无需动作。Owen Grant 已经是 `registered_sponsor`，且没有对应胸卡扫描要求更新为 attended，因此无需动作。Marta Novak 和 Amir Qureshi 需要创建 attended campaign member；Lena Ortiz 需要创建赞助 campaign member，因为 VectorQuay 没有现有 campaign member/联系人。仅来自胸卡的联系人标准化规则为邮箱去空格并小写、电话只保留数字：Marta Novak 为 `marta.novak@tundraport.example` / `19075550108`；Amir Qureshi 为空邮箱 / `15125550121`；Lena Ortiz 为 `lena.ortiz@vectorquay.example` / `2125550166`。

评估包含七个精确评分点，原始权重为 `[3, 2, 2, 2, 2, 1, 1]`：SP001 检查赞助状态和胸卡分类；SP002 检查 campaign member 动作；SP003 检查非赞助机会汇总；SP004 检查未付款赞助跟进集合、金额和日期；SP005 检查仅胸卡联系人标准化；SP006 检查普通活动线索跟进日期；SP007 检查排除原因计数。评估器会忽略无关额外字段，但每个评分点要求归一化后的业务结果完全匹配。常见错误包括把赞助胸卡当作普通线索、漏掉 proposal-only 赞助跟进、没有为 VectorQuay 创建赞助 campaign member、丢弃只有电话的 Glassfield 线索，或使用审计日期而不是活动规则日期。

迁移设计：这是正式训练任务，不是教程。它强化了活动任务中的赞助/参会者区分、基于财务状态的赞助状态、CRM campaign member 创建或无需动作的判断、根据活动金额计算线索机会、跟进日期约定，以及胸卡联系人标准化。这些经验应迁移到后续活动对账和联系人清洗任务，尤其是涉及赞助参会者、未付款赞助跟进和仅胸卡联系人创建的测试任务。

构建记录：Codex 于 2026-06-01 创建。新增了 `prompt.txt`、`answer_template.json`、`answer.json`、`eval/eval.sh`、`eval/evaluate.py` 和本 `train_004` 说明文件。
