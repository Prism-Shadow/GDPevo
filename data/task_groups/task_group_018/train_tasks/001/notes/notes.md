# train_001 Notes

## English Review Notes

Data/source lineage: This task belongs to `SCN_018_court_clerk_disposition_orders_and_financial_entries`, using source examples `E001`, `E002`, and `E003` as the task-group background and `E001` as the closest operational ancestor. The shared generated Court Operations Portal contains the Redwood County target cases `RC-25-0412`, `RC-25-0418`, `RC-24-0987`, and `RC-25-0502`, their charge rows, docket rows, Redwood fee schedule, payment policy, and Arkansas sentencing-order form metadata. Task-local solver-visible payloads are `hearing_notes.md`, `clerk_audit_memo.md`, and `finance_queue_extract.json`.

Task definition: The solver acts as a criminal division clerk preparing a June 9, 2025 Redwood County Arkansas sentencing closeout. They must reconcile hearing notes and queue extracts against the portal, identify material conflicts, decide which cases are disposition-ready, calculate corrected financial entries, summarize docket entries, and total the register. The required answer shape is declared in `input/payloads/answer_template.json`.

Scenario fit: The work mirrors the source Arkansas sentencing closeout pattern: multiple criminal cases, noisy courtroom notes, stale fee entries, counsel-code ambiguity, signed-order status checks, and register balancing. It also reinforces broader task-group habits around using current schedules, not adding unsupported fees, and preserving audit findings separately from final closeout entries.

Material map: `GET /api/cases` supplies official case identity, counsel, status, judge, and disposition-date records. `GET /api/charges` supplies target charge rows, but `RC-25-0418` must be reconciled with the courtroom conviction note and case note rather than blindly accepting a stale nolle field. `GET /api/docket-entries` gives system status and import context. `GET /api/fee-schedules` provides the current Redwood court cost, public defender user fee, and current-vs-stale drug assessment. `GET /api/payment-policies` confirms no account fee and tells the solver not to use stale or unsupported financial additions. `hearing_notes.md` records the actual hearing outcomes and includes deliberate shorthand errors. `clerk_audit_memo.md` identifies suspected conflicts without giving final totals. `finance_queue_extract.json` is a noisy queued worksheet with wrong DOB, counsel, status, and fee values.

Solution and evaluation basis: The standard answer records five audit findings: `RC-25-0412` identity correction, `RC-25-0412` counsel correction, `RC-25-0418` current fee schedule correction, `RC-24-0987` no-departure correction, and `RC-25-0502` unsigned-order hold. Final identities/counsel are Evan Simmons DOB 1991-04-18 appointed-private Lena Ortiz; Marisol Vega DOB 1988-11-22 public defender C. Hill; Tanya Morales DOB 1979-07-03 retained James Pell; Nolan Reed DOB 2000-01-09 public defender C. Hill. `RC-25-0412`, `RC-25-0418`, and `RC-24-0987` are posted; `RC-25-0502` is held as deferred with no financial entry. Fees are $150 for `RC-25-0412`, $850 for `RC-25-0418`, $650 for `RC-24-0987`, and $0 for `RC-25-0502`, producing register totals of 3 assessed cases, 1 held case, $750 fines, $450 court costs, $250 assessments, $200 user fees, and $1,650 grand total.

The evaluator has eight whole-point scoring checks with raw weights `[2, 2, 3, 2, 3, 2, 2, 2]`: audit findings; identity/counsel values; status/action/date decisions; charge sentence and departure classifications; fee item inclusion; per-case totals; docket entry summary codes; and register aggregate totals. These cover distinct outcomes and award no partial credit inside a point.

Likely model pitfalls: copying the finance queue totals; adding the public defender fee to appointed-private counsel; using the stale $125 drug assessment; treating `RC-25-0502` as disposed from the draft worksheet; accepting the legacy departure flag for `RC-24-0987`; or collapsing audit findings into prose that loses controlled codes.

Transfer design: As a train task, this is a real full closeout rather than a tutorial. A fewshot skill can infer that criminal closeout tasks require explicit conflict logging, current effective-date fee schedules, conditional public-defender user-fee treatment, no unsupported add-on fees, signed-order status discipline, controlled docket summary codes, and separate per-case versus register totals.

Construction record: Created by Codex task-builder subagent for train_001 on 2026-07-18. Files added under `task_group/task_group_018/train_tasks/001/` only. Major changes: built solver-visible payloads, answer template, standard answer, deterministic evaluator, and bilingual notes for the Redwood County criminal sentencing closeout.

## 中文审查说明

数据和来源：本任务属于 `SCN_018_court_clerk_disposition_orders_and_financial_entries`，任务组背景来自 `E001`、`E002`、`E003`，其中 `E001` 是最接近的阿肯色刑事判决结案示例。共享的 Court Operations Portal 生成数据中包含 Redwood County 的四个目标案件 `RC-25-0412`、`RC-25-0418`、`RC-24-0987`、`RC-25-0502`，以及对应的案件、指控、案卷、费用表、支付政策和表格元数据。本任务本地可见材料包括 `hearing_notes.md`、`clerk_audit_memo.md` 和 `finance_queue_extract.json`。

任务定义：解题者扮演刑事庭书记员，为 2025-06-09 Redwood County 阿肯色刑事判决庭次做结案包。需要把庭审记录、审计备忘和财务队列与门户数据核对，列出冲突，判断哪些案件可以结案入账，计算正确费用，形成案卷摘要，并汇总登记簿金额。

场景匹配：本任务保留了源场景中的多案件刑事结案、庭审记录与 CMS 冲突、旧费用表陷阱、律师身份含糊、签署命令状态判断、费用登记簿汇总等难点。它也强化了任务组共同规则：使用当前生效费用表，不增加无依据费用，将审计发现和最终结案结果分开记录。

材料说明：`GET /api/cases` 用于核对身份、律师、状态、法官和处分日期；`GET /api/charges` 用于核对指控，但 `RC-25-0418` 需要结合庭审定罪记录和案件备注处理；`GET /api/docket-entries` 提供系统状态和导入线索；`GET /api/fee-schedules` 提供 Redwood 当前法院成本、公设辩护人使用费以及新旧毒品评估费；`GET /api/payment-policies` 说明不能加入账户费等无依据费用。本地三个 payload 则模拟真实办公室中带错误的庭审速记、审计提示和财务队列。

答案和评估依据：标准答案包含五个审计发现：`RC-25-0412` 身份更正、`RC-25-0412` 律师身份更正、`RC-25-0418` 当前费用表更正、`RC-24-0987` 无偏离判决更正、`RC-25-0502` 因未签署命令而暂缓。三个案件入账，一个案件暂缓。每案金额为 150、850、650、0 美元；总计为 3 个入账案件、1 个暂缓案件、罚金 750、法院成本 450、评估费 250、公设辩护人使用费 200、总额 1650 美元。

评估器有 8 个整点评分项，原始权重为 `[2, 2, 3, 2, 3, 2, 2, 2]`，分别检查审计发现、身份和律师、状态和处理动作、指控与量刑、费用项目、每案金额、案卷摘要、登记簿总计。每个评分项内部只给全对或零分，不做部分分。

常见错误：直接复制财务队列；给指定私人律师案件加公设辩护人使用费；使用过期的 125 美元毒品评估费；把 `RC-25-0502` 当成已处分案件；接受 `RC-24-0987` 的旧偏离判决标签；或用自由文本代替受控代码导致结果不可判定。

迁移设计：作为训练任务，它提供真实完整业务样本。少样本技能可以从标准答案推断出刑事结案任务的做法：显式记录冲突，按生效日期使用费用表，区分公设辩护人与指定私人律师，不添加无依据费用，未签署命令不入账，使用受控案卷摘要代码，并区分每案金额和登记簿总额。

构造记录：由 Codex train_001 任务构造子代理于 2026-07-18 创建。只在 `task_group/task_group_018/train_tasks/001/` 下新增文件。主要变更包括可见材料、答案模板、标准答案、确定性评估器和双语 notes。
