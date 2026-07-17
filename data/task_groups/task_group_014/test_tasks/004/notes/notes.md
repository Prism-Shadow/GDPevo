# test_004 Notes: Multi-clinic reimbursement benchmark audit

## English

Task purpose: This is a formal test task for a finance compliance analyst. It asks solvers to use the SQL service at `<TASK_ENV_BASE_URL>/query` and produce a structured reimbursement benchmark audit for `CLN003` and `CLN004` across 2025Q3 and 2025Q4.

Construction-visible data basis: The answer was computed from `encounters`, `members`, `rate_schedules`, and `claim_corrections` in the shared SQLite payer operations database. The audit joins encounters to members for residence state, then to the active `rate_schedules` row matching payer, plan type, service category, CPT code, state, and service date.

Scope: Clinics `CLN003` and `CLN004`; payer `Ticonderoga Health`; plan types `Commercial`, `Exchange`, and `Medicare Advantage`; service categories `Evaluation Management` and `Physical Therapy`; service dates `2025-07-01` through `2025-12-31`. The quarters are `2025Q3` and `2025Q4`.

Solution rules held outside the solver prompt: paid-rate cells exclude encounters with a denial code or non-positive paid amount. Benchmarks use only the active rate schedule for the encounter service date. Material underpayment requires underpayment amount at least `250.00` and variance at least 5 percent below benchmark. Open correction recoveries are included as recovery opportunity; submitted, pending-document, and closed-unrecovered corrections are tracked but not included in open recovery totals. Clinic risk is `high` when material underpaid cells are at least 5 or total material underpayment is at least `2500.00`, `moderate` when material underpaid cells are at least 2 or total material underpayment is at least `1000.00`, and `low` otherwise.

Transfer anchors: `train_004` transfers the active effective-date rate schedule join, weighted benchmark comparison, and denied/unpaid exclusion pattern. `train_005` transfers the habit of aggregating paid amounts separately from expected recoveries and ranking actionable financial opportunities.

Scoring design: The evaluator uses seven exact-match structured business-result points with raw weights `3, 2, 2, 2, 2, 1, 1`. The highest-weight item is active rate-source selection. The remaining items cover paid benchmark variance, material underpayment set, core audit variance totals, top-five recovery ranking, correction handling, and recovery totals.

Prompt hygiene: Solver-visible files disclose only the fixed synthetic Basic Auth credentials and do not expose hidden answer paths, evaluator scoring, localhost, runtime ports, or a full procedural SOP. The detailed construction and evaluation rules are kept in these notes and in evaluator/answer artifacts.

## 中文

任务目的：这是一个正式测试任务，角色是财务合规分析师。任务要求解题者通过 `<TASK_ENV_BASE_URL>/query` 使用 SQL 服务，为 `CLN003` 和 `CLN004` 在 2025Q3 与 2025Q4 的数据生成结构化报销基准审计结果。

构建数据依据：标准答案来自共享 SQLite 付款方运营数据库中的 `encounters`、`members`、`rate_schedules` 和 `claim_corrections`。计算时先用 encounter 关联 member 取得居住州，再按 payer、plan type、service category、CPT code、state 和 service date 关联有效期内的 `rate_schedules` 记录。

范围：诊所 `CLN003` 和 `CLN004`；付款方 `Ticonderoga Health`；计划类型 `Commercial`、`Exchange`、`Medicare Advantage`；服务类别 `Evaluation Management` 和 `Physical Therapy`；服务日期从 `2025-07-01` 到 `2025-12-31`。季度为 `2025Q3` 与 `2025Q4`。

未放入解题提示的解法规则：付费费率单元格排除带拒付代码或 paid amount 非正数的 encounter。基准费率只使用服务日期当天有效的 rate schedule。重大少付要求少付金额至少为 `250.00`，且相对基准低至少 5%。open 状态的 correction recovery 计入 recovery opportunity；submitted、pending documents 和 closed unrecovered correction 只跟踪，不计入 open recovery total。诊所风险规则为：重大少付单元格数量至少 5 个或重大少付总额至少 `2500.00` 时为 `high`；重大少付单元格数量至少 2 个或重大少付总额至少 `1000.00` 时为 `moderate`；否则为 `low`。

迁移锚点：`train_004` 迁移有效日期费率表关联、加权基准比较、拒付和未付款 encounter 排除的模式。`train_005` 迁移将 paid amount 与 expected recovery 分开汇总，并对可行动财务机会进行排序的习惯。

评分设计：评估器使用七个精确匹配的结构化业务结果评分点，原始权重为 `3, 2, 2, 2, 2, 1, 1`。最高权重点是有效 rate source 选择，其余覆盖付费与基准差异、重大少付集合、核心审计差异汇总、前五项 recovery 排名、correction 处理和 recovery 总额。

提示卫生：解题者可见文件只公开固定合成 Basic Auth 凭据，不暴露隐藏答案路径、评估器评分逻辑、localhost、运行时端口或完整 SOP。详细构建和评估规则只保留在 notes、evaluator 和 answer 文件中。
