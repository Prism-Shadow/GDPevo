# train_002 Notes

## English

This task belongs to `task_group_019`, scenario `SCN_019_regulatory_licensing_eligibility_and_compliance_review`, using source examples `E001`, `E002`, and `E003`. The specific task is the restricted alcohol-license review planned in `scratch/task_group_design.md`: decide the issuance posture for a February 2026 application with prior same-premises incidents, a prior settlement, and proposed restrictions that must be separated from standard obligations.

The solver-visible input is `input/prompt.txt` plus `input/payloads/answer_template.json`. The shared CLRP environment supplies the public data through `http://localhost:<PORT>`, especially `/api/alcohol/applications?review_month=2026-02`, `/api/alcohol/premises?premises_id=PM-2026-003`, `/api/alcohol/incidents?premises_id=PM-2026-003`, `/api/alcohol/settlements?premises_id=PM-2026-003`, `/api/alcohol/restrictions?premises_id=PM-2026-003`, and `/api/alcohol/standard-obligations?license_type=F-RTL`. The prompt intentionally does not give a procedural checklist; the solver must discover and reconcile the application, premises, incidents, settlement, restrictions, standard obligations, and same-month comparison context.

The target file is application `AA-2026-0003` for premises `PM-2026-003`, DBA `Waypoint Room 03`, review month `2026-02`. The application requests restricted issuance. The premises record states same address and overlapping service area as the prior licensee, `Foundry Hospitality LLC`, with a risk summary indicating incidents that overlap proposed controls. The incident history contains five records: one high-severity settled service-to-intoxicated-patron incident, one medium pending late-night disorder incident, one low citation for a minor on premises, one low pending noise complaint, and one low security-plan lapse with blank disposition. There is one prior settlement, `AS-2026-0001`, dated `2023-10-23`, with original posture `warning` and final terms allowing operation with age-verification controls.

The target restriction rows are both `FOOD_SERVICE`, category `standard-obligation`, with evidence `menu and receipts`. There are no current `premises-specific` restriction rows for the target. The applicable standard obligations for license type `F-RTL` and `ALL` are `RTL_DISPLAY`, `RTL_SALES`, `RTL_STAFF`, `PUBLIC_RECORDS`, and `INCIDENT_REPORT`; the recorded `FOOD_SERVICE` item is treated as a proposed standard obligation, not as a premises-specific risk control.

Same-month comparison matters because February 2026 has 13 alcohol applications. Among restricted-issuance February reviews, seven applications have premises-specific controls: `AA-2026-0005`, `AA-2026-0011`, `AA-2026-0015`, `AA-2026-0020`, `AA-2026-0035`, `AA-2026-0040`, and `AA-2026-0045`. The target has zero current premises-specific controls, which supports the `STANDARD_ONLY` coverage classification and the `REQUEST_FOLLOWUP` recommendation rather than immediate restricted issuance.

The standard answer uses controlled fields. The recommendation is `REQUEST_FOLLOWUP`. The core risk assessment is `SAME_ADDRESS_OVERLAP`, `HIGH` prior incident level, 5 total incidents, 3 unresolved or blank-disposition incidents, 1 high-severity incident, `PRIOR_WARNING_WITH_CONTROLS`, `STANDARD_ONLY`, and overall `ELEVATED` risk. Verification gaps are the missing current age-verification control, missing late-night/security control, pending police-call dispositions, and missing security-plan-lapse disposition. Inspection controls are separated into standard obligations and location-specific restrictions. The location-specific restrictions are follow-up controls required before issue: `AGE_CHECK`, `NO_AFTER_MIDNIGHT_SERVICE`, and `SECURITY_LOG`, with first-90-day focus values matching the evidence required by the generated CLRP restriction vocabulary.

Evaluation is implemented in `eval/eval.sh`. It has seven exact-match scoring points with raw weights 3, 2, 2, 2, 2, 2, and 3. The points cover the final recommendation and target IDs; risk classifications; incident counts; standard-only coverage and February comparison context; verification-gap set; standard-obligation control objects; and location-specific follow-up control objects. List order is normalized for controlled sets, but the controlled business results must match exactly.

This train task supports transfer to later restricted alcohol-license tasks. Solvers can infer that proposed restrictions are not sufficient merely because the requested posture says restricted issuance, that standard obligations must be kept separate from location-specific restrictions, that same-premises history and prior settlement terms affect the recommendation, and that first-90-day inspection controls should target the actual unresolved risk pattern rather than repeat generic obligations.

Construction record: created by task-builder subagent for `train_002` on 2026-07-07. Major change: initial creation of prompt, answer template, standard answer, notes, and evaluator from the generated CLRP database.

## 中文

本任务属于 `task_group_019`，场景为 `SCN_019_regulatory_licensing_eligibility_and_compliance_review`，来源示例为 `E001`、`E002`、`E003`。本任务对应 `scratch/task_group_design.md` 中的限制性酒类许可审查：针对 2026 年 2 月的一份申请，结合既往同址事件、既往和解记录以及拟议限制，判断发证姿态，并区分标准义务与地点特定限制。

求解者可见输入只有 `input/prompt.txt` 和 `input/payloads/answer_template.json`。共享 CLRP 环境通过 `http://localhost:<PORT>` 提供公开数据，主要端点包括 `/api/alcohol/applications?review_month=2026-02`、`/api/alcohol/premises?premises_id=PM-2026-003`、`/api/alcohol/incidents?premises_id=PM-2026-003`、`/api/alcohol/settlements?premises_id=PM-2026-003`、`/api/alcohol/restrictions?premises_id=PM-2026-003` 和 `/api/alcohol/standard-obligations?license_type=F-RTL`。提示语没有提供步骤清单，求解者需要自行查找并核对申请、场所、事件、和解、限制、标准义务和同月比较信息。

目标文件是申请 `AA-2026-0003`，场所 `PM-2026-003`，DBA 为 `Waypoint Room 03`，审查月份为 `2026-02`。申请请求限制性发证。场所记录显示该地点与前许可人的地址和服务区域重叠，前许可人为 `Foundry Hospitality LLC`，风险摘要说明既往同址经营存在与拟议控制相关的事件。事件历史共有 5 条：1 条高严重度且已和解的向明显醉酒顾客服务事件，1 条中等严重度且待处理的深夜秩序事件，1 条未成年人入场 citation，1 条待处理噪声投诉，以及 1 条处分为空的安全计划缺失。既往和解 `AS-2026-0001` 日期为 `2023-10-23`，原始姿态为 `warning`，最终条款允许在年龄验证控制下经营。

目标限制记录中两条都是 `FOOD_SERVICE`，类别为 `standard-obligation`，所需证据为 `menu and receipts`。目标没有当前 `premises-specific` 限制记录。适用于 `F-RTL` 和 `ALL` 的标准义务是 `RTL_DISPLAY`、`RTL_SALES`、`RTL_STAFF`、`PUBLIC_RECORDS` 和 `INCIDENT_REPORT`；记录中的 `FOOD_SERVICE` 被视为拟议的标准义务，而不是地点特定风险控制。

同月比较是本任务的重要部分。2026 年 2 月共有 13 个酒类申请。在请求限制性发证的 2 月审查中，有 7 个申请具有地点特定控制：`AA-2026-0005`、`AA-2026-0011`、`AA-2026-0015`、`AA-2026-0020`、`AA-2026-0035`、`AA-2026-0040` 和 `AA-2026-0045`。目标申请当前地点特定控制数量为 0，因此覆盖分类为 `STANDARD_ONLY`，最终建议为 `REQUEST_FOLLOWUP`，而不是直接限制性发证。

标准答案使用受控字段。推荐值为 `REQUEST_FOLLOWUP`。核心风险评估为 `SAME_ADDRESS_OVERLAP`、既往事件等级 `HIGH`、事件总数 5、待处理或处分为空事件数 3、高严重度事件数 1、`PRIOR_WARNING_WITH_CONTROLS`、`STANDARD_ONLY`、整体风险 `ELEVATED`。核验缺口包括当前限制中缺少年龄验证控制、缺少深夜或安全控制、警方呼叫记录仍待处理、以及安全计划缺失记录处分为空。检查控制分为标准义务和地点特定限制。地点特定限制为发证前需要补充的 `AGE_CHECK`、`NO_AFTER_MIDNIGHT_SERVICE` 和 `SECURITY_LOG`，其前 90 天检查重点与生成数据中的证据类型对应。

评估脚本为 `eval/eval.sh`。它包含 7 个精确匹配评分点，原始权重分别为 3、2、2、2、2、2、3。评分点覆盖最终建议和目标 ID、风险分类、事件计数、标准义务覆盖与 2 月比较上下文、核验缺口集合、标准义务控制对象、以及地点特定后续控制对象。集合型列表会规范化顺序，但受控业务结果必须完全匹配。

该训练任务为后续限制性酒类许可任务提供可迁移经验。求解者可以从中归纳：不能因为申请请求限制性发证就默认拟议限制充分；标准义务必须与地点特定限制分开；同址历史和既往和解条款会影响建议；前 90 天检查控制应针对真实未解决风险，而不是重复通用义务。

构造记录：由 `train_002` task-builder subagent 于 2026-07-07 创建。主要变更：基于生成的 CLRP 数据库首次创建提示、答案模板、标准答案、说明文件和评估器。
