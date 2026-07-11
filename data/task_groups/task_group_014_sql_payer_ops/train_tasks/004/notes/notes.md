# Train 004 Notes: Clinic Reimbursement Compliance Review

## English

Task builder: `builder_train_004`

Scope: `CLN001`, `CLN002`, `2025Q1`, and `2025Q2` in the shared SQLite payer operations environment.

Construction basis:

- The solver-visible task requires use of `<TASK_ENV_BASE_URL>/query`, discloses the fixed synthetic Basic Auth credentials, and does not disclose a concrete host or port.
- The prompt is intentionally brief after integration guidance: it gives role, business goal, SQL service location, target scope payload, and output requirement only.
- The audit scope payload provides clinic states because the database has encounter clinic IDs but no clinic reference table. State is necessary for matching `rate_schedules.state`.
- The standard answer was computed from `encounters`, `rate_schedules`, and `claim_corrections`.

Solution basis:

- Active benchmark selection joins by payer, plan type, service category, CPT code, clinic state, and service date effective window.
- Paid-rate variance excludes encounters with a denial code or zero payment.
- Recovery tracking separately sums corrections for denied or unpaid encounters when correction status is `open`, `pending documents`, or `submitted`.
- Cell grain for materiality is quarter, clinic, payer, plan type, and service category.
- Material underpayment threshold is paid units at least 5, variance amount at most `-5000.00`, and variance percent at most `-0.1000`.
- Clinic-quarter classification is `high_review` when material cells are at least 3 or active tracked recovery is at least `10000.00`; `monitor` when any material cell exists, any tracked recovery exists, or overall clinic-quarter variance is at most `-0.0500`; otherwise `compliant`.

Scoring design:

- The evaluator uses eight exact-match business-result points with raw weights 1, 2, and 3.
- High-weight checks focus on flagged variance metrics and active rate schedule IDs, because those prove effective-date benchmark selection and correct encounter-level aggregation.
- Medium-weight checks cover clinic-quarter totals, excluded-denied recovery handling, and material-cell identity.
- Low-weight checks cover scope/materiality, top recovery opportunity, and summary totals.

Transfer design:

- This task trains the effective-rate-window habit needed for the test reimbursement benchmark audit.
- It also trains the separation between paid-rate compliance and denial/correction recovery, which carries into profitability and leakage tasks.

Validation record:

- Expected answer contains 10 material underpayment cells using the declared thresholds.
- Top recovery opportunity is correction `CORR000307` on encounter `ENC000307`.
- Evaluator was validated against `output/answer.json`.

## Chinese

任务构建者：`builder_train_004`

范围：共享 SQLite 付款方运营环境中的 `CLN001`、`CLN002`、`2025Q1` 和 `2025Q2`。

构建依据：

- 面向解题者的任务要求通过 `<TASK_ENV_BASE_URL>/query` 使用 SQL 服务并公开固定合成 Basic Auth 凭据，但不暴露具体主机或端口。
- 根据集成提示，prompt 已保持简洁：只包含角色、业务目标、SQL 服务位置、目标范围 payload 和输出要求。
- 审计范围 payload 提供诊所所在州，因为数据库中的 encounter 只有诊所 ID，没有单独的诊所主数据表；匹配 `rate_schedules.state` 时必须知道州。
- 标准答案来自 `encounters`、`rate_schedules` 和 `claim_corrections`。

解题依据：

- 有效基准费率按 payer、plan type、service category、CPT code、诊所州以及服务日期有效期窗口匹配。
- 已付费率差异计算排除有拒付代码或付款为零的 encounter。
- 回收金额单独统计，范围是被排除的拒付或未付 encounter 上状态为 `open`、`pending documents` 或 `submitted` 的 correction。
- materiality 的 cell 粒度是 quarter、clinic、payer、plan type 和 service category。
- material underpayment 阈值是 paid units 至少 5，variance amount 不高于 `-5000.00`，variance percent 不高于 `-0.1000`。
- 诊所季度分类规则：material cells 至少 3 个或 active tracked recovery 至少 `10000.00` 时为 `high_review`；有任一 material cell、任一 tracked recovery，或整体诊所季度 variance 不高于 `-0.0500` 时为 `monitor`；否则为 `compliant`。

评分设计：

- 评估器使用 8 个精确匹配的业务结果评分点，原始权重为 1、2、3。
- 高权重点检查 flagged variance 指标和有效 rate schedule ID，因为这些能验证是否正确选择有效期费率并进行 encounter 级聚合。
- 中权重点覆盖诊所季度汇总、拒付回收处理以及 material cell 身份集合。
- 低权重点覆盖范围和阈值、最高回收机会以及汇总总数。

迁移设计：

- 本任务训练按服务日期选择有效费率窗口的习惯，可迁移到测试集的 reimbursement benchmark audit。
- 本任务也训练 paid-rate compliance 与 denial/correction recovery 的拆分处理，可迁移到 profitability 和 leakage 类任务。

验证记录：

- 标准答案在给定阈值下包含 10 个 material underpayment cells。
- 最高回收机会是 encounter `ENC000307` 上的 correction `CORR000307`。
- 评估器已用 `output/answer.json` 验证通过。
