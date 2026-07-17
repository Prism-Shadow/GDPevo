# test_004 Hidden Notes

## English

Task `test_004` belongs to `task_group_001`, sourced from scenario `SCN_001_crm_marketing_lead_capture` and its examples `E001`, `E002`, and `E003`. It implements the test brief from `scratch/task_group_design.md`: reconcile `Industrial Vision AI Forum 2027` (`event_id`: `industrial_vision_2027`) attendees, sponsors, and CRM gaps. The shared environment is HarborCRM under `task_group/task_group_001/env/`, especially `env/data/harborcrm_data.json`, `env/data/manifest.json`, and the public API served by `env/setup.sh`.

The visible task consists of `input/prompt.txt` and `input/payloads/answer_template.json`. Solvers are expected to inspect the public API endpoints for event details, sponsor orders, invoices, badges, CRM accounts, CRM contacts, campaign members, opportunities, and policies, then return JSON in the declared schema. The prompt intentionally asks for a business handoff rather than exposing the construction rules as a step list.

This task fits the CRM marketing lead-capture scenario because it combines event operations, sponsor finance, badge scanning, CRM contact hygiene, and campaign member cleanup. The key objects are sponsor packages for TerraLens Robotics, Mosaic AI Works, and Prairie Optics; invoice records for TerraLens and Mosaic; badge scans `bdg_0018` through `bdg_0023`; one stale CRM campaign member `acct_terra_lens:cont_lia_foster`; and policy metadata for sponsor status, contact normalization, and follow-up dates.

Material map:

- `GET /api/events/industrial_vision_2027` gives the event name, end date `2027-05-19`, lead amount `47000`, lead follow-up offset `6`, and sponsor follow-up offset `3`.
- `GET /api/events/industrial_vision_2027/sponsor_packages` gives the active sponsor package candidates and package amounts.
- `GET /api/finance/invoices?event_id=industrial_vision_2027` distinguishes TerraLens as `paid_deferred`, Mosaic as an open invoice, and Prairie Optics as proposal-only because no delivered invoice exists.
- `GET /api/events/industrial_vision_2027/badges` supplies attendee records and contact facts. Prairie Optics is classified as a sponsor attendee even though its badge type is `attendee`, because it appears in active sponsor package data.
- `GET /api/crm/accounts` and `GET /api/crm/contacts` show that Crown Assembly and DeltaForge Tools are new account/contact gaps, while the existing TerraLens `Lia Foster` contact is opted out and stale.
- `GET /api/crm/campaign_members?event_id=industrial_vision_2027` exposes the stale TerraLens member that should be updated to `excluded`, not reused for Victor Hale or Crown Assembly's Lia Foster.
- `GET /api/policies` records the public normalization and due-date conventions.

Solution basis:

- Sponsor statuses: Mosaic AI Works `open_invoice` for `24000`; Prairie Optics `proposal_only` for `11000`; TerraLens Robotics `paid_deferred` for `38000`.
- Badge classifications: `bdg_0018`, `bdg_0020`, and `bdg_0022` are sponsor attendees; `bdg_0019` Crown Assembly and `bdg_0021` DeltaForge Tools are qualified non-sponsor leads; `bdg_0023` West Bay University is excluded as `non_business_badge`.
- Campaign actions: create campaign members for the five actionable badge contacts and update stale subject `acct_terra_lens:cont_lia_foster` to `excluded`.
- New lead contacts: Crown Assembly / Lia Foster has normalized email `lia.foster@crownassembly.example` and phone `13135550104`; DeltaForge Tools / Noah Kim has empty normalized email and phone `12165550180`.
- Opportunity total: two qualified non-sponsor accounts at `47000` each, total `94000`.
- Sponsor follow-up: unpaid sponsor accounts are Mosaic AI Works and Prairie Optics, total `35000`.
- Due dates: lead due date is `2027-05-25`; sponsor finance due date is `2027-05-22`.
- Exclusion counts: sponsor attendee `3`, non-business badge `1`, existing disqualified `0`, missing contact `0`.

Evaluation basis: `eval/evaluate.py` has seven exact-match scoring points with raw weights `[3, 2, 2, 2, 2, 2, 1]`.

- SP001, weight 3: sponsor status set and badge sponsor/attendee classification.
- SP002, weight 2: campaign member create/update decisions, including the stale CRM gap.
- SP003, weight 2: unpaid sponsor follow-up account set and amount.
- SP004, weight 2: new lead contact normalization and CRM create decisions.
- SP005, weight 2: non-sponsor opportunity account set and total.
- SP006, weight 2: lead and sponsor follow-up due dates.
- SP007, weight 1: exclusion reason counts and CRM gap summary.

Likely model pitfalls include treating Prairie Optics as an ordinary attendee because its badge type is not `sponsor`; missing the proposal-only sponsor state; counting sponsor attendees as sales leads; suppressing Crown Assembly's Lia Foster because of a same-name stale opted-out TerraLens contact; reusing the stale TerraLens campaign member for the wrong person; and using the audit date instead of event-end-date offsets for due dates.

Transfer design: this test is anchored by `train_001`, `train_003`, and `train_004`. From `train_001`, solvers should transfer sponsor finance status handling and event-end-date follow-up conventions. From `train_004`, they should transfer sponsor attendee exclusion, campaign member action patterns, and proposal-only sponsor handling. From `train_003`, they should transfer email/phone normalization and cautious duplicate/contact matching. The task-specific exploration is identifying the fresh Industrial Vision sponsor and badge records, interpreting the TerraLens stale campaign member, and calculating the new event's amounts and dates.

Construction record: created by Codex task-builder for `test_004` on 2026-06-01. Files created: `input/prompt.txt`, `input/payloads/answer_template.json`, `notes/notes.md`, `output/answer.json`, `eval/eval.sh`, and `eval/evaluate.py`.

## 中文

任务 `test_004` 属于 `task_group_001`，来源场景为 `SCN_001_crm_marketing_lead_capture`，参考示例为 `E001`、`E002` 和 `E003`。本任务实现 `scratch/task_group_design.md` 中的测试设计：核对 `Industrial Vision AI Forum 2027`（`event_id`: `industrial_vision_2027`）的参会者、赞助商和 CRM 缺口。共享环境是 HarborCRM，位于 `task_group/task_group_001/env/`，主要依据 `env/data/harborcrm_data.json`、`env/data/manifest.json` 以及由 `env/setup.sh` 启动的公共 API。

可见输入包括 `input/prompt.txt` 和 `input/payloads/answer_template.json`。解题者应查看公共 API 中的活动详情、赞助订单、发票、胸卡扫描、CRM 账户、CRM 联系人、campaign member、商机和政策元数据，并按模板输出 JSON。提示词只描述业务交付物，不暴露隐藏的逐步操作规则。

该任务符合 CRM 市场线索采集场景，因为它同时涉及活动执行、赞助财务、胸卡扫描、CRM 联系人清洗和 campaign member 清理。关键对象包括 TerraLens Robotics、Mosaic AI Works、Prairie Optics 的赞助包；TerraLens 和 Mosaic 的发票；`bdg_0018` 到 `bdg_0023` 的胸卡记录；一个过期的 CRM campaign member `acct_terra_lens:cont_lia_foster`；以及关于赞助状态、联系方式标准化和跟进日期的政策数据。

材料映射：

- `GET /api/events/industrial_vision_2027` 提供活动名称、结束日期 `2027-05-19`、单个线索金额 `47000`、线索跟进偏移 `6` 天、赞助财务跟进偏移 `3` 天。
- `GET /api/events/industrial_vision_2027/sponsor_packages` 提供有效赞助候选和金额。
- `GET /api/finance/invoices?event_id=industrial_vision_2027` 用于判断 TerraLens 为 `paid_deferred`，Mosaic 为 open invoice，Prairie Optics 因无已开票记录而为 proposal-only。
- `GET /api/events/industrial_vision_2027/badges` 提供参会者和联系方式。Prairie Optics 虽然胸卡类型是 `attendee`，但因为在有效赞助包中，应归为 sponsor attendee。
- `GET /api/crm/accounts` 和 `GET /api/crm/contacts` 显示 Crown Assembly 与 DeltaForge Tools 是新账户和新联系人缺口，而 TerraLens 的 `Lia Foster` 是已退订且过期的旧联系人。
- `GET /api/crm/campaign_members?event_id=industrial_vision_2027` 暴露了 TerraLens 的过期 member，应更新为 `excluded`，不能用于 Victor Hale，也不能用于 Crown Assembly 的 Lia Foster。
- `GET /api/policies` 记录公开的标准化规则和日期规则。

答案依据：

- 赞助状态：Mosaic AI Works 为 `open_invoice`，金额 `24000`；Prairie Optics 为 `proposal_only`，金额 `11000`；TerraLens Robotics 为 `paid_deferred`，金额 `38000`。
- 胸卡分类：`bdg_0018`、`bdg_0020`、`bdg_0022` 是赞助商参会者；`bdg_0019` Crown Assembly 和 `bdg_0021` DeltaForge Tools 是合格的非赞助线索；`bdg_0023` West Bay University 因 `non_business_badge` 排除。
- Campaign actions：为五个可处理的胸卡联系人创建 campaign member，并将过期 subject `acct_terra_lens:cont_lia_foster` 更新为 `excluded`。
- 新线索联系人：Crown Assembly / Lia Foster 的标准化邮箱为 `lia.foster@crownassembly.example`，电话为 `13135550104`；DeltaForge Tools / Noah Kim 的标准化邮箱为空字符串，电话为 `12165550180`。
- 商机总额：两个合格非赞助账户，每个 `47000`，合计 `94000`。
- 赞助跟进：未付款赞助账户为 Mosaic AI Works 和 Prairie Optics，合计 `35000`。
- 日期：线索跟进日期为 `2027-05-25`；赞助财务跟进日期为 `2027-05-22`。
- 排除计数：sponsor attendee 为 `3`，non-business badge 为 `1`，existing disqualified 为 `0`，missing contact 为 `0`。

评估依据：`eval/evaluate.py` 有七个精确匹配评分点，原始权重为 `[3, 2, 2, 2, 2, 2, 1]`。

- SP001，权重 3：赞助状态集合以及胸卡的赞助/参会分类。
- SP002，权重 2：campaign member 创建/更新决策，包括过期 CRM 缺口处理。
- SP003，权重 2：未付款赞助跟进账户集合和金额。
- SP004，权重 2：新线索联系方式标准化和 CRM 创建决策。
- SP005，权重 2：非赞助商机账户集合和总额。
- SP006，权重 2：线索和赞助跟进日期。
- SP007，权重 1：排除原因计数和 CRM 缺口汇总。

常见错误包括：因为 Prairie Optics 的胸卡类型不是 `sponsor` 而把它当普通参会者；漏掉 proposal-only 赞助状态；把赞助商参会者算作销售线索；因为同名的 TerraLens 旧退订联系人而错误抑制 Crown Assembly 的 Lia Foster；把 TerraLens 的过期 campaign member 复用于错误联系人；以及用审计日期而不是活动结束日期加偏移量来计算截止日期。

迁移设计：该测试锚定 `train_001`、`train_003` 和 `train_004`。从 `train_001` 迁移赞助财务状态判断和基于活动结束日期的跟进日期规则；从 `train_004` 迁移赞助商参会者排除、campaign member 动作模式和 proposal-only 赞助处理；从 `train_003` 迁移邮箱/电话标准化以及谨慎的重复联系人判断。任务本身的探索难点是识别 Industrial Vision 的新赞助和胸卡记录、解释 TerraLens 的过期 campaign member、并计算本活动的金额与日期。

构建记录：由 Codex task-builder 于 2026-06-01 为 `test_004` 创建。创建文件包括 `input/prompt.txt`、`input/payloads/answer_template.json`、`notes/notes.md`、`output/answer.json`、`eval/eval.sh` 和 `eval/evaluate.py`。
