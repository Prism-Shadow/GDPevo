# test_002 Notes

## English

### Data and source lineage

This task belongs to `task_group_020`, scenario `SCN_020_ma_transaction_contract_review_and_negotiation`, derived from source examples `E001`, `E002`, and `E003`. The task implements the design brief for `test_002`: seller-side APA counterparty-paper review for deal `D-QUARTZ-311` in the shared Aster Legal Deal Desk environment.

The shared generated environment data is in `task_group/task_group_020/env/data/dealdesk.json`, with manifest `task_group/task_group_020/env/data/manifest.json`. The task-local solver-visible payload is only `input/payloads/answer_template.json`; the solver must obtain deal facts from the runner-provided Deal Desk Web/API base URL.

### Task definition and scenario fit

The solver acts as seller-side counsel for Quartz Commerce Group reviewing the current buyer APA paper for the sale of Quartz Payments Processing Assets to Pinnacle BankTech LLC. The output is a structured JSON issue register plus a summary. This matches the source scenario's seller-side APA review workflow: counsel must compare active counterparty draft terms against current client instructions, the seller APA playbook, active schedules, clause comparison records, and benchmark records while ignoring stale/template distractors.

### Material map

Important environment records:

- `D-QUARTZ-311`: deal profile, economics, client positions, active document links, and negotiation context.
- `DOC-QUARTZ311-DRAFT-02`: active counterparty draft terms.
- `DOC-QUARTZ311-EMAIL-03`: latest client instructions and escalation posture.
- `DOC-QUARTZ311-FIN-04`: headline value, escrow, cap, basket, and working-capital economics.
- `DOC-QUARTZ311-DISC-06`: WARN, employee-transfer, TSA, and IP-transition schedules.
- `DOC-QUARTZ311-MATCON-05`: bank sponsor, processor, and shared-service operational dependencies.
- `P-SELLER-APA-2026`: controlling seller APA response playbook.
- `P-STANDARD-FORM-2026`: generic form library, relevant only as lower-priority context for MAE/template conflicts.
- Active clause records `CL-QUARTZ-311-001` through `CL-QUARTZ-311-009`: normalized draft-vs-playbook comparison.
- Stale/template distractors `DOC-QUARTZ311-CAP-STALE`, `DOC-QUARTZ311-TEMPLATE-99`, `CL-QUARTZ-311-S01`, and `CL-QUARTZ-311-S02` should not displace active draft records.
- Benchmarks `BM-REVERSE-TERMINATION-FEE-FINTECH-2021-053` and `BM-ESCROW-FINTECH-2026-002` support fee and escrow context, but the playbook and client instructions control the negotiating answer.

### Solution and evaluation basis

The standard answer contains six material issues and one summary. The core calculations use headline value of USD 286,000,000.

- Financing/fee: the debt financing condition is prohibited. The negotiating answer deletes it, and any fallback reverse termination fee is fallback-only, based on headline value, with parent guarantee required. The FinTech RTF median is 4.70%, so the fee amount is USD 13,442,000.
- Escrow: draft escrow is 13.00% or USD 37,180,000 for 24 months. The target is 7.50% or USD 21,450,000, with 10.00% or USD 28,600,000 as fallback and a 12-month release.
- Survival/cap/basket/de minimis: draft seller-rep survival is 24 months, cap is 20.00% or USD 57,200,000, and basket is 0.50% tipping with no de minimis. Corrected terms are 12-month general survival, 7.50% target cap or USD 21,450,000, 10.00% fallback cap or USD 28,600,000, 1.00% deductible basket or USD 2,860,000, de minimis required, tipping not allowed.
- Employee/TSA/WARN: buyer must make comparable offers, WARN/severance for transferred employees moves to buyer, and a detailed TSA exhibit is required for chargeback support, compliance reporting, KYC operations, and processor migration.
- MAE: unqualified loss of any bank sponsor cannot be accepted as an MAE trigger. It needs materiality, buyer-control exceptions, and standard market carve-outs.
- IP transition: perpetual mark use and broad source repository access are rejected. The answer requires a limited transition license, retained-IP boundaries, a 9-month trademark phaseout, and limited transition repository access.
- Ranking: financing/fee is first, followed by employee/TSA/WARN, survival/cap/basket/de minimis, escrow, IP transition, and MAE carve-outs.

The evaluator has seven exact-match scoring points, raw weight total 9, synchronized with `task_group.yaml`: financing/fee weight 1, escrow terms weight 1, survival/cap/basket/de minimis weight 1, employee/TSA/WARN weight 1, MAE carve-outs weight 3, IP transition weight 1, and issue ranking/summary weight 1. Each scoring point checks controlled fields, numeric values rounded to the declared precision, booleans, enums, and set/list normalization where appropriate. Source IDs are included for auditability but are not independent scoring points.

Likely model pitfalls include using stale template cap or survival records, treating the generic 10% template escrow as controlling, omitting the fallback-only nature of the reverse termination fee, using the seller note instead of headline value as a fee base adjustment, accepting the draft TSA placeholder, missing retained WARN exposure, and failing to separate MAE and IP transition issues.

### Transfer design

Transfer anchors are `train_002` and `train_004`.

From `train_002`, solvers can infer the seller APA review pattern: active draft and latest client instructions control over templates; seller playbook controls the deviation analysis; financing conditions are not solved by adding a fee alone; escrow, cap, basket, and de minimis values must be normalized from headline value; and issue registers should use controlled recommendations rather than prose.

From `train_004`, solvers can infer the transition-risk pattern: employee transfer, WARN/severance, TSA service continuity, and IP-transition scope are high-priority operational issues when a draft is silent, placeholder-only, or open-ended. The specific Quartz services, FinTech parties, bank sponsor trigger, and numbers remain task-specific exploration.

Transfer-dependent scoring goals are financing/fee, survival/cap/basket/de minimis, employee/TSA/WARN, IP transition, and issue ranking. Task-specific exploration is still required for the Quartz headline value, FinTech benchmark, specific TSA services, material bank sponsor dependency, active clause IDs, and current client email positions.

### Construction record

Author: task-builder subagent for `task_group_020/test_002`.
Created: 2026-07-07.
Updated: 2026-07-07.
Major changes: initial formal task construction with prompt, answer template, standard answer, evaluator, and bilingual notes.

## Chinese

### 数据和来源

本任务属于 `task_group_020`，场景为 `SCN_020_ma_transaction_contract_review_and_negotiation`，来源示例为 `E001`、`E002`、`E003`。任务实现 `test_002` 的设计要求：在共享的 Aster Legal Deal Desk 环境中，对交易 `D-QUARTZ-311` 进行卖方 APA 对方稿审阅。

共享生成数据位于 `task_group/task_group_020/env/data/dealdesk.json`，清单位于 `task_group/task_group_020/env/data/manifest.json`。本任务本地对求解器可见的 payload 只有 `input/payloads/answer_template.json`；求解器需要通过 runner 提供的 Deal Desk Web/API base URL 获取交易事实。

### 任务定义和场景契合

求解器扮演 Quartz Commerce Group 的卖方律师，审阅 Pinnacle BankTech LLC 就 Quartz Payments Processing Assets 交易提交的当前 APA 买方稿。输出为结构化 JSON 问题清单和摘要。本任务符合来源场景中的卖方 APA 审阅工作流：律师需要将当前有效对方稿与最新客户指示、卖方 APA playbook、有效附表、条款对比记录和 benchmark 记录进行比对，同时排除过期或模板干扰信息。

### 材料地图

关键环境记录包括：

- `D-QUARTZ-311`：交易概况、经济条款、客户立场、有效文件链接和谈判背景。
- `DOC-QUARTZ311-DRAFT-02`：当前有效对方稿。
- `DOC-QUARTZ311-EMAIL-03`：最新客户指示和升级口径。
- `DOC-QUARTZ311-FIN-04`：交易价值、escrow、cap、basket 和营运资金相关经济数据。
- `DOC-QUARTZ311-DISC-06`：WARN、员工转移、TSA 和 IP 过渡附表。
- `DOC-QUARTZ311-MATCON-05`：银行 sponsor、processor 和共享服务依赖。
- `P-SELLER-APA-2026`：控制性的卖方 APA response playbook。
- `P-STANDARD-FORM-2026`：通用模板库，仅作为 MAE 或模板冲突的低优先级背景。
- 有效条款记录 `CL-QUARTZ-311-001` 至 `CL-QUARTZ-311-009`：规范化的对方稿与 playbook 对比。
- 过期或模板干扰项 `DOC-QUARTZ311-CAP-STALE`、`DOC-QUARTZ311-TEMPLATE-99`、`CL-QUARTZ-311-S01`、`CL-QUARTZ-311-S02` 不应取代有效稿记录。
- `BM-REVERSE-TERMINATION-FEE-FINTECH-2021-053` 和 `BM-ESCROW-FINTECH-2026-002` 提供费用和 escrow 背景，但谈判答案仍以 playbook 和客户指示为准。

### 答案和评估依据

标准答案包含六个实质问题和一个摘要。核心计算使用 USD 286,000,000 的 headline value。

- 融资/费用：债务融资条件被禁止。谈判答案应删除该条件；任何反向终止费只能作为 fallback，基于 headline value，且需要母公司担保。FinTech RTF 中位数为 4.70%，金额为 USD 13,442,000。
- Escrow：草稿为 13.00%，即 USD 37,180,000，期限 24 个月。目标为 7.50%，即 USD 21,450,000；fallback 为 10.00%，即 USD 28,600,000，释放期为 12 个月。
- 存续期/cap/basket/de minimis：草稿中卖方陈述存续期为 24 个月，cap 为 20.00% 即 USD 57,200,000，basket 为 0.50% tipping 且没有 de minimis。修正条款为一般存续期 12 个月，目标 cap 7.50% 即 USD 21,450,000，fallback cap 10.00% 即 USD 28,600,000，1.00% deductible basket 即 USD 2,860,000，需要 de minimis，不允许 tipping。
- 员工/TSA/WARN：买方必须提供可比雇佣，转移员工的 WARN/遣散责任由买方承担，并需要详细 TSA 附件，服务包括 chargeback support、compliance reporting、KYC operations 和 processor migration。
- MAE：不能接受未加限定的“任何 bank sponsor 丧失即构成 MAE”触发。需要 materiality 限定、buyer-control 例外和标准市场 carve-outs。
- IP 过渡：拒绝永久商标使用和广泛源代码库访问。答案要求有限过渡许可、保留 IP 边界、9 个月商标 phaseout 和有限的过渡性代码库访问。
- 排序：融资/费用第一，其后为员工/TSA/WARN，存续期/cap/basket/de minimis，escrow，IP 过渡，MAE carve-outs。

评估器包含七个 exact-match 评分点，原始总权重为 9，并已与 `task_group.yaml` 同步：融资/费用权重 1，escrow 条款权重 1，存续期/cap/basket/de minimis 权重 1，员工/TSA/WARN 权重 1，MAE carve-outs 权重 3，IP 过渡权重 1，问题排序和摘要权重 1。每个评分点检查受控字段、按声明精度取整的数字、布尔值、枚举，以及必要的集合或列表规范化。source IDs 用于审计，但不是独立评分点。

常见模型错误包括使用过期模板 cap 或 survival 记录、把通用 10% 模板 escrow 当成控制性规则、忽略反向终止费只能作为 fallback、错误地用 seller note 调整 fee base、接受草稿中的 TSA placeholder、遗漏卖方保留 WARN 风险，以及混淆 MAE 与 IP 过渡问题。

### 迁移设计

迁移锚点为 `train_002` 和 `train_004`。

从 `train_002` 可迁移卖方 APA 审阅模式：有效稿和最新客户指示优先于模板；卖方 playbook 控制偏差分析；融资条件不能仅通过增加费用解决；escrow、cap、basket 和 de minimis 需要按 headline value 规范化；问题清单应使用受控 recommendation，而不是自由文本。

从 `train_004` 可迁移过渡风险模式：当草稿沉默、只有 placeholder 或开放式授权时，员工转移、WARN/遣散、TSA 服务连续性和 IP 过渡范围都是高优先级运营问题。Quartz 的具体服务、FinTech 交易方、银行 sponsor 触发和金额仍需针对本任务探索。

依赖迁移的评分目标包括融资/费用、存续期/cap/basket/de minimis、员工/TSA/WARN、IP 过渡和问题排序。任务特定探索仍需确定 Quartz 的 headline value、FinTech benchmark、具体 TSA 服务、重大 bank sponsor 依赖、有效 clause IDs 和当前客户邮件立场。

### 构造记录

作者：`task_group_020/test_002` task-builder subagent。
创建日期：2026-07-07。
更新日期：2026-07-07。
主要变更：初始构造正式任务，包括 prompt、answer template、标准答案、评估器和双语 notes。

## Evaluation Synchronization Update

The evaluator has seven exact-match scoring points, raw weight total 9, synchronized with `task_group.yaml`: financing/fee weight 1, escrow terms weight 1, survival/cap/basket/de minimis weight 1, employee/TSA/WARN weight 1, MAE carve-outs weight 3, IP transition weight 1, and issue ranking/summary weight 1. Each scoring point checks controlled fields, numeric values rounded to the declared precision, booleans, enums, and set/list normalization where appropriate. Source IDs are included for auditability but are not independent scoring points.

This section is authoritative for evaluator weight documentation after the latest rework. It matches `eval/eval.py` and `task_group.yaml`.
