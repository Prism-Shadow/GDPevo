# Test 004 Notes / 测试 004 说明

## Lineage / 来源

English: This task is derived from the SQL database analytics scenario for incident exposure and support aftershock analysis. It uses the shared `ops_analytics.sqlite` database and the actual HelioSync incident `INC-2026-006`.

中文：本任务来源于 SQL 数据库分析场景，聚焦事故暴露与后续工单影响分析。任务使用共享的 `ops_analytics.sqlite` 数据库，并使用真实存在的 HelioSync 事故 `INC-2026-006`。

## Task Definition / 任务定义

English: The solver must report qualified production usage on the incident calendar dates for external customer accounts in the impacted region with an active HelioSync subscription, then combine that exposure with customer-impacting defect tickets opened in the 7 days after incident resolution.

中文：解题者需要统计事故日历日期内、受影响区域中、具备有效 HelioSync 订阅的外部客户账号的合格生产用量，并结合事故解决后 7 天内创建的客户影响型缺陷工单。

## Scenario Fit / 场景契合度

English: The task exercises multi-table SQL joins over incidents, usage, accounts, subscriptions, and tickets. It tests transferable conventions from the training tasks: production-only usage, active subscription windows, external-customer filtering, backfill and telemetry overlap exclusions, customer-impacting defect ticket filtering, duplicate/canceled exclusions, and deterministic account ranking.

中文：该任务要求在 incidents、usage、accounts、subscriptions 和 tickets 多张表之间进行 SQL 关联。它检验训练任务中可迁移的规则：仅统计生产用量、订阅有效期过滤、外部客户过滤、回填和遥测重叠排除、客户影响型缺陷工单过滤、重复/取消工单排除，以及确定性的账号排序。

## Material Map / 材料映射

English: The visible prompt is `input/prompt.txt`; the required JSON contract is `input/payloads/answer_template.json`; the standard answer is `output/answer.json`; the hidden scoring implementation is `eval/evaluate.py`; the shell entry point is `eval/eval.sh`.

中文：可见提示为 `input/prompt.txt`；要求的 JSON 结构为 `input/payloads/answer_template.json`；标准答案为 `output/answer.json`；隐藏评分逻辑为 `eval/evaluate.py`；Shell 入口为 `eval/eval.sh`。

## Solution and Evaluation Basis / 解法与评分依据

English: The standard answer is computed from SQL over the shared database. Incident usage uses HelioSync rows between `date(started_at)` and `date(resolved_at)` for APAC, with external active/paused customer accounts, active/paused/trial subscription states within date bounds, production environment, no backfill, and telemetry-v1 rows removed when telemetry-v2 exists for the same account/product/date. Follow-up tickets use the APAC HelioSync 7-day post-resolution window, external active/paused customer accounts, customer impact, defect categories, non-canceled status, non-duplicate status, and active subscription coverage on ticket creation date.

中文：标准答案通过对共享数据库执行 SQL 得到。事故用量统计 HelioSync 在 `date(started_at)` 到 `date(resolved_at)` 之间的 APAC 记录，要求外部 active/paused 客户账号、日期范围内 active/paused/trial 订阅、生产环境、非回填，并在同一账号/产品/日期存在 telemetry-v2 时排除 telemetry-v1。后续工单统计事故解决后 7 天内 APAC HelioSync 工单，要求外部 active/paused 客户账号、客户影响、缺陷类别、非取消、非重复，并在工单创建日期具备有效订阅。

## Transfer Design / 迁移设计

English: The task transfers train-task usage and ticket conventions but changes the product, incident, date window, region, and final output by requiring combined exposure plus aftershock overlap and risk ranking.

中文：该任务迁移训练任务中的用量和工单规则，但更换了产品、事故、时间窗口、区域和最终输出，要求同时给出暴露、后续影响重叠和风险排序。

English: After direct calibration showed the first prompt over-disclosed the impacted-population, follow-up-window, active-subscription, and customer-impacting defect conventions, the visible prompt and answer template were tightened. The hidden evaluator still checks the same business results, but the solver-visible input now states the business request without restating the transferable SOP or the risk-score formula.

中文：直接校准发现首版提示过度暴露了受影响人群、后续窗口、有效订阅和客户影响型缺陷工单等规则，因此已收紧可见提示和答案模板。隐藏评分仍检查相同业务结果，但 solver 可见输入现在只给出业务请求，不再复述可迁移 SOP 或风险分公式。

English: A second calibration pass found that the hidden 30-day follow-up window was too far from the train incident task, whose reusable convention uses a 7-day post-resolution window. The test answer and evaluator were aligned to the 7-day transfer anchor so the train-derived skill helps rather than misleads.

中文：第二轮校准发现隐藏的 30 天后续窗口与训练事故任务距离过远；训练任务中的可复用规则使用事故解决后 7 天窗口。因此测试答案和 evaluator 已调整为 7 天迁移锚点，使训练技能能够提供帮助而不是误导。

## Construction Record / 构建记录

English: Created `test_tasks/004` only. No shared environment files, task manifests, scratch design files, or other task folders were modified. The prompt uses `<TASK_ENV_BASE_URL>` and contains no local absolute database path or procedural SQL recipe.

中文：仅创建了 `test_tasks/004`。未修改共享环境文件、任务清单、scratch 设计文件或其他任务目录。提示中使用 `<TASK_ENV_BASE_URL>`，不包含本地绝对数据库路径或过程化 SQL 步骤。
