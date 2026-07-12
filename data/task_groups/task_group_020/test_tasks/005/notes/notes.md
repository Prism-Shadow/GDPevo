# test_005 Notes - Solstice Minority Rollover SPA Risk Allocation

## English

### Data and Source Lineage

This task belongs to `task_group_020`, scenario `SCN_020_ma_transaction_contract_review_and_negotiation`, derived from source examples `E001`, `E002`, and `E003`. It implements the `test_005` assignment from `scratch/task_group_design.md`: a buyer-side minority rollover stock purchase for deal `D-SOLSTICE-820`, combining allocation math with risk-allocation overrides.

The shared environment is `Aster Legal Deal Desk`, implemented under `task_group/task_group_020/env/`. The generated data comes from `env/data/dealdesk.json` and `env/data/manifest.json`. Public environment objects used by this task include deal `D-SOLSTICE-820`, policy `P-ROLLOVER-SPA-2026`, active documents `DOC-SOLSTICE820-TERM-01`, `DOC-SOLSTICE820-DRAFT-02`, `DOC-SOLSTICE820-EMAIL-03`, `DOC-SOLSTICE820-CAP-ACTIVE`, `DOC-SOLSTICE820-FIN-04`, `DOC-SOLSTICE820-MATCON-05`, `DOC-SOLSTICE820-DISC-06`, and `DOC-SOLSTICE820-COMMITTEE-07`. Stale or template distractors are `DOC-SOLSTICE820-CAP-STALE`, `DOC-SOLSTICE820-TEMPLATE-99`, `CL-SOLSTICE-820-S01`, and `CL-SOLSTICE-820-S02`.

Task-local solver-visible files are `input/prompt.txt` and `input/payloads/answer_template.json`. The prompt is a realistic deal-desk request and does not include scoring hints, SOP steps, or answers.

### Task Definition and Scenario Fit

The solver acts as buyer-side transaction counsel for Solstice Strategic Capital. The requested deliverable is a normalized JSON drafting and risk-allocation package with two top-level business objects: `deal_terms` and `risk_overrides`. The solver must reconcile active deal records, current draft clauses, policy thresholds, latest client instructions, approval records, cap table data, financial schedules, and consent/customer-risk schedules.

This fits the M&A contract review scenario because it mirrors the original examples' long-horizon legal workflow: select controlling deal-room sources, reject stale or generic materials, calculate consideration and indemnity amounts, identify out-of-policy draft clauses, and convert legal judgment into a structured drafting posture. The task is not a single lookup because the answer requires calculations and source-precedence decisions across several public environment surfaces.

### Material Map

- `GET /api/deals/D-SOLSTICE-820` and `/deals/D-SOLSTICE-820`: deal profile, parties, economics, client positions, active/stale documents, schedules, and policy id.
- `DOC-SOLSTICE820-TERM-01`: signed commercial term sheet with headline value, equity value, signing date, closing deadline, consideration mix, escrow, cap, basket, survival, and NWC terms.
- `DOC-SOLSTICE820-DRAFT-02`: current draft agreement terms, including the unilateral note offset, 3.5% tax escrow, 14.5% headline-value cap, stale NWC baseline, and active negotiation posture.
- `DOC-SOLSTICE820-EMAIL-03`: latest client instruction email, confirming the active allocation schedule, rejection of unilateral note offset, tax escrow reduction to 3%, NWC baseline update, and general-rep cap at escrow.
- `DOC-SOLSTICE820-CAP-ACTIVE`: active July 25, 2026 ownership schedule for seller allocation math.
- `DOC-SOLSTICE820-CAP-STALE`: stale May 31 cap table retained only as a distractor.
- `DOC-SOLSTICE820-FIN-04`: financial schedule for working capital, escrows, cap, basket, and consideration mix.
- `DOC-SOLSTICE820-MATCON-05`: material customer consent matrix and regulatory status.
- `DOC-SOLSTICE820-DISC-06`: transition services, IP transition, employment, and restrictive covenant schedules.
- `DOC-SOLSTICE820-COMMITTEE-07`: committee members and current approval-trigger record.
- `P-ROLLOVER-SPA-2026`: rollover stock purchase risk-allocation standard.
- `/api/clauses?deal_id=D-SOLSTICE-820`: active clause records `CL-SOLSTICE-820-001` through `CL-SOLSTICE-820-006` and stale template distractors.

### Solution and Evaluation Basis

The standard answer in `output/answer.json` uses the active July 25 cap table and active/latest written instructions. Headline value and equity value are both USD 224,000,000. The consideration mix is USD 154,000,000 cash at close, USD 12,000,000 seller note, USD 58,000,000 rollover equity, and no earnout. Following the task-group convention from term-population train tasks, the active ownership schedule controls allocation. The components are prorated by active ownership:

- Prairie Energy Fund: 33.0%, USD 50,820,000 cash, USD 3,960,000 note, USD 19,140,000 rollover, USD 73,920,000 total.
- Solstice Founder Group: 42.0%, USD 64,680,000 cash, USD 5,040,000 note, USD 24,360,000 rollover, USD 94,080,000 total.
- Solstice Management Rollover: 25.0%, USD 38,500,000 cash, USD 3,000,000 note, USD 14,500,000 rollover, USD 56,000,000 total.

Escrow and cap math uses the USD 224,000,000 headline value unless the policy specifies a different base. General escrow stays at 10.0%, or USD 22,400,000. The draft tax escrow is 3.5%, or USD 7,840,000, but the latest risk-allocation instruction caps the tax reserve at 3.0%, or USD 6,720,000. The target aggregate escrow is therefore 13.0%, or USD 29,120,000, rather than the draft 13.5%, or USD 30,240,000. The draft general cap is 14.5% of headline value, or USD 32,480,000. The required drafting position is to cap general reps at the general escrow amount, USD 22,400,000; the fallback cap is 12.0% of cash consideration, or USD 18,480,000, only with committee approval. The deductible basket is 0.75%, or USD 1,680,000, with a USD 50,000 de minimis and 18-month general rep survival.

The seller note offset must be rejected unless written lender consent is obtained. The draft would reduce closing cash by USD 12,000,000 to USD 142,000,000 if accepted, but the target cash-at-close amount remains USD 154,000,000. Working capital uses the USD 26,300,000 target but rejects the stale May baseline. The draft USD 2,250,000 collar is 1.00% of headline value and exceeds the 0.75% maximum of USD 1,680,000 by USD 570,000. The answer uses a true-up against the current active balance sheet.

The material customer consents are BasinOps Master Services and SunWell Safety Services, both closing conditions. Fleet Telematics License is only a notice/post-closing notice item. Customer revenue at risk is USD 65,200,000. HSR is not required after debt and excluded-asset adjustments, so no HSR filing condition should be included. Other approvals list BasinOps consent. Transition services for dispatch, safety reporting, and fleet telematics, plus IP transition, are required.

The risk-overridden clause set is exactly `CAP`, `ESCROW`, `NOTE_OFFSET`, and `NWC`. `CASH_ROLLOVER` and `BASKET` are reviewed active clauses but not overridden clauses because the active draft already matches the controlling schedule or stays within policy. The controlling risk source IDs are `DOC-SOLSTICE820-COMMITTEE-07`, `DOC-SOLSTICE820-DRAFT-02`, `DOC-SOLSTICE820-EMAIL-03`, and `P-ROLLOVER-SPA-2026`; the clause IDs that actually drive override rows are `CL-SOLSTICE-820-002`, `CL-SOLSTICE-820-003`, `CL-SOLSTICE-820-004`, and `CL-SOLSTICE-820-005`. The answer rejects stale/template authority from `DOC-SOLSTICE820-CAP-STALE`, `DOC-SOLSTICE820-TEMPLATE-99`, `CL-SOLSTICE-820-S01`, and `CL-SOLSTICE-820-S02`.

The active rollover policy would route the NWC topic to finance in isolation, but the Solstice draft/email/committee record states that the unrevised Solstice triggers route through credit committee. The standard answer therefore uses `DEAL_SPECIFIC_COMMITTEE_NOTE_CONTROLS`, `CREDIT_COMMITTEE`, and `DOC-SOLSTICE820-COMMITTEE-07` for all four unrevised triggers. The source-precedence enum is generic in the solver-visible template, but the hidden answer maps it to the active Solstice-specific instructions. The final drafting posture is `REVISE_BEFORE_SIGNING` with readiness `READY_AFTER_REVISIONS`.

The evaluator has eight exact-match scoring points, raw total weight 10, synchronized with `task_group.yaml`:

- `SP001_DEAL_TERMS_AND_CLOSING_FACTS`, weight 1: all generic deal-term work, including allocation math, indemnity values, note/NWC treatment, consents, HSR, transition services, and IP transition.
- `SP002_EXACT_CONTROLLING_RISK_SOURCE_IDS`, weight 3: policy id/version, source precedence code, exact `controlling_risk_source_ids`, exact `source_ids`, rejected document source IDs, and superseded source IDs.
- `SP003_EXACT_CONTROLLING_CLAUSE_SOURCE_IDS`, weight 1: exact `controlling_clause_source_ids`, exact `non_overridden_active_clause_ids`, and exact `rejected_template_clause_ids`, with accepted active clauses excluded from the controlling override-clause set.
- `SP004_EXACT_OVERRIDE_CODES_NO_TEMPLATE_SUPERSEDED`, weight 1: exact `override_codes` and `overridden_clause_codes`; `TEMPLATE_SOURCE_POSITION` must not be included merely because template records were rejected.
- `SP005_EXACT_NON_OVERRIDDEN_CLAUSE_HANDLING`, weight 1: exact `non_overridden_clause_codes` and `non_overridden_clause_handling` for active clauses reviewed but accepted.
- `SP006_OVERRIDE_SUBSTANTIVE_POSITIONS`, weight 1: clause-level source clause IDs, source document IDs, policy rule IDs, override actions, draft position codes, and required position codes.
- `SP007_APPROVAL_ROUTING_AND_SUMMARY`, weight 1: routing precedence, per-clause approval routing fields, and approval summary.
- `SP008_FINAL_SOURCE_PRUNED_DRAFTING_POSTURE`, weight 1: final drafting posture, signing readiness, and drafting-position enums tied to the exact source-pruned risk sources, controlling clause IDs, override codes, and non-overridden active-clause handling.

The evaluator accepts a prediction path as its first argument and defaults to `output/answer.json`. It prints JSON with normalized score, earned weight, total weight, point-level pass/fail, and mismatches. Lists are normalized by stable sort keys or sorted scalar values; floats are rounded to two decimal places.

Likely model pitfalls include using the stale May cap table, allocating only total proceeds rather than cash/note/rollover components, accepting the note offset as an economic neutral, keeping the 3.5% tax escrow, computing the cap from the wrong base, omitting SunWell as a closing consent, treating Fleet Telematics as a consent, adding an HSR filing condition, treating generic template clauses as controlling, over-including every consulted diligence source as a controlling risk source, listing all active clauses as controlling clause sources, adding `TEMPLATE_SOURCE_POSITION` to the active override code set, listing `BASKET` or `CASH_ROLLOVER` as overridden clauses, and routing NWC to finance by reading the generic policy without applying the Solstice-specific committee source.

### Transfer Design

This is a test task. Its transfer anchors are `train_001`, `train_002`, and `train_005`.

From `train_001`, solvers should transfer active-source precedence, cap table over stale exports, integer-dollar and two-decimal percentage conventions, and the habit of using material-contract schedules rather than template assumptions for consent and HSR flags. Those conventions support `SP001_DEAL_TERMS_AND_CLOSING_FACTS` and help avoid stale/template source mistakes in `SP002_EXACT_CONTROLLING_RISK_SOURCE_IDS`.

From `train_002`, solvers should transfer the counterparty-paper review habit: compare active draft clauses against the controlling playbook or client instruction, identify deviations as structured issue codes, avoid adding non-deviating clauses as issues, quantify economic corrections, and treat transition/customer operational terms as material even when they are not pure price terms. Those conventions support `SP003_EXACT_CONTROLLING_CLAUSE_SOURCE_IDS`, `SP004_EXACT_OVERRIDE_CODES_NO_TEMPLATE_SUPERSEDED`, `SP005_EXACT_NON_OVERRIDDEN_CLAUSE_HANDLING`, `SP006_OVERRIDE_SUBSTANTIVE_POSITIONS`, and `SP008_FINAL_SOURCE_PRUNED_DRAFTING_POSTURE`.

From `train_005`, solvers should transfer buyer-side term population plus policy-check methods: prorate consideration components by the active ownership schedule when no contrary component schedule controls, distinguish current approval requirements from conditional fallback authority, let deal-specific risk memos override generic templates, route approval bodies from the controlling current authority, and compute escrow/cap/basket amounts from the stated base. Those conventions support `SP001_DEAL_TERMS_AND_CLOSING_FACTS`, `SP002_EXACT_CONTROLLING_RISK_SOURCE_IDS`, `SP006_OVERRIDE_SUBSTANTIVE_POSITIONS`, `SP007_APPROVAL_ROUTING_AND_SUMMARY`, and `SP008_FINAL_SOURCE_PRUNED_DRAFTING_POSTURE`.

Task-specific exploration remains necessary because Solstice uses a minority rollover structure, a seller-side note offset, a 3.5% tax escrow draft deviation, a headline-value cap problem, a stale NWC baseline, and customer consent facts that do not appear in the train answers.

### Construction Record

Author: task-builder subagent for `task_group_020/test_005`.

Created: 2026-07-07.

Updated: 2026-07-07.

Major changes: created solver prompt, answer template, standard answer, exact-match evaluator, and bilingual notes for deal `D-SOLSTICE-820`; reworked after direct calibration scored too high by shifting emphasis from broad allocation/math checks to controlled source precedence, overridden-clause discipline, approval routing, source IDs, and final drafting posture. Later rework synchronized the evaluator and `task_group.yaml` to the current 10-point rubric: generic deal economics are one low-weight point, routing is separate from substantive override checks, and the largest point is exact risk-source pruning.

## 中文

### 数据和来源脉络

本任务属于 `task_group_020`，场景为 `SCN_020_ma_transaction_contract_review_and_negotiation`，来源示例为 `E001`、`E002` 和 `E003`。它实现 `scratch/task_group_design.md` 中的 `test_005`：针对交易 `D-SOLSTICE-820` 的买方少数股权 rollover 股票购买交易，结合分配计算和风险分配覆盖判断。

共享环境是 `Aster Legal Deal Desk`，实现位置在 `task_group/task_group_020/env/`。生成数据来自 `env/data/dealdesk.json` 和 `env/data/manifest.json`。本任务使用的公开环境对象包括交易 `D-SOLSTICE-820`、政策 `P-ROLLOVER-SPA-2026`，有效文件 `DOC-SOLSTICE820-TERM-01`、`DOC-SOLSTICE820-DRAFT-02`、`DOC-SOLSTICE820-EMAIL-03`、`DOC-SOLSTICE820-CAP-ACTIVE`、`DOC-SOLSTICE820-FIN-04`、`DOC-SOLSTICE820-MATCON-05`、`DOC-SOLSTICE820-DISC-06` 和 `DOC-SOLSTICE820-COMMITTEE-07`。过期或模板干扰项为 `DOC-SOLSTICE820-CAP-STALE`、`DOC-SOLSTICE820-TEMPLATE-99`、`CL-SOLSTICE-820-S01` 和 `CL-SOLSTICE-820-S02`。

任务本地、求解器可见的文件是 `input/prompt.txt` 和 `input/payloads/answer_template.json`。提示是现实交易台请求，不包含评分提示、SOP 步骤或答案。

### 任务定义与场景匹配

求解器扮演 Solstice Strategic Capital 的买方交易律师。交付物是规范化的 JSON 起草和风险分配包，包含两个顶层业务对象：`deal_terms` 和 `risk_overrides`。求解器必须核对有效交易记录、当前草案条款、政策阈值、最新客户指示、审批记录、股权表、财务附表以及同意/客户风险附表。

本任务符合并购合同审查场景，因为它复现了来源示例中的长流程法律工作：选择控制性交易室来源，排除过期或通用材料，计算对价和赔偿金额，识别不符合政策的草案条款，并把法律判断转成结构化起草立场。该任务不是单点查询，因为答案需要跨多个公开环境入口完成计算和资料优先级判断。

### 材料地图

- `GET /api/deals/D-SOLSTICE-820` 和 `/deals/D-SOLSTICE-820`：交易档案、交易方、经济条款、客户立场、有效/过期文件、附表和政策编号。
- `DOC-SOLSTICE820-TERM-01`：已签署商业条款书，包含 headline value、equity value、签署日、交割期限、对价组合、托管、cap、basket、存续期和营运资金条款。
- `DOC-SOLSTICE820-DRAFT-02`：当前草案协议条款，包括单方 note offset、3.5% 税务托管、14.5% headline-value cap、过期 NWC 基线和当前谈判立场。
- `DOC-SOLSTICE820-EMAIL-03`：最新客户指示邮件，确认有效分配附表、拒绝单方 note offset、税务托管降至 3%、更新 NWC 基线、一般陈述保证 cap 等于托管。
- `DOC-SOLSTICE820-CAP-ACTIVE`：2026-07-25 有效所有权附表，用于卖方分配计算。
- `DOC-SOLSTICE820-CAP-STALE`：2026-05-31 过期股权表，仅作为干扰项。
- `DOC-SOLSTICE820-FIN-04`：营运资金、托管、cap、basket 和对价组合财务附表。
- `DOC-SOLSTICE820-MATCON-05`：重大客户同意矩阵和监管状态。
- `DOC-SOLSTICE820-DISC-06`：过渡服务、IP 过渡、雇佣和限制性契约附表。
- `DOC-SOLSTICE820-COMMITTEE-07`：委员会成员和当前审批触发记录。
- `P-ROLLOVER-SPA-2026`：rollover 股票购买风险分配标准。
- `/api/clauses?deal_id=D-SOLSTICE-820`：有效条款记录 `CL-SOLSTICE-820-001` 至 `CL-SOLSTICE-820-006` 以及过期模板干扰条款。

### 答案和评估依据

标准答案 `output/answer.json` 使用 2026-07-25 有效股权表以及有效/最新书面指示。Headline value 和 equity value 均为 224,000,000 美元。对价组合为交割现金 154,000,000 美元、卖方票据 12,000,000 美元、rollover equity 58,000,000 美元，没有 earnout。根据条款填充训练任务中的任务组惯例，有效所有权附表控制分配。各对价组成部分按有效持股比例分摊：

- Prairie Energy Fund：33.0%，现金 50,820,000 美元，票据 3,960,000 美元，rollover 19,140,000 美元，总计 73,920,000 美元。
- Solstice Founder Group：42.0%，现金 64,680,000 美元，票据 5,040,000 美元，rollover 24,360,000 美元，总计 94,080,000 美元。
- Solstice Management Rollover：25.0%，现金 38,500,000 美元，票据 3,000,000 美元，rollover 14,500,000 美元，总计 56,000,000 美元。

除非政策指定其他基数，托管和 cap 计算使用 224,000,000 美元 headline value。一般托管保持 10.0%，即 22,400,000 美元。草案税务托管为 3.5%，即 7,840,000 美元，但最新风险分配指示将税务 reserve 上限设为 3.0%，即 6,720,000 美元。因此目标总托管为 13.0%，即 29,120,000 美元，而不是草案的 13.5%，即 30,240,000 美元。草案一般 cap 为 headline value 的 14.5%，即 32,480,000 美元。正确起草立场是一般陈述保证 cap 等于一般托管金额 22,400,000 美元；备用 cap 为现金对价的 12.0%，即 18,480,000 美元，但仅在委员会批准时可用。Deductible basket 为 0.75%，即 1,680,000 美元，de minimis 为 50,000 美元，一般陈述保证存续期为 18 个月。

除非取得书面贷款人同意，卖方票据抵销必须被拒绝。如果接受草案抵销，交割现金会减少 12,000,000 美元至 142,000,000 美元；目标交割现金仍为 154,000,000 美元。营运资本使用 26,300,000 美元目标，但拒绝 5 月过期基线。草案 2,250,000 美元 collar 占 headline value 的 1.00%，超过 0.75% 上限 1,680,000 美元，超出 570,000 美元。答案采用基于当前有效资产负债表的 closing true-up。

重大客户同意为 BasinOps Master Services 和 SunWell Safety Services，二者均为交割条件。Fleet Telematics License 只是通知/交割后通知事项。客户收入风险为 65,200,000 美元。经债务和排除资产调整后不需要 HSR，因此不应加入 HSR filing condition。其他审批列明 BasinOps consent。Dispatch、safety reporting 和 fleet telematics 过渡服务以及 IP 过渡均为必需。

风险覆盖条款集合精确为 `CAP`、`ESCROW`、`NOTE_OFFSET` 和 `NWC`。`CASH_ROLLOVER` 和 `BASKET` 是已审阅的有效条款，但不属于被覆盖条款，因为有效草案已经符合控制性附表或在政策内。控制风险分配的来源 ID 为 `DOC-SOLSTICE820-COMMITTEE-07`、`DOC-SOLSTICE820-DRAFT-02`、`DOC-SOLSTICE820-EMAIL-03` 和 `P-ROLLOVER-SPA-2026`；真正进入覆盖条款行的条款 ID 为 `CL-SOLSTICE-820-002`、`CL-SOLSTICE-820-003`、`CL-SOLSTICE-820-004` 和 `CL-SOLSTICE-820-005`。答案排除 `DOC-SOLSTICE820-CAP-STALE`、`DOC-SOLSTICE820-TEMPLATE-99`、`CL-SOLSTICE-820-S01` 和 `CL-SOLSTICE-820-S02` 等过期/模板来源。

单独阅读 rollover 政策时，NWC 主题会指向 finance committee；但 Solstice 的有效草案、邮件和委员会记录写明未修改的 Solstice 触发项由 credit committee 审批。因此标准答案对四项未修改触发都使用 `DEAL_SPECIFIC_COMMITTEE_NOTE_CONTROLS`、`CREDIT_COMMITTEE` 和 `DOC-SOLSTICE820-COMMITTEE-07`。求解器可见模板中的来源优先级枚举保持通用表述，隐藏答案再将其映射到 Solstice 特定的有效指示。最终起草立场为 `REVISE_BEFORE_SIGNING`，签约准备状态为 `READY_AFTER_REVISIONS`。

评估器包含 8 个精确匹配评分点，原始总权重为 10，并已与 `task_group.yaml` 同步：

- `SP001_DEAL_TERMS_AND_CLOSING_FACTS`，权重 1：所有通用交易条款工作，包括分配计算、赔偿数值、note/NWC 处理、consent、HSR、过渡服务和 IP 过渡。
- `SP002_EXACT_CONTROLLING_RISK_SOURCE_IDS`，权重 3：政策编号/版本、来源优先级代码、精确 `controlling_risk_source_ids`、精确 `source_ids`、被拒绝文件来源 ID 和 superseded source ID。
- `SP003_EXACT_CONTROLLING_CLAUSE_SOURCE_IDS`，权重 1：精确 `controlling_clause_source_ids`、精确 `non_overridden_active_clause_ids` 和精确 `rejected_template_clause_ids`，已接受的有效条款不得进入控制性 override clause 集合。
- `SP004_EXACT_OVERRIDE_CODES_NO_TEMPLATE_SUPERSEDED`，权重 1：精确 `override_codes` 和 `overridden_clause_codes`；不能仅因拒绝模板记录就加入 `TEMPLATE_SOURCE_POSITION`。
- `SP005_EXACT_NON_OVERRIDDEN_CLAUSE_HANDLING`，权重 1：针对已审阅但接受的有效条款，精确填写 `non_overridden_clause_codes` 和 `non_overridden_clause_handling`。
- `SP006_OVERRIDE_SUBSTANTIVE_POSITIONS`，权重 1：条款级 source clause ID、source document ID、policy rule ID、override action、草案立场代码和目标立场代码。
- `SP007_APPROVAL_ROUTING_AND_SUMMARY`，权重 1：路由优先级、逐条款审批路由字段和审批摘要。
- `SP008_FINAL_SOURCE_PRUNED_DRAFTING_POSTURE`，权重 1：最终起草姿态、签署准备状态和起草立场枚举，且必须绑定到精确裁剪后的风险来源、控制条款 ID、override code 和未覆盖有效条款处理。

评估器接受预测文件路径作为第一个参数，默认使用 `output/answer.json`。输出 JSON 包括标准化得分、获得权重、总权重、各点评分通过情况和 mismatch。列表按稳定排序键或标量值排序，浮点数四舍五入到两位小数。

常见模型错误包括使用 5 月过期股权表、只分配总收益而不分配现金/票据/rollover 组成部分、把 note offset 当作经济中性条款、保留 3.5% 税务托管、用错误基数计算 cap、漏掉 SunWell 作为交割同意、把 Fleet Telematics 当作 consent、加入 HSR filing condition、把通用模板条款当作控制条款、把所有查阅过的 diligence 来源都列成控制风险来源、把所有有效条款都列为控制性 clause source、在有效 override code 集合中加入 `TEMPLATE_SOURCE_POSITION`、把 `BASKET` 或 `CASH_ROLLOVER` 列为覆盖条款，以及只读通用政策而未应用 Solstice 特定委员会来源导致把 NWC 路由到 finance committee。

### 迁移设计

这是一个测试任务。迁移锚点是 `train_001`、`train_002` 和 `train_005`。

从 `train_001`，求解器应迁移有效来源优先、有效股权表优先于过期导出、整数美元和两位小数百分比惯例，以及用重大合同附表而非模板假设判断 consent 和 HSR flags 的习惯。这些经验支撑 `SP001_DEAL_TERMS_AND_CLOSING_FACTS`，并帮助避免 `SP002_EXACT_CONTROLLING_RISK_SOURCE_IDS` 中的过期/模板来源错误。

从 `train_002`，求解器应迁移对方稿审阅习惯：用控制性 playbook 或客户指示比对有效草案条款，将偏差识别为结构化问题代码，避免把没有偏差的条款加入 issue/override 列表，量化经济修正，并把过渡/客户运营条款视为重要事项，而不仅关注价格条款。这些经验支撑 `SP003_EXACT_CONTROLLING_CLAUSE_SOURCE_IDS`、`SP004_EXACT_OVERRIDE_CODES_NO_TEMPLATE_SUPERSEDED`、`SP005_EXACT_NON_OVERRIDDEN_CLAUSE_HANDLING`、`SP006_OVERRIDE_SUBSTANTIVE_POSITIONS` 和 `SP008_FINAL_SOURCE_PRUNED_DRAFTING_POSTURE`。

从 `train_005`，求解器应迁移买方条款填充和政策检查方法：在没有相反组成部分分配附表时，按有效所有权附表分摊各对价组成部分；区分当前审批要求和条件性 fallback 授权；让交易特定风险备忘录覆盖通用模板；根据当前控制性来源路由审批机构；按指定基数计算托管、cap 和 basket 金额。这些经验支撑 `SP001_DEAL_TERMS_AND_CLOSING_FACTS`、`SP002_EXACT_CONTROLLING_RISK_SOURCE_IDS`、`SP006_OVERRIDE_SUBSTANTIVE_POSITIONS`、`SP007_APPROVAL_ROUTING_AND_SUMMARY` 和 `SP008_FINAL_SOURCE_PRUNED_DRAFTING_POSTURE`。

任务特定探索仍然必要，因为 Solstice 交易具有少数 rollover 结构、卖方票据抵销、3.5% 税务托管草案偏差、headline-value cap 问题、过期 NWC 基线，以及训练答案中没有出现的客户同意事实。

### 构建记录

作者：`task_group_020/test_005` task-builder subagent。

创建日期：2026-07-07。

更新日期：2026-07-07。

主要变更：为交易 `D-SOLSTICE-820` 创建求解器提示、答案模板、标准答案、精确匹配评估器和双语 notes；在直接校准得分过高后进行重构，将评分重点从宽泛分配/计算检查转向受控来源优先级、覆盖条款纪律、审批路由、来源 ID 和最终起草立场。后续返工将评估器和 `task_group.yaml` 同步为当前 10 分 rubric：通用交易经济条款合并为低权重点，路由与实质 override 检查分离，最高权重点为精确风险来源裁剪。

## Evaluation Synchronization Update

The evaluator has eight exact-match scoring points, raw total weight 10, synchronized with `task_group.yaml`:

- `SP001_DEAL_TERMS_AND_CLOSING_FACTS`, weight 1: all generic deal-term work, including allocation math, indemnity values, note/NWC treatment, consents, HSR, transition services, and IP transition.
- `SP002_EXACT_CONTROLLING_RISK_SOURCE_IDS`, weight 3: policy id/version, source precedence code, exact `controlling_risk_source_ids`, exact `source_ids`, rejected document source IDs, and superseded source IDs.
- `SP003_EXACT_CONTROLLING_CLAUSE_SOURCE_IDS`, weight 1: exact `controlling_clause_source_ids`, exact `non_overridden_active_clause_ids`, and exact `rejected_template_clause_ids`, with accepted active clauses excluded from the controlling override-clause set.
- `SP004_EXACT_OVERRIDE_CODES_NO_TEMPLATE_SUPERSEDED`, weight 1: exact `override_codes` and `overridden_clause_codes`; `TEMPLATE_SOURCE_POSITION` must not be included merely because template records were rejected.
- `SP005_EXACT_NON_OVERRIDDEN_CLAUSE_HANDLING`, weight 1: exact `non_overridden_clause_codes` and `non_overridden_clause_handling` for active clauses reviewed but accepted.
- `SP006_OVERRIDE_SUBSTANTIVE_POSITIONS`, weight 1: clause-level source clause IDs, source document IDs, policy rule IDs, override actions, draft position codes, and required position codes.
- `SP007_APPROVAL_ROUTING_AND_SUMMARY`, weight 1: routing precedence, per-clause approval routing fields, and approval summary.
- `SP008_FINAL_SOURCE_PRUNED_DRAFTING_POSTURE`, weight 1: final drafting posture, signing readiness, and drafting-position enums tied to the exact source-pruned risk sources, controlling clause IDs, override codes, and non-overridden active-clause handling.

This section is authoritative for evaluator weight documentation after the latest rework. It matches `eval/eval.py` and `task_group.yaml`.
