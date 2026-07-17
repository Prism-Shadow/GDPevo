# test_003 Notes / 测试任务 003 说明

## English

### Data and source lineage

This task belongs to `task_group_020`, derived from `SCN_020_ma_transaction_contract_review_and_negotiation` and source examples `E001`, `E002`, and `E003`. It implements the test-side public-company merger escalation workflow for deal `D-NOVA-674` in the shared Aster Legal Deal Desk environment.

The generated shared environment data is in `task_group/task_group_020/env/data/dealdesk.json` and `manifest.json`. Key records are deal `D-NOVA-674`, policy `P-PUBLIC-MERGER-COMMITTEE-2026`, active documents `DOC-NOVA674-DRAFT-02`, `DOC-NOVA674-EMAIL-03`, `DOC-NOVA674-COMMITTEE-07`, and active clause records `CL-NOVA-674-001` through `CL-NOVA-674-004`. Stale records `DOC-NOVA674-CAP-STALE`, `DOC-NOVA674-TEMPLATE-99`, `CL-NOVA-674-S01`, and `CL-NOVA-674-S02` are distractors. The task-local solver-visible files are `input/prompt.txt` and `input/payloads/answer_template.json`.

### Task definition and scenario fit

The solver is asked to use the runner-provided Aster Legal Deal Desk base URL to prepare a structured JSON escalation packet for `D-NOVA-674`. The expected work is to locate the deal, active draft agreement, latest client instruction email, public merger committee policy, active clause comparison records, committee charter, and relevant benchmark records. This matches the Stage 1 merger escalation pattern: identify terms outside delegated authority, quantify exposure where supported, separate market/statistical context from legal judgment, and route the approval decision to the proper committee.

The prompt intentionally avoids SOP steps, thresholds, answer-like issue labels, scoring hints, and exact source lists. The solver must infer the same source-precedence and field conventions practiced in train tasks: active draft and latest written client instructions control over stale template records, committee policy controls approval routing, and percentages are calculated on the deal value base stated by the policy or clause record.

### Material map

- `D-NOVA-674`: deal economics, structure, client positions, negotiation context, stockholder dynamics, committee members, and record links.
- `P-PUBLIC-MERGER-COMMITTEE-2026`: committee policy for RTF, fiduciary-out, R&W survival, MAE, and company break fee.
- `DOC-NOVA674-DRAFT-02`: active current draft terms for RTF, fiduciary-out, survival, and MAE.
- `DOC-NOVA674-EMAIL-03`: latest client instruction, fallback position, strategic context, and benchmark-set note.
- `DOC-NOVA674-COMMITTEE-07`: transaction committee roster and routing categories.
- `/api/clauses?deal_id=D-NOVA-674`: active clause IDs and stale template clause distractors.
- `/api/benchmarks`: relevant current benchmark records `BM-RTF-HEALTHTECH-2026`, `BM-FIDUCIARY-PUBLIC-2026`, and `BM-MAE-HEALTHCARE-2026`.
- `input/payloads/answer_template.json`: solver-visible response contract, enum choices, numeric conventions, and list-ordering rules.

### Solution and evaluation basis

The standard answer is `output/answer.json`. It contains four escalated terms: `FIDUCIARY_OUT`, `MAE_CARVEOUTS`, `RTF`, and `RW_SURVIVAL`. The company break fee is 3.6% and is near the high end but within the committee fallback of up to 3.75% with go-shop support, so it is not included as an escalation term.

The RTF draft is 6.25% of $860,000,000 equity value, or $53,750,000. The committee threshold is 5.50%, so the deviation is 0.75 percentage points and $6,450,000 above threshold. RTF exposure is recorded as the full draft RTF amount with `EQUITY_VALUE` as the basis.

The fiduciary-out clause blocks the superior-proposal termination right during a six-business-day match period, triggering `PUB-FIDUCIARY`. It is non-quantified legal risk. The R&W survival clause has target R&W surviving 18 months after closing, which triggers `PUB-RW-SURVIVAL`; the conservative public-merger exposure is full equity value, $860,000,000. The MAE clause omits industry, cyber, and pandemic carve-outs within the available enum set; the source also mentions reimbursement omissions, but `reimbursement` is not an enum and is intentionally not scored as a carve-out code.

Benchmark context uses `BM-RTF-HEALTHTECH-2026` with sample size 28 and count above threshold 3, `BM-FIDUCIARY-PUBLIC-2026` with sample size 42 and count above threshold 4, and `BM-MAE-HEALTHCARE-2026` with sample size 36 and count above threshold 31. The aggregate risk is `HIGH`, final action is `ESCALATE_AND_RENEGOTIATE_BEFORE_SIGNING`, the route is `BOARD_TRANSACTION_COMMITTEE`, approval is required, and committee members are `Dr. Elaine Park`, `Carla Winthrop`, and `Mateo Silva`. Total quantified exposure is $913,750,000, equal to RTF exposure plus survival exposure. Total policy excess is $866,450,000, equal to RTF excess plus survival exposure.

The evaluator has seven exact-match scoring points with total raw weight 13, synchronized with `task_group.yaml`:

1. RTF threshold, deviation, dollar amounts, and exposure basis, weight 2.
2. Fiduciary-out escalation decision, weight 1.
3. R&W survival exposure, weight 1.
4. MAE restricted carve-out decision and omitted enum codes, weight 2.
5. Benchmark/statistical context for RTF, fiduciary-out, and MAE, weight 3.
6. Individual approval recommendations and term recommendations, weight 1.
7. Aggregate risk, quantified totals, strategic context, and committee routing, weight 3.

The evaluator in `eval/eval.py` accepts an optional prediction path and defaults to `output/answer.json`. It prints JSON with normalized score, raw earned weight, total raw weight, per-point pass/fail entries, and parse/read errors. Set-like fields such as committee members and driver term IDs are sorted before comparison; enums, numbers, and booleans require exact matches at the declared precision.

Likely model pitfalls include using stale template clauses, including the within-fallback break fee as an escalated term, using stale 2019 benchmarks, missing the RTF dollar excess, treating survival exposure as zero because public mergers usually lack indemnity, over-including non-enum MAE omissions, or mapping founder-block support to `FOUNDER_CONTROLLED` instead of the activist/index-fund public-company context.

### Transfer design

`test_003` has explicit transfer anchors in `train_003` and `train_005`.

From `train_003`, solvers should transfer the public merger escalation workflow: combine active draft clauses, committee policy thresholds, benchmark records, and strategic context; compute RTF percentages on equity value; quantify RTF exposure separately from policy excess; treat post-closing public-merger R&W survival as full-equity-value exposure; separate term-level recommendations from aggregate risk; and route out-of-policy public merger terms to the board transaction committee.

From `train_005`, solvers should transfer source-precedence habits and policy judgment: active deal-room records and latest client instructions outrank stale exports and generic template provisions, policy checks should distinguish current approval needs from fallback authority, and controlled enums should be used instead of prose labels. Here those habits apply to stale Nova template clauses, the current client fallback for a lower RTF, and the exact output contract.

Transfer should help identify the right evidence and calculation pattern, but the answer still requires task-specific exploration: Nova has a different equity value, RTF percentage, committee roster, survival period, MAE omissions, stockholder context, and break-fee distractor from the train deals.

### Construction record

Author: Codex task-builder subagent for `task_group_020/test_003`.

Created: 2026-07-07.

Updated: 2026-07-07.

Major changes: created solver prompt, answer template, standard answer, exact-match evaluator, and bilingual construction notes for `D-NOVA-674`.

## 中文

### 数据和来源脉络

本任务属于 `task_group_020`，来源于 `SCN_020_ma_transaction_contract_review_and_negotiation` 以及源示例 `E001`、`E002`、`E003`。任务实现测试侧公共公司合并升级审批流程，交易为共享 Aster Legal Deal Desk 环境中的 `D-NOVA-674`。

生成的共享环境数据位于 `task_group/task_group_020/env/data/dealdesk.json` 和 `manifest.json`。关键记录包括交易 `D-NOVA-674`、政策 `P-PUBLIC-MERGER-COMMITTEE-2026`、有效文件 `DOC-NOVA674-DRAFT-02`、`DOC-NOVA674-EMAIL-03`、`DOC-NOVA674-COMMITTEE-07`，以及有效条款 `CL-NOVA-674-001` 至 `CL-NOVA-674-004`。过期记录 `DOC-NOVA674-CAP-STALE`、`DOC-NOVA674-TEMPLATE-99`、`CL-NOVA-674-S01`、`CL-NOVA-674-S02` 是干扰项。本任务本地、解题者可见文件为 `input/prompt.txt` 和 `input/payloads/answer_template.json`。

### 任务定义和场景匹配

解题者需要使用运行器提供的 Aster Legal Deal Desk base URL，为 `D-NOVA-674` 准备结构化 JSON 升级审批包。预期工作是查找交易、有效草案、最新客户指示邮件、公共公司合并委员会政策、有效条款比较记录、委员会章程和相关基准记录。这符合 Stage 1 的合并升级模式：识别超出授权的条款，在有依据时量化敞口，区分市场/统计背景与法律判断，并把审批决定路由到正确委员会。

提示词刻意不包含 SOP 步骤、阈值、答案式问题标签、评分提示或精确来源清单。解题者必须迁移训练任务中的来源优先级和字段惯例：有效草案和最新书面客户指示优先于过期模板，委员会政策决定审批路由，百分比按政策或条款记录指定的交易价值基数计算。

### 材料地图

- `D-NOVA-674`：交易经济条款、结构、客户立场、谈判背景、股东动态、委员会成员和记录链接。
- `P-PUBLIC-MERGER-COMMITTEE-2026`：RTF、受托退出权、陈述保证存续、MAE 和公司终止费的委员会政策。
- `DOC-NOVA674-DRAFT-02`：RTF、受托退出权、存续和 MAE 的当前有效草案条款。
- `DOC-NOVA674-EMAIL-03`：最新客户指示、后备立场、战略背景和基准组说明。
- `DOC-NOVA674-COMMITTEE-07`：交易委员会成员名单和路由类别。
- `/api/clauses?deal_id=D-NOVA-674`：有效条款 ID 以及过期模板条款干扰项。
- `/api/benchmarks`：相关当前基准记录为 `BM-RTF-HEALTHTECH-2026`、`BM-FIDUCIARY-PUBLIC-2026`、`BM-MAE-HEALTHCARE-2026`。
- `input/payloads/answer_template.json`：解题者可见的响应契约、枚举、数值规则和列表排序规则。

### 答案和评估依据

标准答案为 `output/answer.json`。其中包含四个升级条款：`FIDUCIARY_OUT`、`MAE_CARVEOUTS`、`RTF`、`RW_SURVIVAL`。公司终止费为 3.6%，接近高位但仍在有 go-shop 支持时最高 3.75% 的委员会后备范围内，因此不作为升级条款列入。

RTF 草案为 $860,000,000 股权价值的 6.25%，即 $53,750,000。委员会阈值为 5.50%，所以偏离为 0.75 个百分点，超阈值金额为 $6,450,000。RTF 敞口记录为完整草案 RTF 金额，基数为 `EQUITY_VALUE`。

受托退出权条款在六个工作日匹配期内阻止因更优提案终止，触发 `PUB-FIDUCIARY`，属于不可量化的法律风险。陈述保证存续条款规定目标公司陈述保证交割后存续 18 个月，触发 `PUB-RW-SURVIVAL`；公共公司合并中的保守敞口为完整股权价值 $860,000,000。MAE 条款在可用枚举范围内缺失 industry、cyber 和 pandemic carve-outs；来源还提到 reimbursement 缺失，但 `reimbursement` 不是枚举值，因此不作为评分 carve-out 代码。

基准背景使用 `BM-RTF-HEALTHTECH-2026`，样本量 28，超阈值数量 3；`BM-FIDUCIARY-PUBLIC-2026`，样本量 42，超阈值数量 4；以及 `BM-MAE-HEALTHCARE-2026`，样本量 36，超阈值数量 31。汇总风险为 `HIGH`，最终行动为 `ESCALATE_AND_RENEGOTIATE_BEFORE_SIGNING`，路由为 `BOARD_TRANSACTION_COMMITTEE`，需要审批，委员会成员为 `Dr. Elaine Park`、`Carla Winthrop`、`Mateo Silva`。总量化敞口为 $913,750,000，即 RTF 敞口加存续敞口。总政策超额为 $866,450,000，即 RTF 超额加存续敞口。

评估器有 7 个精确匹配评分点，原始总权重为 13，并已与 `task_group.yaml` 同步：

1. RTF 阈值、偏离、金额和敞口基数，权重 2。
2. 受托退出权升级判断，权重 1。
3. 陈述保证存续敞口，权重 1。
4. MAE 受限 carve-out 判断和缺失枚举代码，权重 2。
5. RTF、受托退出权和 MAE 的基准/统计背景，权重 3。
6. 单项审批建议和条款建议，权重 1。
7. 汇总风险、量化合计、战略背景和委员会路由，权重 3。

`eval/eval.py` 接收可选预测路径，默认读取 `output/answer.json`。评估器输出 JSON，包括归一化得分、获得的原始权重、总权重、逐点评分结果，以及解析或读取错误。委员会成员、主要驱动条款等集合型字段会排序后比较；枚举、数字和布尔值按照声明精度精确匹配。

常见模型错误包括使用过期模板条款、把仍在后备范围内的公司终止费列为升级条款、使用过期 2019 年基准、漏算 RTF 超阈值金额、因为公共公司合并通常无赔偿而把存续敞口当作零、过度加入非枚举 MAE 缺失项，或把 founder block 支持错误映射为 `FOUNDER_CONTROLLED` 而不是激进投资者/指数基金的公共公司语境。

### 迁移设计

`test_003` 的明确迁移锚点是 `train_003` 和 `train_005`。

从 `train_003`，解题者应迁移公共公司合并升级流程：结合有效草案条款、委员会政策阈值、基准记录和战略背景；按股权价值计算 RTF 百分比；区分 RTF 敞口和政策超额；把交割后公共公司合并陈述保证存续作为完整股权价值敞口；区分单项条款建议和汇总风险；并把超政策公共公司合并条款路由到董事会交易委员会。

从 `train_005`，解题者应迁移来源优先级和政策判断习惯：有效交易室记录和最新客户指示优先于过期导出和通用模板，政策检查要区分当前审批需要和后备授权，输出应使用受控枚举而不是叙述标签。在本任务中，这些习惯对应 Nova 的过期模板条款、当前客户对更低 RTF 的后备授权，以及精确输出契约。

迁移会帮助识别正确证据和计算模式，但答案仍需要任务特定探索：Nova 的股权价值、RTF 百分比、委员会成员、存续期限、MAE 缺失项、股东背景和公司终止费干扰项都不同于训练交易。

### 构建记录

作者：`task_group_020/test_003` 的 Codex task-builder subagent。

创建日期：2026-07-07。

更新日期：2026-07-07。

主要变更：为 `D-NOVA-674` 创建了解题提示、答案模板、标准答案、精确匹配评估器和双语构建说明。

## Evaluation Synchronization Update

The evaluator has seven exact-match scoring points with total raw weight 13, synchronized with `task_group.yaml`:

1. RTF threshold, deviation, dollar amounts, and exposure basis, weight 2.
2. Fiduciary-out escalation decision, weight 1.
3. R&W survival exposure, weight 1.
4. MAE restricted carve-out decision and omitted enum codes, weight 2.
5. Benchmark/statistical context for RTF, fiduciary-out, and MAE, weight 3.
6. Individual approval recommendations and term recommendations, weight 1.
7. Aggregate risk, quantified totals, strategic context, and committee routing, weight 3.

This section is authoritative for evaluator weight documentation after the latest rework. It matches `eval/eval.py` and `task_group.yaml`.
