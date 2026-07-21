# train_005 Notes - May Therapy Margin Queue

## English

Data/source lineage: This task belongs to `task_group_014`, scenario `SCN_014_healthcare_payer_authorization_appeals`, using source examples `E001` through `E007`. The closest source anchor is `E004`, the outpatient rehabilitation payer-service profitability example; `E003` also informs reimbursement and rate-correction discipline. The shared environment is the generated Northstar payer-operations SQLite-backed service documented in `scratch/env_blueprint.md` and `task_group/task_group_014/env/manifest.json`. The relevant public data table is `service_margin`; the task-local payload `input/payloads/task_context.json` identifies target business ID `QUEUE-TR-005`, reporting period `2026-05`, and row IDs `SM-TR-005-MCD`, `SM-TR-005-COM`, and `SM-TR-005-WC`.

Task definition: The solver acts as a UM-finance operations analyst summarizing a monthly therapy margin queue. The visible prompt asks for a structured JSON answer, not a memo. The solver must query the shared environment, use the listed queue rows only, compute total cost as `variable_cost + fixed_cost_allocated`, compute margin as `net_revenue - total_cost`, compute revenue-to-cost ratios, identify rows below the 1.2000 threshold, separate charge-sensitive rows, choose the top issue, and assign payer-service actions from the controlled enum.

Scenario fit: This is a realistic payer-operations analytics task adjacent to utilization management and reimbursement. It uses the same shared workplace as the clinical, appeal, P2P, and claim tasks, but exercises the revenue-cycle side of the scenario: payer segment, CPT, payment sensitivity, cost allocation, and monthly queue routing. It preserves the source example challenge of separating government fixed-schedule pressure from commercial or workers-comp charge sensitivity.

Material map: `prompt.txt` gives the business request and environment access shape. `task_context.json` supplies the target row IDs and finance definitions without final calculations. `answer_template.json` defines the output schema, numeric precision, ordering, and enums. The SQL endpoint `POST /sql/query` with token `pa-review-token-014` exposes the `service_margin` table. The environment also contains distractor May therapy rows and unrelated service-margin rows, so the target row IDs are needed to avoid broad month-level aggregation.

Solution and evaluation basis: The standard answer uses row data from `service_margin`. For Medicaid row `SM-TR-005-MCD`, net revenue is 23690.00 and total cost is 21140.00 + 5100.00 = 26240.00, margin is -2550.00, ratio is 0.9028, and the gap to 120 percent of cost is 26240.00 * 1.2 - 23690.00 = 7798.00. For commercial row `SM-TR-005-COM`, total cost is 31700.00, margin is 13570.00, and ratio is 1.4281. For workers-comp row `SM-TR-005-WC`, total cost is 13520.00, margin is 12240.00, and ratio is 1.9053. The below-threshold segment is `medicaid`; charge-sensitive segments are `commercial` and `workers_comp`; top issue is `medicaid_97110`. The seven evaluator points are: case/period/threshold, weight 1; row total costs and margins, weight 2; ratios, weight 2; below-threshold segment and top issue, weight 3; charge-sensitive segment set, weight 2; recommended action by payer segment, weight 2; Medicaid gap to 120 percent, weight 1. Each point is all-or-zero with cent or four-decimal tolerance.

Likely model pitfalls: A solver may include distractor May therapy rows, treat all profitable rows as no action despite charge sensitivity, compute margin from variable cost only, confuse margin ratio with margin percent, order or name payer segments inconsistently, or apply charge-sensitive logic to Medicaid. Another common error is to use all `2026-05` physical therapy rows instead of the three queue row IDs.

Transfer design for this train task: Solving this task and comparing to the answer should teach the solver that Northstar reimbursement analytics require exact row targeting, cost reconstruction from variable and fixed components, four-decimal ratio conventions, and separation of fixed-schedule under-threshold issues from charge-sensitive monitoring. The solved example also reveals field conventions such as `payer_segment`, `service_domain`, `recommended_action`, and top-issue labeling. This is a real train task, not a tutorial; downstream test tasks can transfer these habits to benchmark matching, claim correction, and mixed UM-finance queues.

Construction record: Builder E created this task on 2026-07-18. Files added under `task_group/task_group_014/train_tasks/005/`: solver prompt, task context payload, answer template, standard answer, evaluator, eval shell script, and hidden notes. The evaluator was designed to score the standard answer at 1.0 using seven deterministic whole-point checks.

## Chinese

数据与来源脉络：本任务属于 `task_group_014`，场景为 `SCN_014_healthcare_payer_authorization_appeals`，来源示例为 `E001` 到 `E007`。最接近的来源锚点是 `E004` 门诊康复按付款方和服务线分析盈利能力的任务；`E003` 也提供了报销与费率纠错方面的设计依据。共享环境是 Northstar 付款方运营的 SQLite 服务，环境设计见 `scratch/env_blueprint.md` 和 `task_group/task_group_014/env/manifest.json`。本任务使用的公开数据表是 `service_margin`；任务本地负载 `input/payloads/task_context.json` 给出目标业务 ID `QUEUE-TR-005`、报告期间 `2026-05`，以及三条目标行 `SM-TR-005-MCD`、`SM-TR-005-COM`、`SM-TR-005-WC`。

任务定义：求解者扮演 UM-finance 运营分析师，需要汇总月度治疗服务利润队列。可见提示要求输出结构化 JSON，而不是说明性备忘录。求解者需要查询共享环境，只使用指定队列行，将总成本计算为 `variable_cost + fixed_cost_allocated`，将利润计算为 `net_revenue - total_cost`，计算收入成本比，识别低于 1.2000 阈值的行，区分可受收费调整影响的行，选择首要问题，并从受控枚举中给出付款方服务层面的行动。

场景适配：这是一个贴近真实付款方运营的收入周期分析任务，和利用管理、申诉、同业沟通、理赔任务处在同一工作环境中，但考察收入周期侧的付款方分段、CPT、支付敏感性、成本分摊和月度队列分流。它保留了来源示例中的关键挑战：把政府固定费率压力与商业保险或工伤赔付的收费敏感性分开。

材料地图：`prompt.txt` 给出业务请求和环境访问方式。`task_context.json` 给出目标行 ID 和财务定义，但不包含最终计算结果。`answer_template.json` 定义输出结构、数值精度、排序和枚举。SQL 端点 `POST /sql/query` 使用 token `pa-review-token-014`，可查询 `service_margin` 表。环境中还存在同月治疗服务干扰行和无关利润行，因此必须用目标行 ID 避免错误聚合整个月份。

答案与评估依据：标准答案来自 `service_margin` 表。Medicaid 行 `SM-TR-005-MCD` 的净收入为 23690.00，总成本为 21140.00 + 5100.00 = 26240.00，利润为 -2550.00，收入成本比为 0.9028，到 120% 成本的缺口为 26240.00 * 1.2 - 23690.00 = 7798.00。Commercial 行 `SM-TR-005-COM` 的总成本为 31700.00，利润为 13570.00，收入成本比为 1.4281。Workers-comp 行 `SM-TR-005-WC` 的总成本为 13520.00，利润为 12240.00，收入成本比为 1.9053。低于阈值的分段是 `medicaid`；收费敏感分段是 `commercial` 和 `workers_comp`；首要问题是 `medicaid_97110`。评估器包含七个整点评分项：case/period/threshold 权重 1；行级总成本和利润权重 2；收入成本比权重 2；低于阈值分段与首要问题权重 3；收费敏感分段集合权重 2；按付款方分段的建议行动权重 2；Medicaid 到 120% 成本的缺口权重 1。每个评分项只有全得或不得，货币按分、比率按四位小数容差检查。

常见模型陷阱：求解者可能纳入同月治疗服务干扰行；因为行本身盈利就把收费敏感行错误地标成无需行动；只用可变成本计算利润；混淆利润率和收入成本比；付款方分段命名或排序不一致；或者把收费敏感逻辑错误套到 Medicaid。另一个常见错误是查询全部 `2026-05` physical therapy 行，而不是只看三条队列行。

训练任务的迁移设计：完成本任务并对照答案后，求解者应能学习到 Northstar 报销分析需要精确定位目标行、从可变成本和固定成本还原总成本、遵守四位小数比率约定，并把固定费率下低于阈值的问题与收费敏感监控分开。这个已解样例还揭示了 `payer_segment`、`service_domain`、`recommended_action` 和 `top_issue` 的字段约定。本任务是真实训练任务，不是教程；后续测试任务可将这些习惯迁移到基准费率匹配、理赔纠错和混合 UM-finance 队列。

构建记录：Builder E 于 2026-07-18 创建本任务。新增文件位于 `task_group/task_group_014/train_tasks/005/` 下，包括求解者提示、任务上下文负载、答案模板、标准答案、评估器、评估 shell 脚本和隐藏说明。评估器按七个确定性整点评分项设计，标准答案应得 1.0。

## 2026-07-19 Basis-Audit Update

English: The answer template and standard answer now use `basis_audit`, a business-grounded audit trail rather than an invented control-code layer. `source_precedence` records the source category, `precedence_record_order` records the ordered business source trail, `controlling_record_ids` records the environment records that directly control the result, and `exception_record_ids` records stale, missing, unsupported, unresolved, or route-priority records. For this task, `source_precedence` is `margin_threshold_then_charge_sensitivity`, `precedence_record_order` is `SM-TR-005-MCD`, `SM-TR-005-COM`, `SM-TR-005-WC`, controlling records are `SM-TR-005-MCD`, `SM-TR-005-COM`, `SM-TR-005-WC`, and exception records are `SM-TR-005-MCD`; the train evaluator scores this combined basis trail at low weight.

中文：答案模板和标准答案现在使用 `basis_audit`，这是基于业务依据的审计轨迹，而不是人为 control-code 层。`source_precedence` 记录来源类别，`precedence_record_order` 记录按优先级排列的业务来源轨迹，`controlling_record_ids` 记录直接决定结果的环境记录，`exception_record_ids` 记录过期、缺失、不支持、未解决或路线优先级记录。本任务中，`source_precedence` 为 `margin_threshold_then_charge_sensitivity`，`precedence_record_order` 为 `SM-TR-005-MCD`, `SM-TR-005-COM`, `SM-TR-005-WC`，控制记录为 `SM-TR-005-MCD`, `SM-TR-005-COM`, `SM-TR-005-WC`，例外记录为 `SM-TR-005-MCD`；the train evaluator scores this combined basis trail at low weight。
