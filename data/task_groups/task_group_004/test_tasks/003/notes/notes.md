# Q4 North America Operations Digest Notes

## Data lineage / 数据血缘

EN: The task is built from the ApexCloud Retention Operations API dataset in `task_group_004/env/data`. The answer uses North America Q4 A/R aging rows from `ar_aging.json`, CRM account identity from `accounts.json`, North America Q4 opportunities from `opportunities.json`, the North America Q4 HR row from `hr_summary.json`, and the Q4 `retention_summit` event row from `event_performance.json`.

ZH: 本任务基于 `task_group_004/env/data` 中的 ApexCloud Retention Operations API 数据集构建。答案使用 `ar_aging.json` 中北美第四季度应收账款账龄记录、`accounts.json` 中的 CRM 账户身份、`opportunities.json` 中北美第四季度商机、`hr_summary.json` 中北美第四季度人力记录，以及 `event_performance.json` 中第四季度 `retention_summit` 活动记录。

## Task definition / 任务定义

EN: The solver must produce a formal Q4 2026 operations digest for North America. The digest starts with customers that have A/R exposure in the older aging buckets as of 2026-12-31, ties those receivables to CRM accounts where an exact account exists, summarizes Q4 North America pipeline activity, and adds HR plus event leadership context.

ZH: 解题者需要产出 2026 年第四季度北美区域的正式运营摘要。摘要先识别 2026-12-31 时点处于较旧账龄桶的应收账款客户，再在存在精确账户匹配时关联到 CRM，随后汇总北美第四季度管道活动，并补充人力和活动层面的领导层背景。

## Scenario fit / 场景适配

EN: This fits a Revenue Operations digest because it combines aged receivables, CRM follow-up readiness, closed and open pipeline, product-line concentration, workforce context, and retention event performance in one controlled JSON response.

ZH: 该场景适合收入运营摘要，因为它把账龄应收、CRM 跟进准备度、已结与未结管道、产品线集中度、人力背景和留存活动表现整合到一个受控 JSON 响应中。

## Material map / 材料地图

EN: Solver-visible materials are `input/prompt.txt` and `input/payloads/answer_template.json`. The public service exposes endpoint families for finance A/R aging, accounts, opportunities, HR summaries, and event performance. No generated environment source files are copied into the payloads.

ZH: 解题者可见材料为 `input/prompt.txt` 和 `input/payloads/answer_template.json`。公共服务提供财务账龄、账户、商机、人力摘要和活动表现等端点族。任务没有把生成环境源文件复制到 payload 中。

## Solution and evaluation basis / 解法与评估依据

EN: The expected solution selects North America A/R rows at `as_of=2026-12-31` where `61_90 + 90_plus` is greater than zero, computes overdue balances from those two buckets, links only exact CRM legal-name matches, and assigns `collections_followup` due on 2027-01-15. Pipeline metrics use North America opportunities with close dates from 2026-10-01 through 2026-12-31: `Closed Won` and `Closed Lost` for outcomes, all other stages for open pipeline, and open-pipeline product-line totals for the dominant product line. HR headcount and unpaid claims come from the single North America Q4 HR row; event orders and revenue come from the single Q4 `retention_summit` row.

ZH: 标准答案选择 `as_of=2026-12-31`、区域为北美且 `61_90 + 90_plus` 大于零的账龄记录，用这两个账龄桶计算逾期金额，只对 CRM 法定名称精确匹配的记录进行关联，并把跟进行动设为 2027-01-15 到期的 `collections_followup`。管道指标使用关闭日期在 2026-10-01 至 2026-12-31 之间的北美商机：`Closed Won` 和 `Closed Lost` 作为结果，其他阶段作为未结管道，并按未结管道金额汇总产品线以确定主导产品线。HR 人数和未付报销额来自北美第四季度的单条 HR 记录；活动订单数和收入来自第四季度 `retention_summit` 的单条记录。

## Transfer design / 迁移设计

EN: The task transfers the `train_003` pattern to a stricter regional Q4 digest: identify the receivables trigger population, validate cross-system identity by exact legal name, calculate dated pipeline metrics, and add operating context while preserving a compact JSON contract.

ZH: 本任务把 `train_003` 的模式迁移到更严格的区域性第四季度摘要：先确定应收账款触发群体，再用精确法定名称验证跨系统身份，随后计算指定日期窗口内的管道指标，并在保持紧凑 JSON 合同的同时补充运营背景。

## Construction record / 构建记录

EN: Built for `test_003` in `task_group_004`. The files created are `input/prompt.txt`, `input/payloads/answer_template.json`, `output/answer.json`, `eval/eval.sh`, and this bilingual notes file. The evaluator accepts an optional prediction path and defaults to the task's own answer.

ZH: 本任务为 `task_group_004` 的 `test_003` 构建。创建的文件包括 `input/prompt.txt`、`input/payloads/answer_template.json`、`output/answer.json`、`eval/eval.sh` 和本双语 notes 文件。评估器接受可选预测文件路径；未传入时默认评估任务自带答案。
Updated 2026-06-01: prompt wording was tightened after direct calibration showed the original phrasing made the receivables trigger and matching rule too explicit.
ZH: 2026-06-01 更新：直接校准显示原提示过于明确地暴露了应收账款触发条件和匹配规则，因此已收紧可见提示措辞。
Updated 2026-06-01: added `task_scope` and `policy_audit` fields so scoring includes transfer-dependent source-policy and CRM matching conventions rather than only direct API aggregation.
ZH: 2026-06-01 更新：增加 `task_scope` 和 `policy_audit` 字段，使评分覆盖需要从训练任务迁移的来源政策与 CRM 匹配约定，而不仅是直接 API 聚合。
Updated 2026-06-01: further reduced prompt cueing and expanded policy audit labels after a clean direct attempt still reconstructed most aggregates from the API. Easy aggregate weights were reduced and transfer-dependent policy weights retained at high value.
ZH: 2026-06-01 更新：在一次干净直接尝试仍能从 API 重建大部分聚合值后，进一步减少提示线索并扩展政策审计标签；降低易聚合项权重，保留迁移相关政策项的高权重。
Updated 2026-06-01: added `policy_codes` aligned with `train_003`, so post-skill solvers can transfer internal code conventions learned from train answer comparison.
ZH: 2026-06-01 更新：增加与 `train_003` 对齐的 `policy_codes`，使使用训练技能的求解者可迁移从训练答案对比中学到的内部编码约定。
Updated 2026-06-01: changed policy codes to neutral internal enum values after direct solvers inferred the earlier semantic code labels.
ZH: 2026-06-01 更新：直接求解者能从早期语义化编码标签中推断答案，因此将政策编码改为中性内部枚举值。
