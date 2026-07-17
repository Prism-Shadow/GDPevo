# Task Notes / 任务说明

## English

Task definition and business objective: This train task asks the solver to review remote-work policy case `CASE-RW-221` and decide whether an approved-with-conditions case can close. The objective is to reconcile approval history with document-folder readiness, formal notice quality, remediation ownership, and audit scope.

Visible inputs and Web evidence: The solver-visible prompt provides the local PeopleOps Console entry point and case ID. Public evidence should be gathered from Policy Cases, approval history, Documents/folder checklist, Messages or notice packet inspection, Audit Log detail, and any policy document viewer content needed to interpret required files, tags, or notices.

Expected reasoning and answer basis:
- Use approval history to report `final_decision` as `approved_with_conditions`, authority `HR Director`, and event `APP-221-FINAL`.
- Compare the folder checklist to filed documents. The folder is not ready because `tax-equalization-agreement.pdf` is missing.
- The required tag is present, so `folder_required_tag_action` is `no_tag_action`.
- Inspect the formal notice packet. It is `defective` because it has `missing_appeal_instructions`.
- Use `AUD-CASE221-09` as both `audit_event_id` and the single `supporting_audit_event_ids` entry.
- Set `audit_scope` to `document_notice_findings_only`; no adjacent audit events need exclusion here, so `excluded_audit_event_ids` is empty.
- Approval is not sufficient because folder and notice evidence are defective. Use `approval_not_sufficient_when_folder_or_notice_defective`, blockers `missing_required_files` and `defective_formal_notice`, and final result `hold_for_folder_and_notice_defects`.
- Use `approval_history_folder_notice_audit` as the evidence order, `open_records_remediation` for escalation, `Records` as owner, and `reissue_defective_notices` for notice remediation.

Transferable SOP and field conventions: This task teaches that final approval does not override failed document or formal-notice controls. It anchors reusable labels for closeout gates, blockers, evidence-source order, document/notice audit scope, remediation ownership, and notice reissue. These labels transfer directly to test tasks involving `CASE-445` and document/message audits.

Likely pitfalls: Treating the final approval as enough to close; overlooking the missing required file; writing prose for `approval_closeout_gate`; confusing `next_action` with `escalation_action`; omitting `supporting_audit_event_ids`; or using a broad audit scope instead of `document_notice_findings_only`.

Evaluator/scoring basis: `eval/rubric.json` scores six exact-match checks: case/approval, folder readiness, notice quality, approval gate/blockers, source order/audit, and remediation. The audit check includes `audit_event_id`, `supporting_audit_event_ids`, `excluded_audit_event_ids`, and `audit_scope`.

Construction/rework note: This notes file was expanded after the notes review to reflect the current reworked answer and rubric, especially the added audit-scope fields and normalized remediation labels.

## 中文

任务定义和业务目标：本训练任务要求求解者审核远程办公政策案件 `CASE-RW-221`，判断一个附条件批准的案件是否可以关闭。目标是把审批历史、文档文件夹就绪度、正式通知质量、整改负责人和审计范围统一起来。

可见输入和网页证据：求解者可见 prompt 提供本地 PeopleOps Console 入口和 case ID。公开证据应从 Policy Cases、审批历史、Documents/文件夹 checklist、Messages 或 notice packet inspection、Audit Log 详情，以及解释必需文件/标签/通知所需的 policy document viewer 中获取。

预期推理和答案依据：
- 从审批历史报告 `final_decision` 为 `approved_with_conditions`，审批权限人为 `HR Director`，事件为 `APP-221-FINAL`。
- 将 folder checklist 与已归档文档对比。文件夹未就绪，因为缺少 `tax-equalization-agreement.pdf`。
- 必需标签存在，因此 `folder_required_tag_action` 为 `no_tag_action`。
- 检查正式通知包。通知为 `defective`，缺陷是 `missing_appeal_instructions`。
- 使用 `AUD-CASE221-09` 作为 `audit_event_id`，也是 `supporting_audit_event_ids` 中唯一条目。
- `audit_scope` 设为 `document_notice_findings_only`；此处没有需要排除的相邻审计事件，因此 `excluded_audit_event_ids` 为空。
- 审批并不足以关闭，因为文件夹和通知证据存在缺陷。应使用 `approval_not_sufficient_when_folder_or_notice_defective`，阻断项为 `missing_required_files` 和 `defective_formal_notice`，最终结果为 `hold_for_folder_and_notice_defects`。
- 证据顺序使用 `approval_history_folder_notice_audit`，升级动作为 `open_records_remediation`，负责人为 `Records`，通知整改为 `reissue_defective_notices`。

可迁移 SOP 和字段口径：本任务说明最终审批不能覆盖失败的文档或正式通知控制。它锚定可复用标签：关闭门槛、阻断项、证据来源顺序、文档/通知审计范围、整改负责人和通知重发。这些标签会直接迁移到涉及 `CASE-445` 和文档/消息审计的测试任务。

常见陷阱：把最终审批视为足以关闭；漏看缺失的必需文件；在 `approval_closeout_gate` 中写自由文本；混淆 `next_action` 和 `escalation_action`；遗漏 `supporting_audit_event_ids`；或使用过宽的 audit scope 而不是 `document_notice_findings_only`。

评测依据：`eval/rubric.json` 包含 6 个精确匹配检查：case/approval、folder readiness、notice quality、approval gate/blockers、source order/audit 和 remediation。审计检查包含 `audit_event_id`、`supporting_audit_event_ids`、`excluded_audit_event_ids` 和 `audit_scope`。

构造/返工说明：本 notes 文件已在 notes review 后扩展，以同步当前返工后的 answer 和 rubric，尤其是新增的 audit-scope 字段和规范化整改标签。
