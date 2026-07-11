# test_002 Notes

## English

Lineage: This task instantiates the customer-impacting defect analytics family from the API-mediated SQL task group. It uses the shared operations analytics SQLite database and focuses on AtlasDB tickets created in 2026 Q2.

Task definition: The solver must produce a JSON reliability rollup for `ATLASDB` tickets created from `2026-04-01 00:00:00` through the end of `2026-06-30`. The hidden qualification basis is customer-impacting defect work for external non-test accounts: include defect categories `bug`, `outage`, `performance`, and `data_loss`; require `customer_impact = 1`; exclude canceled tickets; exclude duplicate tickets; exclude internal or test accounts. Churned external accounts remain customer accounts for this task. Incident-linked counts are computed only within the qualified ticket set.

Scenario fit: The task exercises schema discovery, joins between tickets and accounts, timestamp filtering, duplicate and cancellation handling, account noise exclusion, SLA math, incident linkage, and stable account ranking. The prompt is intentionally business-like and does not expose the hidden filtering conventions.

Material map: Solver-visible material is `input/prompt.txt` and `input/payloads/answer_template.json`. The standard answer is stored in `output/answer.json`. The evaluator in `eval/evaluate.py` recomputes the expected answer from the shared DB through SQL and compares structured fields.

Solution and evaluation basis: The qualified ticket set contains 52 tickets. The incident-linked qualified subset contains 12 tickets. `p1_p2_open_count` is 2. SLA breach rate counts tickets closed after `sla_due_at` plus open qualified tickets already past due by the end of Q2, giving `0.8077`. Top accounts are the top 5 by qualified ticket count, then account ID. Exclusion counts are condition counts inside the AtlasDB Q2 ticket window, matching the established train defect task pattern rather than a disjoint funnel.

Transfer design: This test task reuses the train defect conventions for customer-impacting ticket qualification, duplicate and canceled exclusions, account filtering, SLA breach treatment, and account ranking. It changes the product, period, scale, and adds incident-linked ticket accounting.

Construction record: Built under `task_group/task_group_022/test_tasks/002/` only. No environment files, sibling task folders, manifests, or scratch design files were modified.

## 中文

血缘说明：本任务来自通过本地 API 暴露 SQL 查询能力的任务组中的“客户影响缺陷分析”工作流，使用共享的运营分析 SQLite 数据库，分析 2026 年第二季度创建的 AtlasDB 工单。

任务定义：解题者需要针对 `ATLASDB` 在 `2026-04-01 00:00:00` 到 `2026-06-30` 结束期间创建的工单输出 JSON 可靠性汇总。隐藏口径是外部非测试客户的客户影响缺陷：包含 `bug`、`outage`、`performance`、`data_loss` 类别；要求 `customer_impact = 1`；排除取消工单、重复工单、内部或测试账号。已流失但属于外部客户的账号在本任务中仍视为客户账号。事故关联数量只在合格工单集合内计算。

场景适配：本任务考察表结构发现、tickets 与 accounts 关联、时间窗口过滤、重复和取消处理、账号噪声排除、SLA 计算、事故关联和稳定账号排名。提示词保持业务请求风格，不暴露隐藏过滤规则。

材料地图：解题可见材料是 `input/prompt.txt` 和 `input/payloads/answer_template.json`。标准答案保存在 `output/answer.json`。`eval/evaluate.py` 通过 SQL 从共享数据库重新计算期望结果，并对结构化字段评分。

答案与评估依据：合格工单集合包含 52 张工单。合格集合中的事故关联子集包含 12 张工单。`p1_p2_open_count` 为 2。SLA 违约率统计关闭时间晚于 `sla_due_at` 的工单，以及截至第二季度末仍未关闭且已超期的合格工单，结果为 `0.8077`。Top accounts 取合格工单数最高的前 5 个账号，并按账号 ID 打破并列。排除计数是在 AtlasDB 第二季度工单窗口内按条件分别计数，与训练缺陷任务的既有模式一致，不是互斥漏斗。

迁移设计：该测试任务复用训练缺陷任务中的客户影响工单资格、重复排除、取消排除、账号过滤、SLA 违约处理和账号排名规则。变化点是产品、时间窗口、数据规模，以及新增事故关联工单统计。

构建记录：仅在 `task_group/task_group_022/test_tasks/002/` 下构建。未修改环境文件、其他任务目录、manifest 或 scratch 设计文件。
