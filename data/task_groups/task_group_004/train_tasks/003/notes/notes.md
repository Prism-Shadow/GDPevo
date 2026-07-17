# Q3 Receivables And Pipeline Operations Review Notes

## Data lineage / 数据血缘

EN: The task is built from the ApexCloud Retention Operations API dataset in `task_group_004/env/data`. The answer uses A/R aging rows from `ar_aging.json`, CRM account identity from `accounts.json`, pipeline rows from `opportunities.json`, all-region HR context from `hr_summary.json`, and `apex_connect` event context from `event_performance.json`.

ZH: 本任务基于 `task_group_004/env/data` 中的 ApexCloud Retention Operations API 数据集构建。答案使用 `ar_aging.json` 的应收账款账龄记录、`accounts.json` 的 CRM 账户身份、`opportunities.json` 的商机流水、`hr_summary.json` 的全区域人力运营上下文，以及 `event_performance.json` 中 `apex_connect` 的活动表现数据。

## Task definition / 任务定义

EN: The solver must produce a Q3 2026 operations review for all regions. The review starts with customers that have A/R exposure in the older aging buckets as of 2026-09-30, then summarizes CRM opportunities with close dates from 2026-07-01 through 2026-09-30, and adds HR plus event operating context.

ZH: 解题者需要产出 2026 年第三季度、全区域范围的运营复盘。复盘先从 2026-09-30 时点处于较旧账龄桶的应收账款客户开始，再汇总 2026-07-01 至 2026-09-30 关闭日期范围内的 CRM 商机，并补充人力与活动运营背景。

## Scenario fit / 场景适配

EN: This fits a Revenue Operations closeout review because it combines collections follow-up volume, CRM linkage quality, pipeline outcomes, open pipeline exposure, workforce context, and event performance in one controlled JSON output.

ZH: 该场景适合收入运营季度收尾复盘，因为它把催收跟进规模、CRM 关联质量、商机结果、未结商机风险、人力背景和活动表现整合到一个受控 JSON 输出中。

## Material map / 材料地图

EN: Solver-visible materials are the prompt and `answer_template.json`. The public service exposes endpoint families for finance A/R aging, accounts, opportunities, HR summaries, and event performance. No generated source files are copied into the payloads.

ZH: 解题者可见材料包括提示词和 `answer_template.json`。公共服务提供财务账龄、账户、商机、人力摘要和活动表现等端点族。任务没有把生成环境源文件复制到 payload 中。

## Solution and evaluation basis / 解法与评估依据

EN: The expected solution selects A/R rows at `as_of=2026-09-30` where `61_90 + 90_plus` is greater than zero, computes overdue balances from those two buckets, links only rows that correspond to CRM accounts, and assigns `collections_followup` due on 2026-10-15. Pipeline metrics use opportunities with close dates inside Q3 2026: Closed Won and Closed Lost for outcomes, all other stages for open pipeline, and product-line aggregation for the top open product line. HR headcount and unpaid claims are summed across all Q3 rows; event orders and revenue come from the single `apex_connect` Q3 row.

ZH: 标准答案选择 `as_of=2026-09-30` 且 `61_90 + 90_plus` 大于零的账龄记录，用这两个账龄桶计算逾期金额，只对可对应 CRM 账户的记录进行关联，并把跟进动作设为 2026-10-15 到期的 `collections_followup`。商机指标使用关闭日期落在 2026 年第三季度的记录：Closed Won 和 Closed Lost 作为输赢结果，其他阶段作为未结管道，并按产品线汇总得到最大未结产品线。HR 人数和未付报销额跨所有 Q3 区域行求和；活动订单数和收入来自 `apex_connect` 的单条 Q3 记录。

## Transfer design / 迁移设计

EN: The task transfers to other operations-review problems by preserving the same reasoning pattern: start with a trigger population, validate cross-system identity linkage, calculate dated pipeline metrics, then add auxiliary operating context without changing the required JSON contract.

ZH: 该任务可迁移到其他运营复盘问题：先确定触发人群，再验证跨系统身份关联，随后计算指定日期窗口内的管道指标，最后补充辅助运营背景，同时保持 JSON 合同不变。

## Construction record / 构建记录

EN: Built for `train_003` in `task_group_004`. The files created are `input/prompt.txt`, `input/payloads/answer_template.json`, `output/answer.json`, `eval/eval.sh`, and this bilingual notes file. The evaluator accepts an optional prediction path and defaults to the task's own answer.

ZH: 本任务为 `task_group_004` 的 `train_003` 构建。创建的文件包括 `input/prompt.txt`、`input/payloads/answer_template.json`、`output/answer.json`、`eval/eval.sh` 和本双语 notes 文件。评估器接受可选预测文件路径；未传入时默认评估任务自带答案。
Updated 2026-06-01: added `policy_codes` to make the operations-review SOP explicit to train-skill comparison without leaking it into test prompts.
ZH: 2026-06-01 更新：增加 `policy_codes`，让训练答案对技能提炼暴露运营复盘 SOP 编码，但不在测试提示中泄露。
Updated 2026-06-01: changed policy codes from semantic labels to neutral internal enum values so they are learnable from train comparison rather than obvious from the test template.
ZH: 2026-06-01 更新：将政策编码从语义化标签改为中性的内部枚举值，使其需要通过训练答案对比学习，而不是从测试模板中直接看出。
