# Task Notes / 任务说明

## English

Task definition and business objective: This test task audits three lifecycle document folders and related messages, then decides which folders are not ready, which notices are defective, which audit events support the document/notice findings, and what records remediation should occur.

Visible inputs and Web evidence: The solver-visible prompt names folders `DOC-ERIN-ONB`, `DOC-PRIYA-POL`, and `DOC-MARCO-PAY` and gives the local PeopleOps Console entry point. Public evidence should be gathered from Documents folder checklist/details, attachment or file lists, Messages notice inspection, related Policy Cases, Audit Log detail, and any policy viewer content that defines required tags or notice standards.

Expected reasoning and answer basis:
- Review all three folders: `DOC-ERIN-ONB`, `DOC-PRIYA-POL`, and `DOC-MARCO-PAY`.
- `DOC-ERIN-ONB` is not ready because it is missing `benefits-election.pdf`, `executive-exception-approval.pdf`, and required tag `PolicyException2026`.
- `DOC-PRIYA-POL` is not ready because it is missing `decision-record.txt` and required tag `PolicyException2026`.
- `DOC-MARCO-PAY` has no missing required files or tags.
- Use `folder_checklist_comparison` as folder evidence source.
- Identify defective messages `MSG-ERIN-445` and `MSG-PRIYA-118`, using `message_notice_inspection` as notice evidence source.
- Supporting document/notice audit events are `AUD-CASE445-03` and `AUD-DOC118-06`.
- Exclude `AUD-EMP118-LEAVE-04` because it supports leave source precedence, not document/notice findings.
- Set `audit_scope` to `document_notice_findings_only`.
- Remediation should be `open_records_remediation`, owner `Records`, and notice action `reissue_defective_notices`.

Train anchors and transferred knowledge: This test combines `train_002` for folder/notice closeout blocking, evidence source order, `Records` ownership, and `reissue_defective_notices`; `train_004` for audit-scope exclusion of adjacent leave events; and `train_001` for the contrast between clean folders/records and blocked lifecycle closeout. The test-specific work is applying the SOP to three folders rather than one case.

Likely pitfalls: Treating document titles as proof of readiness; missing required tags while finding missing files; including `AUD-EMP118-LEAVE-04` as support because it shares an employee; omitting `audit_scope`; using `People Ops Compliance` instead of `Records` for this records-remediation owner field; or writing prose instead of normalized remediation labels.

Evaluator/scoring basis: `eval/rubric.json` has seven checks with 13 total points: reviewed folders, readiness/files, missing tags/source, defective messages/source, supporting audit events/scope, excluded audit events, and remediation action/owner/notice action. The remediation check is high value and requires all three normalized fields.

Construction/rework note: This notes file was expanded after reviewer feedback to include current source fields, audit-scope fields, exclusion fields, remediation owner, and notice action from `output/answer.json` and `eval/rubric.json`.

## 中文

任务定义和业务目标：本测试任务审核三个生命周期文档文件夹及相关消息，然后判断哪些文件夹未就绪、哪些通知有缺陷、哪些审计事件支撑文档/通知发现，以及应执行什么 records remediation。

可见输入和网页证据：求解者可见 prompt 指定文件夹 `DOC-ERIN-ONB`、`DOC-PRIYA-POL` 和 `DOC-MARCO-PAY`，并提供本地 PeopleOps Console 入口。公开证据应从 Documents 文件夹 checklist/详情、附件或文件列表、Messages notice inspection、相关 Policy Cases、Audit Log detail，以及定义必需标签或通知标准的 policy viewer 中获取。

预期推理和答案依据：
- 审核三个文件夹：`DOC-ERIN-ONB`、`DOC-PRIYA-POL` 和 `DOC-MARCO-PAY`。
- `DOC-ERIN-ONB` 未就绪，因为缺少 `benefits-election.pdf`、`executive-exception-approval.pdf` 和必需标签 `PolicyException2026`。
- `DOC-PRIYA-POL` 未就绪，因为缺少 `decision-record.txt` 和必需标签 `PolicyException2026`。
- `DOC-MARCO-PAY` 没有缺少的必需文件或标签。
- 文件夹证据来源使用 `folder_checklist_comparison`。
- 识别有缺陷消息 `MSG-ERIN-445` 和 `MSG-PRIYA-118`，通知证据来源使用 `message_notice_inspection`。
- 支撑文档/通知发现的审计事件是 `AUD-CASE445-03` 和 `AUD-DOC118-06`。
- 排除 `AUD-EMP118-LEAVE-04`，因为它支撑的是休假来源优先级，不是文档/通知发现。
- 将 `audit_scope` 设为 `document_notice_findings_only`。
- 整改应为 `open_records_remediation`，负责人 `Records`，通知动作为 `reissue_defective_notices`。

训练锚点和迁移知识：该测试组合了 `train_002` 中的 folder/notice closeout blocking、证据来源顺序、`Records` 负责人和 `reissue_defective_notices`；`train_004` 中对相邻 leave event 的 audit-scope exclusion；以及 `train_001` 中干净记录与阻断 lifecycle closeout 的对比。测试特有工作是把 SOP 应用到三个文件夹，而不是单个 case。

常见陷阱：把文档标题当作就绪证明；找到缺失文件但漏掉必需标签；因为同属一个员工就把 `AUD-EMP118-LEAVE-04` 纳入支持证据；遗漏 `audit_scope`；在 records-remediation owner 字段中使用 `People Ops Compliance` 而不是 `Records`；或用自由文本替代规范化整改标签。

评测依据：`eval/rubric.json` 包含 7 个检查，共 13 分：reviewed folders、readiness/files、missing tags/source、defective messages/source、supporting audit events/scope、excluded audit events、remediation action/owner/notice action。remediation check 权重较高，并要求三个规范化字段全部匹配。

构造/返工说明：本 notes 文件已根据 reviewer 反馈扩展，补入当前 `output/answer.json` 和 `eval/rubric.json` 中的 source fields、audit-scope fields、exclusion fields、remediation owner 和 notice action。
