# train_005 Notes

## English

This train task belongs to task_group_005, the shared ERP finance and compliance review environment. The local task brief is an AP payment release risk review for five vendors after account-change events. The task uses generated shared environment records under `task_group/task_group_005/env/data/`, especially `compliance_objects.json` and `vendors.json`, plus the task-local solver payload `input/payloads/account_change_batch.json`.

The solver-visible request asks for a structured release posture for five business IDs: `BUS-2025-0018`, `BUS-2025-0006`, `BUS-2025-0056`, `BUS-2025-0009`, and `BUS-2025-0041`. The review date is `2025-06-01`. The expected output is constrained by `input/payloads/answer_template.json` and uses controlled decision values `release`, `hold`, and `escalate`.

This task fits the scenario because it requires coordination across AP release requests, vendor master data, compliance profile data, and account-change controls. The local payload provides the batch and release gate memo; the shared environment provides the authoritative compliance facts. The main object relationship is `business_id` to `vendor_id`, with bank, tax, license, screening, and risk fields used to reconstruct the effective payment-release state.

Material map: `account_change_batch.json` identifies the five account-change tickets, the review date, and high-level review context. `answer_template.json` defines the output schema, enum values, stable ID ordering, and required lists. The shared compliance object records provide `bank_account_status`, `tax_id`, `license_expiry`, `sanctions_check_status`, `pep_status`, `missing_fields`, and `risk_score`. The vendor records are useful for confirming that the selected business profiles map to the expected vendor master identities.

Solution basis: `BUS-2025-0018` releases because its bank is verified, tax ID is valid, license is active on `2025-06-01`, screening is clear, PEP is none, no fields are missing, and risk is below the override threshold. `BUS-2025-0006` is held because the bank account has `name_mismatch`, license evidence is missing, and risk score `70` triggers the override flag. `BUS-2025-0056` is held because the bank account is closed, sanctions screening is not run, and the license expired before the review date. `BUS-2025-0009` escalates because it has confirmed PEP, invalid placeholder tax ID `TIN999999`, and an expired license. `BUS-2025-0041` escalates because it has possible PEP, bank `name_mismatch`, invalid tax ID format `TIN12X899`, and an expired license.

Evaluation uses eight exact-match scoring points with raw weights totaling 17: SP1 target entity set (1), SP2 release decision for `BUS-2025-0018` (2), SP3 hold decisions for `BUS-2025-0006` and `BUS-2025-0056` (3), SP4 escalation decisions for `BUS-2025-0009` and `BUS-2025-0041` (3), SP5 bank mismatch IDs (2), SP6 invalid tax IDs (2), SP7 expired license IDs (2), and SP8 review queue plus risk-score override flags (2). Lists are normalized by sorted ID set; decision checks are exact enum matches.

Transfer design: as a train task, this is a real calibration task rather than a tutorial. Comparing an attempted answer against the standard answer should teach the transferable habits needed for later payment-release risk tasks: treat the compliance profile as authoritative for release gates, distinguish hold from escalation, treat PEP/sanctions concerns as escalation triggers, compare license expiry to the stated review date, recognize placeholder and malformed tax IDs, keep bank `name_mismatch` separate from other unusable bank states, and return normalized ID lists instead of free-text rationales.

Likely pitfalls include using the current calendar date instead of `2025-06-01`, treating current `review_status` as the final release decision, escalating every non-clear bank or not-run screening case, missing that `TIN999999` is invalid despite matching the basic pattern, omitting the risk override flag for score `70`, or including the closed-bank case in `bank_mismatch_ids`.

Construction record: created by task-builder subagent for `train_005` on 2026-06-01. Files added under `task_group/task_group_005/train_tasks/005/` only.

## 中文

本训练任务属于 `task_group_005`，使用共享的 ERP 财务与合规审查环境。任务场景是在供应商账户变更事件之后，对五个供应商进行 AP 付款放行风险复核。任务使用共享环境中的生成数据，尤其是 `compliance_objects.json` 和 `vendors.json`，并结合本任务本地输入 `input/payloads/account_change_batch.json`。

求解者可见的任务要求是对五个 `business_id` 给出结构化放行判断：`BUS-2025-0018`、`BUS-2025-0006`、`BUS-2025-0056`、`BUS-2025-0009`、`BUS-2025-0041`。复核日期为 `2025-06-01`。输出由 `input/payloads/answer_template.json` 约束，决策枚举为 `release`、`hold`、`escalate`。

该任务符合本任务组场景，因为它要求在 AP 放行请求、供应商主数据、合规档案和账户变更控制之间进行交叉核对。任务本地 payload 给出批次、账户变更工单和控制备忘录；共享环境提供权威的合规事实。核心对象关系是 `business_id` 与 `vendor_id` 的映射，并据此核对银行、税号、许可证、筛查和风险字段。

材料说明：`account_change_batch.json` 提供五个账户变更工单、复核日期和高层级复核背景；`answer_template.json` 定义输出结构、枚举值、ID 排序和必填列表；共享合规记录提供 `bank_account_status`、`tax_id`、`license_expiry`、`sanctions_check_status`、`pep_status`、`missing_fields` 和 `risk_score`；供应商记录可用于确认业务档案与供应商主数据身份一致。

标准答案依据如下：`BUS-2025-0018` 可以放行，因为银行已验证、税号有效、许可证在 `2025-06-01` 仍有效、筛查清晰、无 PEP、无缺失字段且风险分低于阈值。`BUS-2025-0006` 应暂缓，因为银行为 `name_mismatch`、许可证材料缺失且风险分 `70` 触发覆盖标记。`BUS-2025-0056` 应暂缓，因为银行账户关闭、制裁筛查未运行且许可证已过期。`BUS-2025-0009` 应升级，因为存在 confirmed PEP、占位税号 `TIN999999` 无效且许可证过期。`BUS-2025-0041` 应升级，因为存在 possible PEP、银行 `name_mismatch`、税号格式 `TIN12X899` 无效且许可证过期。

评估包含八个精确匹配评分点，原始总权重为 17：SP1 目标实体集合（1），SP2 `BUS-2025-0018` 的放行判断（2），SP3 `BUS-2025-0006` 和 `BUS-2025-0056` 的暂缓判断（3），SP4 `BUS-2025-0009` 和 `BUS-2025-0041` 的升级判断（3），SP5 银行名称不匹配 ID 集合（2），SP6 无效税号 ID 集合（2），SP7 截至 `2025-06-01` 的过期许可证 ID 集合（2），SP8 复核队列与风险分覆盖标记集合（2）。列表按 ID 集合归一化；决策字段按枚举精确匹配。

迁移设计：这是一个真实训练任务，不是教程。求解者在盲做后对照标准答案，可以归纳出后续付款放行风险任务可迁移的方法：以合规档案作为放行闸口的权威来源，区分暂缓和升级，PEP/制裁相关风险进入升级，许可证按指定复核日期判断，识别占位或格式异常税号，将银行 `name_mismatch` 与其他不可用银行状态区分开，并输出规范化 ID 列表而不是自由文本理由。

常见错误包括使用当前日期而不是 `2025-06-01`，把环境中的 `review_status` 直接当作最终放行结论，对所有非清晰银行或未运行筛查都做升级，忽略 `TIN999999` 虽符合基础格式但属于无效占位值，遗漏风险分 `70` 的覆盖标记，或把银行关闭案例误加入 `bank_mismatch_ids`。

构建记录：由 `train_005` task-builder subagent 于 2026-06-01 创建。仅在 `task_group/task_group_005/train_tasks/005/` 下新增文件。
