# train_001 Notes - Alder Ridge Buyer SPA Term Population

## English

### Data and Source Lineage

This task belongs to `task_group_020`, scenario `SCN_020_ma_transaction_contract_review_and_negotiation`, derived from source examples `E001`, `E002`, and `E003`. The direct task pattern is closest to `E001`: populate buyer-side stock purchase terms by reconciling a deal profile, draft agreement, cap table, financial schedule, consent matrix, regulatory status, and client instructions.

The shared environment is `Aster Legal Deal Desk`, implemented under `task_group/task_group_020/env/`. The generated data source is `env/data/dealdesk.json`, with public metadata in `env/data/manifest.json`. This task uses deal `D-ALDER-447` and policy `P-BUYER-MIDMARKET-2026`. The only task-local solver-visible payload is `input/payloads/answer_template.json`.

### Task Definition

The solver is asked, in `input/prompt.txt`, to use the Aster Legal Deal Desk Web/API base URL supplied by the runner, review deal `D-ALDER-447`, and return a JSON object matching the answer template. The expected business result is the buyer-side SPA term population package for Alder Ridge, divided into:

- `deal_terms`: structure, consideration, active cap table source, escrow, basket, indemnity cap, and NWC mechanics.
- `seller_allocations`: seller names, roles, active ownership percentages, and gross proceeds.
- `closing_flags`: material consents, HSR conclusion, employment agreements, non-compete limits, transition service status, and IP assignment confirmation.

The prompt intentionally does not provide an SOP checklist or scored values. Solvers must use the public deal-room records and avoid stale documents and generic template provisions.

### Scenario Fit

This task fits the M&A legal operations scenario because it requires transaction counsel behavior rather than a single lookup. The solver must coordinate multiple deal-room surfaces, distinguish active schedules from stale exports, compute financial terms, and turn legal/business records into a normalized drafting package. It exercises the recurring task-group convention that active deal-room documents and latest written client instructions control over stale cap tables and template language.

### Material Map

- `GET /api/deals/D-ALDER-447` and `/deals/D-ALDER-447`: deal profile, economics, party names, signing and closing dates, active/stale document links, structured schedules, and client positions.
- `DOC-ALDER447-TERM-01`: signed commercial term sheet with headline value, equity value, timing, and economics JSON.
- `DOC-ALDER447-DRAFT-02`: active draft terms for escrow, NWC, consents, HSR, and non-compete.
- `DOC-ALDER447-EMAIL-03`: latest client instruction email, including current economics, required consents, no-HSR posture, fallback authority, and escalation notes.
- `DOC-ALDER447-CAP-ACTIVE`: active June 30, 2026 ownership and cap table schedule used for seller allocations.
- `DOC-ALDER447-CAP-STALE`: stale March 31, 2026 cap table retained as a distractor.
- `DOC-ALDER447-FIN-04`: working capital, escrow, basket, cap, and consideration schedule.
- `DOC-ALDER447-MATCON-05`: material contract consent matrix and regulatory status.
- `DOC-ALDER447-DISC-06`: employment, restrictive covenant, transition services, and IP transition schedules.
- `DOC-ALDER447-TEMPLATE-99`: generic template provisions retained as distractors.
- `P-BUYER-MIDMARKET-2026`: Northstar buyer risk memo and SPA playbook for policy context.
- `/api/clauses?deal_id=D-ALDER-447`: active clause records and stale template distractors for clause-level verification.

### Solution and Evaluation Basis

The standard answer in `output/answer.json` is based on the active deal profile and active documents. Headline purchase price and equity value are both USD 184,000,000. The consideration mix is USD 172,500,000 cash at close and USD 11,500,000 rollover equity, with no seller note or earnout. Because the active cap table expresses ownership as percentages and no share count is generated, `per_share_price_usd` is null with basis `NO_SHARE_COUNT_IN_ACTIVE_CAP_TABLE`. The answer also reports `price_per_as_converted_percent_point_usd`: USD 1,840,000 per 1.00 ownership percentage point.

The active cap table is `DOC-ALDER447-CAP-ACTIVE`, as of 2026-06-30. Seller gross proceeds from that active schedule are:

- Alder ESOP Rollover Pool: 23.7 percent, USD 43,608,000.
- Alder Founder Trust: 44.2 percent, USD 81,328,000.
- Gannet Ventures II, L.P.: 32.1 percent, USD 59,064,000.

Escrows are 10.0 percent general escrow, USD 18,400,000, and 2.5 percent tax escrow, USD 4,600,000. Both are within policy for this task because the deal-specific escalation note is triggered only if the general escrow exceeds 10.0 percent or the tax escrow exceeds 3.0 percent. NWC uses a USD 18,600,000 target, USD 750,000 collar, and dollar-for-dollar adjustment outside the collar. The collar is 0.41 percent of equity value after rounding to two decimal places.

The two required material consents are ForgeWorks SaaS MSA and Municipal Fleet Data License, both closing conditions. Northline Hosting Order is not included in `required_material_consents` because the source matrix marks consent_required as false. HSR is not required because the antitrust memo says the size-of-person test is not met; the draft should have no HSR closing condition and only a cooperation covenant. Founder employment agreements are required for Mina Calder and Owen Petrie for two years. The acceptable non-compete is 36 months only if limited to target products and current territories, with no broad affiliate covenant.

The evaluator has seven exact-match scoring points, raw weight total 15:

- `SP1_PURCHASE_PRICE_CAP_TABLE`, weight 3: purchase price, consideration mix, active cap table source, active date, per-share availability, and per ownership-point value.
- `SP2_SELLER_ALLOCATIONS`, weight 3: active seller allocation set.
- `SP3_ESCROW_TAX_ESCROW`, weight 2: general escrow and tax escrow amounts, percentages, and policy status.
- `SP4_NWC_MECHANICS`, weight 2: NWC target, collar, adjustment mechanic, and collar percentage.
- `SP5_CONSENT_CONDITIONS`, weight 2: material consents as closing conditions.
- `SP6_HSR_EXCLUSION`, weight 1: no-HSR conclusion and empty other regulatory approvals list.
- `SP7_EMPLOYMENT_NONCOMPETE`, weight 2: founder employment and narrowed non-compete terms.

The evaluator accepts a prediction path as its first argument and defaults to `output/answer.json`. It prints JSON with normalized score, earned weight, total weight, and point-level pass/fail results. Lists are normalized by stable sort keys, and numeric values are compared at the precision declared in the answer template.

Likely model pitfalls include using the stale March cap table, treating the generic template non-compete as controlling, including Northline Hosting Order as a required consent, adding an HSR closing condition despite the counsel memo, or treating exactly 10.0 percent general escrow as an escalation.

### Transfer Design

As a train task, `train_001` is a real formal task rather than a tutorial. By attempting it and comparing against the answer, a solver can infer several reusable conventions for later task-group work:

- Active deal-room schedules control over stale cap table exports and generic template provisions.
- Latest client instructions can narrow or qualify generic playbook positions.
- Structured output should use controlled enums, integer dollar amounts, two-decimal percentages, and sorted lists.
- Buyer-side term population requires cross-checking economics, cap table, consents, HSR status, employment terms, and restrictive covenants across multiple environment surfaces.
- Consent and regulatory flags should be based on deal-specific records, not boilerplate drafting assumptions.

These conventions are intended to transfer to `test_001` and `test_005` most directly, and also support the review/escalation tasks where stale records, template clauses, and policy thresholds are distractors.

### Construction Record

Author: task-builder subagent for `task_group_020/train_001`.

Created: 2026-07-07.

Updated: 2026-07-07.

Major changes: created prompt, answer template, standard answer, evaluator, and bilingual notes for deal `D-ALDER-447`.

## 中文

### 数据和来源

本任务属于 `task_group_020`，场景为 `SCN_020_ma_transaction_contract_review_and_negotiation`，来源示例为 `E001`、`E002` 和 `E003`。本任务最接近 `E001`：通过核对交易档案、起草协议、股权表、财务附表、同意矩阵、监管状态和客户指示，填充买方股票购买协议条款。

共享环境是 `Aster Legal Deal Desk`，实现位置在 `task_group/task_group_020/env/`。生成数据来源为 `env/data/dealdesk.json`，公开元数据在 `env/data/manifest.json`。本任务使用交易 `D-ALDER-447` 和政策 `P-BUYER-MIDMARKET-2026`。任务本地唯一对求解器可见的 payload 是 `input/payloads/answer_template.json`。

### 任务定义

求解器在 `input/prompt.txt` 中被要求使用运行器提供的 Aster Legal Deal Desk Web/API base URL，查看交易 `D-ALDER-447`，并返回符合 answer template 的 JSON。期望业务结果是 Alder Ridge 买方 SPA 条款填充包，分为：

- `deal_terms`：交易结构、对价、有效股权表来源、托管、basket、赔偿上限和营运资本机制。
- `seller_allocations`：卖方名称、角色、有效持股比例和总收益。
- `closing_flags`：重大合同同意、HSR 结论、雇佣协议、竞业限制、过渡服务和 IP 转让确认。

提示词刻意不提供 SOP 清单或得分答案。求解器必须使用公开交易室记录，并避开过期文件和通用模板条款。

### 场景匹配

本任务符合并购法律运营场景，因为它要求交易律师式工作，而不是单点查询。求解器需要协调多个交易室入口，区分有效附表和过期导出，计算财务条款，并把法律和业务记录转为规范化起草输入。它训练任务组中的重复规则：有效交易室文件和最新书面客户指示优先于过期股权表和模板语言。

### 材料地图

- `GET /api/deals/D-ALDER-447` 和 `/deals/D-ALDER-447`：交易档案、经济条款、主体名称、签约和交割日期、有效及过期文件链接、结构化附表和客户立场。
- `DOC-ALDER447-TERM-01`：已签署商业条款书，包含 headline value、equity value、时间安排和经济条款 JSON。
- `DOC-ALDER447-DRAFT-02`：有效起草条款，包括托管、营运资本、同意、HSR 和竞业限制。
- `DOC-ALDER447-EMAIL-03`：最新客户指示邮件，包括当前经济条款、所需同意、无 HSR 立场、fallback 权限和升级说明。
- `DOC-ALDER447-CAP-ACTIVE`：2026-06-30 有效所有权和股权表，用于卖方分配。
- `DOC-ALDER447-CAP-STALE`：2026-03-31 过期股权表，是干扰材料。
- `DOC-ALDER447-FIN-04`：营运资本、托管、basket、cap 和对价附表。
- `DOC-ALDER447-MATCON-05`：重大合同同意矩阵和监管状态。
- `DOC-ALDER447-DISC-06`：雇佣、限制性契约、过渡服务和 IP 过渡附表。
- `DOC-ALDER447-TEMPLATE-99`：通用模板条款，是干扰材料。
- `P-BUYER-MIDMARKET-2026`：Northstar 买方风险备忘录和 SPA playbook。
- `/api/clauses?deal_id=D-ALDER-447`：有效条款记录和过期模板干扰项。

### 答案和评估依据

标准答案 `output/answer.json` 基于有效交易档案和有效文件。Headline purchase price 和 equity value 都是 184,000,000 美元。对价组合为 closing cash 172,500,000 美元、rollover equity 11,500,000 美元，没有 seller note 或 earnout。由于有效股权表以百分比表达所有权，且没有生成具体股份数，`per_share_price_usd` 为 null，basis 为 `NO_SHARE_COUNT_IN_ACTIVE_CAP_TABLE`。答案同时填写 `price_per_as_converted_percent_point_usd`，即每 1.00 个所有权百分点 1,840,000 美元。

有效股权表是 `DOC-ALDER447-CAP-ACTIVE`，日期为 2026-06-30。有效附表中的卖方总收益为：

- Alder ESOP Rollover Pool：23.7%，43,608,000 美元。
- Alder Founder Trust：44.2%，81,328,000 美元。
- Gannet Ventures II, L.P.：32.1%，59,064,000 美元。

一般托管为 10.0%，18,400,000 美元；税务托管为 2.5%，4,600,000 美元。二者在本任务中均为政策内，因为交易特定升级说明只在一般托管超过 10.0% 或税务托管超过 3.0% 时触发。营运资本目标为 18,600,000 美元，collar 为 750,000 美元，collar 外逐美元调整。collar 占 equity value 的比例四舍五入为 0.41%。

两个必需的重大合同同意是 ForgeWorks SaaS MSA 和 Municipal Fleet Data License，均为交割条件。Northline Hosting Order 不列入 `required_material_consents`，因为来源矩阵标记为不需要同意。HSR 不需要申报，因为反垄断备忘录说明 size-of-person test 未满足；草案应没有 HSR 交割条件，只保留合作义务。Mina Calder 和 Owen Petrie 需要两年雇佣协议。可接受的竞业限制是 36 个月，但必须限于目标产品和当前地域，且不能有宽泛关联方限制。

评估器有七个 exact-match 评分点，原始总权重 15：

- `SP1_PURCHASE_PRICE_CAP_TABLE`，权重 3：购买价格、对价组合、有效股权表来源、有效日期、每股价格可用性和每所有权百分点价值。
- `SP2_SELLER_ALLOCATIONS`，权重 3：有效卖方分配集合。
- `SP3_ESCROW_TAX_ESCROW`，权重 2：一般托管和税务托管的金额、比例和政策状态。
- `SP4_NWC_MECHANICS`，权重 2：营运资本目标、collar、调整机制和 collar 比例。
- `SP5_CONSENT_CONDITIONS`，权重 2：重大同意作为交割条件。
- `SP6_HSR_EXCLUSION`，权重 1：无 HSR 结论和空的其他监管批准列表。
- `SP7_EMPLOYMENT_NONCOMPETE`，权重 2：创始人雇佣和缩窄后的竞业限制条款。

评估器接受预测文件路径作为第一个参数，默认使用 `output/answer.json`。输出 JSON 包括标准化得分、获得权重、总权重和各评分点通过情况。列表按稳定键排序，数字按 answer template 声明的精度比较。

常见模型错误包括使用 3 月过期股权表、把通用模板竞业限制当作控制条款、把 Northline Hosting Order 列为必需同意、尽管律师备忘录已有结论仍加入 HSR 交割条件，或把正好 10.0% 的一般托管误判为需要升级。

### 迁移设计

作为训练任务，`train_001` 是真实正式任务，不是教程。求解器尝试本任务并对照答案后，可以归纳出若干可迁移规则：

- 有效交易室附表优先于过期股权表导出和通用模板条款。
- 最新客户指示可以缩窄或限定通用 playbook 立场。
- 结构化输出应使用受控枚举、整数美元金额、两位小数百分比和排序列表。
- 买方条款填充需要跨多个环境入口核对经济条款、股权表、同意、HSR 状态、雇佣条款和限制性契约。
- 同意和监管 flags 应以交易特定记录为依据，而不是以样板起草假设为依据。

这些规则主要迁移到 `test_001` 和 `test_005`，也支持其他审查和升级任务，因为那些任务同样包含过期记录、模板条款和政策阈值干扰项。

### 构造记录

作者：`task_group_020/train_001` task-builder subagent。

创建日期：2026-07-07。

更新日期：2026-07-07。

主要变更：为交易 `D-ALDER-447` 创建 prompt、answer template、标准答案、评估器和双语 notes。
