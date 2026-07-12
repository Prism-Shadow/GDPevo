# train_005 Notes

## English

### Data and Source Lineage

This task belongs to scenario `SCN_020_ma_transaction_contract_review_and_negotiation`, derived from source examples `E001`, `E002`, and `E003`. The task implements the task-group design brief for `train_005`: buyer-side first-draft term population plus policy checks for deal `D-HARBOR-562`, code-named Harbor Lantern, in the shared Aster Legal Deal Desk environment.

The generated shared data comes from `task_group/task_group_020/env/data/dealdesk.json` and `task_group/task_group_020/env/data/manifest.json`. The relevant public environment objects are the deal profile for `D-HARBOR-562`, active documents `DOC-HARBOR562-TERM-01`, `DOC-HARBOR562-DRAFT-02`, `DOC-HARBOR562-EMAIL-03`, `DOC-HARBOR562-CAP-ACTIVE`, `DOC-HARBOR562-FIN-04`, `DOC-HARBOR562-MATCON-05`, `DOC-HARBOR562-DISC-06`, stale documents `DOC-HARBOR562-CAP-STALE` and `DOC-HARBOR562-TEMPLATE-99`, active clause records `CL-HARBOR-562-001` through `CL-HARBOR-562-006`, and policy `P-BUYER-MIDMARKET-2026`.

Task-local solver-visible files are `input/prompt.txt` and `input/payloads/answer_template.json`. The prompt asks for a realistic legal deal-desk deliverable and does not provide a checklist, answer path, or hidden scoring criteria. The template defines the required JSON shape, units, enum choices, numeric precision, and list ordering rules without filling in the Harbor values.

### Task Definition and Scenario Fit

The solver acts as buyer counsel preparing the structured first-draft term population and policy checks for a stock purchase agreement. The expected JSON contains `draft_terms` and `policy_checks`. The solver must reconcile a deal profile, active and stale deal-room documents, active clauses, material-contract schedules, financial schedules, the Northstar buyer risk memo/playbook, and the latest client instruction email.

This fits the M&A transaction review scenario because it mirrors a first-draft SPA workstream: populate consideration, seller allocation, escrow, cap, basket, survival, working capital, closing-condition, HSR, and drafting-position terms while checking client policy exceptions and approval routing. The task uses the same difficulty drivers as the source examples: cross-document precedence, legal/business judgment, dollar calculations, policy threshold checks, and distractor template/stale records.

### Material Map

- `D-HARBOR-562` deal profile supplies buyer, seller, target, structure, headline/equity value, signing date, closing deadline, client side, policy id, economics, client positions, and schedules.
- `DOC-HARBOR562-TERM-01` supplies the signed commercial term sheet and the main economics.
- `DOC-HARBOR562-DRAFT-02` supplies active first-draft instructions, current drafting posture, fallback authority, and escalation note.
- `DOC-HARBOR562-EMAIL-03` supplies the latest client instruction and strategic context; it confirms buyer-form use, cap/escrow alignment, material consents, no-HSR facts, earnout fallback, and conditional escalations.
- `DOC-HARBOR562-CAP-ACTIVE` controls seller ownership and allocation math. `DOC-HARBOR562-CAP-STALE` is a distractor retained for audit only.
- `DOC-HARBOR562-FIN-04` supplies working capital, escrow, cap, basket, and consideration mix.
- `DOC-HARBOR562-MATCON-05` supplies material-contract consent status and the regulatory basis for no HSR.
- `DOC-HARBOR562-DISC-06` supplies employment, non-compete, transition services, and IP transition facts.
- `DOC-HARBOR562-TEMPLATE-99` is a generic template distractor and should not override active client instructions.
- `P-BUYER-MIDMARKET-2026` supplies policy thresholds and approval categories for escrow, cap, basket, NWC, non-compete, material consents, and HSR.

### Solution and Evaluation Basis

The answer uses the active cap table as the controlling allocation source. The consideration mix is cash at close `$157,000,000`, seller note `$18,500,000`, rollover equity `$15,000,000`, and earnout `$8,000,000`, totaling `$198,500,000`. Each component is allocated pro rata by active ownership: HarborGrid Founders LLC 51%, Management Option Sellers 18%, and Tern Cyber Fund I 31%. This yields total proceeds of `$101,235,000`, `$35,730,000`, and `$61,535,000`, respectively.

Escrow and indemnity math uses headline value `$198,500,000`. General escrow is 10% or `$19,850,000`; tax escrow is 2% or `$3,970,000`; aggregate escrow is 12% or `$23,820,000`; the general indemnity cap equals the 10% general escrow amount; the deductible basket is 0.75% or `$1,488,750`; de minimis is `$50,000`; survival is 18 months for general reps and 72 months for fundamental and tax reps.

Closing conditions require Federal SOC Platform Order and BlueBank MDR Agreement consents. GovCloud Hosting Addendum is a post-closing notice item. HSR is not required, no filing condition should be included, and the correct HSR drafting position is cooperation covenant only. Other approvals include Federal customer novation consent.

The risk memo override is that no HSR condition should be included despite sensitive cyber assets because reportable thresholds are not met after debt adjustments. The latest client instruction and material-contract/regulatory schedule override generic template language. The active cap table overrides the stale cap export.

All active positions are currently within Northstar policy or covered by the deal-specific override; no approval is required now and current policy exception count is zero. Conditional escalation triggers are adding a financing condition or removing the federal customer consent. Policy checks must use the approval categories and rule ids from `P-BUYER-MIDMARKET-2026`.

The evaluator has six exact-match scoring points, matching the requested plan:

1. `consideration_mix_and_allocation`, weight 3: consideration mix, active allocation source, and seller allocation schedule.
2. `escrow_cap_basket_math`, weight 3: escrow, cap, basket, de minimis, and survival math.
3. `consent_hsr_flags`, weight 2: closing consents, post-closing notice, HSR status, HSR clause position, and other approval.
4. `risk_memo_overrides`, weight 2: override source documents, override codes, superseded documents, and HSR override basis.
5. `policy_exceptions_approvals`, weight 2: per-topic policy checks and summary approvals/exceptions.
6. `drafting_position_enums`, weight 2: controlled drafting-position enums.

Likely model pitfalls are using the stale cap table, omitting the seller note or earnout from allocation, subtracting escrow from cash consideration without being asked, treating cyber assets as an automatic HSR filing condition, applying generic template non-compete language, failing to include BlueBank or Federal SOC as closing consents, or marking in-policy terms as approval-required merely because the policy lists escalation thresholds.

### Transfer Design

As a train task, `train_005` reinforces transferable conventions for later test tasks. Solvers can infer that active deal-room records outrank stale exports and generic templates; latest client instructions and deal-specific risk memos can override generic form language; percentages should be applied to headline/equity value as specified; seller allocations can require prorating every consideration component by the active cap table; policy checks must distinguish current approval requirements from conditional future escalation triggers; and drafting outputs should use controlled enums instead of narrative labels.

The task is not a tutorial. The solver must discover the relevant records in the shared environment, select active sources, perform calculations, and reconcile policy thresholds against live deal terms. These habits transfer to buyer-side term-population and policy-check test tasks without revealing test answers.

### Construction Record

Author: task-builder subagent for `task_group_020/train_005`.

Created: 2026-07-07.

Updated: 2026-07-07.

Major changes: created solver prompt, answer template, standard answer, exact-match evaluator, and bilingual notes for `D-HARBOR-562`.

## 中文

### 数据和来源脉络

本任务属于场景 `SCN_020_ma_transaction_contract_review_and_negotiation`，来源示例为 `E001`、`E002`、`E003`。任务实现 `train_005` 的设计：在共享的 Aster Legal Deal Desk 环境中，为交易 `D-HARBOR-562`（Harbor Lantern）完成买方首稿条款填充和政策检查。

生成的共享数据来自 `task_group/task_group_020/env/data/dealdesk.json` 和 `task_group/task_group_020/env/data/manifest.json`。相关公开环境对象包括交易档案 `D-HARBOR-562`，有效文件 `DOC-HARBOR562-TERM-01`、`DOC-HARBOR562-DRAFT-02`、`DOC-HARBOR562-EMAIL-03`、`DOC-HARBOR562-CAP-ACTIVE`、`DOC-HARBOR562-FIN-04`、`DOC-HARBOR562-MATCON-05`、`DOC-HARBOR562-DISC-06`，过期或模板文件 `DOC-HARBOR562-CAP-STALE`、`DOC-HARBOR562-TEMPLATE-99`，有效条款记录 `CL-HARBOR-562-001` 至 `CL-HARBOR-562-006`，以及政策 `P-BUYER-MIDMARKET-2026`。

任务本地、解题者可见的文件是 `input/prompt.txt` 和 `input/payloads/answer_template.json`。提示语是现实业务请求，不提供步骤清单、答案路径或隐藏评分标准。模板只定义 JSON 结构、单位、枚举、数值精度和列表排序规则，不填入 Harbor 的答案值。

### 任务定义与场景匹配

解题者扮演买方律师，为股票购买协议首稿准备结构化条款和政策检查 JSON。预期输出包含 `draft_terms` 和 `policy_checks`。解题者需要协调交易档案、有效和过期文件、有效条款、重大合同清单、财务附表、Northstar 买方风险备忘录/剧本以及最新客户指示邮件。

这符合并购合同审查场景，因为它模拟 SPA 首稿工作流：填充对价、卖方分配、托管、赔偿上限、篮子、存续期、营运资金、交割条件、HSR 和起草立场，同时检查客户政策例外和审批路径。难度来自跨文件优先级、法律和商业判断、金额计算、政策阈值检查，以及模板/过期记录干扰。

### 材料地图

- `D-HARBOR-562` 交易档案提供买方、卖方、目标公司、交易结构、headline/equity value、签署日、最晚交割日、客户方、政策编号、经济条款、客户立场和附表。
- `DOC-HARBOR562-TERM-01` 提供签署的商业条款书和主要经济条款。
- `DOC-HARBOR562-DRAFT-02` 提供有效首稿指示、当前起草立场、后备授权和升级提示。
- `DOC-HARBOR562-EMAIL-03` 提供最新客户指示和战略背景，确认使用买方表格、上限与托管一致、重大同意、无 HSR 事实、earnout 后备方案和条件性升级事项。
- `DOC-HARBOR562-CAP-ACTIVE` 控制卖方持股和分配计算；`DOC-HARBOR562-CAP-STALE` 只是审计保留的干扰文件。
- `DOC-HARBOR562-FIN-04` 提供营运资金、托管、赔偿上限、篮子和对价组合。
- `DOC-HARBOR562-MATCON-05` 提供重大合同同意状态和无 HSR 的监管依据。
- `DOC-HARBOR562-DISC-06` 提供雇佣、竞业限制、过渡服务和 IP 过渡事实。
- `DOC-HARBOR562-TEMPLATE-99` 是通用模板干扰项，不能覆盖有效客户指示。
- `P-BUYER-MIDMARKET-2026` 提供托管、赔偿上限、篮子、营运资金、竞业限制、重大同意和 HSR 的政策阈值与审批类别。

### 答案和评估依据

标准答案使用有效 cap table 作为控制分配来源。对价组合为现金交割 `$157,000,000`、卖方票据 `$18,500,000`、滚存股权 `$15,000,000`、earnout `$8,000,000`，合计 `$198,500,000`。各组成部分按有效持股比例分摊：HarborGrid Founders LLC 51%，Management Option Sellers 18%，Tern Cyber Fund I 31%。对应总收益分别为 `$101,235,000`、`$35,730,000` 和 `$61,535,000`。

托管和赔偿金额以 headline value `$198,500,000` 为基数。一般托管为 10% 即 `$19,850,000`；税务托管为 2% 即 `$3,970,000`；合计托管为 12% 即 `$23,820,000`；一般赔偿上限等于 10% 一般托管金额；deductible basket 为 0.75% 即 `$1,488,750`；de minimis 为 `$50,000`；一般陈述保证存续 18 个月，基本陈述和税务陈述存续 72 个月。

交割条件需要 Federal SOC Platform Order 和 BlueBank MDR Agreement 的同意。GovCloud Hosting Addendum 是交割后通知事项。HSR 不需要申报，不应加入申报条件，正确 HSR 起草立场是仅保留合作承诺。其他审批/同意包括 Federal customer novation consent。

风险备忘录覆盖点是：尽管存在敏感网络安全资产，但因债务调整后未达到可申报阈值，不应加入 HSR 条件。最新客户指示和重大合同/监管附表覆盖通用模板语言。有效 cap table 覆盖过期 cap table 导出。

所有有效立场目前均在 Northstar 政策内，或已有交易特定覆盖依据；当前无需审批，当前政策例外数量为零。条件性升级触发项是加入融资条件，或删除联邦客户同意。政策检查必须使用 `P-BUYER-MIDMARKET-2026` 中的审批类别和规则编号。

评估器包含六个精确匹配评分点，符合指定计划：

1. `consideration_mix_and_allocation`，权重 3：对价组合、有效分配来源和卖方分配表。
2. `escrow_cap_basket_math`，权重 3：托管、上限、篮子、de minimis 和存续期计算。
3. `consent_hsr_flags`，权重 2：交割同意、交割后通知、HSR 状态、HSR 条款立场和其他同意。
4. `risk_memo_overrides`，权重 2：覆盖来源文件、覆盖代码、被覆盖文件和 HSR 覆盖依据。
5. `policy_exceptions_approvals`，权重 2：逐项政策检查以及审批/例外汇总。
6. `drafting_position_enums`，权重 2：受控起草立场枚举。

常见模型错误包括使用过期 cap table、漏掉卖方票据或 earnout 的分配、未经要求就从现金对价中扣除托管、把敏感网络安全资产误判为自动 HSR 条件、套用通用模板竞业限制、漏掉 BlueBank 或 Federal SOC 作为交割同意，或因为政策列出升级阈值而把合规条款误标为需要审批。

### 迁移设计

作为训练任务，`train_005` 强化后续测试任务可迁移的惯例：有效交易室记录优先于过期导出和通用模板；最新客户指示和交易特定风险备忘录可以覆盖通用表格语言；百分比应按指定的 headline/equity value 计算；卖方分配可能需要按有效 cap table 对每个对价组成部分逐项按比例分摊；政策检查必须区分当前审批要求和未来条件性升级触发；起草输出应使用受控枚举而不是叙述标签。

本任务不是教程。解题者必须在共享环境中自行发现相关记录、选择有效来源、完成计算，并用实时交易条款对照政策阈值。这些习惯可以迁移到买方条款填充和政策检查类测试任务，但不会泄露测试答案。

### 构建记录

作者：`task_group_020/train_005` 的 task-builder subagent。

创建日期：2026-07-07。

更新日期：2026-07-07。

主要变更：为 `D-HARBOR-562` 创建了解题提示、答案模板、标准答案、精确匹配评估器和双语说明。
