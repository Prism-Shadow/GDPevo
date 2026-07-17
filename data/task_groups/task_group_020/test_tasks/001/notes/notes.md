# test_001 Notes - Lumen Vale Buyer SPA Term Population

## English

### Data and Source Lineage

This task belongs to `task_group_020`, scenario `SCN_020_ma_transaction_contract_review_and_negotiation`, derived from source examples `E001`, `E002`, and `E003`. It implements the `test_001` design brief for buyer-side stock purchase term population and drafting posture on deal `D-LUMEN-908`, code-named Lumen Vale, in the shared Aster Legal Deal Desk environment.

The generated shared data is in `task_group/task_group_020/env/data/dealdesk.json`, with public metadata in `task_group/task_group_020/env/data/manifest.json`. Relevant public environment objects are the deal profile for `D-LUMEN-908`; active documents `DOC-LUMEN908-TERM-01`, `DOC-LUMEN908-DRAFT-02`, `DOC-LUMEN908-EMAIL-03`, `DOC-LUMEN908-CAP-ACTIVE`, `DOC-LUMEN908-FIN-04`, `DOC-LUMEN908-MATCON-05`, and `DOC-LUMEN908-DISC-06`; stale/template documents `DOC-LUMEN908-CAP-STALE` and `DOC-LUMEN908-TEMPLATE-99`; active clauses `CL-LUMEN-908-001` through `CL-LUMEN-908-005`; stale/template clauses `CL-LUMEN-908-S01` and `CL-LUMEN-908-S02`; and policy document `DOC-BUYERMIDMARKET2026-POLICY` for policy `P-BUYER-MIDMARKET-2026`.

Task-local solver-visible files are `input/prompt.txt` and `input/payloads/answer_template.json`. The prompt states the business request, environment entry point convention, target deal ID, and required JSON keys. It does not give a procedure, source-precedence rule list, scoring rubric, or answers.

### Task Definition and Scenario Fit

The solver acts as buyer counsel preparing a structured SPA drafting package for `D-LUMEN-908`. The required JSON now has six top-level sections: `deal_terms`, `seller_allocations`, `closing_flags`, `source_precedence`, `policy_checks`, and `drafting_positions`.

The task fits the M&A legal operations scenario because the solver must reconcile commercial terms, current draft instructions, cap table schedules, material contracts, regulatory status, disclosure schedules, stale/template conflicts, and the Northstar buyer playbook. This preserves the source examples' difficulty drivers: party precision, active-vs-stale source selection, legal drafting posture, approval/risk judgment, and exact financial calculations.

This file was reworked after direct calibration scored too high: attempts scored 1.0 and 0.733, average 0.867. The previous scoring over-rewarded direct environment lookup and arithmetic. The revised output and evaluator move most weight to transfer-dependent controlled fields: source precedence, exact risk posture, active-vs-stale/template conflict resolution, conditional escalation triggers, precise source IDs, policy checks, and drafting posture enums.

### Material Map

- `GET /api/deals/D-LUMEN-908` and `/deals/D-LUMEN-908`: deal profile, parties, headline/equity value, dates, active/stale document links, schedules, client positions, and negotiation context.
- `DOC-LUMEN908-TERM-01`: signed commercial term sheet for value, timing, consideration mix, escrow, cap, basket, survival periods, and working capital.
- `DOC-LUMEN908-DRAFT-02`: active draft instructions for cap-table priority, consents, escrow, non-compete, fallback authority, and escalation posture.
- `DOC-LUMEN908-EMAIL-03`: latest client instruction confirming active cap-table priority, named consent positions, SensorForge fallback, and escalation if seller uses the stale cap table or moves OmniAuto/KiteRail post-close.
- `DOC-LUMEN908-CAP-ACTIVE`: controlling July 31, 2026 ownership schedule for seller allocation.
- `DOC-LUMEN908-CAP-STALE`: February 28, 2026 stale cap table retained for audit trail and rejected as controlling allocation evidence.
- `DOC-LUMEN908-FIN-04`: financial schedule for working capital, escrow, cap, basket, de minimis, and consideration mix.
- `DOC-LUMEN908-MATCON-05`: material-contract consent matrix and regulatory status, including HSR and University license consent.
- `DOC-LUMEN908-DISC-06`: employment, non-compete, transition-service, and IP confirmation facts.
- `DOC-LUMEN908-TEMPLATE-99`: generic imported template provisions, including distracting non-compete and consent language.
- `DOC-BUYERMIDMARKET2026-POLICY` / `P-BUYER-MIDMARKET-2026`: Northstar buyer risk memo and SPA playbook with rule IDs, approval categories, thresholds, and policy bases.
- `/api/clauses?deal_id=D-LUMEN-908`: clause-level active/stale cross-check for allocation, escrow, non-compete, consents, and HSR.

### Solution and Evaluation Basis

The standard answer uses `DOC-LUMEN908-CAP-ACTIVE`, dated 2026-07-31, because it supersedes the February stale cap table. Headline purchase price and equity value are both USD 257,500,000. Consideration is USD 232,500,000 cash at close and USD 25,000,000 rollover equity, with no seller note or earnout. The active cap table has no share count, so `per_share_price_usd` is null and `per_share_price_basis` is `NO_SHARE_COUNT_IN_ACTIVE_CAP_TABLE`. One ownership percentage point equals USD 2,575,000.

The active seller allocation set is BrightPath Ventures III at 34.0 percent and USD 87,550,000; Lumen Founder Holdings at 39.5 percent and USD 101,712,500; and Lumen Management Pool at 26.5 percent and USD 68,237,500. Seller proceeds are based on headline/equity value, not cash-at-close net of escrow.

Escrow and indemnity terms are calculated on headline value. General escrow is 10.0 percent or USD 25,750,000; tax escrow is 2.5 percent or USD 6,437,500; indemnity cap is 10.0 percent or USD 25,750,000; the basket is a 0.75 percent deductible basket or USD 1,931,250; and de minimis is USD 60,000. Working capital uses a USD 27,800,000 target, USD 1,000,000 collar, and true-up against the active July balance sheet. The collar is 0.39 percent of equity value.

The required material-contract closing consents are OmniAuto Robotics Supply and KiteRail Deployment Agreement, both sourced to `DOC-LUMEN908-MATCON-05`. SensorForge License is an accepted post-closing notice item only. HSR is required because the antitrust memo says reportable thresholds are met; HSR should be a closing condition and is sourced to `DOC-LUMEN908-MATCON-05`. Other regulatory approvals include University license consent.

Employment and restrictive covenant fields are sourced to `DOC-LUMEN908-DISC-06`. Dani Rowe, founder, and Victor Hsu, VP Controls, require retention agreements. No fixed employment term is stated, so `employment_agreement_term_months` is null. The non-compete is 30 months, limited to target products, and does not allow broad affiliate scope. No general transition services are required, but IP assignment confirmation is required.

Source precedence and drafting posture are central to the revised task. The controlling sources are the active cap table, latest client email, active draft, financial schedule, material-contract schedule, disclosure schedule, and buyer policy. `DOC-LUMEN908-CAP-STALE` and `DOC-LUMEN908-TEMPLATE-99` are superseded. Active clauses `CL-LUMEN-908-001` through `CL-LUMEN-908-005` control over stale/template clauses `CL-LUMEN-908-S01` and `CL-LUMEN-908-S02`. Drafting positions use controlled enums such as `BUYER_FORM`, `ALLOCATION_DRAFTING_POSITION`, `HSR_FILING_CONDITION`, `TARGETED_PRODUCT_SCOPE_RESTRICTIVE_COVENANT`, and `ACTIVE_DRAFT_SUPERSEDES_TEMPLATE`.

Policy checks use `P-BUYER-MIDMARKET-2026` version `2026.2`. Current active terms are within policy; no approval is required now and current policy exception count is zero. The conditional escalation triggers are only `CONSENT_TIMING_TRIGGER` and `ALLOCATION_SOURCE_TRIGGER`. Reviewed but non-triggered thresholds include basket below 0.5 percent, broad non-compete, cap above 12.5 percent, general escrow above 12 percent, tax escrow above 3 percent, unclear HSR analysis, and unverified NWC target.

The evaluator has eight exact-match scoring points, raw weight total 12, synchronized with `task_group.yaml`:

- `SP1_SOURCE_PRECEDENCE_CONTROLLED_SOURCES`, weight 3: source-precedence decisions, active/stale clause IDs, and superseded source IDs.
- `SP2_DRAFTING_POSTURE_ENUMS`, weight 1: controlled drafting posture fields.
- `SP3_POLICY_CHECKS_CURRENT_STATUS`, weight 3: policy rule IDs, approval categories, current status, approval summary, and conditional trigger set.
- `SP4_CONDITIONAL_ESCALATION_RISK_POSTURE`, weight 1: risk posture, non-triggered thresholds, conditional escalation details, and risk-memo override source IDs.
- `SP5_CONSENT_HSR_SOURCE_SELECTION`, weight 1: consent, post-closing notice, HSR, regulatory approval, and source-document treatment.
- `SP6_EMPLOYMENT_NONCOMPETE_SOURCE_SELECTION`, weight 1: employment, non-compete, transition service, IP confirmation, and source document.
- `SP7_ACTIVE_CAP_TABLE_ALLOCATION_MATH`, weight 1: economics, active cap table, per-share availability, and seller allocations.
- `SP8_ESCROW_NWC_VALUE_POLICY_MATH`, weight 1: escrow, cap, basket, de minimis, and working-capital mechanics.

Likely model pitfalls include using the stale February cap table, treating the generic template as a fallback source, over-including all possible policy thresholds as current conditional triggers, counting SensorForge as a material closing consent, omitting source document IDs, labeling current in-policy terms as approval-required, using the wrong HSR posture from a train task, or returning narrative drafting labels instead of controlled enums.

### Transfer Design

This test task is anchored by `train_001` and `train_005`.

From `train_001`, solvers should transfer buyer-side term-population conventions: active deal-room schedules control over stale cap tables; active client instructions and disclosure schedules control over templates; seller allocation uses the active ownership schedule and headline/equity value unless the schema states otherwise; regulatory and consent flags come from deal-specific records; and outputs use controlled enums, integer dollars, two-decimal percentages, precise source IDs, and sorted lists.

From `train_005`, solvers should transfer policy and drafting-posture habits: latest client instructions and deal-specific risk records can override generic form language; policy checks must separate current approval requirements from conditional future escalation triggers; active/source override records require exact source and superseded document IDs; and drafting positions should be encoded as controlled enums rather than prose.

The transfer-dependent scoring points are `SP1`, `SP2`, `SP3`, and `SP4`, with additional transfer pressure in `SP5` and `SP6` through source-document selection and active-vs-template conflict resolution. Task-specific exploration remains necessary for Lumen-specific numbers, sellers, contracts, HSR result, source IDs, active and stale clause IDs, and non-compete facts. The solver-visible prompt does not teach the source-precedence or policy-posture procedure.

### Construction Record

Author: task-builder subagent for `task_group_020/test_001`.

Created: 2026-07-07.

Updated: 2026-07-07.

Major changes: created the original task files, then reworked after direct calibration average 0.867 by adding transfer-dependent `source_precedence`, `policy_checks`, `drafting_positions`, stricter `risk_posture_flags`, exact source document IDs, controlled policy measurement codes, and an eight-point evaluator.

## 中文

### 数据和来源脉络

本任务属于 `task_group_020`，场景为 `SCN_020_ma_transaction_contract_review_and_negotiation`，来源示例为 `E001`、`E002` 和 `E003`。任务实现 `test_001` 的设计：在共享的 Aster Legal Deal Desk 环境中，为交易 `D-LUMEN-908`（Lumen Vale）完成买方股票购买协议条款填充和起草立场判断。

共享生成数据位于 `task_group/task_group_020/env/data/dealdesk.json`，公开元数据位于 `task_group/task_group_020/env/data/manifest.json`。相关公开环境对象包括交易档案 `D-LUMEN-908`；有效文件 `DOC-LUMEN908-TERM-01`、`DOC-LUMEN908-DRAFT-02`、`DOC-LUMEN908-EMAIL-03`、`DOC-LUMEN908-CAP-ACTIVE`、`DOC-LUMEN908-FIN-04`、`DOC-LUMEN908-MATCON-05`、`DOC-LUMEN908-DISC-06`；过期或模板文件 `DOC-LUMEN908-CAP-STALE` 和 `DOC-LUMEN908-TEMPLATE-99`；有效条款 `CL-LUMEN-908-001` 至 `CL-LUMEN-908-005`；过期或模板条款 `CL-LUMEN-908-S01`、`CL-LUMEN-908-S02`；以及政策文件 `DOC-BUYERMIDMARKET2026-POLICY` 和政策 `P-BUYER-MIDMARKET-2026`。

任务本地、解题者可见文件为 `input/prompt.txt` 和 `input/payloads/answer_template.json`。提示词说明业务请求、环境入口约定、目标交易编号和所需 JSON 键，但不提供操作步骤、来源优先级清单、评分规则或答案。

### 任务定义与场景匹配

解题者扮演买方律师，为 `D-LUMEN-908` 准备结构化 SPA 起草包。所需 JSON 现在包含六个顶层部分：`deal_terms`、`seller_allocations`、`closing_flags`、`source_precedence`、`policy_checks` 和 `drafting_positions`。

本任务符合并购法律运营场景，因为解题者必须协调商业条款、当前起草指示、cap table、重大合同、监管状态、披露附表、过期/模板冲突以及 Northstar 买方 playbook。它保留来源示例中的难度因素：主体精确性、有效与过期来源选择、法律起草立场、审批和风险判断，以及精确财务计算。

本文件是在直接校准过高后重做的：两次尝试得分为 1.0 和 0.733，平均 0.867。原评分过多奖励直接环境查询和算术。新版输出和评估器把大部分权重转移到依赖迁移的受控字段：来源优先级、精确风险立场、有效与过期/模板冲突处理、条件性升级触发、精确来源 ID、政策检查和起草立场枚举。

### 材料地图

- `GET /api/deals/D-LUMEN-908` 和 `/deals/D-LUMEN-908`：交易档案、主体、headline/equity value、日期、有效/过期文件链接、附表、客户立场和谈判背景。
- `DOC-LUMEN908-TERM-01`：已签署商业条款书，提供价值、时间安排、对价组合、托管、赔偿上限、basket、存续期和营运资本。
- `DOC-LUMEN908-DRAFT-02`：有效起草指示，提供 cap table 优先级、同意、托管、竞业限制、fallback 权限和升级立场。
- `DOC-LUMEN908-EMAIL-03`：最新客户指示，确认有效 cap table 优先、具名同意立场、SensorForge fallback，以及卖方使用过期 cap table 或将 OmniAuto/KiteRail 移至交割后时需升级。
- `DOC-LUMEN908-CAP-ACTIVE`：2026-07-31 控制性所有权附表，用于卖方分配。
- `DOC-LUMEN908-CAP-STALE`：2026-02-28 过期 cap table，仅用于审计轨迹，不作为控制性分配依据。
- `DOC-LUMEN908-FIN-04`：财务附表，提供营运资本、托管、赔偿上限、basket、de minimis 和对价组合。
- `DOC-LUMEN908-MATCON-05`：重大合同同意矩阵和监管状态，包括 HSR 与大学许可同意。
- `DOC-LUMEN908-DISC-06`：雇佣、竞业限制、过渡服务和 IP 确认事实。
- `DOC-LUMEN908-TEMPLATE-99`：通用导入模板条款，包含具有干扰性的竞业限制和同意语言。
- `DOC-BUYERMIDMARKET2026-POLICY` / `P-BUYER-MIDMARKET-2026`：Northstar 买方风险备忘录和 SPA playbook，包含规则 ID、审批类别、阈值和政策依据。
- `/api/clauses?deal_id=D-LUMEN-908`：用于 allocation、escrow、non-compete、consents 和 HSR 的条款级有效/过期交叉核对。

### 答案和评估依据

标准答案使用日期为 2026-07-31 的 `DOC-LUMEN908-CAP-ACTIVE`，因为它取代 2 月过期 cap table。Headline purchase price 和 equity value 均为 257,500,000 美元。对价为 232,500,000 美元 closing cash 和 25,000,000 美元 rollover equity，没有 seller note 或 earnout。有效 cap table 没有股份数，因此 `per_share_price_usd` 为 null，`per_share_price_basis` 为 `NO_SHARE_COUNT_IN_ACTIVE_CAP_TABLE`。每 1 个所有权百分点价值为 2,575,000 美元。

有效卖方分配集合为 BrightPath Ventures III 34.0%、87,550,000 美元；Lumen Founder Holdings 39.5%、101,712,500 美元；Lumen Management Pool 26.5%、68,237,500 美元。卖方收益基于 headline/equity value，而不是扣除托管后的 closing cash。

托管和赔偿条款按 headline value 计算。一般托管为 10.0% 即 25,750,000 美元；税务托管为 2.5% 即 6,437,500 美元；赔偿上限为 10.0% 即 25,750,000 美元；basket 为 0.75% deductible basket 即 1,931,250 美元；de minimis 为 60,000 美元。营运资本目标为 27,800,000 美元，collar 为 1,000,000 美元，并针对 7 月有效资产负债表 true-up。Collar 占 equity value 的比例为 0.39%。

必需重大合同交割同意是 OmniAuto Robotics Supply 和 KiteRail Deployment Agreement，来源均为 `DOC-LUMEN908-MATCON-05`。SensorForge License 仅是可接受的交割后通知事项。HSR 是必需的，因为反垄断备忘录说明达到可申报阈值；因此 HSR 应作为交割条件，来源为 `DOC-LUMEN908-MATCON-05`。其他监管批准包括 University license consent。

雇佣和限制性契约字段来源于 `DOC-LUMEN908-DISC-06`。Dani Rowe, founder 和 Victor Hsu, VP Controls 需要 retention agreements。没有来源说明固定雇佣期限，因此 `employment_agreement_term_months` 为 null。竞业限制为 30 个月、限于目标产品，不允许宽泛关联方范围。无需一般过渡服务，但需要 IP 转让确认。

来源优先级和起草立场是新版任务核心。控制性来源包括有效 cap table、最新客户邮件、有效起草文件、财务附表、重大合同附表、披露附表和买方政策。`DOC-LUMEN908-CAP-STALE` 与 `DOC-LUMEN908-TEMPLATE-99` 被取代。有效条款 `CL-LUMEN-908-001` 至 `CL-LUMEN-908-005` 优先于过期/模板条款 `CL-LUMEN-908-S01` 和 `CL-LUMEN-908-S02`。起草立场使用受控枚举，例如 `BUYER_FORM`、`ALLOCATION_DRAFTING_POSITION`、`HSR_FILING_CONDITION`、`TARGETED_PRODUCT_SCOPE_RESTRICTIVE_COVENANT` 和 `ACTIVE_DRAFT_SUPERSEDES_TEMPLATE`。

政策检查使用 `P-BUYER-MIDMARKET-2026` 版本 `2026.2`。当前有效条款均在政策内；当前无需审批，当前政策例外数为 0。条件性升级触发仅为 `CONSENT_TIMING_TRIGGER` 和 `ALLOCATION_SOURCE_TRIGGER`。已复核但未触发的阈值包括 basket 低于 0.5%、扩大竞业限制、赔偿上限超过 12.5%、一般托管超过 12%、税务托管超过 3%、HSR 分析不清以及未验证 NWC 目标。

评估器有 8 个 exact-match 评分点，原始总权重为 12，并已与 `task_group.yaml` 同步：

- `SP1_SOURCE_PRECEDENCE_CONTROLLED_SOURCES`，权重 3：来源优先级决策、有效/过期条款 ID 和被取代来源 ID。
- `SP2_DRAFTING_POSTURE_ENUMS`，权重 1：受控起草立场字段。
- `SP3_POLICY_CHECKS_CURRENT_STATUS`，权重 3：政策规则 ID、审批类别、当前状态、审批摘要和条件性触发集合。
- `SP4_CONDITIONAL_ESCALATION_RISK_POSTURE`，权重 1：风险立场、未触发阈值、条件性升级明细和风险备忘录覆盖来源 ID。
- `SP5_CONSENT_HSR_SOURCE_SELECTION`，权重 1：同意、交割后通知、HSR、监管批准和来源文件处理。
- `SP6_EMPLOYMENT_NONCOMPETE_SOURCE_SELECTION`，权重 1：雇佣、竞业限制、过渡服务、IP 确认和来源文件。
- `SP7_ACTIVE_CAP_TABLE_ALLOCATION_MATH`，权重 1：交易经济条款、有效 cap table、每股价格可用性和卖方分配。
- `SP8_ESCROW_NWC_VALUE_POLICY_MATH`，权重 1：托管、赔偿上限、basket、de minimis 和营运资本机制。

常见模型错误包括使用 2 月过期 cap table、把通用模板当作 fallback 来源、把所有可能政策阈值都列为当前条件性触发、把 SensorForge 作为重大交割同意、遗漏来源文件 ID、把当前政策内条款标为需要审批、套用训练任务中的错误 HSR 立场，或用叙述性起草标签代替受控枚举。

### 迁移设计

本测试任务由 `train_001` 和 `train_005` 锚定。

从 `train_001`，解题者应迁移买方条款填充惯例：有效交易室附表优先于过期 cap table；有效客户指示和披露附表优先于模板；除非 schema 另有说明，卖方分配使用有效所有权附表和 headline/equity value；监管和同意 flags 来自交易特定记录；输出使用受控枚举、整数美元、两位小数百分比、精确来源 ID 和排序列表。

从 `train_005`，解题者应迁移政策和起草立场习惯：最新客户指示和交易特定风险记录可以覆盖通用表格语言；政策检查必须区分当前审批需求和未来条件性升级触发；有效来源覆盖记录需要精确来源和被取代文件 ID；起草立场应编码为受控枚举而不是自由叙述。

依赖迁移的评分点是 `SP1`、`SP2`、`SP3` 和 `SP4`；`SP5` 和 `SP6` 也通过来源文件选择及有效/模板冲突处理体现迁移要求。任务自身探索仍需找出 Lumen 特有数字、卖方、合同、HSR 结果、来源 ID、有效和过期条款 ID 以及竞业限制事实。解题者可见提示词不教授来源优先级或政策立场流程。

### 构建记录

作者：`task_group_020/test_001` task-builder subagent。

创建日期：2026-07-07。

更新日期：2026-07-07。

主要变更：创建原始任务文件；随后在直接校准平均 0.867 后重做，新增依赖迁移的 `source_precedence`、`policy_checks`、`drafting_positions`、更严格的 `risk_posture_flags`、精确来源文件 ID、受控政策测量代码，以及 8 点评估器。

## Evaluation Synchronization Update

The evaluator has eight exact-match scoring points, raw weight total 12, synchronized with `task_group.yaml`:

- `SP1_SOURCE_PRECEDENCE_CONTROLLED_SOURCES`, weight 3: source-precedence decisions, active/stale clause IDs, and superseded source IDs.
- `SP2_DRAFTING_POSTURE_ENUMS`, weight 1: controlled drafting posture fields.
- `SP3_POLICY_CHECKS_CURRENT_STATUS`, weight 3: policy rule IDs, approval categories, current status, approval summary, and conditional trigger set.
- `SP4_CONDITIONAL_ESCALATION_RISK_POSTURE`, weight 1: risk posture, non-triggered thresholds, conditional escalation details, and risk-memo override source IDs.
- `SP5_CONSENT_HSR_SOURCE_SELECTION`, weight 1: consent, post-closing notice, HSR, regulatory approval, and source-document treatment.
- `SP6_EMPLOYMENT_NONCOMPETE_SOURCE_SELECTION`, weight 1: employment, non-compete, transition service, IP confirmation, and source document.
- `SP7_ACTIVE_CAP_TABLE_ALLOCATION_MATH`, weight 1: economics, active cap table, per-share availability, and seller allocations.
- `SP8_ESCROW_NWC_VALUE_POLICY_MATH`, weight 1: escrow, cap, basket, de minimis, and working-capital mechanics.

This section is authoritative for evaluator weight documentation after the latest rework. It matches `eval/eval.py` and `task_group.yaml`.
