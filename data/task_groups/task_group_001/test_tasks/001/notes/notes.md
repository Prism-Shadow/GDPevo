# test_001 Hidden Notes

## English

This task is `test_001` for `task_group_001`, derived from source scenario `SCN_001_crm_marketing_lead_capture` and source examples `E001`, `E002`, and `E003`. Its design brief is the event-to-CRM operation family: audit `Predictive Ops Summit 2027` (`event_id: predictive_ops_2027`) after the event and produce a finance and sales handoff from the shared HarborCRM environment.

Solver-visible inputs are only `input/prompt.txt`, `input/payloads/answer_template.json`, and the public HarborCRM API. The relevant public data comes from event metadata, sponsor packages, event badges, finance invoices, CRM accounts, CRM contacts, opportunities, campaign members, and policies. The solver should not inspect generated data files or these notes.

The task fits the group because it combines the same business objects as the train event tasks: sponsor packages, invoices, badge scans, CRM state, campaign membership, lead opportunity sizing, and follow-up dates. It is not a tutorial version of a train task. The Predictive Ops event introduces task-specific exploration through a split Lumina Manufacturing invoice, an inactive Keystone AGV sponsor package, a pre-existing Riverbend lead with stale contact data, and a stale campaign-member mismatch for Fathom Ops.

Material map:

- `/api/events/predictive_ops_2027` supplies the event end date, lead opportunity amount, and follow-up offsets.
- `/api/events/predictive_ops_2027/sponsor_packages` and `/orders` identify Fathom Ops, Lumina Manufacturing, OrbitRail Systems, and the inactive Keystone AGV package.
- `/api/finance/invoices?event_id=predictive_ops_2027` supplies the paid/deferred Fathom invoice, the split Lumina paid/open invoices, and the absence of an OrbitRail delivered invoice.
- `/api/events/predictive_ops_2027/badges` supplies sponsor attendees and non-sponsor attendees.
- `/api/crm/accounts` and `/api/crm/contacts` distinguish existing accounts, disqualified accounts, stale contact data, and new accounts.
- `/api/crm/campaign_members?event_id=predictive_ops_2027` shows Riverbend Chemical already registered and a stale Fathom Ops campaign-member mismatch using `cont_sofia_meyer`.
- `/api/policies` records the public conventions for sponsor status, follow-up date offsets, contact normalization, and lead amount field names.

Solution basis:

- Active sponsors are Fathom Ops (`paid_deferred`), Lumina Manufacturing (`open_invoice` because one split invoice remains open), and OrbitRail Systems (`proposal_only`). Keystone AGV is a no-show sponsor package and is not active.
- Sponsor finance totals are invoice/proposal segment totals: paid/deferred invoiced value is `72000 + 26000 = 98000`, open delivered invoice value is `16000`, proposal-only value is `22000`, and open balance is `16000`.
- Qualified non-sponsor lead accounts are Cascadia Steel and Riverbend Chemical. Each uses the event lead opportunity amount `51000`, so `lead_pipeline_total` is `102000` and `average_deal_size` is `51000.00`.
- Riverbend Chemical maps to existing account `acct_riverbend_chem` and contact `cont_hana_park`; the badge has the fresher email `hana.park@riverbendchem.example`, so the contact and campaign member should be updated rather than duplicated. Cascadia Steel is a new account/contact/campaign-member create.
- Excluded records are sponsor badge attendees Cole Ivers and Nadia Volk, inactive sponsor package contact Anika Shah, disqualified Old Quarry Logistics contact Rhea Moon, non-business press attendee Dev Singh, and the stale Fathom Ops campaign-member mismatch for Sofia Meyer.
- Follow-up dates are event end date `2027-03-24` plus the event offsets: lead follow-up `2027-04-01` and sponsor finance follow-up `2027-03-28`. Lead task count is `2`; sponsor finance task count is `2` for Lumina Manufacturing and OrbitRail Systems.

Evaluation uses seven exact-match scoring points with raw weights:

- SP001, weight 3: exact active sponsor status set, including Lumina's split-invoice status and invoice IDs.
- SP002, weight 2: exact sponsor revenue totals by paid/deferred, open invoice, proposal-only, and open balance.
- SP003, weight 3: exact qualified non-sponsor lead account set and CRM actions.
- SP004, weight 2: exact exclusion set, including sponsor attendees, inactive sponsor record, disqualified badge, non-business badge, and stale CRM duplicate.
- SP005, weight 2: exact lead pipeline total and average deal size.
- SP006, weight 3: exact follow-up due dates, counts, and sponsor finance account set.
- SP007, weight 1: exact CRM create/update counts.

Transfer design:

- `train_001` anchors sponsor/attendee separation, sponsor finance status reconstruction from packages plus invoices, non-sponsor lead inclusion, CRM action counts, and due-date offsets.
- `train_004` anchors event badge classification, campaign member create/update decisions, sponsor attendee exclusion, and how existing CRM state affects handoff actions.
- The high-value transfer-dependent points are SP001, SP002, SP003, SP004, and SP006. SP005 and SP007 require more task-local exploration because the split invoice, stale contact/campaign-member state, and lead count are specific to this event.
- The prompt exposes the public endpoints and output schema but does not restate the hidden step-by-step operating method. Solvers must infer the reconciliation pattern from the train tasks and apply it to the Predictive Ops records.

Likely model pitfalls include counting Lumina's full package only as open invoice revenue, missing the paid/deferred part of the split invoice, including Keystone AGV as an active sponsor, treating Riverbend as a new lead because the badge email differs from stale CRM, counting sponsor attendees as sales leads, missing the stale Fathom campaign-member mismatch, or anchoring follow-up dates to the audit date instead of the event end date.

Construction record: built by task-builder for `test_001` on 2026-06-01. Created solver prompt, answer template, standard answer, exact-match evaluator, and these bilingual notes.

## 中文

本任务是 `task_group_001` 的 `test_001`，来源于场景 `SCN_001_crm_marketing_lead_capture` 以及源示例 `E001`、`E002`、`E003`。任务设计属于“活动到 CRM 管道核对”这一类：在 `Predictive Ops Summit 2027`（`event_id: predictive_ops_2027`）结束后，审计赞助商财务交接和销售线索交接。

求解器可见的输入只有 `input/prompt.txt`、`input/payloads/answer_template.json` 和 HarborCRM 的公开 API。相关公开数据包括活动元数据、赞助包、胸卡扫描、财务发票、CRM 账户、CRM 联系人、机会、活动成员和政策。求解器不应查看生成数据文件或本隐藏说明。

该任务符合任务组，因为它复用了训练活动任务中的核心业务对象：赞助包、发票、胸卡记录、CRM 状态、活动成员、线索机会金额和跟进日期。它不是训练题的教程版。Predictive Ops 的特定探索难点包括 Lumina Manufacturing 的拆分发票、Keystone AGV 的无效 no-show 赞助包、Riverbend 已有但过期的联系人信息，以及 Fathom Ops 的陈旧活动成员错配。

材料映射：

- `/api/events/predictive_ops_2027` 提供活动结束日期、单个线索机会金额和跟进日期偏移。
- `/api/events/predictive_ops_2027/sponsor_packages` 和 `/orders` 标识 Fathom Ops、Lumina Manufacturing、OrbitRail Systems 以及无效的 Keystone AGV 赞助记录。
- `/api/finance/invoices?event_id=predictive_ops_2027` 提供 Fathom 的已支付递延发票、Lumina 的已支付和未结清拆分发票，以及 OrbitRail 没有已开具发票这一事实。
- `/api/events/predictive_ops_2027/badges` 提供赞助商参会者和非赞助商参会者。
- `/api/crm/accounts` 和 `/api/crm/contacts` 用于区分已有账户、已取消资格账户、过期联系人数据和新账户。
- `/api/crm/campaign_members?event_id=predictive_ops_2027` 显示 Riverbend Chemical 已注册，以及 Fathom Ops 使用 `cont_sofia_meyer` 的陈旧活动成员错配。
- `/api/policies` 记录赞助状态、跟进日期、联系人规范化和线索金额字段的公开约定。

答案依据：

- 有效赞助商是 Fathom Ops（`paid_deferred`）、Lumina Manufacturing（`open_invoice`，因为拆分发票中仍有未结清部分）和 OrbitRail Systems（`proposal_only`）。Keystone AGV 是 no-show 赞助包，不属于有效赞助商。
- 赞助财务汇总按发票/提案片段统计：已支付递延发票金额为 `72000 + 26000 = 98000`，未结清已开票金额为 `16000`，仅提案金额为 `22000`，未结清余额为 `16000`。
- 合格的非赞助商线索账户是 Cascadia Steel 和 Riverbend Chemical。每个账户使用活动字段中的线索机会金额 `51000`，因此 `lead_pipeline_total` 为 `102000`，`average_deal_size` 为 `51000.00`。
- Riverbend Chemical 对应已有账户 `acct_riverbend_chem` 和联系人 `cont_hana_park`；胸卡中的邮箱 `hana.park@riverbendchem.example` 更新，因此应更新联系人和活动成员，而不是创建重复记录。Cascadia Steel 是新账户、新联系人和新活动成员。
- 排除记录包括赞助商参会者 Cole Ivers 和 Nadia Volk、无效赞助包联系人 Anika Shah、已取消资格的 Old Quarry Logistics 联系人 Rhea Moon、非业务媒体参会者 Dev Singh，以及 Fathom Ops 的陈旧活动成员错配 Sofia Meyer。
- 跟进日期以活动结束日期 `2027-03-24` 加活动偏移计算：线索跟进为 `2027-04-01`，赞助财务跟进为 `2027-03-28`。线索任务数为 `2`；赞助财务任务数为 `2`，对应 Lumina Manufacturing 和 OrbitRail Systems。

评测使用七个精确匹配评分点，原始权重如下：

- SP001，权重 3：有效赞助商状态集合完全正确，包括 Lumina 的拆分发票状态和发票 ID。
- SP002，权重 2：已支付递延、未结清发票、仅提案和未结清余额的赞助收入汇总完全正确。
- SP003，权重 3：合格非赞助商线索账户集合和 CRM 动作完全正确。
- SP004，权重 2：排除集合完全正确，包括赞助商参会者、无效赞助记录、已取消资格胸卡、非业务胸卡和陈旧 CRM 重复记录。
- SP005，权重 2：线索管道总额和平均交易金额完全正确。
- SP006，权重 3：跟进日期、任务数和赞助财务账户集合完全正确。
- SP007，权重 1：CRM 创建/更新计数完全正确。

迁移设计：

- `train_001` 锚定赞助商与普通参会者分离、基于赞助包和发票重建财务状态、非赞助商线索纳入、CRM 动作计数和跟进日期偏移。
- `train_004` 锚定胸卡分类、活动成员创建/更新决策、赞助商参会者排除，以及已有 CRM 状态如何影响交接动作。
- 高价值的迁移依赖评分点是 SP001、SP002、SP003、SP004 和 SP006。SP005 和 SP007 更依赖本任务局部探索，因为拆分发票、陈旧联系人/活动成员状态和线索数量都是本活动特有的。
- 提示只暴露公开端点和输出结构，不在求解器可见文件中重述隐藏的逐步操作方法。求解器需要从训练任务中归纳核对模式，并应用到 Predictive Ops 的记录。

常见模型陷阱包括：把 Lumina 的全部赞助包只算作未结清发票收入，漏掉拆分发票中已支付递延的部分，把 Keystone AGV 当作有效赞助商，因为胸卡邮箱不同而把 Riverbend 当作新线索，把赞助商参会者计入销售线索，漏掉 Fathom 的陈旧活动成员错配，或把跟进日期锚定到审计日期而不是活动结束日期。

构建记录：由 `test_001` task-builder 于 2026-06-01 构建。创建了求解器提示、答案模板、标准答案、精确匹配评测器和本双语隐藏说明。
