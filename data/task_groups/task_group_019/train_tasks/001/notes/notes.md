# train_001 Notes

## English

### Data and Source Lineage

This task belongs to `SCN_019_regulatory_licensing_eligibility_and_compliance_review`, using the contractor-eligibility workflow represented by source example `E001` and the shared task-group design in `scratch/task_group_design.md`. The shared environment data is generated in `task_group/task_group_019/env/generate_data.py` with seed `19019` and stored in `task_group/task_group_019/env/data/licensing.db`; the manifest identifies `train_001` target application ids `C-TR1-001` through `C-TR1-008`.

No task-local business-data payload is added beyond `input/payloads/answer_template.json`. Solvers must use the public environment endpoints rooted at `<TASK_ENV_BASE_URL>` and may not inspect the hidden database, manifest, generator, notes, standard answer, or evaluator.

### Task Definition and Scenario Fit

The solver is acting as a Senior Licensing Examiner reviewing an escalated Q2 contractor application batch. The visible prompt gives the eight application ids, the environment base URL placeholder, relevant contractor endpoints, and the required JSON output schema. The expected work is to reconcile policies, application fields, bond and insurance records, prior license status, violations, correspondence, and inspection notes into application-level determinations and a batch summary.

This matches the source contractor example because the business problem is not a single lookup: it requires multi-record reconciliation, source freshness judgment, current-policy application, risk tiering, and structured final actions for a licensing office.

### Material Map

- `GET /api/policies`: contractor policy thresholds and the prior baseline used for policy-impact analysis.
- `GET /api/contractor/applications`: target application attributes including trade, requested class, experience, endorsement status, prior license id, and submitted date.
- `GET /api/contractor/bonds`: active, cancelled, and old bond records; only a current active bond with sufficient amount satisfies the bond requirement.
- `GET /api/contractor/insurance`: active, pending, expired, and insufficient liability coverage records.
- `GET /api/contractor/license-history`: prior license status; active suspension is blocking.
- `GET /api/contractor/violations`: open serious violations block release; open minor violations require review; resolved history informs risk but is not an automatic denial.
- `GET /api/contractor/correspondence`: stale or unverified correspondence must not override current public records.
- `GET /api/contractor/inspections`: failed or conditional adverse findings create document or safety actions.
- `POST /api/sql`: optional read-only querying surface over the same public tables.

### Solution Basis

The current contractor policy rows define minimum bond, insurance, experience, and endorsement expectations by trade and class. The prior contractor baseline reduces bond minimums by 10,000 and does not require the specialty endorsement baseline, which is used only to flag policy-impact cases. The standard answer applies current public records first, treats applicant-only or stale correspondence as non-overriding, and separates historical resolved issues from current blocking issues.

Application outcomes:

- `C-TR1-001`: `HOLD`; bond is 25,000 against a 30,000 Plumbing minimum, endorsement is missing, and experience is 3 against a 4-year minimum. The bond shortfall is policy impacted.
- `C-TR1-002`: `HOLD`; endorsement is pending, the current insurance record expired on `2025-04-15`, and the conditional inspection has `DOC_GAP`.
- `C-TR1-003`: `DENY`; prior license `CL-CTR1003` is suspended, insurance is pending, and the failed inspection requires a safety recheck.
- `C-TR1-004`: `HOLD`; the current bond record is cancelled as of `2025-05-30`. Resolved violations do not independently block the application.
- `C-TR1-005`: `DENY`; there is an open serious violation, insurance is short by 250,000, endorsement is pending, and experience is 1 against a 3-year minimum. The specialty endorsement issue is policy impacted.
- `C-TR1-006`: `HOLD`; experience is 4 against a 5-year Electrical minimum. Other current financial records are sufficient.
- `C-TR1-007`: `HOLD`; bond is 25,000 against a 30,000 Plumbing minimum, endorsement is missing, there is an open minor violation requiring review, and the failed inspection has `DOC_GAP`. The bond shortfall is policy impacted.
- `C-TR1-008`: `HOLD`; endorsement is pending and the current insurance record expired on `2025-04-15`.

High-risk applications are `C-TR1-003` and `C-TR1-005`. Policy-impacted applications are `C-TR1-001`, `C-TR1-005`, and `C-TR1-007`. Stale or unverified correspondence identifiers are `COR-C-TR1-001-1`, `COR-C-TR1-002-1`, `COR-C-TR1-004-1`, and `COR-C-TR1-007-1`.

### Evaluation Basis

The evaluator uses eight whole scoring points with raw weights totaling 16:

- `SP001`, weight 1: exactly the eight target applications in ascending `application_id` order.
- `SP002`, weight 3: correct `APPROVE`/`HOLD`/`DENY` determination for every target application.
- `SP003`, weight 3: correct deficiency code set for each target application.
- `SP004`, weight 2: correct required action set for each target application.
- `SP005`, weight 2: correct risk tiers and high-risk summary set.
- `SP006`, weight 2: correct policy-impact flags and policy-impact summary set.
- `SP007`, weight 2: correct approve, hold, and deny summary counts.
- `SP008`, weight 1: correct stale or unverified correspondence identifiers.

Each point is pass/fail only; there is no within-point fractional credit. The scoring dimensions cover target coverage, determinations, deficiencies, operational actions, risk tiering, policy-change impact, batch rollup, and source-conflict handling.

Likely model pitfalls include using expired or cancelled records as current, letting unverified correspondence override registry records, treating resolved violations as automatic denials, missing active suspension, ignoring insurance expiration, failing to compare current policy to the prior baseline for policy-impact flags, and returning non-controlled free text instead of the template enums.

### Transfer Design

This is a formal train task, not a tutorial. A fewshot skill can infer recurring contractor-review habits from the prompt and answer: inspect the shared endpoint families, prioritize current policy and public registry records over stale correspondence, evaluate bond amount and status together, evaluate insurance status and expiration together, treat active suspension and unresolved serious violations as blocking, separate resolved history from current defects, use controlled deficiency/action codes, and produce consistent application-level and summary-level outputs. These conventions are intended to transfer to the contractor test tasks and to the second contractor train task without making the test answers template copies.

### Construction Record

- Author: task-builder-train-001 / Codex
- Created: 2026-07-18
- Updated: 2026-07-18
- Major changes: Created the complete train_001 task package under `train_tasks/001/`.

## 中文

### 数据与来源

本任务属于 `SCN_019_regulatory_licensing_eligibility_and_compliance_review`，采用源示例 `E001` 中的 contractor eligibility review 工作流，并遵循 `scratch/task_group_design.md` 的任务组设计。共享环境数据由 `task_group/task_group_019/env/generate_data.py` 使用 seed `19019` 生成，存放在隐藏的 SQLite 数据库中；manifest 指定 `train_001` 的目标申请为 `C-TR1-001` 到 `C-TR1-008`。

除 `input/payloads/answer_template.json` 外，本任务没有额外的本地业务数据 payload。求解者只能使用 `<TASK_ENV_BASE_URL>` 下的公开环境端点，不能查看隐藏数据库、manifest、生成脚本、notes、标准答案或 evaluator。

### 任务定义与场景匹配

求解者扮演 State Contractors Licensing Board 的 Senior Licensing Examiner，审查一批 Q2 升级处理的 contractor applications。可见 prompt 提供八个申请编号、环境 base URL 占位符、相关 contractor endpoints，以及必须返回的 JSON schema。预期工作是把 policy、application、bond、insurance、license history、violations、correspondence 和 inspections 结合起来，形成每个申请的 eligibility decision 和批次 summary。

该任务与源 contractor 示例一致，因为它不是单表查询，而是需要多来源核对、来源新旧判断、当前政策适用、风险分级和结构化行政处理动作。

### 材料地图

- `GET /api/policies`：contractor 政策门槛和用于 policy-impact 的 prior baseline。
- `GET /api/contractor/applications`：目标申请的 trade、class、experience、endorsement、prior license 和 submitted date。
- `GET /api/contractor/bonds`：active、cancelled、old bond；只有当前 active 且金额足够的 bond 满足要求。
- `GET /api/contractor/insurance`：active、pending、expired 或金额不足的 liability coverage。
- `GET /api/contractor/license-history`：prior license 状态；active suspension 是阻断性事实。
- `GET /api/contractor/violations`：open serious violation 阻断放行；open minor violation 需要 review；resolved history 不自动 denial。
- `GET /api/contractor/correspondence`：stale 或 unverified correspondence 不能覆盖当前公共记录。
- `GET /api/contractor/inspections`：fail 或 conditional 且有不利 finding 时产生 document 或 safety action。
- `POST /api/sql`：对同一公开表的可选只读查询入口。

### 解答依据

当前 contractor policy 按 trade 和 class 定义 minimum bond、insurance、experience 和 endorsement。prior contractor baseline 将 bond minimum 降低 10,000，并且 specialty endorsement baseline 不作为当前要求；它只用于标记 policy-impact case。标准答案优先使用当前公开记录，不让 applicant-only 或 stale correspondence 覆盖 registry 记录，并区分历史已解决问题和当前阻断性问题。

各申请结论：

- `C-TR1-001`：`HOLD`；Plumbing bond 25,000 低于 30,000，endorsement missing，experience 3 年低于 4 年。bond shortfall 属于 policy impacted。
- `C-TR1-002`：`HOLD`；endorsement pending，当前 insurance 于 `2025-04-15` 过期，conditional inspection 有 `DOC_GAP`。
- `C-TR1-003`：`DENY`；prior license `CL-CTR1003` suspended，insurance pending，failed inspection 需要 safety recheck。
- `C-TR1-004`：`HOLD`；当前 bond 在 `2025-05-30` cancelled。resolved violations 不单独阻断申请。
- `C-TR1-005`：`DENY`；存在 open serious violation，insurance 少 250,000，endorsement pending，experience 1 年低于 3 年。specialty endorsement 问题属于 policy impacted。
- `C-TR1-006`：`HOLD`；Electrical experience 4 年低于 5 年，其他当前财务记录足够。
- `C-TR1-007`：`HOLD`；Plumbing bond 25,000 低于 30,000，endorsement missing，open minor violation 需要 review，failed inspection 有 `DOC_GAP`。bond shortfall 属于 policy impacted。
- `C-TR1-008`：`HOLD`；endorsement pending，当前 insurance 于 `2025-04-15` 过期。

High-risk applications 是 `C-TR1-003` 和 `C-TR1-005`。Policy-impacted applications 是 `C-TR1-001`、`C-TR1-005`、`C-TR1-007`。Stale 或 unverified correspondence identifiers 是 `COR-C-TR1-001-1`、`COR-C-TR1-002-1`、`COR-C-TR1-004-1`、`COR-C-TR1-007-1`。

### 评测依据

Evaluator 使用八个 whole scoring points，raw weights 总计 16：

- `SP001`，weight 1：正好包含八个目标申请，并按 `application_id` 升序排列。
- `SP002`，weight 3：每个目标申请的 `APPROVE`/`HOLD`/`DENY` 结论正确。
- `SP003`，weight 3：每个目标申请的 deficiency code set 正确。
- `SP004`，weight 2：每个目标申请的 required action set 正确。
- `SP005`，weight 2：risk tier 和 high-risk summary set 正确。
- `SP006`，weight 2：policy-impact flags 和 summary set 正确。
- `SP007`，weight 2：approve、hold、deny summary counts 正确。
- `SP008`，weight 1：stale 或 unverified correspondence identifiers 正确。

每个 scoring point 都是通过或不通过，不给点内部分分。评分维度覆盖目标集合、申请结论、缺陷、操作动作、风险分级、政策影响、批次统计和来源冲突处理。

常见模型错误包括把 expired 或 cancelled records 当成 current，允许 unverified correspondence 覆盖 registry record，把 resolved violations 当作 automatic denial，漏掉 active suspension，忽略 insurance expiration，未用 prior baseline 判断 policy-impact，以及输出自由文本而非 template 中的受控 enum。

### 迁移设计

这是正式 train task，不是教程。fewshot skill 可以从 prompt 和 answer 中推断 contractor review 的重复性习惯：检查共享 endpoint families，优先当前 policy 和 public registry records 而非 stale correspondence，把 bond amount 与 status 一起判断，把 insurance status 与 expiration 一起判断，把 active suspension 和 unresolved serious violation 视为阻断性事实，把 resolved history 与当前缺陷区分开，使用受控 deficiency/action codes，并保持 application-level 与 summary-level 输出一致。这些经验会迁移到 contractor test tasks 和第二个 contractor train task，但不会使 test answers 变成模板复制。

### 构造记录

- Author: task-builder-train-001 / Codex
- Created: 2026-07-18
- Updated: 2026-07-18
- Major changes: 在 `train_tasks/001/` 下创建完整的 train_001 任务包。
