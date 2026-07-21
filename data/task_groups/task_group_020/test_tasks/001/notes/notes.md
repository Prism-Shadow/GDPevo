# test_001 Notes: Project Keystone Seller APA Review

## English

### Data and Source Lineage

This task belongs to `SCN_020_ma_transaction_contract_review_and_negotiation` and follows the task-group design for `test_001`: seller-side counsel reviews buyer APA paper for `PRJ_KEYSTONE`. The source-example lineage is `E002` for counterparty-paper deviation review, with transfer support from `E001` for multi-record closing/economics extraction and `E003` for structured issue escalation. The task uses generated environment data from `task_group/task_group_020/env/`, especially `deals`, `draft_terms`, `playbook_rules`, `benchmarks`, `risk_estimates`, `consents`, `employees`, `material_contracts`, `regulatory`, `diligence_findings`, `deal_notes`, and `documents`.

Task-local payloads are limited to `input/payloads/answer_template.json`. The environment database, source generator, manifests, and setup files are not copied into the task payload.

### Task Definition

The visible prompt asks the solver to act as seller-side counsel for Keystone Instruments LLC in Project Keystone, an asset purchase agreement for Keystone Flow Controls. The solver must use `<TASK_ENV_BASE_URL>` to retrieve the Keystone deal record, current buyer draft terms, the `PB_SELLER_A` seller playbook, and supporting risk, consent, employee, contract, regulatory, diligence, note, and benchmark records.

The expected output is a normalized JSON answer with `issue_register`, `priority_order`, and `summary_metrics`. The issue register uses controlled IDs, status enums, risk ratings, recommended actions, percent-point fields, integer-dollar fields, boolean flags, and business-outcome labels. Important objects are `PRJ_KEYSTONE`, `PB_SELLER_A`, draft terms `TERM_PRJ_KEYSTONE_01` through `TERM_PRJ_KEYSTONE_04`, risk records `RSK_PRJ_KEYSTONE_01` through `RSK_PRJ_KEYSTONE_03`, employee records `EMP_PRJ_KEYSTONE_01` through `EMP_PRJ_KEYSTONE_03`, and closing-required consents `CNS_PRJ_KEYSTONE_01` and `CNS_PRJ_KEYSTONE_03`.

### Scenario Fit

The task represents real M&A counsel workflow: counsel must reconcile counterparty paper against a client playbook, combine legal terms with deal economics and diligence facts, quantify negotiation gaps, and produce a prioritized response for business stakeholders. It tests coordination across draft terms, legal policy, economics, operations, employment, consents, and regulatory facts in a read-only deal workbench rather than simple document summarization.

### Material Map

`/api/deals/PRJ_KEYSTONE` supplies headline value of 248,000,000 dollars, upfront cash of 228,000,000 dollars, milestone value of 20,000,000 dollars, seller-side role, and the `PB_SELLER_A` playbook. `/api/deals/PRJ_KEYSTONE/terms` supplies four current buyer draft terms: financing condition, reverse break fee, indemnity cap, and escrow. `/api/playbooks/PB_SELLER_A/rules` supplies seller limits for financing, indemnity cap, escrow, survival, and transition services. `/api/deals/PRJ_KEYSTONE/benchmarks` provides market context for termination economics and indemnity. `/api/deals/PRJ_KEYSTONE/risk-estimates` supports closing certainty, indemnity leakage, and transition disruption risk. `/api/deals/PRJ_KEYSTONE/employees` supplies headcount, service-credit requirements, and accrued PTO liabilities. `/api/deals/PRJ_KEYSTONE/consents` and `/api/deals/PRJ_KEYSTONE/material-contracts` support closing-certainty and operational-risk context. `/api/deals/PRJ_KEYSTONE/regulatory` supplies HSR-only status and indicates that HHW should not be required.

### Solution and Evaluation Basis

The standard answer has seven issues: `financing_condition`, `reverse_break_fee_hhw`, `escrow`, `indemnity_cap_basket`, `employee_tsa`, `milestone_non_compete`, and `tax_law`.

Key calculations use 248,000,000 dollars as the purchase-price or enterprise-value base. The 2.0 percent draft reverse break fee equals 4,960,000 dollars; the 6.0 percent required fallback equals 14,880,000 dollars; the shortfall is 9,920,000 dollars. The 12.0 percent draft escrow equals 29,760,000 dollars; the 10.0 percent fallback equals 24,800,000 dollars; excess over fallback is 4,960,000 dollars, and the release should move from 18 months to 12 months. The 16.0 percent draft indemnity cap equals 39,680,000 dollars; the 12.5 percent fallback equals 31,000,000 dollars; excess over fallback is 8,680,000 dollars. Employee headcount is 174, and PTO liability is 3,520,000 dollars. Closing-required consent amount at risk is 14,490,000 dollars. Total quantified draft delta is 23,560,000 dollars, which combines the reverse break fee shortfall, escrow excess over fallback, and indemnity-cap excess over fallback.

The evaluator has eight all-or-nothing scoring points with raw weights: issue set (2), financing/RBF/HHW treatment (3), escrow math (2), indemnity/basket treatment (2), milestone/non-compete treatment (1), employee/TSA treatment (2), tax/law fixes (1), and priority/summary metrics (2). These points cover distinct business outcomes: closing certainty, economic exposure, indemnity recourse, employee continuity and transition operations, milestone value, tax allocation, and dispute control. The checks are deterministic and compare normalized enums, stable issue IDs, booleans, exact integer-dollar amounts, exact month counts, and exact priority ordering. No point gives fractional credit internally.

Likely solver pitfalls include using upfront cash instead of headline value as the percentage base, treating the reverse break fee benchmark median as the controlling playbook requirement, missing draft silence as an issue for milestone/TSA/tax-law protections, overlooking service-credit and PTO data, counting all consents instead of only closing-required consent amounts at risk, or adding distractor issues such as stale survival or generic material-contract issues.

### Transfer Design

This is a test task anchored by `train_001` and `train_004`, with some support from `train_005`. The solver should transfer seller-side APA review habits from `train_001`: buyer financing conditions are not acceptable for the seller, the RBF is a mitigation only if it meets the seller playbook, and percentage math uses the headline/purchase-price base unless a rule says otherwise. From `train_004`, the solver should transfer carveout-transition judgment: missing or buyer-favorable transition-service and employee-transfer mechanics can be operational issues even when not listed as draft terms. From `train_005`, the solver should transfer controlled-output discipline and cap/fallback math.

The transfer-dependent difficulty is in recognizing missing required protections, combining financing condition and RBF/HHW treatment, and applying seller playbook fallback values correctly. The task-specific exploration difficulty is finding Keystone-specific values across the deal, terms, employees, risk estimates, consents, and regulatory records.

### Construction Record

Author: task-builder-test-001. Created: 2026-07-18. Updated: 2026-07-18. Major changes: created `prompt.txt`, `answer_template.json`, `answer.json`, `eval.sh`, `evaluate.py`, and bilingual notes for `test_001`.

## 中文

### 数据与来源

本任务属于 `SCN_020_ma_transaction_contract_review_and_negotiation`，对应任务组设计中的 `test_001`：卖方律师审查 `PRJ_KEYSTONE` 的买方 APA 文稿。来源示例主要是 `E002` 的交易文件偏差审查，同时借鉴 `E001` 的多记录经济与交割信息抽取，以及 `E003` 的结构化升级判断。任务使用 `task_group/task_group_020/env/` 中生成的环境数据，重点表包括 `deals`、`draft_terms`、`playbook_rules`、`benchmarks`、`risk_estimates`、`consents`、`employees`、`material_contracts`、`regulatory`、`diligence_findings`、`deal_notes` 和 `documents`。

任务本地 payload 仅包含 `input/payloads/answer_template.json`。环境数据库、生成脚本、manifest 和部署文件没有复制到任务 payload 中。

### 任务定义

可见提示要求解题者作为 Keystone Instruments LLC 的卖方律师，为 Project Keystone 的资产购买协议准备问题清单。解题者需要通过 `<TASK_ENV_BASE_URL>` 获取 Keystone 的交易记录、当前买方草案条款、`PB_SELLER_A` 卖方 playbook，以及风险、同意、员工、合同、监管、尽调、备注和文件记录。

期望输出是规范化 JSON，包括 `issue_register`、`priority_order` 和 `summary_metrics`。问题清单使用受控的 issue ID、状态枚举、风险评级、建议动作、百分点字段、整数美元字段、布尔字段和业务结果标签。关键对象包括 `PRJ_KEYSTONE`、`PB_SELLER_A`、草案条款 `TERM_PRJ_KEYSTONE_01` 到 `TERM_PRJ_KEYSTONE_04`、风险记录 `RSK_PRJ_KEYSTONE_01` 到 `RSK_PRJ_KEYSTONE_03`、员工记录 `EMP_PRJ_KEYSTONE_01` 到 `EMP_PRJ_KEYSTONE_03`，以及交割所需同意 `CNS_PRJ_KEYSTONE_01` 和 `CNS_PRJ_KEYSTONE_03`。

### 场景匹配

该任务模拟真实并购律师工作：律师需要把交易对方文稿与客户 playbook 对照，结合法律条款、交易经济、尽调事实和运营信息，量化谈判差距，并向业务团队给出优先级排序。它测试的是只读交易工作台中的跨表取证、规则适用、计算和商业判断，而不是简单摘要。

### 材料地图

`/api/deals/PRJ_KEYSTONE` 提供 248,000,000 美元 headline value、228,000,000 美元 upfront cash、20,000,000 美元 milestone value、卖方角色和 `PB_SELLER_A`。`/api/deals/PRJ_KEYSTONE/terms` 提供四条当前买方草案条款：融资条件、反向分手费、赔偿上限和 escrow。`/api/playbooks/PB_SELLER_A/rules` 提供卖方在融资、赔偿上限、escrow、陈述存续和过渡服务上的限制。`/api/deals/PRJ_KEYSTONE/benchmarks` 提供终止经济和赔偿的市场背景。`/api/deals/PRJ_KEYSTONE/risk-estimates` 支持交割确定性、赔偿泄漏和过渡中断风险。`/api/deals/PRJ_KEYSTONE/employees` 提供员工人数、服务年限承认要求和 PTO 负债。`/api/deals/PRJ_KEYSTONE/consents` 与 `/api/deals/PRJ_KEYSTONE/material-contracts` 支持交割确定性和运营风险判断。`/api/deals/PRJ_KEYSTONE/regulatory` 提供 HSR-only 状态，并说明不应要求 HHW。

### 标准答案与评估依据

标准答案包含七个问题：`financing_condition`、`reverse_break_fee_hhw`、`escrow`、`indemnity_cap_basket`、`employee_tsa`、`milestone_non_compete` 和 `tax_law`。

关键计算使用 248,000,000 美元作为 purchase price 或 enterprise value 基数。2.0% 草案反向分手费为 4,960,000 美元；6.0% 规定 fallback 为 14,880,000 美元；缺口为 9,920,000 美元。12.0% 草案 escrow 为 29,760,000 美元；10.0% fallback 为 24,800,000 美元；超过 fallback 4,960,000 美元，释放期应从 18 个月缩短为 12 个月。16.0% 草案赔偿上限为 39,680,000 美元；12.5% fallback 为 31,000,000 美元；超过 fallback 8,680,000 美元。员工总数为 174，PTO 负债为 3,520,000 美元。交割所需同意的风险金额为 14,490,000 美元。量化草案差距合计为 23,560,000 美元，包含反向分手费缺口、escrow 超额和赔偿上限超额。

评估器有八个全有或全无评分点，原始权重分别为：问题集合 2，融资/RBF/HHW 处理 3，escrow 计算 2，赔偿和 basket 处理 2，milestone 和 non-compete 处理 1，员工和 TSA 处理 2，税务和法律管辖修正 1，优先级和汇总指标 2。这些评分点覆盖不同业务结果：交割确定性、经济风险、赔偿追索、员工连续性和过渡运营、milestone 价值、税务分配和争议控制。检查完全确定，比较规范化枚举、稳定 issue ID、布尔值、整数美元金额、月份和优先级顺序；单个评分点内部没有部分得分。

常见错误包括使用 upfront cash 而不是 headline value 作为百分比基数，把 RBF 市场 benchmark 中位数当作控制性 playbook 要求，忽略草案沉默导致的 milestone/TSA/tax-law 缺失保护，没有合并服务年限和 PTO 数据，把所有同意金额而不是交割所需同意金额纳入汇总，或加入陈述存续、一般重大合同等干扰项。

### 迁移设计

这是测试任务，主要锚定 `train_001` 和 `train_004`，并部分借鉴 `train_005`。解题者应从 `train_001` 迁移卖方 APA 审查习惯：卖方不接受买方融资条件，RBF 只有达到卖方 playbook 要求时才是有效缓释，百分比计算默认使用 headline/purchase-price 基数。从 `train_004` 迁移 carveout 过渡判断：即便 draft term 表中没有明列，缺失或偏向买方的过渡服务和员工转移机制也可能构成运营问题。从 `train_005` 迁移受控输出格式和 cap/fallback 计算方法。

迁移依赖的难点在于识别缺失的必要保护、合并融资条件与 RBF/HHW 处理，并正确应用卖方 playbook fallback。任务本地探索的难点在于从 Keystone 的交易、条款、员工、风险估计、同意和监管记录中找到具体数值。

### 构建记录

作者：task-builder-test-001。创建日期：2026-07-18。更新日期：2026-07-18。主要变更：为 `test_001` 创建了 `prompt.txt`、`answer_template.json`、`answer.json`、`eval.sh`、`evaluate.py` 和双语 notes。
