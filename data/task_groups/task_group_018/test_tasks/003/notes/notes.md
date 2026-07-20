# test_003 Notes

## English Review Notes

`test_003` is a Virginia Gloucester County DUI appeal post-sentencing task for `task_group_018`, derived from source scenario `SCN_018_court_clerk_disposition_orders_and_financial_entries`, especially source example `E003`. It uses target case `VA-CR25-1044-00` and payment petition `VA-PET-1044A`.

Solver-visible materials are `input/prompt.txt`, `input/payloads/appeal_sentencing_intake.json`, `input/payloads/payment_petition_and_budget.json`, `input/payloads/form_packet_excerpt.json`, and `input/payloads/answer_template.json`. The shared Court Operations Portal is referenced only through `<TASK_ENV_BASE_URL>` and supplies corroborating case, charge, form, policy, and financial-petition records. The important generated environment records are the Gloucester jurisdiction `VA-GLO`, case `VA-CR25-1044-00`, petition `VA-PET-1044A`, policy `POL-VA-GLO-FIRST`, and forms `VA_CC1375` and `VA_CC1379`.

The business task is to prepare a clerk-ready post-sentencing JSON packet after a circuit DUI appeal. The packet has four linked work products: a case memo, a CC-1375-style probation referral, a CC-1379-style license/installment order, and review lists for placeholders and excluded financial items. The task fits the group because it combines case disposition reconciliation, form field mapping, payment policy selection, budget review, monthly installment math, and disciplined non-fabrication of missing court-form data.

Material map: `appeal_sentencing_intake.json` controls the circuit appeal conviction and sentence posture: conviction on `2025-05-08`, DUI first offense under `Va. Code 18.2-266`, 30 jail days imposed with 25 suspended and 5 active, `$750.00` fine, `$230.00` costs, 6 months supervised probation, 12-month license suspension, release on `2025-05-09`, and probation report datetime `2025-05-12T09:30:00`. `payment_petition_and_budget.json` gives the first petition, `$980.00` fines/costs balance, no ordered restitution or account fee, `$60.00` requested monthly payment, household budget, a stale `$25.00` account-fee row, and an unsupported `$180.00` restitution estimate. `form_packet_excerpt.json` provides the local field groups and exact placeholder text. The environment policy confirms the Gloucester first-petition installment band of `$50.00-$100.00`, no down payment, first due after 30 days, return-to-court offset of 60 days, and no account fee.

The standard answer keeps the same sentence facts across all form sections. The case memo marks `circuit_appeal_conviction`, `2025-05-08` conviction date, `$980.00` fines/costs total, 6 months supervised probation, and 12 months license suspension. CC-1375 is `VA_CC1375` with a supervised 6-month term and `2025-05-12T09:30:00` report datetime. CC-1379 is `VA_CC1379`; the license is suspended for 12 months effective `2025-05-08`, and the driver license number remains `TBD from case file`.

The payment order is an `initial_installment` under `POL-VA-GLO-FIRST`: total due `$980.00`, fines/costs balance `$980.00`, restitution `$0.00`, account fee `$0.00`, down payment `$0.00`, monthly installment `$60.00`, first due `2025-06-08`, 16 full installments plus a final `$20.00` payment, 17 payments total, final due `2026-10-08`, and return to court on `2026-12-07` at `09:00` for nonpayment. Budget review uses `$2,050.00` monthly income minus `$1,785.00` obligations for `$265.00` disposable income; `$60.00` is inside the Gloucester band and is classified as `supported_by_budget`.

Unknown SSN, mailing address, residence address, phone, driver license number, probation officer, and probation office location use exactly `TBD from case file`. The stale `$25.00` account-management fee and unsupported `$180.00` restitution estimate are listed in `excluded_financial_items` and are not included in the order balance.

Evaluation uses 8 deterministic whole-point scoring checks with raw weights totaling 12:

- `SP001` weight 1: case memo identity, appeal posture, sentence totals, and required work flags.
- `SP002` weight 1: CC-1375 probation referral and report date-time.
- `SP003` weight 1: CC-1379 license suspension tied to the conviction date.
- `SP004` weight 1: initial installment policy classification and supported balance components.
- `SP005` weight 3: payment schedule math, final partial payment, final due date, and return-to-court setting.
- `SP006` weight 1: budget review, policy band, and support classification.
- `SP007` weight 3: placeholder discipline.
- `SP008` weight 1: unsupported account-management fee and restitution exclusion.

These checks span distinct outcomes: memo/disposition consistency, probation referral, license consequence, installment policy, schedule math, budget support, placeholder handling, and exclusion of unsupported financial items. Each scoring point is all-or-nothing and uses structured fields rather than subjective text. The highest weights focus on the schedule math and no-fabrication rules that require transfer from the solved Virginia train tasks rather than simple field lookup.

Transfer design: `train_003` anchors the single-case Gloucester DUI post-sentencing packet pattern: sentence posture must stay consistent across memo, probation referral, license order, and payment order; CC-1379 license suspension uses the conviction date; unknown form identifiers use `TBD from case file`; and the payment schedule needs final partial-payment math and return-to-court handling. `train_005` reinforces Gloucester first-petition installment treatment with no down payment, no account-management fee, budget-supported monthly amounts, exact monthly schedules, and strict separation of probation, license, and payment fields. In this test, transfer-dependent scoring points are `SP002`, `SP003`, `SP004`, `SP005`, `SP006`, `SP007`, and `SP008`; `SP001` also benefits from the train-inferred habit of keeping the case memo consistent with the signed sentencing intake rather than stale imported charge posture. Task-specific exploration remains necessary for the new appeal facts, Talia Nguyen's budget, the `$60.00` monthly amount, and the `$980.00` schedule.

Likely model pitfalls include copying the stale imported charge disposition instead of the appeal sentencing intake, using the release date instead of the conviction date for license suspension, treating the first petition as a subsequent review, including the old account-management fee or unsworn restitution estimate, using `$25.00` or `$180.00` in the total due, choosing an amount outside the Gloucester band, omitting the final `$20.00` payment, miscounting monthly due dates, or inventing a driver license number, SSN, address, phone, probation officer, or office location.

Construction record: authored by Codex task-builder subagent for `test_003`; created and updated on 2026-07-18. Major changes: created the full task folder under `task_group/task_group_018/test_tasks/003/` with prompt, three realistic local payloads, answer template, standard answer, deterministic evaluator, and bilingual notes; later calibration rework adjusted rubric weights while preserving the same scoring points and standard answer.

## 中文复核说明

`test_003` 是 Virginia Gloucester County 的 DUI 上诉后判决文书任务，属于 `task_group_018`，来源场景为 `SCN_018_court_clerk_disposition_orders_and_financial_entries`，主要对应源示例 `E003`。目标案件为 `VA-CR25-1044-00`，付款申请为 `VA-PET-1044A`。

求解者可见材料包括 `input/prompt.txt`、`input/payloads/appeal_sentencing_intake.json`、`input/payloads/payment_petition_and_budget.json`、`input/payloads/form_packet_excerpt.json` 和 `input/payloads/answer_template.json`。共享 Court Operations Portal 只能通过 `<TASK_ENV_BASE_URL>` 引用，用于核对案件、charge、表格、付款政策和 financial petition 记录。关键环境记录包括 Gloucester 管辖区 `VA-GLO`、案件 `VA-CR25-1044-00`、申请 `VA-PET-1044A`、政策 `POL-VA-GLO-FIRST`、表格 `VA_CC1375` 和 `VA_CC1379`。

业务任务是在 circuit DUI appeal 判决后准备书记员可用的结构化 JSON。该包包含四类工作成果：案件备忘录、CC-1375 风格缓刑转介、CC-1379 风格驾照暂停和分期付款命令，以及占位字段和被排除财务项目清单。它符合本任务组，因为它同时考查案件处分核对、表格字段映射、付款政策选择、预算审核、月度分期计算，以及缺失表格信息不得编造的纪律。

材料用途如下：`appeal_sentencing_intake.json` 控制 circuit appeal 的定罪和判决姿态：`2025-05-08` 定罪，DUI first offense，法条 `Va. Code 18.2-266`，判 30 天监禁其中 25 天 suspended、5 天 active，罚金 `$750.00`，诉讼成本 `$230.00`，6 个月 supervised probation，12 个月驾照暂停，`2025-05-09` 释放，并在 `2025-05-12T09:30:00` 向 probation 报到。`payment_petition_and_budget.json` 提供首次申请、`$980.00` fines/costs 余额、无已命令 restitution 或 account fee、请求每月 `$60.00`、家庭预算、过期的 `$25.00` account-fee 行，以及无命令支持的 `$180.00` restitution estimate。`form_packet_excerpt.json` 提供本地字段组和精确占位文本。环境政策确认 Gloucester 首次申请分期区间为 `$50.00-$100.00`、无首付款、30 天后首次到期、最终到期后 60 天返庭、无 account fee。

标准答案在所有表格部分保持同一判决事实。案件备忘录标记为 `circuit_appeal_conviction`，定罪日期为 `2025-05-08`，fines/costs 总额 `$980.00`，6 个月 supervised probation，12 个月 license suspension。CC-1375 使用 `VA_CC1375`，6 个月 supervised probation，并记录 `2025-05-12T09:30:00` 报到。CC-1379 使用 `VA_CC1379`；驾照从 `2025-05-08` 起暂停 12 个月，驾照号保持 `TBD from case file`。

付款命令为 `POL-VA-GLO-FIRST` 下的 `initial_installment`：总欠款 `$980.00`，fines/costs `$980.00`，restitution `$0.00`，account fee `$0.00`，首付款 `$0.00`，每月 `$60.00`，首次到期 `2025-06-08`，16 次完整付款加最后一次 `$20.00`，共 17 次，最终到期 `2026-10-08`，如未付款则 `2026-12-07` `09:00` 返庭。预算审核为月收入 `$2,050.00` 减月义务 `$1,785.00`，可支配收入 `$265.00`；`$60.00` 位于 Gloucester 政策区间内，因此分类为 `supported_by_budget`。

缺失的 SSN、邮寄地址、居住地址、电话、驾照号、缓刑官和缓刑办公室地点均使用精确文本 `TBD from case file`。过期的 `$25.00` account-management fee 和无依据的 `$180.00` restitution estimate 应列入 `excluded_financial_items`，不得加入付款命令余额。

评测包含 8 个确定性的整点评分项，原始权重合计 12：

- `SP001` 权重 1：案件备忘录身份、上诉姿态、判决金额和后续工作标志。
- `SP002` 权重 1：CC-1375 缓刑转介和报到日期时间。
- `SP003` 权重 1：CC-1379 驾照暂停，并绑定定罪日期。
- `SP004` 权重 1：首次分期政策分类和可支持的余额组成。
- `SP005` 权重 3：付款计划计算、最后一期部分付款、最终到期日和返庭设置。
- `SP006` 权重 1：预算、政策区间和可支持性分类。
- `SP007` 权重 3：占位字段纪律。
- `SP008` 权重 1：排除无依据的 account-management fee 和 restitution。

这些评分点覆盖备忘录/处分一致性、缓刑转介、驾照后果、分期政策、计划计算、预算支持、占位处理和无依据财务项目排除等不同业务结果。每个评分点都是全得或零分，并使用结构化字段而非主观文本评分。最高权重集中在 schedule math 和不得编造缺失信息的规则上，这些需要从 Virginia 训练任务迁移，而不是简单字段查找。

迁移设计：`train_003` 锚定 Gloucester 单案件 DUI 判后包的模式：判决姿态必须在 memo、probation referral、license order 和 payment order 中保持一致；CC-1379 驾照暂停使用定罪日期；未知表格身份信息使用 `TBD from case file`；付款计划要计算最后一期部分付款和返庭日期。`train_005` 强化 Gloucester 首次申请分期处理：无首付款、无 account-management fee、月付款金额需由预算支持、按月精确排期，并且 probation、license 和 payment 字段需要保持分离。此测试中依赖迁移的评分点为 `SP002`、`SP003`、`SP004`、`SP005`、`SP006`、`SP007` 和 `SP008`；`SP001` 也受益于训练任务中“以签署的 sentencing intake 保持 memo 一致，而不是照抄过期导入 charge 姿态”的经验。任务特定探索仍然需要处理新的 appeal facts、Talia Nguyen 的预算、`$60.00` 月付款和 `$980.00` 计划。

常见错误包括：照抄过期导入的 charge disposition 而不是 appeal sentencing intake；把释放日期当作驾照暂停生效日期；把首次申请误判为 subsequent review；加入旧 account-management fee 或未宣誓的 restitution estimate；把 `$25.00` 或 `$180.00` 加入总欠款；选择不符合 Gloucester 区间的金额；遗漏最后 `$20.00`；算错月度到期日；或编造驾照号、SSN、地址、电话、缓刑官或办公室地点。

构造记录：作者为 Codex task-builder subagent for `test_003`；创建和更新日期为 2026-07-18。主要变更：在 `task_group/task_group_018/test_tasks/003/` 下创建完整任务文件夹，包括 prompt、三个真实风格本地 payload、answer template、标准答案、确定性 evaluator 和双语 notes；后续 calibration rework 调整了 rubric weights，但保留相同 scoring points 和 standard answer。
