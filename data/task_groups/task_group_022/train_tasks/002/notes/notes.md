# train_002 Notes

## English

Lineage: This task instantiates the customer-impacting defect analytics family from the API-mediated SQL task group. It uses the shared operations analytics SQLite database and focuses on HelioSync tickets created in March 2026.

Task definition: The solver must produce a JSON rollup for `HELIOSYNC` tickets created from `2026-03-01 00:00:00` through the end of `2026-03-31`. The hidden qualification basis is customer-impacting defect work for external non-test accounts: include defect categories `bug`, `outage`, `performance`, and `data_loss`; require `customer_impact = 1`; exclude canceled tickets; exclude duplicate tickets; exclude internal or test accounts. Churned external accounts remain customer accounts for this task.

Scenario fit: The task exercises schema discovery, joins between tickets and accounts, timestamp filtering, duplicate handling, SLA math, and stable ranking. The prompt is intentionally business-like and does not expose the hidden filtering conventions.

Material map: Solver-visible material is `input/prompt.txt` and `input/payloads/answer_template.json`. The standard answer is stored in `output/answer.json`. The evaluator in `eval/evaluate.py` recomputes the expected answer from the shared DB through SQL and compares structured fields.

Solution and evaluation basis: The qualified ticket set contains 10 tickets. `p1_p2_open_count` is 0. SLA breach rate counts tickets closed after `sla_due_at` plus open qualified tickets already past due by the end of March, giving `0.7000`. Median close hours is computed over closed qualified tickets only and rounded to `115.71`. Top accounts are the top 5 by qualified ticket count, then account ID.

Transfer design: This train task teaches customer defect filtering, duplicate exclusion, canceled-ticket exclusion, account noise exclusion, SLA breach treatment, and account ranking. The same conventions transfer to later hidden defect reliability tasks with different products, windows, and incident links.

Construction record: Built under `task_group/task_group_022/train_tasks/002/` only. No environment files, sibling task folders, manifests, or scratch design files were modified.

## 中文

血缘说明：本任务来自通过本地 API 暴露 SQL 查询能力的任务组中的“客户影响缺陷分析”工作流，使用共享的运营分析 SQLite 数据库，分析 2026 年 3 月创建的 HelioSync 工单。

任务定义：解题者需要针对 `HELIOSYNC` 在 `2026-03-01 00:00:00` 到 `2026-03-31` 结束期间创建的工单输出 JSON 汇总。隐藏口径是外部非测试客户的客户影响缺陷：包含 `bug`、`outage`、`performance`、`data_loss` 类别；要求 `customer_impact = 1`；排除取消工单、重复工单、内部或测试账号。已流失但属于外部客户的账号在本任务中仍视为客户账号。

场景适配：本任务考察表结构发现、tickets 与 accounts 关联、时间窗口过滤、重复工单处理、SLA 计算和稳定排序。提示词保持业务请求风格，不暴露隐藏过滤规则。

材料地图：解题可见材料是 `input/prompt.txt` 和 `input/payloads/answer_template.json`。标准答案保存在 `output/answer.json`。`eval/evaluate.py` 通过 SQL 从共享数据库重新计算期望结果，并对结构化字段评分。

答案与评估依据：合格工单集合包含 10 张工单。`p1_p2_open_count` 为 0。SLA 违约率统计关闭时间晚于 `sla_due_at` 的工单，以及截至 3 月底仍未关闭且已超期的合格工单，结果为 `0.7000`。关闭耗时中位数只基于已关闭的合格工单，四舍五入为 `115.71` 小时。Top accounts 取合格工单数最高的前 5 个账号，并按账号 ID 打破并列。

迁移设计：该训练任务传递客户缺陷过滤、重复排除、取消排除、账号噪声排除、SLA 违约处理和账号排名规则。这些规则可迁移到后续隐藏缺陷可靠性任务，但产品、时间窗口和事故关联会变化。

构建记录：仅在 `task_group/task_group_022/train_tasks/002/` 下构建。未修改环境文件、其他任务目录、manifest 或 scratch 设计文件。
