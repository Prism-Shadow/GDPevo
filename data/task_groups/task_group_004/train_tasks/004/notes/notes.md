# Churn Model Validation And Outreach Ranking Notes

## EN - Data lineage

The task uses the ApexCloud Retention Operations churn exports exposed by the shared environment: `/exports/churn/train.csv`, `/exports/churn/validation.csv`, and `/exports/churn/candidates.csv`. The row counts are taken from the public export files, and the model-validation answer is computed from the training and validation exports using the construction-only deterministic churn procedure.

## ZH - 数据血缘

本任务使用共享环境提供的 ApexCloud Retention Operations 流失预测导出文件：`/exports/churn/train.csv`、`/exports/churn/validation.csv` 和 `/exports/churn/candidates.csv`。行数来自公开导出文件，模型验证答案按照构造阶段规定的确定性流失建模流程计算。

## EN - Task definition

The visible request asks Analytics Ops to validate the churn export, report model validation metrics, and rank a fixed subset of candidate accounts by predicted churn probability. The deliverable is a JSON object matching the provided answer template, with percentages rounded to 1 decimal and probabilities rounded to 3 decimals.

## ZH - 任务定义

可见请求要求 Analytics Ops 验证流失导出数据，报告模型验证指标，并对指定候选账户子集按预测流失概率排序。交付物是符合模板的 JSON，对百分比保留 1 位小数，对概率保留 3 位小数。

## EN - Scenario fit

This is a practical retention-operations scenario: the team needs confidence that the exported churn data is usable and needs a short outreach queue for customer-success action. The task combines dataset validation, coefficient sanity checking, candidate ranking, and operational action assignment.

## ZH - 场景适配

该任务符合真实留存运营场景：团队需要确认流失导出数据可用，并生成一份简短的客户成功外联队列。任务结合了数据集验证、系数方向检查、候选排序和运营动作分配。

## EN - Material map

- `input/prompt.txt`: solver-facing business request and candidate subset.
- `input/payloads/answer_template.json`: required JSON shape.
- `output/answer.json`: deterministic reference answer.
- `eval/eval.sh`: exact-match business-result evaluator with an optional prediction path.
- Environment exports: source CSVs served by the local API.

## ZH - 材料地图

- `input/prompt.txt`：面向解题者的业务请求和候选账户范围。
- `input/payloads/answer_template.json`：要求的 JSON 结构。
- `output/answer.json`：确定性参考答案。
- `eval/eval.sh`：可接受可选预测路径的业务结果精确匹配评估器。
- 环境导出文件：由本地 API 提供的源 CSV。

## EN - Solution and evaluation basis

The reference result uses 180 training rows, 60 validation rows, and 19 model features. The validation accuracy is 93.3%, placing it in the `90_plus` band, and the tenure coefficient direction is negative. The ranked top five are `acct_tandemworks`, `acct_northstar_finance`, `acct_northstar_retail`, `acct_globex_north`, and `acct_valence`. Evaluation awards eight weighted business-result checks for counts, accuracy, coefficient direction, ordering, probabilities, actions with reason codes, cohort checks, and neutral model-policy codes.

## ZH - 解法与评估依据

参考结果使用 180 行训练数据、60 行验证数据和 19 个模型特征。验证准确率为 93.3%，属于 `90_plus` 档位，tenure 系数方向为负。前五名依次为 `acct_tandemworks`、`acct_northstar_finance`、`acct_northstar_retail`、`acct_globex_north` 和 `acct_valence`。评估器按八个加权业务结果检查计分，包括行数与特征数、准确率、系数方向、排序、概率、动作与原因码、群组检查，以及中性模型政策编码。

## EN - Transfer design

This train task teaches solvers how to handle churn exports, verify feature counts, check whether tenure behaves in the expected business direction, rank a selected candidate cohort, and preserve probability precision. Those behaviors transfer to test tasks that use the same export family with different candidate subsets or longer training settings.

## ZH - 迁移设计

该训练任务帮助解题者学习如何处理流失导出、核对特征数量、检查 tenure 是否符合业务预期方向、对指定候选群体排序，并保持概率精度。这些能力可迁移到使用同类导出但候选范围或训练设置不同的测试任务。

## EN - Construction record

Created the complete task folder for train task 004 under `task_group_004/train_tasks/004/`. No files outside the assigned folder were modified. The evaluator defaults to grading `output/answer.json` and can also grade a supplied prediction file path.

## ZH - 构造记录

已在 `task_group_004/train_tasks/004/` 下创建训练任务 004 的完整任务文件夹。未修改指定目录之外的文件。评估器默认评估 `output/answer.json`，也可以评估传入的预测文件路径。

## EN/ZH - Update record / 更新记录

EN: Updated 2026-06-01 to add neutral `model_policy_codes` fields for model protocol, probability scale, deployment rule, and outreach mapping transfer.

ZH: 2026-06-01 更新：增加中性的 `model_policy_codes` 字段，用于迁移模型协议、概率尺度、部署规则和外联映射约定。
