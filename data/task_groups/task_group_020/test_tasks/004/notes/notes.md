# test_004 Notes / 测试004说明

## English

### Data and Source Lineage

This task belongs to `task_group_020`, scenario `SCN_020_ma_transaction_contract_review_and_negotiation`, sourced from examples `E001`, `E002`, and `E003`. It implements the design brief for `test_004`: a buyer-side hybrid review/escalation task for deal `D-KEPLER-155` in the shared Aster Legal Deal Desk environment.

The task uses generated environment data in `task_group/task_group_020/env/data/dealdesk.json` and `manifest.json`. The controlling deal record is `D-KEPLER-155` with policy `P-HYBRID-INVEST-2026`. Important active documents are `DOC-KEPLER155-TERM-01`, `DOC-KEPLER155-DRAFT-02`, `DOC-KEPLER155-EMAIL-03`, `DOC-KEPLER155-CAP-ACTIVE`, `DOC-KEPLER155-FIN-04`, `DOC-KEPLER155-MATCON-05`, `DOC-KEPLER155-DISC-06`, and `DOC-KEPLER155-COMMITTEE-07`. Stale/template distractors are `DOC-KEPLER155-CAP-STALE` and `DOC-KEPLER155-TEMPLATE-99`.

### Task Definition and Expected Work

The solver-visible prompt asks for a structured buyer-side hybrid review packet for Kepler Stone using the runner-provided Deal Desk base URL. The expected output is a JSON object matching `input/payloads/answer_template.json`, with `reviewed_terms` and `committee_packet`.

The solver must distinguish current draft terms that are within the playbook or negotiated fallback authority from terms that require investment committee escalation. The key reviewed terms are escrow, tax escrow, rollover valuation, indemnity cap, governance, and non-compete. The task intentionally includes stale/template material so the solver has to follow active current deal-room sources, current client instructions, and the current playbook.

### Scenario Fit and Material Map

This task fits the scenario because it combines legal document review, client playbook comparison, committee threshold analysis, and quantified deal economics. It is a hybrid between deviation review and escalation, matching source examples where counsel must compare draft terms to playbooks, quantify economic exposure, and route terms to the correct approval body.

Material map:

- `DOC-KEPLER155-DRAFT-02`: current draft terms and current negotiation posture.
- `DOC-KEPLER155-EMAIL-03`: latest written client instruction and strategic context.
- `P-HYBRID-INVEST-2026`: controlling hybrid acquisition and minority rollover playbook.
- `DOC-KEPLER155-FIN-04`: headline value, escrow amounts, rollover value, and cap base.
- `DOC-KEPLER155-COMMITTEE-07`: committee members and escalation categories.
- `DOC-KEPLER155-DISC-06`: founder employment and non-compete scope.
- Clause records `CL-KEPLER-155-001` through `CL-KEPLER-155-006`: normalized clause comparison data.
- `BM-ROLLOVER-VALUATION-2026` and `BM-ESCROW-SAAS-ANALYTICS-2024-040`: benchmark context for rollover and escrow.
- `DOC-KEPLER155-CAP-STALE` and `DOC-KEPLER155-TEMPLATE-99`: distractors that should not override active/current materials.

### Solution and Evaluation Basis

The correct escalation-required set is `GOVERNANCE`, `INDEMNITY_CAP`, and `ROLLOVER`. Rollover has a 3.5% valuation mismatch against a 2.0% threshold; on the $40,000,000 rollover equity base, this is $1,400,000 draft exposure, $800,000 fallback amount, and $600,000 policy excess. Indemnity cap is 15.0% against a 12.5% threshold on $146,000,000 headline value; this is $21,900,000 draft exposure, $18,250,000 fallback amount, and $3,650,000 policy excess. Governance is a founder ordinary-course veto over annual budget and debt above $1,000,000, so it is a non-quantified control risk.

The correct within-playbook set is `ESCROW`, `TAX_ESCROW`, and `NONCOMPETE`. Escrow is 12.0% or $17,520,000, within the documented fallback for revenue-recognition diligence. Tax escrow is 2.0% or $2,920,000, within the 2%-3% range and below the 3% escalation threshold. Non-compete is 36 months limited to SaaS analytics with founder employment, within fallback.

The committee route is `INVESTMENT_COMMITTEE`, with members Ruth Hall, Devin Cho, and Mika Stone from `DOC-KEPLER155-COMMITTEE-07`. The committee packet has aggregate risk tier `HIGH`, final action `ESCALATE_AND_RENEGOTIATE_BEFORE_SIGNING`, primary drivers `GOVERNANCE`, `INDEMNITY_CAP`, and `ROLLOVER`, total quantified exposure $23,300,000, and total policy excess $4,250,000. The approval conditions are cap reduction to at or below 12.5%, removal of budget and ordinary-course debt vetoes, and rollover discount at or below 2% or a price reduction.

The evaluator has seven exact-match scoring points with raw weight total 11, synchronized with `task_group.yaml`:

- SP001 weight 1: escalation-required term set and term-level escalation flags.
- SP002 weight 3: within-playbook term set and non-escalation flags.
- SP003 weight 3: dollar exposure and policy excess calculations.
- SP004 weight 1: committee routing and member set.
- SP005 weight 1: negotiated fallback recommendations for reviewed terms.
- SP006 weight 1: approval conditions for committee packet.
- SP007 weight 1: aggregate risk tier, action, totals, and strategic context.

Likely model pitfalls include escalating escrow solely because it is above the preferred 10% position, missing that tax escrow is within the 2%-3% range, treating all negotiated fallbacks as committee escalations, using stale template clauses, calculating rollover exposure on the full headline value instead of the rollover equity value, or failing to separate cap draft exposure from cap policy excess.

### Transfer Design

The transfer anchors are `train_002`, `train_003`, and `train_004`.

From `train_002`, solvers can infer that playbook fallback positions are not automatically escalations, current client instructions and active drafts control over templates, and economic deviations should be normalized into controlled action enums and dollar amounts.

From `train_003`, solvers can infer committee-packet structure: term-level escalation flags, policy thresholds, committee route, committee members, benchmark context, aggregate risk tier, final action, primary driver terms, and quantified exposure/excess totals.

From `train_004`, solvers can infer how to treat negotiated transition-style or fallback positions: a term may need revision, approval, or acceptance depending on threshold and approval owner, not just because it differs from the preferred first position.

This test changes the facts and policy family. It is buyer-side, strategic, and hybrid rollover-focused rather than seller APA or public merger-focused. The transfer-dependent difficulty is the distinction between within-playbook fallback and committee escalation; task-specific exploration difficulty comes from finding Kepler’s active draft, latest email, hybrid policy, committee record, and benchmark records in the Deal Desk.

### Construction Record

Author: task-builder subagent for `task_group_020/test_004`.

Created: 2026-07-07.

Updated: 2026-07-07.

Major changes: created solver prompt, answer template, standard answer, exact-match evaluator, and bilingual notes for the Kepler Stone hybrid review/escalation task.

## 中文

### 数据和来源

本任务属于 `task_group_020`，场景为 `SCN_020_ma_transaction_contract_review_and_negotiation`，来源示例为 `E001`、`E002`、`E003`。任务实现设计文档中的 `test_004`：在共享的 Aster Legal Deal Desk 环境中，对交易 `D-KEPLER-155` 做买方混合审查和升级分析。

任务使用 `task_group/task_group_020/env/data/dealdesk.json` 和 `manifest.json` 中生成的环境数据。控制性交易记录是 `D-KEPLER-155`，适用政策为 `P-HYBRID-INVEST-2026`。重要的有效文件包括 `DOC-KEPLER155-TERM-01`、`DOC-KEPLER155-DRAFT-02`、`DOC-KEPLER155-EMAIL-03`、`DOC-KEPLER155-CAP-ACTIVE`、`DOC-KEPLER155-FIN-04`、`DOC-KEPLER155-MATCON-05`、`DOC-KEPLER155-DISC-06`、`DOC-KEPLER155-COMMITTEE-07`。干扰文件是过期的 `DOC-KEPLER155-CAP-STALE` 和模板文件 `DOC-KEPLER155-TEMPLATE-99`。

### 任务定义和预期工作

可见提示要求求解者使用运行器提供的 Deal Desk 基础 URL，为 Kepler Stone 准备结构化买方混合审查包。预期输出是符合 `input/payloads/answer_template.json` 的 JSON 对象，主要字段为 `reviewed_terms` 和 `committee_packet`。

求解者需要区分当前草案中哪些条款可以留在操作手册或谈判回退权限内，哪些条款在签署前必须提交投资委员会。关键审查条款包括一般托管、税务托管、展期估值、赔偿上限、治理权和竞业限制。任务故意保留过期和模板材料，要求求解者以有效的当前交易文件、最新客户指示和当前操作手册为准。

### 场景适配和材料地图

本任务符合场景，因为它结合了法律文件审查、客户操作手册比较、委员会阈值分析和交易经济量化。它是偏差审查和升级分析的混合任务，与源示例中律师需要比较草案和操作手册、量化经济风险并确定审批路径的工作一致。

材料地图：

- `DOC-KEPLER155-DRAFT-02`：当前草案条款和谈判姿态。
- `DOC-KEPLER155-EMAIL-03`：最新书面客户指示和战略背景。
- `P-HYBRID-INVEST-2026`：控制性的混合收购和少数展期操作手册。
- `DOC-KEPLER155-FIN-04`：交易总价值、托管金额、展期价值和上限计算基础。
- `DOC-KEPLER155-COMMITTEE-07`：委员会成员和升级类别。
- `DOC-KEPLER155-DISC-06`：创始人雇佣和竞业限制范围。
- 条款记录 `CL-KEPLER-155-001` 至 `CL-KEPLER-155-006`：标准化条款比较数据。
- `BM-ROLLOVER-VALUATION-2026` 和 `BM-ESCROW-SAAS-ANALYTICS-2024-040`：展期和托管的市场基准。
- `DOC-KEPLER155-CAP-STALE` 和 `DOC-KEPLER155-TEMPLATE-99`：不应覆盖当前有效材料的干扰项。

### 解答和评估依据

正确的必须升级条款集合是 `GOVERNANCE`、`INDEMNITY_CAP` 和 `ROLLOVER`。展期估值折价为 3.5%，阈值为 2.0%；以 40,000,000 美元展期股权为基础，草案风险为 1,400,000 美元，回退金额为 800,000 美元，超出政策部分为 600,000 美元。赔偿上限为 15.0%，阈值为 12.5%；以 146,000,000 美元总交易价值为基础，草案风险为 21,900,000 美元，回退金额为 18,250,000 美元，超出政策部分为 3,650,000 美元。治理权是创始人对年度预算和超过 1,000,000 美元债务的日常经营否决权，因此属于无法直接量化的控制风险。

正确的手册内或回退内条款集合是 `ESCROW`、`TAX_ESCROW` 和 `NONCOMPETE`。一般托管为 12.0%，即 17,520,000 美元，因收入确认尽调风险而在书面回退范围内。税务托管为 2.0%，即 2,920,000 美元，在 2%-3% 范围内且低于 3% 的升级阈值。竞业限制为 36 个月，限定于 SaaS analytics，并伴随创始人雇佣安排，属于回退范围内。

委员会路径是 `INVESTMENT_COMMITTEE`，成员为 `DOC-KEPLER155-COMMITTEE-07` 中的 Ruth Hall、Devin Cho、Mika Stone。委员会包的整体风险等级为 `HIGH`，最终行动为 `ESCALATE_AND_RENEGOTIATE_BEFORE_SIGNING`，主要驱动条款为 `GOVERNANCE`、`INDEMNITY_CAP`、`ROLLOVER`，量化风险总额为 23,300,000 美元，超出政策总额为 4,250,000 美元。审批条件是将赔偿上限降至 12.5% 或以下，删除预算和日常经营债务否决权，以及将展期折价降至 2% 或以下或降低交易价格。

评估器包含七个精确匹配评分点，原始总权重为 11，并已与 `task_group.yaml` 同步：

- SP001 权重 1：必须升级的条款集合和条款级升级标记。
- SP002 权重 3：手册内或回退内条款集合和非升级标记。
- SP003 权重 3：美元风险和政策超额计算。
- SP004 权重 1：委员会路径和成员集合。
- SP005 权重 1：被审查条款的谈判回退建议。
- SP006 权重 1：委员会包审批条件。
- SP007 权重 1：整体风险等级、行动、合计金额和战略背景。

常见错误包括：仅因一般托管高于首选的 10% 就升级；漏掉税务托管仍在 2%-3% 范围内；把所有谈判回退都当作委员会升级；使用过期模板条款；用总交易价值而不是展期股权价值计算展期风险；或者混淆赔偿上限的草案风险和政策超额。

### 迁移设计

迁移锚点是 `train_002`、`train_003` 和 `train_004`。

从 `train_002`，求解者可以迁移以下经验：操作手册中的回退位置不必然等于升级；当前客户指示和有效草案优先于模板；经济偏差应被标准化为受控行动枚举和美元金额。

从 `train_003`，求解者可以迁移委员会包结构：条款级升级标记、政策阈值、委员会路径、委员会成员、基准背景、整体风险等级、最终行动、主要驱动条款以及量化风险和超额合计。

从 `train_004`，求解者可以迁移如何处理谈判型或回退型条款：条款是否需要修订、审批或接受取决于阈值和审批主体，而不是仅仅因为它不同于首选初始位置。

本测试改变了事实和政策族。它是买方、战略性、展期股权导向的任务，而不是卖方 APA 或上市公司合并任务。迁移依赖的难点是区分手册内回退和委员会升级；任务自身探索难点来自在 Deal Desk 中找到 Kepler 的有效草案、最新邮件、混合政策、委员会记录和基准记录。

### 构建记录

作者：`task_group_020/test_004` task-builder subagent。

创建日期：2026-07-07。

更新日期：2026-07-07。

主要变更：创建 Kepler Stone 混合审查和升级任务的求解提示、答案模板、标准答案、精确匹配评估器和双语说明。

## Evaluation Synchronization Update

The evaluator has seven exact-match scoring points with raw weight total 11, synchronized with `task_group.yaml`:

- SP001 weight 1: escalation-required term set and term-level escalation flags.
- SP002 weight 3: within-playbook term set and non-escalation flags.
- SP003 weight 3: dollar exposure and policy excess calculations.
- SP004 weight 1: committee routing and member set.
- SP005 weight 1: negotiated fallback recommendations for reviewed terms.
- SP006 weight 1: approval conditions for committee packet.
- SP007 weight 1: aggregate risk tier, action, totals, and strategic context.

This section is authoritative for evaluator weight documentation after the latest rework. It matches `eval/eval.py` and `task_group.yaml`.
