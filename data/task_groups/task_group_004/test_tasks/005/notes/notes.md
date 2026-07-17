# Executive Retention Watchlist Notes

## Data lineage / 数据血缘

EN: The task uses the ApexCloud Retention Operations environment for Q3 2026. Account identity and segment values come from `accounts.json`; current ARR comes from the latest posted billing snapshot on or before 2026-09-30; receivables come from `ar_aging.json` matched by exact legal customer name; support health comes from clean Q3 support tickets; NPS comes from valid Q3 survey responses; usage comes from monthly account metrics; open expansion pipeline comes from open opportunities with Q3 close dates.

ZH: 本任务使用 ApexCloud Retention Operations 的 2026 年第三季度环境数据。账户身份和分层来自 `accounts.json`；当前 ARR 来自 2026-09-30 当日或之前最新已过账的账单快照；应收账款通过法定客户名称精确匹配 `ar_aging.json`；支持健康度来自第三季度清洁工单；NPS 来自第三季度有效问卷；使用率来自月度账户指标；开放扩展管道来自关闭日期在第三季度且仍未关闭的机会。

## Task definition / 任务定义

EN: The solver must create a CEO staff watchlist for ten named accounts and return the top seven by the shared retention risk score. Each row combines rank, risk score, risk level, primary action, current ARR, overdue balance, open expansion pipeline, net revenue exposure, next-touch due date, and reason-code set. The summary totals ARR at risk, overdue receivables, expansion offset, net exposure, and action counts.

ZH: 求解者需要为 10 个指定账户创建 CEO 幕僚观察名单，并按共享留存风险评分返回前 7 名。每行结合排名、风险评分、风险等级、首要行动、当前 ARR、逾期余额、开放扩展管道、净收入敞口、下一次触达日期和原因代码集合。汇总部分统计风险 ARR、逾期应收、扩展抵消、净敞口和行动数量。

## Scenario fit / 场景适配

EN: The scenario fits an executive retention review because it elevates accounts where customer health, receivables, renewal timing, usage, and pipeline offsets interact. It is intentionally leadership-oriented and focuses on ordered action rather than raw operational diagnostics.

ZH: 该场景适合高管留存复盘，因为它突出客户健康、应收款、续约时点、使用率和管道抵消相互作用的账户。任务刻意面向管理层，重点是排序后的行动，而不是原始运营诊断。

## Material map / 材料映射

EN: `input/prompt.txt` contains the visible business request and dates. `input/payloads/answer_template.json` defines the required JSON shape. `output/answer.json` is the deterministic gold answer. `eval/eval.sh` accepts an optional prediction path and otherwise evaluates the included gold answer.

ZH: `input/prompt.txt` 包含可见业务请求和日期；`input/payloads/answer_template.json` 定义必需 JSON 结构；`output/answer.json` 是确定性的标准答案；`eval/eval.sh` 接受可选预测路径，否则评估随附的标准答案。

## Solution and evaluation basis / 解法与评估依据

EN: Ranking uses score descending, then current ARR descending, then account id ascending. Current ARR uses 2026-09-30 posted billing snapshots. Overdue balance is `61_90 + 90_plus` from exact legal-name A/R rows as of 2026-09-30. Open expansion excludes Closed Won and Closed Lost opportunities and uses close dates from 2026-07-01 through 2026-09-30. Net revenue exposure is current ARR plus overdue balance minus open expansion pipeline. The evaluator checks ordered business results, risk fields, finance values, reason-code sets, due dates, action map, summary totals, and action counts.

ZH: 排序使用评分降序、当前 ARR 降序、账户 ID 升序。当前 ARR 使用 2026-09-30 已过账账单快照。逾期余额为 2026-09-30 精确法定名称 A/R 行中的 `61_90 + 90_plus`。开放扩展排除 Closed Won 和 Closed Lost，并使用 2026-07-01 至 2026-09-30 的关闭日期。净收入敞口为当前 ARR 加逾期余额再减开放扩展管道。评估器检查排序后的业务结果、风险字段、财务数值、原因代码集合、截止日期、行动映射、汇总总额和行动数量。

## Transfer design / 迁移设计

EN: This test transfers patterns from the training tasks: retention score ranking, overdue priority, billing ARR precedence, exact legal-name receivables matching, open-pipeline offsets, controlled enum labels, and executive due-date mapping.

ZH: 本测试迁移训练任务中的模式：留存评分排序、逾期优先级、账单 ARR 优先、法定名称精确匹配应收款、开放管道抵消、受控枚举标签以及高管行动截止日期映射。

## Construction record / 构建记录

EN: Constructed for `task_group_004/test_tasks/005` only. No environment source files were copied into payloads. The evaluator uses ten weighted exact-match business-result checks and gives full credit to the included gold answer.

ZH: 仅为 `task_group_004/test_tasks/005` 构建。未将环境源文件复制到 payload 中。评估器使用 10 个加权精确匹配业务结果检查，并会给予随附标准答案满分。

EN: Updated 2026-06-01 to add neutral retention board `policy_codes` aligned with train_001/train_005 and consolidate scoring to 10 business-result points.

ZH: 2026-06-01 更新：增加与 train_001/train_005 对齐的中性留存看板 `policy_codes`，并将评分合并为 10 个业务结果点。
