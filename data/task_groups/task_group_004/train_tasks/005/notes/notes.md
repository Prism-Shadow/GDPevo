# High-Touch Retention Operations Board Notes

## Data lineage / 数据血缘

EN: The task uses the ApexCloud Retention Operations environment for Q2 2026. Account identity and segment values come from `accounts.json`; current ARR comes from the latest posted billing snapshot on or before 2026-06-30; receivables come from `ar_aging.json` matched by exact legal customer name; support health comes from clean Q2 support tickets; NPS comes from valid Q2 survey responses; usage comes from monthly account metrics; expansion pipeline comes from open opportunities with Q2 close dates.

ZH: 本任务使用 ApexCloud Retention Operations 的 2026 年第二季度环境数据。账户身份和分层来自 `accounts.json`；当前 ARR 来自 2026-06-30 当日或之前最新已过账的账单快照；应收账款通过法定客户名称精确匹配 `ar_aging.json`；支持健康度来自第二季度清洁工单；NPS 来自第二季度有效问卷；使用率来自月度账户指标；扩展管道来自关闭日期在第二季度且仍未关闭的机会。

## Task definition / 任务定义

EN: The solver must create an action board for eight named high-touch accounts as of 2026-06-30. The board combines retention risk level, primary action, billing ARR, Q2 open expansion pipeline, overdue receivables, next-touch due date, and reason-code sets. It also returns segment counts and portfolio-level exposure totals.

ZH: 求解者需要在 2026-06-30 时点为 8 个指定高接触账户创建行动看板。看板结合留存风险等级、首要行动、账单 ARR、第二季度开放扩展管道、逾期应收款、下一次触达日期和原因代码集合，并返回分层数量及组合层面的敞口汇总。

## Scenario fit / 场景适配

EN: The scenario fits CS leadership operating-review work: it requires reconciling financial exposure, service deterioration, renewal timing, NPS movement, usage weakness, and expansion offsets before deciding where leadership attention should go.

ZH: 该场景符合客户成功领导层运营复盘需求：在决定管理层关注顺序之前，需要综合财务敞口、服务恶化、续约窗口、NPS 变化、使用率疲弱和扩展机会抵消因素。

## Material map / 材料映射

EN: `input/prompt.txt` gives the visible business request. `input/payloads/answer_template.json` provides the required JSON shape. `output/answer.json` is the deterministic gold answer. `eval/eval.sh` compares a submitted prediction, or the gold answer by default, against exact business-result checks.

ZH: `input/prompt.txt` 给出可见业务请求；`input/payloads/answer_template.json` 给出必需 JSON 结构；`output/answer.json` 是确定性的标准答案；`eval/eval.sh` 会将提交预测文件，或默认标准答案，与精确业务结果检查进行比较。

## Solution and evaluation basis / 解法与评估依据

EN: Ranking follows the shared retention risk score order. Current ARR uses billing snapshot values as of 2026-06-30. Overdue balance is `61_90 + 90_plus` from A/R aging. Q2 open expansion pipeline excludes Closed Won and Closed Lost opportunities and uses close dates from 2026-04-01 through 2026-06-30. `arr_at_risk` sums current ARR for medium, high, and critical accounts; `net_revenue_exposure` subtracts all Q2 open expansion pipeline from that at-risk ARR total.

ZH: 排序遵循共享留存风险评分顺序。当前 ARR 使用 2026-06-30 的账单快照值。逾期余额为 A/R aging 中的 `61_90 + 90_plus`。第二季度开放扩展管道排除 Closed Won 和 Closed Lost，并使用 2026-04-01 至 2026-06-30 的关闭日期。`arr_at_risk` 汇总中、高、严重风险账户的当前 ARR；`net_revenue_exposure` 用该风险 ARR 总额减去全部第二季度开放扩展管道。

## Transfer design / 迁移设计

EN: This task transfers the same conventions needed by executive watchlist tasks: retention risk ranking, action priority, billing ARR precedence, A/R legal-name matching, open-pipeline offsets, and action due-date mapping.

ZH: 本任务迁移到后续高管观察名单任务所需的相同约定：留存风险排序、行动优先级、账单 ARR 优先、A/R 法定名称匹配、开放管道抵消，以及行动到截止日期的映射。

## Construction record / 构建记录

EN: Constructed for `task_group_004/train_tasks/005` only. No environment source files were copied into payloads. The evaluator uses nine weighted business-result checks and gives full credit to the included gold answer.

ZH: 仅为 `task_group_004/train_tasks/005` 构建。未将环境源文件复制到 payload 中。评估器使用 9 个加权业务结果检查，并会给予随附标准答案满分。

EN: Updated 2026-06-01 to add neutral retention board `policy_codes`, including board sorting, exposure formula, and calendar policy codes for train-to-test transfer.

ZH: 2026-06-01 更新：增加中性留存看板 `policy_codes`，包括看板排序、敞口公式和日历政策编码，用于训练到测试迁移。
