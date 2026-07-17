# Churn Model Deployment Shortlist Notes

## English

### Data lineage

This task uses the ApexCloud Retention Operations churn exports from the shared environment: `churn_train.csv`, `churn_validation.csv`, and `churn_candidates.csv`. The account segment check for the shortlisted cohort is grounded in `accounts.json`; the shortlist itself is produced from the churn candidate export.

### Task definition

The solver is asked to validate the churn model export and return a deployment-oriented report plus the top six accounts from a fixed candidate subset. The visible prompt names the API endpoints and candidate IDs but does not disclose the construction-only model settings, encodings, or training procedure.

### Scenario fit

The scenario fits Analytics Ops and enterprise renewal workflows: the validation result gives model readiness context, while the ordered shortlist gives the renewal team a compact account queue with probability, risk, action, and reason labels.

### Material map

- `input/prompt.txt`: solver-visible business request and candidate list.
- `input/payloads/answer_template.json`: required JSON shape and enum examples.
- `output/answer.json`: deterministic reference answer.
- `eval/eval.sh`: exact-match evaluator for the nine weighted business-result checks.

### Solution and evaluation basis

The deterministic test-task churn procedure uses all 19 exported feature columns, 180 training rows, and 60 validation rows. Validation accuracy is 93.3%, the accuracy band is `90_plus`, and the fitted tenure coefficient is negative. The top six candidates by predicted churn probability are `acct_bayside_bio`, `acct_helios`, `acct_valence`, `acct_westport`, `acct_apexia`, and `acct_southridge`. Probabilities are rounded to three decimals, percentages to one decimal, and cohort checks are based on the same top-six shortlist.

### Transfer design

This task transfers the churn-export handling from the train anchor while changing the candidate subset, required list length, top-level schema, and deployment-readiness fields. It also adds risk levels and enterprise-or-strategic cohort counting so solvers must combine the model output with customer account context.

### Construction record

Created the five required task files under `test_tasks/004/` only. The evaluator defaults to the task's own answer and accepts an optional prediction JSON path as its first argument.

## 中文

### 数据血缘

本任务使用共享环境中的 ApexCloud Retention Operations 流失模型导出数据：`churn_train.csv`、`churn_validation.csv` 和 `churn_candidates.csv`。入围队列的客户分层校验来自 `accounts.json`，候选排序来自流失候选导出文件。

### 任务定义

求解者需要验证流失模型导出结果，并返回可部署的验证报告以及固定候选集合中的前六名客户。可见提示给出 API 端点和候选客户 ID，但不暴露构造阶段专用的模型参数、编码方式或训练流程。

### 场景适配

该场景适合 Analytics Ops 与企业续约团队：验证报告提供模型上线判断，排序名单为续约团队提供带概率、风险、行动和原因标签的精简客户队列。

### 材料映射

- `input/prompt.txt`：求解者可见的业务请求和候选名单。
- `input/payloads/answer_template.json`：要求的 JSON 结构和枚举示例。
- `output/answer.json`：确定性的参考答案。
- `eval/eval.sh`：针对九个加权业务结果检查的精确匹配评估器。

### 解法与评估依据

确定性的测试任务流程使用 19 个导出特征列、180 条训练记录和 60 条验证记录。验证准确率为 93.3%，准确率分段为 `90_plus`，拟合出的 tenure 系数方向为负。按预测流失概率排序的前六名为 `acct_bayside_bio`、`acct_helios`、`acct_valence`、`acct_westport`、`acct_apexia` 和 `acct_southridge`。概率保留三位小数，百分比保留一位小数，队列校验基于同一前六名名单。

### 迁移设计

本任务继承训练锚点中的流失导出处理方式，同时更换候选集合、返回名单长度、顶层结构和部署建议字段。它还增加了风险等级以及 Enterprise 或 Strategic 客户计数，要求求解者把模型结果与客户上下文结合起来。

### 构造记录

仅在 `test_tasks/004/` 下创建了五个必需任务文件。评估器默认评估本任务自己的答案，也支持将预测 JSON 路径作为第一个参数传入。

English update 2026-06-01: added neutral `model_policy_codes` aligned with train_004 and consolidated evaluator policy scoring into two business-result points.

中文更新 2026-06-01：增加与 train_004 对齐的中性 `model_policy_codes`，并将评估器中的政策编码评分合并为两个业务结果点。
