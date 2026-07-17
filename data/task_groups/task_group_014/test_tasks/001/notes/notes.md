# test_001 Notes: Cross-state authorization queue audit

## English

### Purpose

This formal test task asks a UM supervisor to audit the `test_intake_batch` authorization queue through the shared SQL service. It is not a tutorial: the prompt gives the business rules and controlled output values, while solvers must discover the necessary rows and reference data through `<TASK_ENV_BASE_URL>/query`.

### Data lineage

Target cases come from `authorization_requests.target_bucket = 'test_intake_batch'`:

- `AUTH00013`
- `AUTH00014`
- `AUTH00015`
- `AUTH00016`
- `AUTH00017`
- `AUTH00018`

The answer is derived from joins across `authorization_requests`, `auth_lines`, `members`, `plans`, `providers`, `facilities`, `service_codes`, `state_sla_rules`, and `existing_authorizations`.

### Solution basis

The first-failure intake order is active coverage, covered service, servicing-provider network or exception, facility service area, prior-authorization requirement, and duplicate check. SLA due times use the most restrictive applicable state rule among the plan, member residence, and facility state for the plan type. Gold-card auto-approval is evaluated only when no earlier intake halt applies.

Expected high-level results:

- `AUTH00013` and `AUTH00015` are ready for clinical review.
- `AUTH00014` halts for out-of-network servicing provider without exception; an expired prior authorization is ignored.
- `AUTH00016` halts for an open overlapping duplicate authorization.
- `AUTH00017` and `AUTH00018` halt at the noncovered-service gate before later network or facility issues matter.
- No case qualifies for gold-card auto-approval.

Reason-code fields use compact operational audit labels rather than prose. Clear cases name the routing driver, earlier intake halts name the halt category, duplicate codes distinguish no prior match, open overlap, and duplicate-not-checked-after-benefit-halt situations, and SLA basis codes use `STATE_PlanType_daytype_Nd`.

### Transfer anchors

- `train_001`: transfers first-failure intake order, duplicate handling, SLA source selection, gold-card exclusions, and notice counting.
- `train_002`: transfers queue implications once a case clears intake, especially mandatory MD review and delegated vendor routing.

### Scoring goals

The evaluator uses ten exact-match structured business-result points:

- first-failure and final disposition by case, raw weight 2;
- SLA due timestamp and rule source by case, raw weight 1;
- gold-card posture and queue destination, raw weight 1;
- duplicate treatment plus existing-authorization trace, raw weight 3;
- notice and ready-for-review summary metrics, raw weight 1;
- SLA source and candidate-rule trace, raw weight 3;
- intake source barrier trace, raw weight 1;
- intake reason codes, raw weight 3;
- duplicate reason codes, raw weight 3;
- SLA basis codes, raw weight 3.

### Construction record

The construction-visible database was inspected directly to compute the canonical answer. Solver-visible files disclose the fixed synthetic Basic Auth credentials but do not include machine-specific host, port, or database-path details.

## 中文

### 目的

这个正式测试任务要求 UM 主管通过共享 SQL 服务审核 `test_intake_batch` 授权队列。它不是教程：提示只提供业务规则和受控输出值，解题者必须通过 `<TASK_ENV_BASE_URL>/query` 查询所需行和参考数据。

### 数据来源

目标病例来自 `authorization_requests.target_bucket = 'test_intake_batch'`：

- `AUTH00013`
- `AUTH00014`
- `AUTH00015`
- `AUTH00016`
- `AUTH00017`
- `AUTH00018`

答案基于 `authorization_requests`、`auth_lines`、`members`、`plans`、`providers`、`facilities`、`service_codes`、`state_sla_rules` 和 `existing_authorizations` 的关联查询。

### 解题依据

准入审核的首个失败点顺序为：会员覆盖有效性、服务是否为覆盖福利、服务提供者是否在网内或有例外、机构是否在服务区域内、服务是否需要 PA、重复授权检查。SLA 到期时间使用计划、会员居住州和机构州中对该计划类型适用且最严格的州规则。只有没有更早准入暂停时，才评估 gold-card 自动批准。

预期高层结果：

- `AUTH00013` 和 `AUTH00015` 可以进入临床审核。
- `AUTH00014` 因服务提供者不在网内且无例外而暂停；过期的既往授权被忽略。
- `AUTH00016` 因存在开放且日期重叠的重复授权而暂停。
- `AUTH00017` 和 `AUTH00018` 在非覆盖服务关口暂停，后续网络或机构问题不再改变首个失败点。
- 没有病例符合 gold-card 自动批准。

原因代码字段使用紧凑的运营审计标签，而不是解释性句子。通过准入的病例标明路由驱动因素；较早准入暂停的病例标明暂停类别；重复授权代码区分无既往匹配、开放重叠以及因福利暂停未继续检查重复授权；SLA basis 代码使用 `STATE_PlanType_daytype_Nd` 格式。

### 迁移锚点

- `train_001`：迁移首个失败点顺序、重复授权处理、SLA 来源选择、gold-card 排除和通知计数。
- `train_002`：迁移通过准入后的队列含义，特别是强制 MD 审核和委托供应商路由。

### 评分目标

评估器使用十个精确匹配的结构化业务结果点：

- 每个病例的首个失败点和最终处置，原始权重 2；
- 每个病例的 SLA 到期时间和规则来源，原始权重 1；
- gold-card 状态和队列目的地，原始权重 1；
- 重复授权处理和既往授权追踪，原始权重 3；
- 通知和可进入审核汇总指标，原始权重 1；
- SLA 来源和候选规则追踪，原始权重 3；
- 准入来源障碍追踪，原始权重 1；
- 准入原因代码，原始权重 3；
- 重复授权原因代码，原始权重 3；
- SLA basis 代码，原始权重 3。

### 构建记录

构建时直接检查了 construction-visible 数据库来计算标准答案。面向解题者的文件公开固定合成 Basic Auth 凭据，但不包含机器相关的主机、端口或数据库路径信息。
