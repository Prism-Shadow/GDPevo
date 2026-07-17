# Notes

## English

Data/source lineage: This test task belongs to `SCN_012_erp_hr_employee_lifecycle` and adapts the recruitment, offer, notice, payroll handoff, and audit-control patterns into opening `REQ-OPS-19`. The solver-visible prompt gives only the business request, local URL, login, and output contract. The answer facts must be found in the PeopleOps Console.

Task definition: The solver must reconcile the candidate outcome, accepted offer, cost ledger, waitlist notice defect, payroll handoff gate, draft exclusion, and supporting audit event. Evidence is intentionally distributed across Recruitment candidate review, offer register, cost ledger, notice inspection, Messages, Policy Viewer, related case detail, and Audit Log.

Solution and evaluation basis: Gold identifies `CAND-OPS-1902` as selected, `CAND-OPS-1901` as waitlisted, and `CAND-OPS-1903` plus `CAND-OPS-1904` as rejected. Offer `OFFER-OPS-1902` is accepted with base salary `124000`. Cost ledger total is `7350`. The defective notice belongs to `CAND-OPS-1901` with defect `missing_waitlist_status`, requiring `reissue_waitlist_notice_not_rejection`. The already-sent rejected-candidate notices require `no_action`. Payroll handoff requires `create_submitted_assignment_after_acceptance`, with gate `accepted_offer_only`, required status `submitted_after_acceptance`, policy `PAY-SRC-001`, and exclusion of draft precheck `PAY-PRECHECK-OPS-1901-D`. Supporting audit event is `AUD-REQOPS-11`.

Transfer design: This task deliberately combines 2-3 train anchors. `train_003` transfers candidate outcome reconstruction, accepted-offer use, recruitment cost summing, and notice follow-up conventions. `train_005` transfers submitted-versus-draft payroll assignment handling. `train_002` transfers formal notice defect review and use of audit evidence. The test-specific work is finding the new opening's evidence and applying those conventions across more modules.

Likely pitfalls: Copying the recruitment summary without opening the review panels; treating the waitlisted candidate as offer-eligible; accepting a draft payroll precheck; omitting one rejected candidate; taking notice quality from status alone without inspecting the message; or citing the case instead of the audit event.

Construction record: Author: Codex task-builder. Created: 2026-06-05. Updated: 2026-06-05 after rework to remove prompt leakage and make the recruitment task Web-first.

## 中文

数据和来源：本测试任务属于 `SCN_012_erp_hr_employee_lifecycle`，将招聘、offer、通知、薪资交接和审计控制模式迁移到 opening `REQ-OPS-19`。求解者可见 prompt 只提供业务请求、本地 URL、登录信息和输出契约。答案事实必须在 PeopleOps Console 中查找。

任务定义：求解者需要核对候选人结果、已接受 offer、成本台账、候补通知缺陷、薪资交接门槛、草稿排除规则和支撑审计事件。证据有意分布在 Recruitment 的候选人复核、offer register、cost ledger、notice inspection、Messages、Policy Viewer、关联 case 详情和 Audit Log 中。

答案和评估依据：标准答案将 `CAND-OPS-1902` 识别为入选，`CAND-OPS-1901` 识别为候补，`CAND-OPS-1903` 与 `CAND-OPS-1904` 识别为拒绝。`OFFER-OPS-1902` 已接受，base salary 为 `124000`。成本台账合计为 `7350`。有缺陷通知属于 `CAND-OPS-1901`，缺陷为 `missing_waitlist_status`，需要 `reissue_waitlist_notice_not_rejection`。已发送且合规的拒绝通知需要 `no_action`。薪资交接动作为 `create_submitted_assignment_after_acceptance`，门槛为 `accepted_offer_only`，所需状态为 `submitted_after_acceptance`，政策为 `PAY-SRC-001`，并排除草稿 precheck `PAY-PRECHECK-OPS-1901-D`。支撑审计事件为 `AUD-REQOPS-11`。

迁移设计：该任务刻意组合 2-3 个训练锚点。`train_003` 迁移候选人结果重建、已接受 offer 使用、招聘成本求和和通知 follow-up 约定。`train_005` 迁移 submitted 与 draft 薪资分配处理。`train_002` 迁移正式通知缺陷复核和审计证据使用。测试特有工作是找到新 opening 的证据，并跨更多模块应用这些约定。

常见陷阱：只复制招聘摘要而不打开复核面板；把候补候选人当成可发 offer；接受草稿 payroll precheck；漏掉一个拒绝候选人；只凭状态判断通知质量而不检查消息；或引用 case 而非审计事件。

构建记录：作者：Codex task-builder。创建日期：2026-06-05。更新日期：2026-06-05，rework 后移除 prompt 泄露并改为 Web-first 招聘任务。
