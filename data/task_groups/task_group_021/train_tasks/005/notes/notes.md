# Train 005 — February Freight Accrual Cleanup

## English

### Problem and materials

This task cleans February freight charges before accrual close. Shared freight, alias, unit, FX, snapshot, schema, and query interfaces expose noisy service descriptions, duplicate invoice lines, mixed weight and distance units, multiple currencies, and invalid or ambiguous records.

### Solution basis

Select and deduplicate the authoritative charge population, resolve effective aliases with token boundaries, retain expected-versus-actual mismatches as valid exceptions, quarantine ambiguous or invalid charges, normalize weight, distance, and spend, and route every retained charge through the controlled source and ledger decisions.

### Transfer value and pitfalls

The task reinforces train 002's reference and normalization conventions in freight. It adds invoice-line deduplication, service-class recognition, carrier exposure, and accrual routing. Common mistakes collapse mismatch into quarantine, use the wrong effective reference, or aggregate before deduplication and eligibility checks.

### Evaluation

Eight exact whole-point gates use weights `1,3,2,2,2,2,2,2`. Complete deterministic business outcomes are required for each point; there is no within-point fractional credit.

## 中文

### 问题与材料

本任务在应计结账前清洗二月份货运费用。共享货运、别名、单位、汇率、快照、模式和查询接口提供噪声服务描述、重复发票行、混合重量与距离单位、多币种以及非法或歧义记录。

### 解题依据

选择并去重权威费用群体，按生效时间和词边界解析别名，把预期与实际类别不匹配保留为有效异常，隔离歧义或非法费用，统一重量、距离和金额，并按受控来源与台账规则路由每笔保留费用。

### 迁移价值与易错点

该题在货运场景中强化 train 002 的参考与归一化约定，并增加发票行去重、服务类别识别、承运商暴露和应计路由。常见错误是把不匹配等同于隔离、使用错误生效参考，或在去重和资格检查前汇总。

### 评测

八个精确整点门槛的权重为 `1,3,2,2,2,2,2,2`。每个评分点都要求完整确定性业务结果，不提供点内比例得分。
