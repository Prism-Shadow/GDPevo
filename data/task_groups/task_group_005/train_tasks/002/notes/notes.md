# train_002 Notes - Entity Access Vendor Onboarding

## English

Data/source lineage: This task belongs to `task_group_005`, an ERP finance shared environment for claims, AP, payments, vendors, compliance review, prepaid accounting, GL balances, and close logs. The task uses the compliance and vendor JSON API surfaces implemented from the shared generated data with seed `5005`: `/api/compliance/objects`, `/api/compliance/profile/{business_id}`, `/api/compliance/ownership/{business_id}`, `/api/compliance/registry/{business_id}`, `/api/compliance/screening/{business_id}`, `/api/compliance/bank/{business_id}`, `/api/compliance/risk/{business_id}`, and `/api/vendors`. The task-local payload `input/payloads/onboarding_batch.json` names batch `VOB-FR-2025-05-TRAIN-002`, as-of date `2025-05-31`, and candidate business IDs `BUS-2025-0009`, `BUS-2025-0017`, `BUS-2025-0022`, `BUS-2025-0036`, and distractor/clean comparator `BUS-2025-0033`.

Task definition: Finance vendor access needs release-control decisions for a real onboarding batch. The solver-visible prompt is intentionally non-procedural: the solver must use the shared API and return the controlled JSON shape in `answer_template.json`. The expected output includes per-business decisions, reportable UBO counts, hard-stop flags, a follow-up business ID set, and one overall release-ready boolean. The final decisions are finance-risk release judgments, not a direct copy of `review_status`.

Scenario fit: This is an entity access and vendor onboarding finance-risk task inside the group’s recurring compliance operation family. It exercises cross-object reconciliation between a business compliance object, detailed compliance endpoints, and the linked vendor record. It also uses noisy source state: `BUS-2025-0022` has source `review_status` approved but should not be released because the bank account is closed, sanctions screening is not run, and the license is expired as of `2025-05-31`.

Material map: `prompt.txt` defines the business request and points to the API and payload contract. `onboarding_batch.json` defines the candidate set and as-of date. `answer_template.json` defines controlled enums and ordering. The shared compliance endpoints expose profile, ownership, registry, screening, bank, and risk facts. `/api/vendors` is needed to detect vendor-level release blockers such as `on_hold`.

Solution and evaluation basis: The construction policy for this task is: approve only when there are no release blockers, screening is clear, bank is verified, required fields are present, the license is current as of `2025-05-31`, no confirmed PEP/shell/sanctions issue exists, and vendor status is active. Escalate when a confirmed PEP, shell-company suspicion, bank closed, bank name mismatch, expired license with other serious blocker, or vendor on-hold condition creates compliance/legal review risk. Use `awaiting_information` when the record is blocked by missing documents or unrun checks without a stronger escalation trigger. Reportable UBO count is the count of unique owner names with `ownership_pct >= 25`; duplicates count once. Follow-up business IDs include all non-approved businesses requiring remediation, compliance review, or missing-information action.

Standard-answer evidence:

- `BUS-2025-0009`: vendor `VEN-0064` is `on_hold`; license expired `2025-02-12`; PEP is `confirmed_pep`; decision `escalate`; reportable UBO count `1`.
- `BUS-2025-0017`: shell suspected, PEP `confirmed_pep`, bank `name_mismatch`; decision `escalate`; reportable UBO count `0`.
- `BUS-2025-0022`: bank `closed`, sanctions `not_run`, license expired `2025-01-01`, possible PEP; source status is approved but release decision is `escalate`; duplicated Owen Grant UBO is deduplicated; reportable UBO count `2`.
- `BUS-2025-0033`: no missing fields, bank verified, screening clear, PEP none, active vendor, current license; decision `approve`; reportable UBO count `2`.
- `BUS-2025-0036`: missing `license` and `beneficial_owner_id`, PEP `not_run`, risk score `62`, bank verified, no shell; decision `awaiting_information`; reportable UBO count `1`.

Evaluation has 8 exact-match scoring points with raw weights `[3, 2, 2, 1, 3, 3, 2, 1]`: SP1 decisions for `0009/0017/0022`; SP2 decisions for `0033/0036`; SP3 UBO counts for `0009/0017/0022`; SP4 UBO counts for `0033/0036`; SP5 hard-stop flags for `0009/0017`; SP6 hard-stop flags for `0022/0033/0036`; SP7 follow-up ID set; SP8 overall release-ready boolean. The evaluator accepts one prediction path argument and normalizes list order for flag maps and follow-up IDs. Likely pitfalls are copying `review_status`, counting duplicate UBO rows, missing the linked vendor status, treating `possible_pep` as the same as `confirmed_pep`, and approving a source-approved record with a closed bank account.

Transfer design: As a train task, this is not a tutorial but it exposes reusable conventions for later entity-access tasks: current review status is not authoritative for release, linked vendor status can create a finance hard stop, compliance detail endpoints should be combined rather than using only the summary row, UBO counts are unique-name counts above the reporting threshold, stale/expired registry facts matter as of the batch date, and output enums should be stable and ordered. A solver that compares an attempted answer with the standard answer can infer these conventions and transfer them to test tasks that contain different business IDs, noisier source statuses, and similar release-control decisions.

Construction record: Author: task-builder subagent for `task_group_005 train_002`. Created: 2026-06-01. Updated: 2026-06-01. Major changes: created solver prompt, batch payload, answer template, standard answer, exact-match evaluator, and bilingual notes for the entity access vendor onboarding finance-risk task.

## 中文

数据和来源：本任务属于 `task_group_005`，共享环境是 ERP 财务 JSON API，覆盖报销、应付、付款、供应商、合规审核、预付、总账余额和关账日志。任务使用固定种子 `5005` 生成的共享合规与供应商数据，主要接口包括 `/api/compliance/objects`、各类 `/api/compliance/.../{business_id}` 明细接口以及 `/api/vendors`。任务本地材料 `input/payloads/onboarding_batch.json` 给出批次 `VOB-FR-2025-05-TRAIN-002`、基准日期 `2025-05-31`，以及候选业务 ID：`BUS-2025-0009`、`BUS-2025-0017`、`BUS-2025-0022`、`BUS-2025-0036` 和作为干扰/干净对照的 `BUS-2025-0033`。

任务定义：财务供应商准入团队需要对一个真实风格的 onboarding 批次作放行控制判断。求解者可见 prompt 不提供步骤化 SOP，只说明业务目标、API 环境和输出契约。输出包括每个 business 的决定、需报告 UBO 数量、hard-stop flags、需要后续跟进的 business ID 集合，以及整体是否可放行。最终决定是财务风险放行判断，不能直接照抄源系统 `review_status`。

场景契合度：本任务对应任务组中的实体准入和供应商 onboarding 合规操作族。它要求把业务合规对象、各类合规明细接口以及关联供应商记录进行交叉核对。数据中故意包含噪声状态，例如 `BUS-2025-0022` 的源系统状态是 approved，但由于银行账户关闭、sanctions 未运行、证照已过期，不能被放行。

材料说明：`prompt.txt` 给出业务请求和 API/输出契约入口；`onboarding_batch.json` 给出候选集合和 as-of 日期；`answer_template.json` 约束枚举、字段和排序。共享合规接口提供 profile、ownership、registry、screening、bank、risk 信息；`/api/vendors` 用于识别供应商层面的阻断，例如 `on_hold`。

解答和评测依据：本任务的构造规则是：只有在没有放行阻断、筛查 clear、银行 verified、必填材料齐全、截至 `2025-05-31` 证照有效、没有 confirmed PEP/shell/sanctions 问题且供应商 active 时，才能 approve。存在 confirmed PEP、疑似 shell、银行 closed、银行 name mismatch、过期证照叠加强阻断或供应商 on_hold 时，应 escalate。仅因缺材料或检查未运行而没有更强升级触发时，标记 `awaiting_information`。需报告 UBO 数量按 `ownership_pct >= 25` 的唯一自然人姓名计数，重复姓名只计一次。`follow_up_business_ids` 包括所有未批准且需要整改、合规复核或补资料的 business。

标准答案证据：`BUS-2025-0009` 的供应商 `VEN-0064` 为 `on_hold`，证照 `2025-02-12` 过期，PEP 为 `confirmed_pep`，所以 `escalate`，UBO 数为 `1`。`BUS-2025-0017` 有 shell suspicion、confirmed PEP、bank name mismatch，所以 `escalate`，UBO 数为 `0`。`BUS-2025-0022` 银行 closed、sanctions not_run、证照 `2025-01-01` 过期且 possible PEP，虽然源状态 approved，仍应 `escalate`；重复的 Owen Grant 去重后 UBO 数为 `2`。`BUS-2025-0033` 没有缺失项、银行 verified、screening clear、PEP none、供应商 active、证照未过期，所以 `approve`，UBO 数为 `2`。`BUS-2025-0036` 缺 `license` 和 `beneficial_owner_id`，PEP not_run，风险分 `62`，银行 verified 且无 shell，因此 `awaiting_information`，UBO 数为 `1`。

评测包含 8 个精确匹配评分点，原始权重为 `[3, 2, 2, 1, 3, 3, 2, 1]`：SP1 检查 `0009/0017/0022` 决策；SP2 检查 `0033/0036` 决策；SP3 检查 `0009/0017/0022` UBO 数；SP4 检查 `0033/0036` UBO 数；SP5 检查 `0009/0017` hard-stop flags；SP6 检查 `0022/0033/0036` hard-stop flags；SP7 检查 follow-up ID 集合；SP8 检查整体 release-ready 布尔值。评测器接收一个 prediction path 参数，并对 flags 和 follow-up 列表排序后比较。常见错误包括照抄 `review_status`、重复计算 UBO、漏看关联供应商状态、把 possible PEP 等同于 confirmed PEP、以及把银行关闭但源状态 approved 的记录错误放行。

迁移设计：作为训练任务，本任务不是教程，但会暴露可迁移的业务约定：当前 review status 不等于放行结论；关联供应商状态可能造成财务 hard stop；需要组合多个 compliance 明细接口而不是只看 summary；UBO 数量按达到阈值的唯一姓名去重；registry 的过期日期要按批次日期判断；输出枚举和排序应稳定。求解者在盲做并对照标准答案后，可以把这些经验迁移到测试任务中不同 business ID、更复杂噪声状态和类似放行控制判断上。

构造记录：作者：`task_group_005 train_002` task-builder subagent。创建日期：2026-06-01。更新日期：2026-06-01。主要变更：创建实体准入供应商 onboarding 财务风险任务的 solver prompt、批次 payload、答案模板、标准答案、精确匹配评测器和双语 notes。
