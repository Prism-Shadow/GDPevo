# train_002 Notes

## English

### Data and Source Lineage

This task belongs to `task_group_020`, scenario `SCN_020_ma_transaction_contract_review_and_negotiation`, sourced from examples `E001`, `E002`, and `E003`. It implements the `train_002` assignment from `scratch/task_group_design.md`: a seller-side asset purchase agreement counterparty paper review for deal `D-BRASS-219`, codename `Brass Foundry`.

The shared environment is Aster Legal Deal Desk under `task_group/task_group_020/env/`. The task uses generated environment data from `env/data/dealdesk.json` and `env/data/manifest.json`. The core public records are the deal profile for `D-BRASS-219`, active documents `DOC-BRASS219-TERM-01`, `DOC-BRASS219-DRAFT-02`, `DOC-BRASS219-EMAIL-03`, `DOC-BRASS219-FIN-04`, `DOC-BRASS219-MATCON-05`, `DOC-BRASS219-DISC-06`, clause records `CL-BRASS-219-001` through `CL-BRASS-219-009`, policy `P-SELLER-APA-2026`, and benchmark `BM-REVERSE-TERMINATION-FEE-AEROSPACE-COMPONENTS-2026-014`. Stale/template records such as `DOC-BRASS219-TEMPLATE-99`, `CL-BRASS-219-S01`, and `CL-BRASS-219-S02` are deliberate distractors.

### Task Definition and Scenario Fit

The solver acts as seller-side transaction counsel for BrassWorks Holdings after receiving Vector Machine Group's buyer APA draft. The visible prompt asks for a compact JSON issue register using the runner-provided Aster Legal Deal Desk base URL and deal `D-BRASS-219`. The solver must compare active counterparty paper, current client instructions, playbook positions, financial schedules, disclosure schedules, clause comparison records, and relevant benchmarks. The task matches the source seller-side APA review example: it requires clause-by-clause deviation identification, economic calculations, source-precedence judgment, and normalized negotiation recommendations rather than free-form memo writing.

The output schema is in `input/payloads/answer_template.json`. It requires `deal_id`, `review_type`, `currency`, and an `issues` list. Each issue uses controlled `issue_id`, `severity`, `recommended_action`, `corrected_value`, and `source_ids` fields. Currency values are integer USD; percentages are decimal percentage points rounded to two decimals. The standard answer is `output/answer.json`.

### Material Map

- `D-BRASS-219` deal profile: headline value `$236,000,000`, seller-side APA context, client preferred and fallback positions, and operational rationale.
- `DOC-BRASS219-DRAFT-02`: active buyer draft terms, including financing condition, escrow, survival, cap/basket, employee transfer, TSA, IP, and non-compete language.
- `DOC-BRASS219-EMAIL-03`: latest client instruction email. It confirms striking the financing condition, reducing escrow to 7.5%, capping at escrow, using a 1% deductible basket, adding TSA, and adding employee offer standards.
- `DOC-BRASS219-FIN-04`: economic schedule for escrow amount, indemnity cap, basket, NWC target, and NWC collar.
- `DOC-BRASS219-MATCON-05` and `DOC-BRASS219-DISC-06`: transition services, employment, material contract, regulatory, and IP transition context.
- `P-SELLER-APA-2026`: seller APA playbook. It controls over generic template clauses and identifies escalation categories.
- `CL-BRASS-219-001` through `CL-BRASS-219-009`: active clause comparison records that expose the draft value, playbook value, policy threshold, and risk hint.
- `BM-REVERSE-TERMINATION-FEE-AEROSPACE-COMPONENTS-2026-014`: benchmark used only to quantify the fallback reverse termination fee if the financing condition cannot be deleted.

### Solution and Evaluation Basis

The evaluator uses seven exact-match scoring points with total raw weight 17:

- `SP001`, weight 3: `FINANCING_CONDITION` must be `CRITICAL`, action `DELETE`, with financing and lender diligence conditions not allowed, executive committee approval required, and replacement `CLOSING_CERTAINTY_COVENANT`.
- `SP002`, weight 2: `REVERSE_TERMINATION_FEE` must be `HIGH`, action `ADD_FALLBACK_ONLY`, fallback-only, based on headline value, parent-guaranteed, and calculated at the 2026 aerospace reverse-fee benchmark median of 7.26% of `$236,000,000`, or `$17,133,600`.
- `SP003`, weight 2: `ESCROW` must reduce the general escrow to 7.5%, `$17,700,000`; include fallback 10.0%, `$23,600,000`; release after 12 months; allocate investment benefit to seller; and reject escrow longer than survival.
- `SP004`, weight 3: `SURVIVAL_CAP_BASKET` must set seller rep survival at 12 months, cap at the 7.5% escrow amount, use a 1.0% deductible basket, require de minimis, and reject tipping.
- `SP005`, weight 2: because anti-sandbagging/undisclosed-liability terms are not present in this generated deal, the supported equivalent playbook gap is `ASSUMED_LIABILITIES_AND_NWC`: buyer assumed-liability covenant survives until fully performed, buyer cannot reset working capital after signing, NWC target is `$32,100,000`, and collar is `$1,200,000`.
- `SP006`, weight 2: `RESTRICTIVE_COVENANT` must narrow the draft to a 3-year non-compete, 4-year customer non-solicit, no worldwide scope, no affiliate-wide scope, and transferred-business-only coverage.
- `SP007`, weight 3: `EMPLOYEE_TSA_IP_TRANSITION` must add comparable offers, buyer WARN/severance liability for transferred employees, required TSA services `ERP`, `IT_HELPDESK`, `PAYROLL`, and `QUALITY_CERTIFICATIONS`, a transition IP license, retained-IP boundaries, and a 9-month trademark phase-out.

Likely model pitfalls include using the stale template 10% escrow as the preferred position, accepting the buyer financing condition if paired with a fee, using the generic 5-year worldwide non-compete, omitting the missing TSA because it is operational rather than monetary, calculating percentages from the wrong base, and treating the absence of anti-sandbagging text as a missing answer rather than selecting the supported equivalent gap.

The evaluator is `eval/eval.sh`, with helper `eval/eval.py`. It accepts a prediction path as the first argument and defaults to `output/answer.json`. It prints JSON with normalized `score`, raw score, max raw score, and per-point pass/fail results.

### Transfer Design

As a train task, this is not a tutorial. It is a formal seller-side APA review that teaches transferable habits through answer comparison: active/current client instructions outrank stale template provisions; seller playbook positions control over buyer paper; financing conditions are closing-certainty issues, not only economic terms; percentages must be calculated from the specified deal value; and transition risks can carry the same importance as escrow or cap deviations. These conventions anchor later test deviation-review tasks, especially `test_002`, and also support hybrid review/escalation tasks where fallback positions must be separated from accepted terms.

### Construction Record

Author: task-builder subagent for `task_group_020 train_002`.

Created: 2026-07-07.

Updated: 2026-07-07.

Major changes: Created solver prompt, answer template, standard answer, bilingual notes, and exact-match evaluator for deal `D-BRASS-219`.

## 中文

### 数据和来源

本任务属于 `task_group_020`，场景为 `SCN_020_ma_transaction_contract_review_and_negotiation`，来源示例包括 `E001`、`E002` 和 `E003`。任务对应 `scratch/task_group_design.md` 中的 `train_002`：针对交易 `D-BRASS-219`（代号 `Brass Foundry`）进行卖方视角的资产购买协议对方稿审阅。

共享环境是 `task_group/task_group_020/env/` 下的 Aster Legal Deal Desk。任务使用 `env/data/dealdesk.json` 和 `env/data/manifest.json` 中生成的数据。核心记录包括交易档案 `D-BRASS-219`，有效文件 `DOC-BRASS219-TERM-01`、`DOC-BRASS219-DRAFT-02`、`DOC-BRASS219-EMAIL-03`、`DOC-BRASS219-FIN-04`、`DOC-BRASS219-MATCON-05`、`DOC-BRASS219-DISC-06`，条款记录 `CL-BRASS-219-001` 至 `CL-BRASS-219-009`，政策 `P-SELLER-APA-2026`，以及反向终止费基准 `BM-REVERSE-TERMINATION-FEE-AEROSPACE-COMPONENTS-2026-014`。`DOC-BRASS219-TEMPLATE-99`、`CL-BRASS-219-S01`、`CL-BRASS-219-S02` 等陈旧或模板记录是干扰项。

### 任务定义和场景契合

求解者扮演 BrassWorks Holdings 的卖方交易律师，审阅 Vector Machine Group 提供的买方 APA 草案。可见提示要求使用运行器提供的 Aster Legal Deal Desk 基础 URL 和交易 `D-BRASS-219`，输出紧凑的 JSON 问题登记表。求解者需要比较有效对方稿、最新客户指示、卖方 APA playbook、财务附表、披露附表、条款比对记录和相关市场基准。该任务符合来源示例中的卖方 APA 审阅工作：需要识别条款偏差、计算经济影响、判断资料优先级，并给出结构化谈判建议。

输出格式由 `input/payloads/answer_template.json` 定义，要求包含 `deal_id`、`review_type`、`currency` 和 `issues`。每个问题使用受控的 `issue_id`、`severity`、`recommended_action`、`corrected_value` 和 `source_ids` 字段。金额为 USD 整数，百分比为保留两位小数的百分点。标准答案位于 `output/answer.json`。

### 材料地图

- `D-BRASS-219` 交易档案：提供 `$236,000,000` 的 headline value、卖方 APA 背景、客户优先和备用立场，以及运营层面的交易理由。
- `DOC-BRASS219-DRAFT-02`：有效买方草案，包含融资条件、托管、存续期、赔偿上限和 basket、员工转移、TSA、知识产权和竞业限制。
- `DOC-BRASS219-EMAIL-03`：最新客户指示，确认删除融资条件、托管降至 7.5%、上限等于托管、1% deductible basket、增加 TSA 和员工 offer 标准。
- `DOC-BRASS219-FIN-04`：提供托管金额、赔偿上限、basket、营运资本目标和 collar。
- `DOC-BRASS219-MATCON-05` 与 `DOC-BRASS219-DISC-06`：提供过渡服务、员工、重大合同、监管和 IP 过渡背景。
- `P-SELLER-APA-2026`：卖方 APA playbook，优先于通用模板条款，并给出升级类别。
- `CL-BRASS-219-001` 至 `CL-BRASS-219-009`：有效条款比对记录，显示草案值、playbook 值、政策阈值和风险提示。
- `BM-REVERSE-TERMINATION-FEE-AEROSPACE-COMPONENTS-2026-014`：仅用于在融资条件无法删除时量化备用反向终止费。

### 答案和评估依据

评估器使用 7 个精确匹配评分点，原始总分为 17：

- `SP001`，权重 3：`FINANCING_CONDITION` 必须为 `CRITICAL`，动作为 `DELETE`，融资条件和贷款人尽调条件均不允许，需要执行委员会批准，并以 `CLOSING_CERTAINTY_COVENANT` 替代。
- `SP002`，权重 2：`REVERSE_TERMINATION_FEE` 必须为 `HIGH`，动作为 `ADD_FALLBACK_ONLY`，仅作为备用，基于 headline value，需要母公司担保，并按 2026 年航空零部件反向终止费中位数 7.26% 乘以 `$236,000,000`，即 `$17,133,600`。
- `SP003`，权重 2：`ESCROW` 必须将一般托管降至 7.5%、即 `$17,700,000`；备用为 10.0%、即 `$23,600,000`；12 个月释放；投资收益归卖方；不允许托管期长于存续期。
- `SP004`，权重 3：`SURVIVAL_CAP_BASKET` 必须将卖方陈述保证存续期设为 12 个月，赔偿上限等于 7.5% 托管金额，使用 1.0% deductible basket，要求 de minimis，并拒绝 tipping。
- `SP005`，权重 2：本生成交易中没有反 sandbagging 或未披露负债条款，因此使用有数据支持的等价 playbook 缺口 `ASSUMED_LIABILITIES_AND_NWC`：买方承担负债承诺应持续至完全履行，买方不得在签约后重设营运资本目标，NWC target 为 `$32,100,000`，collar 为 `$1,200,000`。
- `SP006`，权重 2：`RESTRICTIVE_COVENANT` 必须缩窄为 3 年竞业限制、4 年客户不招揽、不得 worldwide、不得 affiliate-wide，范围仅限转让业务。
- `SP007`，权重 3：`EMPLOYEE_TSA_IP_TRANSITION` 必须增加可比雇佣 offer、由买方承担转移员工的 WARN 和 severance 责任、要求 TSA 服务 `ERP`、`IT_HELPDESK`、`PAYROLL`、`QUALITY_CERTIFICATIONS`，并加入过渡 IP 许可、保留 IP 边界和 9 个月商标退出期。

常见错误包括把陈旧模板中的 10% 托管当作优先立场、认为有反向终止费即可接受融资条件、沿用通用 5 年 worldwide 竞业限制、因为 TSA 是运营事项而漏掉、用错误的金额基础计算百分比，以及在没有反 sandbagging 文本时没有选择有数据支持的等价缺口。

评估入口为 `eval/eval.sh`，辅助脚本为 `eval/eval.py`。它接受预测文件路径作为第一个参数，默认使用 `output/answer.json`，并输出包含标准化分数、原始分数、最高原始分数和逐项通过情况的 JSON。

### 迁移设计

作为训练任务，本任务不是教程，而是一个正式的卖方 APA 审阅任务。通过比较预测和标准答案，模型可以学习可迁移经验：有效且最新的客户指示优先于陈旧模板；卖方 playbook 优先于买方草案；融资条件是 closing certainty 问题，不只是经济问题；百分比必须按指定交易价值计算；过渡服务、员工和 IP 风险可能与托管或赔偿上限同样重要。这些经验会支撑之后的测试任务，尤其是 `test_002`，也会帮助混合审阅和升级类任务区分备用立场与可接受条款。

### 构造记录

作者：`task_group_020 train_002` 的 task-builder subagent。

创建日期：2026-07-07。

更新日期：2026-07-07。

主要变更：为交易 `D-BRASS-219` 创建了可见提示、答案模板、标准答案、双语 notes 和精确匹配评估器。
