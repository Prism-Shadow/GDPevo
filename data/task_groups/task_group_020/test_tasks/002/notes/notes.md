# test_002 Notes

## English

This task belongs to `task_group_020`, source scenario `SCN_020_ma_transaction_contract_review_and_negotiation`, with transfer primarily anchored in source example `E003` and the committee-escalation train task `train_003`. The assigned deal is `PRJ_VEGA`, a public-company merger in which Verdantis Therapeutics plc is the buyer and Vega BioSystems Inc. is the counterparty. The generated shared environment under `task_group/task_group_020/env/` provides the construction evidence. No environment source file, SQLite database, manifest, seed file, or setup script is copied into the solver payload.

The solver-visible inputs are `input/prompt.txt` and `input/payloads/answer_template.json`. The prompt directs the solver to use `<TASK_ENV_BASE_URL>` and the workbench APIs, including the optional read-only SQL endpoint. The required work product is a structured committee escalation package with `routing`, `escalation_terms`, and `aggregate_summary`.

The task fits the group design because it requires counsel to reconcile a live draft merger agreement against a committee policy, benchmarks, risk estimates, cap table, deal notes, and dates. The important records are: deal metadata for headline value, client, counterparty, signing date, meeting date, and strategic context; `draft_terms` for the four current draft positions; `policy_thresholds` for `POL_MA_2025_A`; `benchmarks` for reverse termination fee and survival context; `risk_estimates` for closing-certainty and indemnity-leakage exposure; `cap_table` for the voting-agreement distractor; and notes for the rival-bidder pressure.

The standard answer escalates exactly four current term categories: `reverse_termination_fee`, `fiduciary_out`, `rw_survival`, and `mae_carveouts`. It excludes `termination_fee` and `voting_agreements` because PRJ_VEGA has no current draft term requiring escalation for those categories, and the largest cap-table support holder is 34.1%, below the 35.0% policy threshold. The reverse termination fee is 4.8% of the 980,000,000 USD equity value, so the draft amount is 47,040,000 USD. The policy cap is 4.0%, or 39,200,000 USD, and the policy excess is 7,840,000 USD. The fee is above the benchmark upper quartile of 4.1% by 0.7 percentage points. The fiduciary-out term removes the intervening-event trigger and limits the board-change process to superior proposal only; the answer rejects that current draft unless the full process, intervening-event trigger, and required match right are restored. The survival term has 21-month fundamental and 17-month general representation survival against a 15-month policy threshold, with 7,840,000 to 27,440,000 USD indemnity-leakage exposure. The MAE term adds pandemic, clinical-trial hold, and sector-wide regulatory-change carve-outs; the clinical-trial hold is classified as target-specific regulatory risk to delete, while pandemic and sector-wide regulatory change require narrowing plus a disproportionate-effect carveback.

The evaluator has eight deterministic whole-point scoring goals with raw weights 1-3: correct out-of-policy term set and distractor exclusion (2); correct RTF math and benchmark comparison (3); fiduciary-out deviation and mitigation (2); survival exposure and threshold calculation (2); MAE carve-out classification (2); term recommendations and priority order (2); aggregate exposure and strategic/cap-table context (2); and routing/date fields (1). These cover distinct business outcomes: entity selection, economics, governance/legal covenant risk, post-closing exposure, MAE drafting classification, recommendation posture, aggregate committee risk, and administrative routing. Each point is all-or-nothing and uses exact enums, integer dollars, stable term IDs, sorted sets, and fixed numeric precision.

Likely pitfalls include using upfront cash rather than equity value for the RTF calculation, treating the 34.1% lead investor group as a voting-agreement breach, including a termination-fee distractor, missing the fiduciary-out intervening-event trigger, treating the clinical-trial hold as a generic regulatory carve-out, or summing every risk estimate instead of the declared exposure components.

Transfer design: `train_003` teaches the committee-escalation pattern, including out-of-policy filtering, policy-threshold comparison, benchmark use, survival exposure, MAE restricted-carve-out treatment, recommendations, and routing fields. For this test task, transfer-dependent difficulty appears in the RTF base selection, the fiduciary-out mitigation judgment, the MAE classification, and the choice to exclude near-threshold policy distractors. Task-specific exploration is still required because PRJ_VEGA has different economics, dates, counterparty, cap-table values, and risk ranges from the train deal.

Construction record: created by task-builder-test-002 on 2026-07-18. Initial version created `prompt.txt`, `answer_template.json`, `answer.json`, `eval.sh`, `evaluate.py`, and this bilingual notes file for test task 002.

## 中文

本任务属于 `task_group_020`，来源场景为 `SCN_020_ma_transaction_contract_review_and_negotiation`，主要迁移锚点是来源示例 `E003` 和委员会升级类训练任务 `train_003`。指定交易是 `PRJ_VEGA`，交易类型为上市公司合并，Verdantis Therapeutics plc 是买方，Vega BioSystems Inc. 是相对方。共享环境 `task_group/task_group_020/env/` 中的生成数据用于构造证据，但没有把环境源码、SQLite 数据库、manifest、种子或部署脚本复制进求解器 payload。

求解器可见输入是 `input/prompt.txt` 和 `input/payloads/answer_template.json`。提示要求使用 `<TASK_ENV_BASE_URL>` 访问工作台和 API，包括可选的只读 SQL 查询端点。预期输出是结构化的委员会升级材料，包含 `routing`、`escalation_terms` 和 `aggregate_summary`。

该任务符合本组设计，因为它要求交易律师把当前合并协议草案与委员会政策、市场基准、风险估计、股权表、交易笔记和日期进行交叉核对。关键材料包括：交易元数据中的股权价值、客户、相对方、签署日期、会议日期和战略背景；`draft_terms` 中四个当前草案条款；`POL_MA_2025_A` 的 `policy_thresholds`；反向终止费和陈述保证存续期相关 `benchmarks`；关于成交确定性和赔偿泄漏的 `risk_estimates`；用于投票协议干扰项判断的 `cap_table`；以及说明竞争买家压力的交易笔记。

标准答案只升级四个当前条款类别：`reverse_termination_fee`、`fiduciary_out`、`rw_survival` 和 `mae_carveouts`。答案排除 `termination_fee` 和 `voting_agreements`，因为 PRJ_VEGA 没有这两类需要升级的当前草案条款，而且最大支持股东比例为 34.1%，低于 35.0% 的政策阈值。反向终止费为 980,000,000 美元股权价值的 4.8%，即 47,040,000 美元；政策上限为 4.0%，即 39,200,000 美元，超出额为 7,840,000 美元。该费用比 4.1% 的基准上四分位高 0.7 个百分点。信义退出条款删除了介入事件触发条件，并把董事会变更流程限制为仅限更优提案；标准答案拒绝当前草案，除非恢复完整流程、介入事件触发条件和必要匹配权。陈述保证存续期为基本陈述 21 个月、一般陈述 17 个月，均高于 15 个月政策阈值，并对应 7,840,000 至 27,440,000 美元赔偿泄漏风险。MAE 条款新增 pandemic、clinical-trial hold 和 sector-wide regulatory change 例外；其中 clinical-trial hold 被分类为目标公司特定监管风险，应删除，其他两项需要缩窄并加入不成比例影响例外。

评估器设置八个确定性的整点评分目标，原始权重为 1 至 3：正确识别越权条款集合并排除干扰项（2）；正确计算反向终止费及基准比较（3）；正确信义退出偏离和修正要求（2）；正确存续期风险敞口和阈值计算（2）；正确分类 MAE 例外（2）；正确条款建议和优先级（2）；正确汇总风险敞口、战略背景和股权表判断（2）；正确路由和日期字段（1）。这些目标覆盖不同业务结果：实体选择、经济计算、治理和法律契约风险、交割后风险、MAE 起草分类、建议立场、委员会汇总风险和行政路由。每个评分点都是全有或全无，使用精确枚举、整数美元、稳定条款 ID、排序集合和固定数值精度。

常见错误包括：用 upfront cash 而不是 equity value 计算反向终止费；把 34.1% 的主要投资人组误判为投票协议违规；加入 termination fee 干扰项；漏掉信义退出中的介入事件触发条件；把 clinical-trial hold 当成一般监管例外；或把所有风险估计都相加而不是使用标准答案声明的风险组成项。

迁移设计：`train_003` 体现委员会升级任务的通用模式，包括筛选越权条款、比较政策阈值、使用市场基准、计算存续期风险、处理 MAE 限制性例外、给出建议和填写路由字段。本测试任务中，反向终止费基数选择、信义退出修正判断、MAE 分类以及排除接近阈值的政策干扰项都依赖迁移能力。任务本身仍需要探索，因为 PRJ_VEGA 的经济数据、日期、相对方、股权表数值和风险区间均不同于训练交易。

构造记录：task-builder-test-002 于 2026-07-18 创建。初版为测试任务 002 创建了 `prompt.txt`、`answer_template.json`、`answer.json`、`eval.sh`、`evaluate.py` 和本双语 notes 文件。
