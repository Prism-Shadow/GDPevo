# Hidden Notes: test_002 Vendor Intake Exception Board

## English

Data/source lineage: This task belongs to `task_group_005`, based on seed scenario `SCN_005_erp_finance_expense_control` and especially the business-entity verification pattern from source example `E002`. It uses the shared ERP finance API implemented for the task group, with authoritative data in the compliance and vendor domains. The task-local payload `input/payloads/vendor_intake_scope.json` only names batch `grant_supplier_intake_april_2025`, review date `2025-04-30`, and target business IDs `BUS-2025-0025`, `BUS-2025-0027`, `BUS-2025-0034`, `BUS-2025-0042`, and `BUS-2025-0052`.

Task definition: Finance control needs an April 2025 vendor intake exception board for grant-funded supplier candidates. The solver-visible prompt asks for a structured JSON response and does not expose the decision SOP. Solvers are expected to use the runner-provided API base URL and the shared compliance/vendor endpoints to reconstruct the current finance intake posture for each target business.

Scenario fit: The task is in the same ERP finance close-operations scenario as the train tasks. It exercises vendor master and compliance evidence review, current-state reconciliation, entity exception classification, and controlled JSON reporting. It is not a tutorial and not a copy of a train task; the target entities and evidence conflicts are new, while the operation family is anchored by `train_002` and `train_005`.

Material map: `prompt.txt` provides the business request and output location. `vendor_intake_scope.json` defines the batch and target IDs. `answer_template.json` defines required fields, enum values, ID ordering, and list normalization. The shared API supplies `/api/compliance/objects`, `/api/compliance/profile/{business_id}`, `/api/compliance/ownership/{business_id}`, `/api/compliance/registry/{business_id}`, `/api/compliance/screening/{business_id}`, `/api/compliance/bank/{business_id}`, `/api/compliance/risk/{business_id}`, and `/api/vendors`. The prompt deliberately does not direct solvers to inspect environment files.

Solution and evaluation basis: The hidden construction rule is that deterministic exception evidence controls the intake decision; current review status and numeric risk score are supporting context only. Reportable UBO count is the count of owner rows at or above the 25 percent reporting threshold. For this task, the selected records resolve as follows:

- `BUS-2025-0025`: bank is `not_verified`; no reportable UBOs; risk score is high; linked vendor `VEN-0016` is inactive as context. Decision `escalate`; hard stops `["bank_not_verified"]`.
- `BUS-2025-0027`: tax ID is placeholder `TIN999999`; missing `bank_statement`; license expired on `2025-03-08`, which is more than 42 days before `2025-04-30`; one reportable UBO. Decision `escalate`; hard stops `["invalid_tax_id", "license_expired_over_42_days", "missing_required_information"]`.
- `BUS-2025-0034`: bank is `not_verified`; missing `address`; PEP status is `possible_pep`; shell-company flag is true; four reportable UBOs. Decision `escalate`; hard stops `["bank_not_verified", "missing_required_information", "possible_pep", "shell_company_suspected"]`.
- `BUS-2025-0042`: bank is `not_verified`; license expired on `2025-02-16`, more than 42 days before review; no reportable UBOs. Decision `escalate`; hard stops `["bank_not_verified", "license_expired_over_42_days"]`.
- `BUS-2025-0052`: license expired on `2025-02-04`, more than 42 days before review; missing `address` and `beneficial_owner_id`; two reportable UBOs. Decision `escalate`; hard stops `["license_expired_over_42_days", "missing_required_information"]`.

The evaluator has 8 exact-match scoring points with raw weights `[3, 2, 2, 2, 3, 2, 2, 1]`, total weight `17`: metadata plus high-impact decisions, remaining decisions and actions, risk levels, UBO counts, primary hard-stop code sets, remaining hard-stop code sets, follow-up business set, and batch status with ready count. Lists are normalized by sorted string values. The standard answer scores `1.0`.

Transfer design: `train_002` anchors vendor onboarding compliance review: combine compliance detail endpoints, do not copy source `review_status`, count reportable UBOs using the reporting threshold, and normalize controlled output sets. `train_005` anchors payment-release and account-change risk habits: compare license dates to the stated review date, recognize placeholder or malformed tax IDs, and distinguish informational risk score from hard exception evidence. In `test_002`, those same habits transfer to a different batch, new business IDs, different missing-information combinations, and a stricter license-age code. High-value scoring points for hard-stop sets, UBO counts, and decisions are intended to benefit from this train-derived experience.

Likely model pitfalls: trusting `review_status` or risk score as the final decision; omitting the `license_expired_over_42_days` code for `BUS-2025-0027`; counting owners below the threshold; failing to normalize hard-stop code order; treating missing information as a lower-priority follow-up when another hard stop requires escalation; or using current calendar date instead of the task review date.

Construction record: Author: clean-context task-builder owner for `task_group_005 test_002`. Created: 2026-06-01. Rebuilt: 2026-06-02. Major changes: replaced leaky/terse solver materials, corrected the `BUS-2025-0027` license hard-stop evidence, updated the standard answer and evaluator, and rewrote bilingual notes in valid UTF-8.

## 中文

数据与来源：本任务属于 `task_group_005`，来源场景是 `SCN_005_erp_finance_expense_control`，重点继承源示例 `E002` 的业务实体核验模式。任务使用本任务组共享的 ERP 财务 API，权威数据来自合规与供应商主数据域。任务本地输入 `input/payloads/vendor_intake_scope.json` 只给出批次 `grant_supplier_intake_april_2025`、复核日期 `2025-04-30`，以及目标业务主体 `BUS-2025-0025`、`BUS-2025-0027`、`BUS-2025-0034`、`BUS-2025-0042`、`BUS-2025-0052`。

任务定义：财务控制团队需要为 2025 年 4 月的 grant-funded supplier 候选供应商准备准入异常看板。求解者可见的 prompt 只要求输出结构化 JSON，并不暴露完整决策 SOP。求解者应使用 runner 提供的 API base URL，通过共享的合规和供应商接口还原每个目标主体的当前准入状态。

场景契合：该任务属于 ERP 财务关账运营场景中的供应商主数据与合规证据核验工作。它要求进行供应商主数据核对、合规证据复核、当前状态重构、异常分类以及受控 JSON 汇报。它不是教程，也不是训练任务的拷贝；目标主体和证据冲突是新的，但操作族由 `train_002` 和 `train_005` 锚定。

材料说明：`prompt.txt` 提供业务请求和输出要求。`vendor_intake_scope.json` 定义批次和目标 ID。`answer_template.json` 定义必填字段、枚举值、ID 排序和列表规范化。共享 API 提供 `/api/compliance/objects`、`/api/compliance/profile/{business_id}`、`/api/compliance/ownership/{business_id}`、`/api/compliance/registry/{business_id}`、`/api/compliance/screening/{business_id}`、`/api/compliance/bank/{business_id}`、`/api/compliance/risk/{business_id}` 和 `/api/vendors`。prompt 没有要求求解者查看环境文件。

解答与评测依据：隐藏构造规则是确定性的异常证据优先决定准入结论；当前 `review_status` 和数值型 `risk_score` 只能作为辅助背景。需报告的 UBO 数量按持股比例达到或超过 25% 的 owner 记录计数。本任务的目标记录如下：

- `BUS-2025-0025`：银行状态为 `not_verified`；无可报告 UBO；风险分较高；关联供应商 `VEN-0016` 为 inactive 背景信息。结论为 `escalate`，硬停代码为 `["bank_not_verified"]`。
- `BUS-2025-0027`：税号是占位值 `TIN999999`；缺少 `bank_statement`；执照于 `2025-03-08` 过期，距离 `2025-04-30` 超过 42 天；有 1 个可报告 UBO。结论为 `escalate`，硬停代码为 `["invalid_tax_id", "license_expired_over_42_days", "missing_required_information"]`。
- `BUS-2025-0034`：银行状态为 `not_verified`；缺少 `address`；PEP 状态为 `possible_pep`；shell-company 标记为 true；有 4 个可报告 UBO。结论为 `escalate`，硬停代码为 `["bank_not_verified", "missing_required_information", "possible_pep", "shell_company_suspected"]`。
- `BUS-2025-0042`：银行状态为 `not_verified`；执照于 `2025-02-16` 过期，距离复核日超过 42 天；无可报告 UBO。结论为 `escalate`，硬停代码为 `["bank_not_verified", "license_expired_over_42_days"]`。
- `BUS-2025-0052`：执照于 `2025-02-04` 过期，距离复核日超过 42 天；缺少 `address` 和 `beneficial_owner_id`；有 2 个可报告 UBO。结论为 `escalate`，硬停代码为 `["license_expired_over_42_days", "missing_required_information"]`。

评测器包含 8 个精确匹配评分点，原始权重为 `[3, 2, 2, 2, 3, 2, 2, 1]`，总权重 `17`：元数据与高影响决策、剩余决策与动作、风险等级、UBO 数量、主要硬停代码集、剩余硬停代码集、后续跟进主体集合、批次状态与可准入数量。列表按字符串排序后比较。标准答案得分为 `1.0`。

迁移设计：`train_002` 锚定供应商 onboarding 合规核验经验：组合多个合规明细接口、不要照抄源系统 `review_status`、按报告阈值计算 UBO、并规范化受控输出集合。`train_005` 锚定付款放行和账户变更风险经验：按指定复核日期判断执照过期、识别占位或异常税号、区分信息性风险分与硬异常证据。在 `test_002` 中，这些经验迁移到不同批次、新 business ID、不同缺失信息组合以及更具体的执照超期代码上。硬停代码集、UBO 数量和准入决策等高价值评分点应能受益于训练集经验。

常见错误：把 `review_status` 或 `risk_score` 当成最终结论；漏掉 `BUS-2025-0027` 的 `license_expired_over_42_days`；把低于阈值的 owner 计入 UBO；没有规范化 hard-stop code 顺序；在存在升级硬停时仍把缺失信息当作低优先级跟进；或使用当前日历日期而不是任务复核日期。

构造记录：作者：`task_group_005 test_002` clean-context task-builder owner。创建日期：2026-06-01。重建日期：2026-06-02。主要变更：替换过于简略且带有过程提示的可见材料，修正 `BUS-2025-0027` 执照超期硬停证据，更新标准答案和评测器，并以有效 UTF-8 重写双语 notes。
