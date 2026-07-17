# train_002 Notes - Lakeview Q1 Application Allocation

## English

Data/source lineage: This task belongs to `SCN_011_bank_branch_credit_risk_lending_committee`, using the shared generated credit-office environment for `task_group_011_bank_branch_credit_risk_lending_committee`. It is the train application-allocation task for branch `LAKEVIEW`. The solver-visible files are `input/prompt.txt` and `input/payloads/answer_template.json`; the business evidence is in the public API endpoints for branch details, metrics, sector exposures, applications, and policies.

Task definition: The solver must evaluate Lakeview's pending applications for Q1 committee allocation, assign controlled decisions, use capacity-aware approved amounts, identify concentration handling, record controlled decline reasons, and report post-approval sector concentrations. The output schema covers `branch_id`, `allocation`, `decisions`, `concentration_flags`, `decline_reasons`, and `post_approval_concentrations`.

Scenario fit and material map: This is a branch lending-committee workflow matching the source examples' portfolio and application decision work. `/api/branches/LAKEVIEW` supplies capacity and limits, `/api/branches/LAKEVIEW/metrics` supplies total loans outstanding, `/api/branches/LAKEVIEW/sector-exposures` supplies current exposures and sector limit overrides, `/api/branches/LAKEVIEW/applications` supplies the application queue, and `/api/policies` supplies concentration and SBA/participation conventions.

Solution and evaluation basis: The standard answer approves `LAK-APP-004` and `LAK-APP-005`, conditionally approves `LAK-APP-901` with participation and `LAK-APP-902` with SBA guaranty/startup monitoring, and declines `LAK-APP-001`, `LAK-APP-002`, `LAK-APP-003`, `LAK-APP-006`, and `LAK-APP-903`. Gross approved amount is `4574253.45`; bank capacity used is `3802366.76`; remaining capacity is `2097633.24`. Healthcare is the planted strong-applicant concentration case: `LAK-APP-901` is strong but receives participation handling. High-risk consumer `LAK-APP-903` is declined for `low_fico` and `recent_bankruptcy`. SBA startup `LAK-APP-902` uses `840000.00` gross approval and `210000.00` bank capacity after guaranty. Post-approval concentrations are exact matched for Construction, Consumer, Healthcare, and Hospitality. Scoring uses seven exact-match points: SP001 decision sets weight 3; SP002 capacity numbers weight 2; SP003 Healthcare breach handling weight 3; SP004 high-risk consumer decline reason weight 2; SP005 SBA startup structure weight 2; SP006 post-approval concentrations weight 2; SP007 priority ranking weight 1.

Transfer design: As a train task, this teaches by answer comparison rather than by visible instructions. Useful transferable habits are discovering the generic API surfaces, separating gross approved exposure from bank-held capacity when guarantees or participation apply, treating sector ceilings as committee constraints, using controlled decline reasons, and preserving stable application IDs and ordered rankings.

Construction record: Author `train_002` task-builder worker. Created and updated on 2026-06-03. Minimum complete version created after user requested rapid finalization; no shared environment, task-group metadata, scratch design, or other task files were edited.

## 中文

数据与来源：本任务属于 `SCN_011_bank_branch_credit_risk_lending_committee`，使用 `task_group_011_bank_branch_credit_risk_lending_committee` 的共享信贷办公室生成环境。目标分行为 `LAKEVIEW`。求解者可见文件为 `input/prompt.txt` 与 `input/payloads/answer_template.json`，业务证据来自分行信息、指标、行业敞口、申请队列和政策等公开 API。

任务定义：求解者需要为 Lakeview 的 Q1 贷款委员会申请分配做出结构化结果，包括受控决策、占用额度、集中度处理、受控拒绝原因以及审批后的行业集中度。输出字段包括 `branch_id`、`allocation`、`decisions`、`concentration_flags`、`decline_reasons` 和 `post_approval_concentrations`。

场景适配与材料地图：该任务对应分行贷款委员会的真实工作流，与源示例中的组合审查和申请审批相同。`/api/branches/LAKEVIEW` 提供额度和限额，`/api/branches/LAKEVIEW/metrics` 提供贷款总额，`/api/branches/LAKEVIEW/sector-exposures` 提供当前行业敞口和覆盖限额，`/api/branches/LAKEVIEW/applications` 提供申请队列，`/api/policies` 提供集中度、SBA 担保和参与贷款处理惯例。

答案与评估依据：标准答案批准 `LAK-APP-004` 和 `LAK-APP-005`，有条件批准带参与安排的 `LAK-APP-901` 以及带 SBA 担保和初创监控的 `LAK-APP-902`，拒绝 `LAK-APP-001`、`LAK-APP-002`、`LAK-APP-003`、`LAK-APP-006` 和 `LAK-APP-903`。总批准额度为 `4574253.45`，占用银行额度为 `3802366.76`，剩余额度为 `2097633.24`。Healthcare 是强申请人与集中度约束冲突的核心案例；高风险消费申请 `LAK-APP-903` 因 `low_fico` 和 `recent_bankruptcy` 被拒；SBA 初创申请 `LAK-APP-902` 使用 `840000.00` 总批准和 `210000.00` 银行额度占用。评估包含七个精确匹配点：决策集合、额度数字、Healthcare 处理、高风险消费拒因、SBA 初创结构、审批后集中度和优先级排序。

迁移设计：作为训练任务，本任务通过盲解后对照答案形成迁移经验，而不是在提示中教学。可迁移经验包括发现通用 API、区分总批准敞口与银行实占额度、在担保或参与安排下处理容量、将行业上限视为委员会约束、使用受控拒因，以及保持稳定 ID 和排序。

构建记录：作者为 `train_002` task-builder worker。创建和更新日期为 2026-06-03。根据用户要求完成最小可用版本；未编辑共享环境、任务组元数据、scratch 设计文件或其他任务目录。
