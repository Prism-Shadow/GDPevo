# train_003 Notes / 训练任务 003 说明

## English

### Data and source lineage

This task belongs to `task_group_020`, derived from `SCN_020_ma_transaction_contract_review_and_negotiation` and source examples `E001`, `E002`, and `E003`. It implements the escalation family from the group design: a buyer-side public merger committee packet for deal `D-CYPRESS-735` in the shared Aster Legal Deal Desk environment.

The task uses generated shared environment data in `task_group/task_group_020/env/data/dealdesk.json` and `manifest.json`. Key environment records are deal `D-CYPRESS-735`, policy `P-PUBLIC-MERGER-COMMITTEE-2026`, active documents `DOC-CYPRESS735-DRAFT-02`, `DOC-CYPRESS735-EMAIL-03`, `DOC-CYPRESS735-COMMITTEE-07`, and active clause records `CL-CYPRESS-735-001` through `CL-CYPRESS-735-004`. The task-local visible payload is `input/payloads/answer_template.json`; it defines the JSON schema and controlled enums without giving the standard answer.

### Task definition and scenario fit

The solver is asked to use the runner-provided Deal Desk base URL to prepare a structured JSON committee escalation analysis for `D-CYPRESS-735`. The expected work process is to locate the deal, active draft agreement, client instruction email, public merger committee policy, clause comparison records, and relevant benchmarks. This mirrors the Stage 1 merger escalation workflow: identify terms outside delegated authority, quantify exposure where possible, apply public merger policy, and recommend term-by-term escalation positions.

The prompt intentionally does not include a SOP checklist, thresholds, answer-like issue set, or tool-call order. The solver must discover that active deal-room records and latest written client instructions control over stale template records. Stale cap-table/template records are present in the environment as distractors.

### Material map

- `D-CYPRESS-735`: deal economics, structure, parties, client positions, negotiation context, and record links.
- `P-PUBLIC-MERGER-COMMITTEE-2026`: committee escalation rules for reverse termination fee, fiduciary out, R&W survival, MAE, and company break fee.
- `DOC-CYPRESS735-DRAFT-02`: current draft terms; the active source for RTF, fiduciary-out, survival, and MAE language.
- `DOC-CYPRESS735-EMAIL-03`: latest client instruction and strategic context, including BATNA and benchmark-memo requirement.
- `DOC-CYPRESS735-COMMITTEE-07`: committee members and routing categories.
- `/api/clauses?deal_id=D-CYPRESS-735`: active and stale clause records; active clause IDs support exact answer construction.
- `/api/benchmarks`: relevant benchmark IDs are `BM-RTF-HEALTHTECH-2026`, `BM-FIDUCIARY-PUBLIC-2026`, and `BM-MAE-HEALTHCARE-2026`.

### Solution and evaluation basis

Standard answer fields are in `output/answer.json`. The task has eight exact-match scoring points with total raw weight 17:

1. Committee routing and member set, weight 1.
2. RTF threshold/deviation, dollar amounts, and benchmark, weight 3. The draft RTF is 7.5% of $1,180,000,000, or $88,500,000. The committee threshold is 5.5%, so the deviation is 2.0 percentage points and $23,600,000 over threshold.
3. Fiduciary-out deviation and benchmark context, weight 2. The draft blocks superior-proposal termination after buyer match, triggering `PUB-FIDUCIARY`; benchmark context is 4 of 42.
4. R&W survival exposure, weight 2. The draft has 24-month post-closing R&W survival with damages covenant. The task treats uncapped public-merger damages exposure conservatively as full equity value, $1,180,000,000.
5. MAE restricted carve-outs, weight 2. The active clause identifies missing `CYBER_INCIDENT`, `CUSTOMER_LOSS`, `INDUSTRY`, `LAW_CHANGE`, and `MARKET` carve-outs; benchmark context is 31 of 36.
6. BATNA and strategic context, weight 2. The correct structured context is lower-risk private-platform BATNA, moderate leverage, activist/index-fund ownership pressure, market-standard-risk rationale, and benchmark memo required.
7. Individual recommendations, weight 3. Correct recommendations are to reduce RTF to 5.5% with superior regulatory covenant, restore superior-proposal termination, delete post-closing R&W survival, and restore full public-company MAE carve-outs; each is `DO_NOT_APPROVE_AS_DRAFTED`.
8. Aggregate risk, weight 2. Correct aggregate risk is `HIGH`, `ESCALATE_AND_RENEGOTIATE_BEFORE_SIGNING`, four escalation terms, drivers `FIDUCIARY_OUT`, `MAE_CARVEOUTS`, `RTF`, `RW_SURVIVAL`, total quantified exposure $1,268,500,000, and total policy excess $1,203,600,000.

The evaluator in `eval/eval.py` accepts an optional prediction path and defaults to `output/answer.json`. It prints JSON with normalized score, raw earned weight, total raw weight, per-point pass/fail results, and parse/read error if applicable. It normalizes set-like lists by sorting but otherwise requires exact enum and numeric matches.

Likely model pitfalls include using stale template provisions, treating the 3.25% company break fee as an escalation, failing to compute the RTF dollar excess, omitting the fiduciary-out issue because the board can change recommendation, failing to quantify survival exposure, or using irrelevant older benchmarks.

### Transfer design

As a train task, `train_003` teaches by real answer comparison that public merger escalation requires combining current draft terms, committee policy thresholds, active clause records, benchmarks, and strategic context. It reinforces recurring group conventions: use active/latest sources, compute percentages on equity or headline value as specified, separate individual term recommendations from aggregate risk, and use controlled enums instead of prose labels. These conventions anchor later test tasks, especially `test_003` and `test_004`, without exposing those test answers.

### Construction record

Author: Codex task-builder subagent. Created: 2026-07-07. Updated: 2026-07-07. Major changes: created solver prompt, answer template, standard answer, bilingual notes, and exact-match evaluator for `train_003`.

## 中文

### 数据和来源

本任务属于 `task_group_020`，来源于 `SCN_020_ma_transaction_contract_review_and_negotiation` 以及源示例 `E001`、`E002`、`E003`。任务实现了设计文档中的升级审批工作流：针对共享 Aster Legal Deal Desk 环境中的 `D-CYPRESS-735`，为买方公共公司合并委员会准备结构化升级分析。

任务使用 `task_group/task_group_020/env/data/dealdesk.json` 和 `manifest.json` 中的生成环境数据。关键记录包括交易 `D-CYPRESS-735`、政策 `P-PUBLIC-MERGER-COMMITTEE-2026`、活跃文件 `DOC-CYPRESS735-DRAFT-02`、`DOC-CYPRESS735-EMAIL-03`、`DOC-CYPRESS735-COMMITTEE-07`，以及活跃条款 `CL-CYPRESS-735-001` 到 `CL-CYPRESS-735-004`。本任务唯一的本地可见 payload 是 `input/payloads/answer_template.json`，用于说明输出结构和受控枚举，不泄露标准答案。

### 任务定义和场景匹配

求解者需要使用运行器提供的 Deal Desk base URL，为 `D-CYPRESS-735` 准备结构化 JSON 委员会升级分析。预期工作流程是查找交易、活跃草案、最新客户邮件、公共公司合并委员会政策、条款比较记录和相关基准。该流程对应 Stage 1 中的合并升级场景：识别超出授权的条款，尽可能量化风险敞口，适用公共公司合并政策，并给出逐项谈判建议。

提示词刻意不包含 SOP 清单、阈值、答案式问题列表或工具调用顺序。求解者必须从环境中推断活跃交易室记录和最新书面客户指令优先于陈旧模板记录。环境中的陈旧 cap table 和模板条款是干扰项。

### 材料映射

- `D-CYPRESS-735`：交易经济条款、结构、各方、客户立场、谈判背景和记录链接。
- `P-PUBLIC-MERGER-COMMITTEE-2026`：反向终止费、受托退出权、陈述保证存续、MAE 和公司终止费的委员会升级规则。
- `DOC-CYPRESS735-DRAFT-02`：当前草案条款，是 RTF、受托退出权、存续和 MAE 文本的活跃来源。
- `DOC-CYPRESS735-EMAIL-03`：最新客户指令和战略背景，包括 BATNA 和基准备忘录要求。
- `DOC-CYPRESS735-COMMITTEE-07`：委员会成员和升级类别。
- `/api/clauses?deal_id=D-CYPRESS-735`：活跃和陈旧条款记录；活跃条款 ID 支持标准答案构造。
- `/api/benchmarks`：相关基准 ID 为 `BM-RTF-HEALTHTECH-2026`、`BM-FIDUCIARY-PUBLIC-2026` 和 `BM-MAE-HEALTHCARE-2026`。

### 答案和评估依据

标准答案位于 `output/answer.json`。本任务有 8 个精确匹配评分点，原始总权重为 17：

1. 委员会路由和成员集合，权重 1。
2. RTF 阈值、偏离、金额和基准，权重 3。草案 RTF 为 $1,180,000,000 的 7.5%，即 $88,500,000。委员会阈值为 5.5%，因此偏离 2.0 个百分点，超阈值金额为 $23,600,000。
3. 受托退出权偏离和基准背景，权重 2。草案在买方匹配后阻止因更优提案终止，触发 `PUB-FIDUCIARY`；基准背景为 42 个样本中的 4 个。
4. 陈述保证存续风险敞口，权重 2。草案包含交割后 24 个月陈述保证存续和损害赔偿承诺。本任务保守地将无上限公共合并损害敞口视为完整股权价值 $1,180,000,000。
5. MAE 受限 carve-out，权重 2。活跃条款识别缺失 `CYBER_INCIDENT`、`CUSTOMER_LOSS`、`INDUSTRY`、`LAW_CHANGE` 和 `MARKET`；基准背景为 36 个样本中的 31 个。
6. BATNA 和战略背景，权重 2。正确结构化背景是低反垄断风险的私有临床数据平台 BATNA、中等杠杆、激进投资者和指数基金持股压力、需要平台但坚持市场标准风险分配，以及需要基准备忘录。
7. 单项建议，权重 3。正确建议是将 RTF 降至 5.5% 并配套更强监管承诺、恢复更优提案终止权、删除交割后陈述保证存续、恢复完整公共公司 MAE carve-outs；每项均为 `DO_NOT_APPROVE_AS_DRAFTED`。
8. 汇总风险，权重 2。正确汇总风险为 `HIGH`、`ESCALATE_AND_RENEGOTIATE_BEFORE_SIGNING`、4 个升级条款、驱动项 `FIDUCIARY_OUT`、`MAE_CARVEOUTS`、`RTF`、`RW_SURVIVAL`、总量化敞口 $1,268,500,000，以及总政策超额 $1,203,600,000。

`eval/eval.py` 接收可选预测路径，默认读取 `output/answer.json`。评估器输出 JSON，包括归一化得分、获得的原始权重、总权重、逐点评分结果，以及解析或读取错误。评估器会对集合型列表排序归一化，但枚举和数字字段要求精确匹配。

常见模型错误包括使用陈旧模板条款、把 3.25% 公司终止费误判为升级项、没有计算 RTF 超阈值金额、因为董事会可改变推荐而遗漏受托退出权问题、没有量化存续风险敞口，或使用无关的旧基准。

### 迁移设计

作为训练任务，`train_003` 通过真实作答和答案对比让求解者学习：公共公司合并升级需要结合当前草案条款、委员会政策阈值、活跃条款记录、基准和战略背景。它强化任务组内复用的规则：使用活跃和最新来源，按指定的股权价值或交易价值计算百分比，区分单项条款建议和汇总风险，并使用受控枚举而不是自由文本。这些经验会支撑后续测试任务，尤其是 `test_003` 和 `test_004`，但不会暴露测试答案。

### 构建记录

作者：Codex task-builder subagent。创建日期：2026-07-07。更新日期：2026-07-07。主要变更：为 `train_003` 创建求解者提示、答案模板、标准答案、双语说明和精确匹配评估器。
