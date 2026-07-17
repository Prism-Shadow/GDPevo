# Task Notes / 任务说明

## English

Task definition and business objective: This test task asks the solver to review policy case `CASE-445` and determine whether an approved-with-conditions lifecycle case is ready to close. The business objective is to combine approval history, document readiness, formal notice quality, audit evidence, closeout blockers, and tag remediation into one operational decision.

Visible inputs and Web evidence: The solver-visible prompt gives the local PeopleOps Console URL/login and the case under review. Public evidence should be gathered from Policy Cases, approval history, document folder checklist or attachment viewer, message/notice inspection, policy document viewer if needed, and Audit Log detail. The answer template exposes field names and allowed shapes, but not the business findings.

Expected reasoning and answer basis:
- Use approval history to identify `CASE-445`, final decision `approved_with_conditions`, authority `VP People`, and approval event `APP-445-FINAL`.
- Open the folder checklist and compare required files/tags to filed evidence. The folder is not ready; missing files are `benefits-election.pdf` and `executive-exception-approval.pdf`; `required_tag_present` is `false`.
- Inspect the formal notice rather than trusting case summary. Notice quality is `defective`, with `missing_appeal_instructions` and `missing_ack_deadline`.
- Cite audit event `AUD-CASE445-03`.
- Approval does not permit closeout when folder or notice controls fail. Use `approval_not_sufficient_when_folder_or_notice_defective`.
- Return blockers `missing_required_files`, `missing_required_tag`, and `defective_formal_notice`.
- Use `approval_history_folder_notice_audit` as evidence source order.
- Because the required tag is absent, use `add_required_tag_before_close`.
- Use `block_close_and_reissue_notice` as the next action.

Train anchors and transferred knowledge: This test reuses `train_002` for approved-but-blocked closeout, formal-notice defect handling, source order, and the approval gate label. It reuses `train_001` for the contrast between clean closeout and blocked closeout. It reuses `train_004` for scoped audit reasoning and not overusing adjacent evidence. The task-specific work is finding the `CASE-445` folder, message, approval, and audit details.

Likely pitfalls: Closing the case because the approval says final; listing only one missing file; forgetting the missing required tag; using prose for `approval_closeout_gate`; omitting `missing_required_tag` from blockers; or selecting an audit event that confirms payroll rather than case closeout.

Evaluator/scoring basis: `eval/rubric.json` has eight checks with 18 total points: case ID, approval record, folder readiness, notice quality, approval closeout gate, closeout blockers, evidence source/tag action, and audit/next action. The highest-weight points require the normalized gate, blockers, and next action.

Construction/rework note: This notes file was expanded after reviewer feedback to synchronize with current `output/answer.json` and `eval/rubric.json`, including `approval_closeout_gate`, `closeout_blockers`, `evidence_source_order`, and `folder_required_tag_action`.

## 中文

任务定义和业务目标：本测试任务要求求解者审核政策案件 `CASE-445`，判断一个附条件批准的生命周期案件是否可以关闭。业务目标是把审批历史、文档就绪度、正式通知质量、审计证据、关闭阻断项和标签整改合并为一个运营决定。

可见输入和网页证据：求解者可见 prompt 提供本地 PeopleOps Console URL/登录信息和待审核 case。公开证据应从 Policy Cases、审批历史、文档文件夹 checklist 或附件 viewer、消息/通知检查、必要时的 policy document viewer，以及 Audit Log detail 中收集。answer template 暴露字段名和结构，但不暴露业务结论。

预期推理和答案依据：
- 从审批历史识别 `CASE-445`，最终决定为 `approved_with_conditions`，审批权限人为 `VP People`，审批事件为 `APP-445-FINAL`。
- 打开 folder checklist，将必需文件/标签与已归档证据对比。文件夹未就绪；缺少 `benefits-election.pdf` 和 `executive-exception-approval.pdf`；`required_tag_present` 为 `false`。
- 检查正式通知，而不是相信 case summary。通知质量为 `defective`，缺陷为 `missing_appeal_instructions` 和 `missing_ack_deadline`。
- 引用审计事件 `AUD-CASE445-03`。
- 当文件夹或通知控制失败时，审批不能允许关闭。使用 `approval_not_sufficient_when_folder_or_notice_defective`。
- 返回阻断项 `missing_required_files`、`missing_required_tag` 和 `defective_formal_notice`。
- 证据来源顺序使用 `approval_history_folder_notice_audit`。
- 因必需标签缺失，使用 `add_required_tag_before_close`。
- 下一步动作为 `block_close_and_reissue_notice`。

训练锚点和迁移知识：该测试复用 `train_002` 中附条件批准但被阻断的关闭、正式通知缺陷处理、证据来源顺序和 approval gate 标签；复用 `train_001` 中干净关闭与阻断关闭的对比；复用 `train_004` 中审计范围限定和不滥用相邻证据的规则。测试特有工作是找到 `CASE-445` 的 folder、message、approval 和 audit 详情。

常见陷阱：因为审批显示 final 就关闭 case；只列一个缺失文件；忘记缺失必需标签；在 `approval_closeout_gate` 中写自由文本；从 blockers 中漏掉 `missing_required_tag`；或选择确认 payroll 的审计事件而不是 case closeout 审计事件。

评测依据：`eval/rubric.json` 包含 8 个检查，共 18 分：case ID、approval record、folder readiness、notice quality、approval closeout gate、closeout blockers、evidence source/tag action，以及 audit/next action。最高权重点要求规范化 gate、blockers 和 next action。

构造/返工说明：本 notes 文件已根据 reviewer 反馈扩展，以同步当前 `output/answer.json` 和 `eval/rubric.json`，包括 `approval_closeout_gate`、`closeout_blockers`、`evidence_source_order` 和 `folder_required_tag_action`。
