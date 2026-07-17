# Hidden Notes: test_003

## English

This task belongs to `task_group_005` for `SCN_005_erp_finance_expense_control`, using source examples `E001`, `E002`, and especially `E003` for prepaid amortization and GL close reconciliation. The task-builder brief is the April prepaid reconciliation test task: a controller-facing close review over shared ERP finance records, scoped by a small local invoice list but solved through the runner-provided shared API.

Solver-visible inputs are `input/prompt.txt`, `input/payloads/prepaid_april_scope.json`, and `input/payloads/answer_template.json`. The scope payload gives only the entity, period, accounts, and ten target invoice IDs. It does not provide the amortization schedule, GL balances, exception flags, priority rules, scoring weights, or answer values. The shared environment records used for construction are prepaid invoices and GL balances exposed through the finance API; the hidden standard answer is stored in `output/answer.json`.

The business task is to reconcile Aurisic US April 2025 prepaid activity for accounts `1250` and `1251`. The selected invoices are `PPD-2025-0025` through `PPD-2025-0034`. The expected output includes the selected invoice population, account rollups, invoice-level prepaid results, default or missing-term invoice IDs, all exception invoice IDs, the controller priority list, and final close status. Account `1250` is Prepaid Expenses and account `1251` is Prepaid Insurance.

The solution uses the selected invoice records only. Monthly amortization is taken from the source invoice records for active service months through April. The account rollup sums original amount, April amortization, cumulative amortization through April, and schedule ending balance. GL ending balances are the April 2025 ledger balances for the same entity and accounts. Variance amount is `schedule_ending_balance - gl_ending_balance`, matching the train prepaid-close convention.

Standard account results: account `1250` has 8 selected invoices, original amount `355994.61`, April amortization `74359.00`, cumulative amortization `183211.32`, schedule ending balance `172783.29`, GL ending balance `559377.61`, and variance `-386594.32`. Account `1251` has 2 selected invoices, original amount `179263.83`, April amortization `22404.79`, cumulative amortization `74686.88`, schedule ending balance `104576.95`, GL ending balance `369976.70`, and variance `-265399.75`. Both accounts require reconciliation.

The default or missing-term invoice set is `PPD-2025-0025` and `PPD-2025-0033`. The full exception invoice set is `PPD-2025-0025`, `PPD-2025-0027`, `PPD-2025-0031`, `PPD-2025-0032`, `PPD-2025-0033`, and `PPD-2025-0034`. The priority exception list is `PPD-2025-0034`, `PPD-2025-0033`, `PPD-2025-0025`, and `PPD-2025-0032`: manual override first, missing-contract items next by business impact, then rounded amount. Duplicate-only flags remain in the exception set but are not in the controller priority list. Final close status is `blocked` because both accounts have material unreconciled GL variances and priority exceptions.

The evaluator has nine exact-match scoring points with raw weights `1,1,1,1,2,2,3,3,3`, total `17`, aligned with the existing task-group rubric entry for this task. They check: period/entity/selected invoice order; account totals for `1250` and `1251`; April GL ending balances; variance amount/flag/status for both accounts; exception ID set; default or missing-term ID set; priority exception membership; priority exception ranking; and final close status. Numeric values are compared after rounding to cents. Lists are exact-order where the template requires scope or priority order, and sorted for set-like ID fields. The answer also carries invoice-level detail for auditability and schema consistency with the prepaid close family.

Transfer design: `train_003` anchors the reusable prepaid close method, especially using current API records, separating scoped schedules from full ledger balances, carrying cumulative amortization through the close month, using `schedule - GL` variance sign, mapping data-quality flags to exception sets, and treating missing contract dates as default/missing-term flags. This test changes the period, invoice population, account mix, exception combination, and priority ranking so it is not a clone. High-value scoring points that depend on transfer are the variance decision, invoice results, flag/default interpretation, priority list, and close-status judgment. Task-specific difficulty comes from querying the new April records and computing all ten invoice outcomes.

Likely model pitfalls include using all prepaid invoices instead of the scoped IDs, reversing the variance sign, treating April as a daily prorated month rather than using the source monthly amount, assuming the scoped schedule must equal the full GL balance, including duplicate-only flags in the priority list, or omitting flagged invoices from amortization totals.

Construction record: rebuilt by the clean-context task-builder owner for `task_group_005` test task `003` on 2026-06-02. Major changes were replacing mojibake Chinese notes, expanding the answer template to match the prepaid close distribution, aligning variance sign with the train anchor, adding invoice-level answer detail, and rebuilding the deterministic evaluator.

## 中文

本任务属于 `task_group_005`，对应场景 `SCN_005_erp_finance_expense_control`，来源样例包括 `E001`、`E002`，其中与本任务最相关的是 `E003` 的预付费用摊销与总账关账核对。任务构建目标是 April prepaid reconciliation test task：面向 controller 的关账复核，局部输入只限定发票范围，实际解题需要通过 runner 提供的共享 API 查询当前 ERP 财务记录。

求解者可见输入为 `input/prompt.txt`、`input/payloads/prepaid_april_scope.json` 和 `input/payloads/answer_template.json`。scope payload 只给出主体、期间、账户和 10 个目标发票 ID，不提供摊销明细、GL 余额、异常 flag、优先级规则、评分权重或答案值。构造标准答案时使用的是共享财务 API 中的 prepaid invoice 和 GL balance 记录；隐藏标准答案保存在 `output/answer.json`。

业务任务是核对 Aurisic US 在 2025 年 4 月的预付费用关账情况，账户范围为 `1250` 和 `1251`。选定发票为 `PPD-2025-0025` 到 `PPD-2025-0034`。期望输出包括选定发票集合、账户汇总、发票级预付费用结果、默认或缺失合同期限发票 ID、全部异常发票 ID、controller 优先复核列表以及最终关账状态。账户 `1250` 是 Prepaid Expenses，账户 `1251` 是 Prepaid Insurance。

解法只使用选定发票记录。月摊销额来自发票源记录，并按截至 4 月的有效服务月份累计。账户汇总需要合计原始金额、April amortization、through April 的累计摊销额和 schedule ending balance。GL ending balance 使用同一主体和账户在 2025 年 4 月的总账余额。variance amount 定义为 `schedule_ending_balance - gl_ending_balance`，与训练任务中的 prepaid close 约定一致。

标准账户结果如下：账户 `1250` 有 8 张选定发票，原始金额 `355994.61`，April amortization `74359.00`，累计摊销 `183211.32`，schedule ending balance `172783.29`，GL ending balance `559377.61`，variance `-386594.32`。账户 `1251` 有 2 张选定发票，原始金额 `179263.83`，April amortization `22404.79`，累计摊销 `74686.88`，schedule ending balance `104576.95`，GL ending balance `369976.70`，variance `-265399.75`。两个账户都需要 reconciliation。

默认或缺失合同期限发票集合为 `PPD-2025-0025` 和 `PPD-2025-0033`。全部异常发票集合为 `PPD-2025-0025`、`PPD-2025-0027`、`PPD-2025-0031`、`PPD-2025-0032`、`PPD-2025-0033` 和 `PPD-2025-0034`。优先异常列表为 `PPD-2025-0034`、`PPD-2025-0033`、`PPD-2025-0025`、`PPD-2025-0032`：manual override 最高，其次是按业务影响排序的 missing-contract 项，再其次是 rounded amount。只有 duplicate flag 的发票仍属于异常集合，但不进入 controller priority list。最终关账状态为 `blocked`，原因是两个账户都有重大未调节 GL 差异并且存在优先异常。

评估器包含 9 个精确匹配评分点，原始权重为 `1,1,1,1,2,2,3,3,3`，总权重 `17`，与当前 task-group rubric 中本任务的条目保持一致。评分内容包括：period/entity/selected invoice 顺序；`1250` 和 `1251` 的账户合计；April GL ending balance；两个账户的 variance amount/flag/status；异常 ID 集合；默认或缺失期限 ID 集合；优先异常成员集合；优先异常排序；最终 close status。金额按 cents 四舍五入后比较。需要顺序的列表按模板要求精确匹配，集合型 ID 字段排序后比较。标准答案同时保留发票级明细，用于审计和保持 prepaid close 任务族的 schema 一致性。

迁移设计：`train_003` 提供可迁移的 prepaid close 方法，包括使用当前 API 记录、区分 scoped schedule 与完整 GL balance、累计到关账月份、使用 `schedule - GL` 的差异方向、把 data-quality flags 转换为 exception set，以及把 missing contract dates 识别为 default/missing-term flags。本测试任务更换了期间、发票群体、账户组合、异常组合和优先级排序，因此不是训练任务的简单复制。高价值迁移评分点包括差异结论、发票级结果、flag/default 判断、优先级列表和 close status。任务自身难度来自查询新的 April 记录并计算 10 张发票的完整结果。

常见错误包括使用全部 prepaid invoices 而不是 scoped IDs、反转 variance 符号、把 April 按日分摊而不是使用源记录中的 monthly amount、误以为 scoped schedule 必须等于完整 GL balance、把只有 duplicate flag 的发票放入 priority list，或者在摊销汇总中排除带 flag 的发票。

构造记录：由 `task_group_005` test task `003` 的 clean-context task-builder owner 于 2026-06-02 重建。主要变更包括修复乱码中文说明、扩展 answer template 以匹配 prepaid close 任务分布、将 variance 符号与训练锚点统一、增加发票级标准答案细节，并重建确定性评估器。
