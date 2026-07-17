# test_003 Hidden Notes

## English

### Data lineage and task definition

This task belongs to `task_group_002`, scenario `SCN_002_crm_b2b_quote_account_response`, and uses the milestone engagement response family. It targets opportunity `OPP-TE-POLARIS` for customer `CUST-POLARIS` / Polaris Cold Chain and is a test analogue to the training milestone reconciliation tasks. The solver-visible files are English-only; this notes file is bilingual as requested.

The task uses the shared MedBridge Sales Ops API described in `task_factory/scratch/env_blueprint.md`. The prompt asks the solver to use the runner-provided `API_BASE_URL` and reconcile opportunity, invoice, payment, revenue journal, event, and voucher records. It also gives controller-confirmed review facts for the Polaris account contact and overdue phase-2 due date so the test remains aligned to the task-builder assignment.

### Scenario fit and material map

This is a CRM/account-management reconciliation workflow, not a quote calculation. The expected work is to confirm the won opportunity value, tie the value to two phased invoices, distinguish paid/recognized phase 1 from unpaid/overdue phase 2, verify revenue recognition only for paid milestones, and create CRM follow-up work for collection and event invitation.

Relevant shared API entry points include `/api/opportunities`, `/api/customers`, `/api/invoices`, `/api/payments`, `/api/revenue-journals`, `/api/events`, `/api/vouchers`, `/api/policies`, and `/api/search?q=Polaris`. `input/prompt.txt` provides the realistic account request and review overrides. `input/payloads/answer_template.json` defines the exact output shape, stable IDs, controlled enums, and money/date formats. `output/answer.json` is the canonical answer. `eval/eval.py` implements eight weighted exact-match scoring points, and `eval/eval.sh` is the entry point that accepts an optional candidate path.

### Solution and evaluation basis

Canonical facts: opportunity `OPP-TE-POLARIS` belongs to `CUST-POLARIS` / Polaris Cold Chain, is stage `WON`, and has won amount `120000.00`. Phase `POL-P1` / invoice `INV-POLARIS-P1` totals `62000.00`, is paid, has `62000.00` paid and `0.00` unpaid, is not overdue, and is recognized. Phase `POL-P2` / invoice `INV-POLARIS-P2` totals `58000.00`, is unpaid, has `0.00` paid and `58000.00` unpaid, is overdue as of `2026-06-01`, and has due date `2026-05-20`. The outstanding balance is `58000.00`, and the milestone total matches the won amount.

Revenue recognition status is `COMPLETE_FOR_PAID_MILESTONES`; recognized milestones are `["MS1"]` using the reporting label; there are no missing required recognized milestones; recognized amount is `62000.00`. The event is `EVT-POLARIS-GALA`, event date `2026-06-18`, status `LIVE`, voucher `POLARIS100VIP`, discount `100.00`, and max uses `3`.

The collection follow-up task is type `COLLECTION`, action `ESCALATE_COLLECTION`, linked to customer `CUST-POLARIS`, opportunity `OPP-TE-POLARIS`, contact Amara Singh, milestone `POL-P2`, amount due `58000.00`, and due date `2026-06-01`. The invitation follow-up task is type `EVENT_INVITATION`, action `SEND_EVENT_INVITATION`, linked to the same customer/opportunity/contact, event `EVT-POLARIS-GALA`, voucher `POLARIS100VIP`, and due date `2026-06-10`.

Scoring points and raw weights: opportunity/account identity (1), reporting milestone labels with source phase IDs and phase totals (3), payment/outstanding balance (2), paid-milestone due-date nulling and collection convention (10), revenue recognition state (3), event/voucher action (2), CRM follow-up actions and due dates (2), and contact linkage (1). The evaluator normalizes by total raw weight `24`, compares currency at cent precision, normalizes enum casing, and requires stable IDs for milestones, source phases, invoices, event, voucher, customer, and opportunity.

Likely pitfalls include using stale account metadata instead of Amara Singh, using an unconfirmed phase-2 due date, treating the won opportunity as fully settled, recognizing revenue for the unpaid milestone, missing the escalation action, or omitting the event/voucher from the invitation follow-up.

### Transfer design

This test checks whether solvers transfer milestone engagement conventions from the train tasks: opportunity value should equal milestone invoice totals; unpaid overdue milestones drive collection escalation; paid completed milestones require revenue recognition verification; unpaid milestones should not be recognized yet; event and voucher facts should become CRM invitation work; and follow-up tasks must be linked to customer, opportunity, contact, and stable business records.

### Construction record

Author: Codex main agent. Created: 2026-06-01. Updated: 2026-06-01. Major changes: created the `test_003` prompt, answer template, canonical answer, bilingual notes, and exact-match evaluator within the assigned write scope.

## 中文

### 数据来源与任务定义

本任务属于 `task_group_002`，来源场景为 `SCN_002_crm_b2b_quote_account_response`，使用 milestone engagement response 业务线。目标记录是 opportunity `OPP-TE-POLARIS`，客户为 `CUST-POLARIS` / Polaris Cold Chain，是训练集中 milestone reconciliation 任务的测试版。求解器可见文件全部为英文；本 notes 文件按要求提供中英双语说明。

任务使用 `task_factory/scratch/env_blueprint.md` 描述的共享 MedBridge Sales Ops API。prompt 要求求解器使用 runner 提供的 `API_BASE_URL`，核对 opportunity、invoice、payment、revenue journal、event 和 voucher 记录。同时，prompt 提供 Polaris 账户联系人和第二阶段逾期 due date 的 controller-confirmed review facts，以保证测试与 task-builder assignment 中指定的事实一致。

### 场景适配与材料地图

这是 CRM / account management 的核对工作流，不是报价计算。预期工作是确认已赢单商机金额，将金额和两个阶段 invoice 对齐，区分第一阶段已付款且已确认收入与第二阶段未付款且逾期，验证收入确认只覆盖已付款 milestone，并为 collection 和 event invitation 创建 CRM follow-up work。

相关共享 API 入口包括 `/api/opportunities`、`/api/customers`、`/api/invoices`、`/api/payments`、`/api/revenue-journals`、`/api/events`、`/api/vouchers`、`/api/policies` 和 `/api/search?q=Polaris`。`input/prompt.txt` 提供真实业务请求和 review override。`input/payloads/answer_template.json` 定义精确输出结构、稳定 ID、受控枚举以及金额和日期格式。`output/answer.json` 是标准答案。`eval/eval.py` 实现八个带权重的精确匹配评分点，`eval/eval.sh` 是入口脚本，并支持可选候选答案路径。

### 答案与评测依据

标准事实：opportunity `OPP-TE-POLARIS` 属于 `CUST-POLARIS` / Polaris Cold Chain，stage 为 `WON`，won amount 为 `120000.00`。Phase `POL-P1` / invoice `INV-POLARIS-P1` 总额 `62000.00`，已付款，已付 `62000.00`，未付 `0.00`，不逾期，并已收入确认。Phase `POL-P2` / invoice `INV-POLARIS-P2` 总额 `58000.00`，未付款，已付 `0.00`，未付 `58000.00`，截至 `2026-06-01` 已逾期，due date 为 `2026-05-20`。outstanding balance 为 `58000.00`，两个 milestone 总额等于 won amount。

收入确认状态为 `COMPLETE_FOR_PAID_MILESTONES`；已确认 milestone 使用报告标签 `["MS1"]`；没有缺失的必需收入确认；recognized amount 为 `62000.00`。活动为 `EVT-POLARIS-GALA`，活动日期 `2026-06-18`，状态 `LIVE`，voucher 为 `POLARIS100VIP`，discount 为 `100.00`，max uses 为 `3`。

collection follow-up task 的类型为 `COLLECTION`，动作为 `ESCALATE_COLLECTION`，关联客户 `CUST-POLARIS`、商机 `OPP-TE-POLARIS`、联系人 Amara Singh、milestone `POL-P2`、amount due `58000.00`，due date 为 `2026-06-01`。invitation follow-up task 的类型为 `EVENT_INVITATION`，动作为 `SEND_EVENT_INVITATION`，关联同一客户、商机和联系人，以及 event `EVT-POLARIS-GALA`、voucher `POLARIS100VIP`，due date 为 `2026-06-10`。

评分点和原始权重：opportunity/account identity (1)，带 source phase ID 的报告用 milestone 标签和阶段合计 (3)，payment/outstanding balance (2)，已付款 milestone due date 置空与催收约定 (10)，revenue recognition state (3)，event/voucher action (2)，CRM follow-up actions and due dates (2)，contact linkage (1)。总原始权重为 `24`，评测器按比例归一化；金额按美分精度比较，枚举会统一大小写，并要求 milestone、source phase、invoice、event、voucher、customer 和 opportunity 使用稳定 ID。

常见错误包括：使用过期账户元数据而不是 Amara Singh；使用未确认的第二阶段 due date；把已赢单商机当成已全部结清；为未付款 milestone 做收入确认；漏掉 escalation action；或者在 invitation follow-up 中漏掉 event/voucher。

### 迁移设计

本测试检查求解器是否能迁移训练任务中的 milestone engagement 规则：opportunity value 应等于 milestone invoice totals；未付款且逾期的 milestone 触发 collection escalation；已完成且已付款的 milestone 需要验证收入确认；未付款 milestone 暂不确认收入；event 和 voucher 信息应转化为 CRM invitation work；follow-up task 必须稳定关联 customer、opportunity、contact 和业务记录 ID。

### 构造记录

作者：Codex main agent。创建日期：2026-06-01。更新日期：2026-06-01。主要变更：在指定写入范围内创建 `test_003` 的 prompt、answer template、标准答案、双语 notes 和精确匹配 evaluator。
