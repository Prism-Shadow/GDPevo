# train_002 Notes

## English

Data/source lineage: This task belongs to `SCN_019_regulatory_licensing_eligibility_and_compliance_review`, using source examples `E001`, `E002`, and `E003` as the scenario basis. The direct design anchor is the Oregon restricted liquor license package pattern from `E002`. The shared generated environment is `task_group_019/env`, especially `liquor_applications`, `liquor_settlements`, `liquor_privileges`, `liquor_incidents`, `liquor_site_evidence`, and `policies`. The task-local visible files are `input/prompt.txt` and `input/payloads/answer_template.json`.

Task definition: The solver is asked to prepare a structured staff package for application `L-TR2-001` at location `LOC-TR2`. The expected answer is a JSON object with the recommended posture, same-premises applicability, covered risks, unresolved verification gaps, standard obligations, location-specific controls, first-90-day monitoring checks, and escalation triggers. The prompt gives only the target identifiers and public endpoints through `<TASK_ENV_BASE_URL>`.

Scenario fit: This is licensing examiner work over a restricted-premises liquor transfer. It requires coordination across the application record, prior and active settlements, license-class privileges, incident history, site evidence, and current liquor policy. The core business relationship is the location, not only the applicant name, because same-premises history and settlement controls follow the premises.

Material map: `GET /api/liquor/applications` identifies `L-TR2-001` as `Crescent Market Group`, DBA `Corner Market 01`, Restaurant class, transfer posture, at `107 Pine St`, location `LOC-TR2`. `GET /api/liquor/settlements` supplies four location records; the active record is `SET-LOC-TR2-1`, basis `SAME_PREMISES`, controls `SECURITY`, `CCTV`, and `HOURS`, expiring `2026-12-31`. Older inactive settlements include `SALE_TO_MINOR`, `SAME_PREMISES`, and `PUBLIC_SAFETY` bases. `GET /api/liquor/privileges` supplies Restaurant standard obligations: `ID_CHECK`, `HOURS`, and `FOOD_SERVICE`. `GET /api/liquor/incidents` supplies a referred `MINOR_SALE`, closed `ASSAULT`, closed high `AFTER_HOURS`, and dismissed `TAX_HOLD`. `GET /api/liquor/site-evidence` supplies missing and conflicting `CONTROL_SIGNAGE` evidence plus conflicting `POLICE_MEMO` evidence. `GET /api/policies` supplies the controlling liquor rules: same-premises history matters, current site evidence is required, standard obligations are separate from location controls, and major incidents trigger board review.

Solution and evaluation basis: The standard answer recommends `request_follow_up`. Denial is not warranted because the active settlement supplies current restricted controls and there is no current unresolved major incident. Immediate issuance is not clean because the current site-evidence record for control signage is missing, another signage record is conflicting, the police memo is conflicting, and the minor-sale incident is referred. `same_premises_basis_applies` is true because an active same-premises settlement applies to the target location and older same-premises history remains relevant. Covered risk codes are `AFTER_HOURS`, `ASSAULT`, `MINOR_SALE`, `SALE_TO_MINOR`, and `SAME_PREMISES`. Verification gaps are `CONTROL_SIGNAGE_CONFLICTING`, `CONTROL_SIGNAGE_CURRENT_MISSING`, `OPEN_INCIDENT_FOLLOW_UP`, and `POLICE_MEMO_CONFLICTING`. Standard obligations are `FOOD_SERVICE`, `HOURS`, and `ID_CHECK`; active location-specific controls are `CCTV`, `HOURS`, and `SECURITY`. The first-90-day plan checks after-hours service, control signage, ID-check practice, police memo follow-up, and security/CCTV controls. Escalation triggers are after-hours violation, control signage not verified, major incident reported, referred minor sale unresolved, and security/CCTV control failure.

Evaluation criteria: The evaluator has eight whole scoring points with raw weights `[3, 2, 2, 3, 2, 2, 2, 1]`. `SP001` checks recommended posture. `SP002` checks same-premises applicability. `SP003` checks the covered risk-code set. `SP004` checks verification gaps. `SP005` checks standard obligations. `SP006` checks location-specific controls. `SP007` checks the first-90-day plan check/timing set. `SP008` checks escalation triggers. Each point is all-or-nothing after deterministic normalization of string sets and plan pairs.

Likely model pitfalls: A solver may treat old inactive settlements as irrelevant and miss the same-premises basis, collapse standard obligations and settlement controls into one list, deny the application because of closed high-severity history, issue the application despite current missing/conflicting site evidence, or include dismissed `TAX_HOLD` as an active covered risk or trigger.

Transfer design: As a train task, this solved example lets a later skill infer several recurring conventions: location-level same-premises history matters; current policy and active settlement controls drive posture; standard license obligations must be separated from location-specific controls; missing or conflicting current site evidence drives follow-up rather than automatic denial; and first-90-day monitoring should target the active controls and unresolved incidents.

Construction record: Author `task-builder-train-002` via Codex. Created `2026-07-18`. Updated `2026-07-18`. Major changes: initial formal task creation with prompt, answer template, standard answer, bilingual notes, and deterministic evaluator.

## 中文

数据和来源脉络：本任务属于 `SCN_019_regulatory_licensing_eligibility_and_compliance_review`，场景依据来自 `E001`、`E002` 和 `E003`。直接设计锚点是 `E002` 中受限制酒类许可证的工作人员审查包。共享生成环境为 `task_group_019/env`，主要使用 `liquor_applications`、`liquor_settlements`、`liquor_privileges`、`liquor_incidents`、`liquor_site_evidence` 和 `policies`。任务本地可见文件是 `input/prompt.txt` 和 `input/payloads/answer_template.json`。

任务定义：求解者需要为申请 `L-TR2-001`、地点 `LOC-TR2` 准备结构化工作人员审查包。预期答案是 JSON 对象，包含建议处理姿态、同址历史是否适用、已覆盖风险、未解决核验缺口、标准义务、地点特定控制、前九十天检查计划和升级触发项。提示只通过 `<TASK_ENV_BASE_URL>` 提供目标标识和公共接口。

场景适配：这是受限制场所酒类许可证转让审查工作。它需要协调申请记录、既往及当前和解记录、许可证类别权限、事件历史、现场证据和现行酒类政策。核心业务对象是地点，而不仅是申请人名称，因为同址历史和和解控制会随场所延续。

材料地图：`GET /api/liquor/applications` 显示 `L-TR2-001` 为 `Crescent Market Group`，营业名 `Corner Market 01`，Restaurant 类别，转让姿态，地址 `107 Pine St`，地点 `LOC-TR2`。`GET /api/liquor/settlements` 提供四条地点记录；有效记录是 `SET-LOC-TR2-1`，基础为 `SAME_PREMISES`，控制为 `SECURITY`、`CCTV` 和 `HOURS`，到期日为 `2026-12-31`。较旧的无效和解包括 `SALE_TO_MINOR`、`SAME_PREMISES` 和 `PUBLIC_SAFETY`。`GET /api/liquor/privileges` 给出 Restaurant 标准义务：`ID_CHECK`、`HOURS` 和 `FOOD_SERVICE`。`GET /api/liquor/incidents` 给出转交处理的 `MINOR_SALE`、已关闭的 `ASSAULT`、已关闭且高严重度的 `AFTER_HOURS`，以及已驳回的 `TAX_HOLD`。`GET /api/liquor/site-evidence` 给出缺失和冲突的 `CONTROL_SIGNAGE` 证据，以及冲突的 `POLICE_MEMO` 证据。`GET /api/policies` 给出控制性酒类规则：同址历史重要、需要当前现场证据、标准义务要与地点控制分离、重大事件触发委员会审查。

解答和评估依据：标准答案建议 `request_follow_up`。不应拒绝，因为有效和解已经提供当前限制性控制，且没有当前未解决的重大事件。也不宜直接签发，因为当前控制标识证据缺失，另一条标识证据冲突，警方备忘录冲突，并且未成年人销售事件仍为转交状态。`same_premises_basis_applies` 为 true，因为有效的同址和解适用于目标地点，且较旧同址历史仍然相关。已覆盖风险代码为 `AFTER_HOURS`、`ASSAULT`、`MINOR_SALE`、`SALE_TO_MINOR` 和 `SAME_PREMISES`。核验缺口为 `CONTROL_SIGNAGE_CONFLICTING`、`CONTROL_SIGNAGE_CURRENT_MISSING`、`OPEN_INCIDENT_FOLLOW_UP` 和 `POLICE_MEMO_CONFLICTING`。标准义务为 `FOOD_SERVICE`、`HOURS` 和 `ID_CHECK`；有效地点特定控制为 `CCTV`、`HOURS` 和 `SECURITY`。前九十天计划检查营业时间违规、控制标识、年龄核验做法、警方备忘录跟进以及安保和摄像控制。升级触发项为营业时间违规、控制标识未验证、出现重大事件、转交的未成年人销售未解决、安保或摄像控制失败。

评估标准：评估器有八个整点评分项，原始权重为 `[3, 2, 2, 3, 2, 2, 2, 1]`。`SP001` 检查建议处理姿态。`SP002` 检查同址适用性。`SP003` 检查已覆盖风险代码集合。`SP004` 检查核验缺口。`SP005` 检查标准义务。`SP006` 检查地点特定控制。`SP007` 检查前九十天计划中的检查项和时间窗口集合。`SP008` 检查升级触发项。每个评分项在字符串集合和计划键值对确定性归一化后整体通过或整体失败。

常见模型陷阱：模型可能把旧的无效和解完全忽略而漏掉同址基础，可能把标准义务和和解控制混成一个列表，可能因为已关闭的高严重度历史而错误拒绝，也可能在当前现场证据缺失或冲突时直接签发，或把已驳回的 `TAX_HOLD` 当作有效风险或触发项。

迁移设计：作为训练任务，这个已解样例让后续技能推断出若干复用约定：地点层面的同址历史重要；现行政策和有效和解控制决定处理姿态；标准许可证义务必须与地点特定控制分开；当前现场证据缺失或冲突时应要求跟进而不是自动拒绝；前九十天监测应围绕有效控制和未解决事件安排。

构建记录：作者为通过 Codex 执行的 `task-builder-train-002`。创建日期 `2026-07-18`。更新日期 `2026-07-18`。主要变更：首次创建正式任务，包括提示、答案模板、标准答案、双语说明和确定性评估器。
