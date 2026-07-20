# test_001 Notes

## English

Data/source lineage: This task belongs to `SCN_019_regulatory_licensing_eligibility_and_compliance_review`, using source examples `E001`, `E002`, and `E003` as the scenario basis. The direct family is the contractor eligibility review pattern from `E001`, with transfer anchors planned for `train_001` and `train_004`. The shared generated environment is `task_group_019/env`, especially `policies`, `contractor_applications`, `contractor_bonds`, `contractor_insurance`, `contractor_license_history`, `contractor_violations`, `contractor_correspondence`, and `contractor_inspections`. The task-local visible files are `input/prompt.txt` and `input/payloads/answer_template.json`.

Task definition: The solver reviews application ids `C-TE1-001` through `C-TE1-009` for current contractor eligibility and release handling. The expected answer is a JSON object with one ordered decision per application and a batch summary. Each decision includes `determination`, `deficiency_codes`, `required_actions`, `risk_tier`, and `policy_impacted`. The prompt gives only target identifiers and environment endpoints through `<TASK_ENV_BASE_URL>`.

Scenario fit: This is licensing examiner work over a batch of contractor applications. The work requires coordination across application records, current policy thresholds, bond and insurance records, prior license history, violation records, correspondence, and inspection notes. It matches the scenario's regulatory eligibility-review workload because the final output is not a memo summary; it is an operational release decision with controlled reason and action codes.

Material map: `GET /api/policies` provides the current contractor standards by trade/class and the legacy comparison policy. `GET /api/contractor/applications` identifies the nine target applicants, trades, classes, experience, endorsement status, and prior license links. `GET /api/contractor/bonds` and `GET /api/contractor/insurance` provide current versus old financial responsibility records. `GET /api/contractor/license-history` identifies matched public-registry status. `GET /api/contractor/violations` supplies resolved, dismissed, open nonserious, and open serious records. `GET /api/contractor/correspondence` supplies stale or unverified applicant-side corrections that should not override current registry or financial records. `GET /api/contractor/inspections` supplies field follow-up context for selected holds and risk tiers.

Solution and evaluation basis: The standard answer approves `C-TE1-003` and `C-TE1-009`, holds `C-TE1-001`, `C-TE1-004`, `C-TE1-005`, `C-TE1-006`, and `C-TE1-007`, and denies `C-TE1-002` and `C-TE1-008`. `C-TE1-002` and `C-TE1-008` have open serious violations, so they are denials and high risk even though they also have insurance and endorsement issues. `C-TE1-004` is a high-risk hold because it has a current bond shortfall, missing endorsement, open nonserious violation history, and field recheck need. `C-TE1-004` is the only policy-impact application because its active bond would meet the legacy reduced bond threshold but not the current trade standard. `C-TE1-001` and `C-TE1-007` lack a current bond and required endorsement. `C-TE1-005` has expired current insurance and insufficient experience. `C-TE1-006` has pending insurance, insufficient experience, and a site recheck issue. Stale or unverified correspondence ids are `COR-C-TE1-001-1`, `COR-C-TE1-002-1`, `COR-C-TE1-004-1`, `COR-C-TE1-007-1`, `COR-C-TE1-008-1`, and `COR-DIS-0112`.

Evaluation criteria: The evaluator has eight whole scoring points with raw weights `[1, 3, 3, 2, 2, 2, 2, 1]`. `SP001` checks the exact target application coverage and required ordering. `SP002` checks the complete determination set. `SP003` checks deficiency-code sets. `SP004` checks required action-code sets. `SP005` checks risk tiers and the high-risk summary. `SP006` checks policy-impact flags and summary. `SP007` checks approve/hold/deny counts. `SP008` checks the stale or unverified correspondence summary. Each point is all-or-nothing after deterministic normalization; no point gives partial credit.

Likely model pitfalls: A solver may trust stale correspondence over current bond or insurance records, treat a resolved serious or dismissed violation as an automatic denial, miss that open serious violations are different from open nonserious complaints, count a cancelled bond as current because the amount is high enough, ignore insurance expiration dates, or miss the legacy/current bond comparison for `C-TE1-004`.

Transfer design: This is a test task. The intended train anchors are `train_001` and `train_004`, which exercise contractor batch eligibility over the same policy universe. The transferable knowledge is the source-precedence habit for current public records over correspondence, bond and insurance status plus amount/expiration checks, open serious violation denial logic, active/current policy comparison, controlled deficiency/action coding, and high-risk tiering. The new work in this task is the specific nine-application batch, new applicant names and trades, extra stale correspondence, and mixed current versus old financial records.

Construction record: Author `task-builder-test-001` via Codex. Created `2026-07-18`. Updated `2026-07-18`. Major changes: initial formal task creation with prompt, answer template, standard answer, bilingual notes, and deterministic evaluator.

## 中文

数据和来源脉络：本任务属于 `SCN_019_regulatory_licensing_eligibility_and_compliance_review`，场景依据来自 `E001`、`E002` 和 `E003`。直接任务族是 `E001` 的承包商资格审查模式，计划迁移锚点为 `train_001` 和 `train_004`。共享生成环境为 `task_group_019/env`，主要使用 `policies`、`contractor_applications`、`contractor_bonds`、`contractor_insurance`、`contractor_license_history`、`contractor_violations`、`contractor_correspondence` 和 `contractor_inspections`。任务本地可见文件是 `input/prompt.txt` 和 `input/payloads/answer_template.json`。

任务定义：求解者需要审查 `C-TE1-001` 至 `C-TE1-009` 的当前承包商申请资格和放行处理。预期答案是 JSON 对象，包含每个申请的有序决策和批次摘要。每条决策包括 `determination`、`deficiency_codes`、`required_actions`、`risk_tier` 和 `policy_impacted`。提示只通过 `<TASK_ENV_BASE_URL>` 提供目标标识和环境接口。

场景适配：这是承包商申请批次的许可证审查工作。工作需要协调申请记录、现行政策门槛、保证金和保险记录、既往许可证历史、违规记录、往来函件和检查备注。它符合监管资格审查场景，因为最终输出不是叙述性备忘录，而是带有受控原因和行动代码的业务放行决策。

材料地图：`GET /api/policies` 提供按工种和等级划分的当前承包商标准以及旧规则比较政策。`GET /api/contractor/applications` 标识九个目标申请人的工种、等级、经验、背书状态和既往许可证链接。`GET /api/contractor/bonds` 与 `GET /api/contractor/insurance` 提供当前和旧的财务责任记录。`GET /api/contractor/license-history` 标识匹配的公共登记状态。`GET /api/contractor/violations` 提供已解决、已驳回、未结非严重和未结严重记录。`GET /api/contractor/correspondence` 提供陈旧或未核验的申请人侧更正，这些内容不应覆盖当前登记或财务记录。`GET /api/contractor/inspections` 为部分暂缓和风险分层提供现场跟进背景。

解答和评估依据：标准答案批准 `C-TE1-003` 和 `C-TE1-009`，暂缓 `C-TE1-001`、`C-TE1-004`、`C-TE1-005`、`C-TE1-006` 和 `C-TE1-007`，拒绝 `C-TE1-002` 和 `C-TE1-008`。`C-TE1-002` 和 `C-TE1-008` 有未结严重违规，因此即使还存在保险和背书问题，也应拒绝并列为高风险。`C-TE1-004` 是高风险暂缓，因为它有当前保证金不足、缺少背书、未结非严重违规历史以及现场复查需要。`C-TE1-004` 是唯一受政策变化影响的申请，因为它的有效保证金满足旧规则降低后的门槛，但不满足当前工种标准。`C-TE1-001` 和 `C-TE1-007` 缺少当前保证金和必要背书。`C-TE1-005` 的当前保险已过期且经验不足。`C-TE1-006` 的保险待核验、经验不足并需要现场复查。陈旧或未核验函件编号为 `COR-C-TE1-001-1`、`COR-C-TE1-002-1`、`COR-C-TE1-004-1`、`COR-C-TE1-007-1`、`COR-C-TE1-008-1` 和 `COR-DIS-0112`。

评估标准：评估器有八个整点评分项，原始权重为 `[1, 3, 3, 2, 2, 2, 2, 1]`。`SP001` 检查目标申请覆盖和规定顺序。`SP002` 检查完整处理结论集合。`SP003` 检查缺陷代码集合。`SP004` 检查所需行动代码集合。`SP005` 检查风险分层和高风险摘要。`SP006` 检查政策影响标记和摘要。`SP007` 检查批准、暂缓、拒绝数量。`SP008` 检查陈旧或未核验函件摘要。每个评分项在确定性归一化后整体通过或整体失败，不给单项内部部分分。

常见模型陷阱：模型可能相信陈旧函件而不是当前保证金或保险记录，可能把已解决的严重违规或已驳回违规当作自动拒绝，可能漏掉未结严重违规和未结非严重投诉的区别，可能因为保证金额度足够而忽视保证金已取消，可能忽视保险到期日期，或漏掉 `C-TE1-004` 的旧规则与当前规则保证金比较。

迁移设计：这是测试任务。预期训练锚点为 `train_001` 和 `train_004`，它们在相同政策体系下审查承包商申请批次。需要迁移的知识包括：当前公共记录优先于函件的来源优先级，保证金和保险必须同时检查状态、金额和到期，未结严重违规导致拒绝，现行政策比较，受控缺陷和行动代码，以及高风险分层。本任务的新工作是具体九个申请批次、新申请人名称和工种、额外陈旧函件，以及当前和旧财务记录混杂。

构建记录：作者为通过 Codex 执行的 `task-builder-test-001`。创建日期 `2026-07-18`。更新日期 `2026-07-18`。主要变更：首次创建正式任务，包括提示、答案模板、标准答案、双语说明和确定性评估器。
