# train_001 Notes: Lumbar PT Nurse Review

## English

### Data and source lineage

This task belongs to `SCN_014_healthcare_payer_authorization_appeals`, using the payer authorization and nurse-review patterns from source examples `E001`, `E005`, and `E006`. The task-group design names `CASE-TR-001` as the complete lumbar physical therapy nurse-review train case. The shared environment is the generated Northstar Health Plan SQLite-backed HTTP service described by `scratch/env_blueprint.md` and `task_group/task_group_014/env/manifest.json`, generated with seed `140417`.

The task-local solver-visible files are `input/prompt.txt`, `input/payloads/task_context.json`, and `input/payloads/answer_template.json`. They identify the role, target case, reporting date, environment access, and required JSON schema, but do not include the determination outcome.

### Task definition and scenario fit

The solver acts as a UM nurse reviewer preparing a structured determination summary for the authorization team. The visible target is `CASE-TR-001`, a prior authorization case for lumbar physical therapy. The expected work is to use the shared environment to reconcile the case, member and plan context, request lines, applicable physical therapy policy criteria, current clinical documents, stale documents, and the authorization record.

This fits the group because it exercises the central payer UM workflow: case intake, clinical evidence review, criteria mapping, role-based routing, and final authorization handoff. It also anchors later transfer for clinical cases where current documentation and stale exports conflict.

### Material map

`POST /sql/query` with bearer token `pa-review-token-014` is the main structured access path. Useful tables include `cases`, `members`, `providers`, `request_lines`, `documents`, `document_facts`, `policies`, `policy_criteria`, `case_criteria`, and `authorizations`. The business endpoints `/api/cases/{case_id}`, `/api/documents/{document_id}`, and `/api/policies/{policy_id}` expose the same business records through joined summaries.

For `CASE-TR-001`, the relevant current evidence documents are `DOC-TR-001-EVAL` and `DOC-TR-001-POC`. The older `DOC-TR-001-STALE` LegacyUM export is a closed knee episode and is excluded from the current lumbar determination. The request lines are CPT `97110`, `97112`, and `97530`, all with modifier `GP`, totaling 24 requested units from `2026-05-06` through `2026-07-05`.

### Solution and evaluation basis

The standard answer recommends `approve`, sets `final_status` to `approved`, uses route `nurse_approval`, and carries authorization `NPA-2405014` for 24 units from `2026-05-06` to `2026-07-05`. Approved CPT codes are `97110`, `97112`, and `97530` with modifier `GP`. Criteria results are all `met` for `PT-ACTIVE`, `PT-DEFICIT`, `PT-DX`, `PT-POC`, and `PT-UNITS`. The current evidence documents are `DOC-TR-001-EVAL` and `DOC-TR-001-POC`; `DOC-TR-001-STALE` is excluded. The determination letter is `approval` and next action is `issue_approval`.

The evaluator has seven whole-point scoring goals with raw weights `[1, 2, 2, 1, 2, 2, 1]`: target case and nurse route; approval recommendation and final status; authorization number, units, and dates; CPT and modifier line set; all-met PT criteria map; current evidence and stale exclusion; approval letter and next action without MD or peer-to-peer escalation. Each goal is pass/fail with no partial credit within the goal. The standard answer scores `1.0`.

Likely model pitfalls include treating the stale LegacyUM export as evidence, missing the modifier, returning only prose, escalating to MD despite all criteria being met, or approving fewer units than the matched request and authorization record support.

### Transfer design

As a train task, this solved example can teach the transferable convention that nurse approval is available when every applicable criterion is met and the evidence is current. It also demonstrates stable output conventions for recommendation, final status, route, criteria-result enums, authorization fields, and document inclusion/exclusion. Future test tasks can vary service line, evidence clarity, or document conflicts while relying on the same learned distinction between current evidence and stale records.

### Construction record

Author: task-builder Builder A. Created: `2026-07-18`. Updated: `2026-07-18`. Major changes: created train task files for `train_001`, including prompt, context payload, answer template, standard answer, evaluator, and bilingual notes.

## Chinese

### 数据与来源

本任务属于 `SCN_014_healthcare_payer_authorization_appeals`，采用来源样例 `E001`、`E005`、`E006` 中的授权审核与护士审查工作流。任务组设计将 `CASE-TR-001` 指定为一个资料完整的腰椎物理治疗护士审核训练案例。共享环境是 `scratch/env_blueprint.md` 和 `task_group/task_group_014/env/manifest.json` 描述的 Northstar Health Plan SQLite 后端 HTTP 服务，生成种子为 `140417`。

任务本地可见材料包括 `input/prompt.txt`、`input/payloads/task_context.json` 和 `input/payloads/answer_template.json`。这些文件只给出角色、目标案例、报告日期、环境访问方式和输出 JSON 结构，不泄露最终决定。

### 任务定义与场景匹配

求解者扮演 UM 护士审核员，为授权团队准备结构化裁定摘要。可见目标是 `CASE-TR-001`，这是一个腰椎物理治疗的事前授权案例。预期工作是在共享环境中核对案例、会员与计划信息、申请服务行、适用的物理治疗政策标准、当前临床文档、过期文档以及授权记录。

该任务符合任务组场景，因为它覆盖付款方 UM 的核心流程：案例受理、临床证据审查、标准映射、基于角色的路由以及最终授权交接。它也为后续临床类测试任务提供迁移基础，尤其是当前证据与过期导出记录冲突时的取舍。

### 材料地图

主要结构化访问路径是带 bearer token `pa-review-token-014` 的 `POST /sql/query`。关键表包括 `cases`、`members`、`providers`、`request_lines`、`documents`、`document_facts`、`policies`、`policy_criteria`、`case_criteria` 和 `authorizations`。业务端点 `/api/cases/{case_id}`、`/api/documents/{document_id}`、`/api/policies/{policy_id}` 提供同类业务记录的汇总视图。

对于 `CASE-TR-001`，当前有效证据文档是 `DOC-TR-001-EVAL` 和 `DOC-TR-001-POC`。较早的 `DOC-TR-001-STALE` 是 LegacyUM 中已关闭的膝部治疗记录，不应作为本次腰椎申请的当前证据。申请服务行为 CPT `97110`、`97112` 和 `97530`，修饰符均为 `GP`，合计 24 个单位，服务期为 `2026-05-06` 至 `2026-07-05`。

### 解答与评价依据

标准答案给出 `approve` 建议，`final_status` 为 `approved`，路由为 `nurse_approval`，授权号为 `NPA-2405014`，批准 24 个单位，日期为 `2026-05-06` 至 `2026-07-05`。批准 CPT 为 `97110`、`97112`、`97530`，修饰符为 `GP`。`PT-ACTIVE`、`PT-DEFICIT`、`PT-DX`、`PT-POC`、`PT-UNITS` 全部为 `met`。当前证据文档是 `DOC-TR-001-EVAL` 和 `DOC-TR-001-POC`，排除文档是 `DOC-TR-001-STALE`。信函类型为 `approval`，下一步动作为 `issue_approval`。

评价器包含七个整体得分点，原始权重为 `[1, 2, 2, 1, 2, 2, 1]`：目标案例与护士路由；批准建议与最终状态；授权号、单位数和日期；CPT 与修饰符集合；全部满足的 PT 标准映射；当前证据与过期文档排除；批准信函与下一步动作且不升级 MD 或 P2P。每个得分点只有通过或不通过，没有点内部分分。标准答案得分为 `1.0`。

常见错误包括把过期 LegacyUM 导出当作证据、遗漏修饰符、只返回叙述性文字、在全部标准满足时仍升级给医疗主任、或批准单位数少于申请行与授权记录支持的数量。

### 迁移设计

作为训练任务，本已解样例可以帮助推断一个可迁移规则：当所有适用标准都满足且证据为当前有效资料时，护士可以批准。它还展示了 recommendation、final_status、route、criteria-result 枚举、授权字段以及文档纳入与排除字段的稳定输出约定。后续测试任务可以改变服务线、证据清晰度或文档冲突，但仍依赖相同的当前证据优先与过期记录排除判断。

### 构建记录

作者：task-builder Builder A。创建日期：`2026-07-18`。更新日期：`2026-07-18`。主要变更：创建 `train_001` 的 prompt、context payload、answer template、standard answer、evaluator 和双语 notes。

## 2026-07-19 Basis-Audit Update

English: The answer template and standard answer now use `basis_audit`, a business-grounded audit trail rather than an invented control-code layer. `source_precedence` records the source category, `precedence_record_order` records the ordered business source trail, `controlling_record_ids` records the environment records that directly control the result, and `exception_record_ids` records stale, missing, unsupported, unresolved, or route-priority records. For this task, `source_precedence` is `current_clinical_records_over_stale_export`, `precedence_record_order` is `DOC-TR-001-EVAL`, `DOC-TR-001-POC`, `DOC-TR-001-STALE`, controlling records are `DOC-TR-001-EVAL`, `DOC-TR-001-POC`, and exception records are `DOC-TR-001-STALE`; the train evaluator scores this combined basis trail at low weight.

中文：答案模板和标准答案现在使用 `basis_audit`，这是基于业务依据的审计轨迹，而不是人为 control-code 层。`source_precedence` 记录来源类别，`precedence_record_order` 记录按优先级排列的业务来源轨迹，`controlling_record_ids` 记录直接决定结果的环境记录，`exception_record_ids` 记录过期、缺失、不支持、未解决或路线优先级记录。本任务中，`source_precedence` 为 `current_clinical_records_over_stale_export`，`precedence_record_order` 为 `DOC-TR-001-EVAL`, `DOC-TR-001-POC`, `DOC-TR-001-STALE`，控制记录为 `DOC-TR-001-EVAL`, `DOC-TR-001-POC`，例外记录为 `DOC-TR-001-STALE`；the train evaluator scores this combined basis trail at low weight。
