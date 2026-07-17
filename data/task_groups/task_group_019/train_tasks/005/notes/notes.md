# train_005 Notes

## English

### Data and Source Lineage

This is `train_005` for `task_group_019`, built from scenario `SCN_019_regulatory_licensing_eligibility_and_compliance_review` and source examples `E001`, `E002`, and `E003`. The task implements the restricted on-premises alcohol license review family described in `scratch/task_group_design.md`, with a renewal-style successor-risk habit: same address history must be treated as premises evidence, but not confused with unrelated roster matches.

The shared environment is the Cascadia Licensing Review Portal (CLRP) under `task_group/task_group_019/env/`. The target records are generated in `env/data/clrp.db` and exposed through the HTTP API documented in `env/data/public_manifest.json`. The construction anchor for March 2026 lists application `AA-2026-0018`, premises `PM-2026-018`, and issue tags `SAME_PREMISES_OVERLAP`, `CONTROL_OVERLAP`, and `FIRST_90_DAY_CHECK`.

Solver-visible files are limited to `input/prompt.txt` and `input/payloads/answer_template.json`. The prompt gives the base URL placeholder `http://localhost:<PORT>` and target IDs without exposing answer logic.

### Task Definition and Material Map

The business task is to prepare a restricted-license monitoring plan for application `AA-2026-0018` at premises `PM-2026-018` for review month `2026-03`. Important CLRP records:

- `GET /api/alcohol/applications?review_month=2026-03` identifies the target application as a `BREWPUB` application requesting restricted issuance.
- `GET /api/alcohol/premises?premises_id=PM-2026-018` shows same address and overlapping service area as prior licensee `Juniper Hospitality LLC`, plus a risk summary that prior incidents overlap proposed controls.
- `GET /api/alcohol/incidents?premises_id=PM-2026-018` shows pending incidents `AI-2026-0008` and `AI-2026-0009`, high-severity late-night disorder citation `AI-2026-0145`, and security-plan lapse citation `AI-2026-0086`.
- `GET /api/alcohol/settlements?premises_id=PM-2026-018` shows settlement `AS-2026-0007` with final terms for noise abatement and quarterly inspection.
- `GET /api/alcohol/restrictions?premises_id=PM-2026-018` shows `AR-2026-0013` as a standard-obligation style training control and `AR-2026-0014` as the premises-specific `AGE_CHECK` control.
- `GET /api/alcohol/standard-obligations?license_type=BREWPUB` and `license_type=ALL` provide the standard obligations `BREW_PRODUCTION`, `BREW_SAMPLES`, `BREW_TRAINING`, `PUBLIC_RECORDS`, and `INCIDENT_REPORT`.
- `GET /api/search/address?address=226%20Orchard%20St` has no renewal rows, so the successor risk is based on the alcohol premises history rather than an unrelated renewal match.

The required output is a controlled JSON object with recommendation, successor risk, verification gaps, standard obligations, premises-specific controls, records requests, and escalation triggers.

### Solution and Evaluation Basis

The standard answer recommends `ISSUE_RESTRICTED_WITH_MONITORING`, not standard issuance or denial. The reason is that the application already requests restricted issuance, but the same-premises history and incidents require monitoring. The successor risk is `HIGH` because the premises record has same address and service-area overlap, a high-severity late-night disorder citation, recent pending late-night disorder, pending noise complaint, and prior controls that overlap the risk.

Verification gaps are:

- `SUCCESSOR_CONTROL_SEPARATION` from `PM-2026-018`.
- `PENDING_INCIDENT_DISPOSITIONS` from `AI-2026-0008` and `AI-2026-0009`.
- `STANDARD_CONTROL_OVERLAP` from `AR-2026-0013`, which should not be treated as a site-specific restriction.
- `POST_REVIEW_SETTLEMENT_TIMING` from `AS-2026-0007`, because its date is after the March review month and should be verified before it is relied on as final.

Standard obligations are exactly the `BREWPUB` obligations plus `ALL` obligations: `BREW_PRODUCTION`, `BREW_SAMPLES`, `BREW_TRAINING`, `PUBLIC_RECORDS`, and `INCIDENT_REPORT`.

Premises-specific controls are `AGE_CHECK`, `LATE_NIGHT_DISORDER_MONITORING`, `QUARTERLY_INSPECTION_CONDITION`, and `SECURITY_PLAN_LAPSE_REVIEW`, all marked for first-90-day checking. The answer intentionally excludes `TRAINING_STANDARD` from `premises_specific_controls` because the CLRP restriction category marks it as `standard-obligation`.

The evaluator has seven exact-match scoring points with raw weights:

- Recommendation and target identity: weight 2.
- Successor risk classification: weight 2.
- Verification gap map with source IDs and statuses: weight 2.
- Standard obligation code set: weight 2.
- Premises-specific control map with source IDs, check codes, and first-90-day flags: weight 3.
- Records request code set: weight 2.
- Escalation trigger code set: weight 2.

Common pitfalls are using `F-COM` obligations instead of `BREWPUB`; treating `TRAINING_STANDARD` as premises-specific; ignoring the pending disposition records; missing the high-severity late-night disorder evidence; over-denying despite the requested restricted posture; or searching renewal rows and inventing a match where the address search returns none.

### Transfer Design

This train task reinforces the restricted-license SOP shared with `train_002` and later restricted-license test tasks. It is still a real formal task, not a tutorial: the solver must infer the separation between standard obligations and premises-specific controls from the records and answer comparison. Transferable lessons include checking the current application's license type before selecting standard obligations, treating same-premises history as successor risk evidence, not accepting proposed controls at face value when they overlap prior failed risks, and converting first-90-day concerns into controlled monitoring and escalation outputs.

### Construction Record

Author: task-builder subagent for `train_005`.
Created: 2026-07-07.
Updated: 2026-07-07.
Major changes: initial task construction with prompt, answer template, standard answer, exact-match evaluator, and bilingual notes.

## 中文

### 数据与来源

本任务是 `task_group_019` 的 `train_005`，来源场景为 `SCN_019_regulatory_licensing_eligibility_and_compliance_review`，参考示例为 `E001`、`E002`、`E003`。任务属于受限制酒类牌照审查工作流，并加入类似续期审查中的继任经营风险判断：同地址历史应作为场所风险证据，但不能和无关的续期名单匹配混淆。

共享环境是 `task_group/task_group_019/env/` 下的 Cascadia Licensing Review Portal。目标记录由 `env/data/clrp.db` 生成，并通过 `env/data/public_manifest.json` 中记录的 HTTP API 暴露。构造清单中，2026 年 3 月锚点包括申请 `AA-2026-0018`、场所 `PM-2026-018`，问题标签为 `SAME_PREMISES_OVERLAP`、`CONTROL_OVERLAP`、`FIRST_90_DAY_CHECK`。

求解器可见文件只有 `input/prompt.txt` 和 `input/payloads/answer_template.json`。提示中只给出 `http://localhost:<PORT>` 和目标 ID，不暴露求解流程或标准答案。

### 任务定义与材料地图

业务任务是为 2026 年 3 月的申请 `AA-2026-0018`、场所 `PM-2026-018` 准备受限制牌照监控计划。关键 CLRP 记录如下：

- `GET /api/alcohol/applications?review_month=2026-03` 显示目标申请是 `BREWPUB`，并请求受限制发照。
- `GET /api/alcohol/premises?premises_id=PM-2026-018` 显示该场所与前任持牌人 `Juniper Hospitality LLC` 同地址且服务区域重叠。
- `GET /api/alcohol/incidents?premises_id=PM-2026-018` 显示待处理事件 `AI-2026-0008`、`AI-2026-0009`，高严重度深夜秩序事件 `AI-2026-0145`，以及安全计划缺失事件 `AI-2026-0086`。
- `GET /api/alcohol/settlements?premises_id=PM-2026-018` 显示和噪音消减、季度检查有关的和解 `AS-2026-0007`。
- `GET /api/alcohol/restrictions?premises_id=PM-2026-018` 显示 `AR-2026-0013` 是标准义务类培训控制，`AR-2026-0014` 是场所特定的 `AGE_CHECK` 控制。
- `GET /api/alcohol/standard-obligations?license_type=BREWPUB` 和 `license_type=ALL` 给出标准义务。
- `GET /api/search/address?address=226%20Orchard%20St` 没有续期记录，因此继任风险来自酒类场所历史，而非续期名单。

输出必须是受控 JSON，字段包括建议、继任风险等级、核验缺口、标准义务、场所特定控制、记录请求和升级触发条件。

### 解答与评估依据

标准答案建议 `ISSUE_RESTRICTED_WITH_MONITORING`。原因是申请本身请求受限制发照，但同场所历史、近期待处理事件和既往高严重度事件要求配套监控，而不是普通发照或直接拒绝。继任风险为 `HIGH`。

核验缺口包括：来自 `PM-2026-018` 的继任控制分离，来自 `AI-2026-0008` 和 `AI-2026-0009` 的待处理事件结果，来自 `AR-2026-0013` 的标准控制重叠，以及来自 `AS-2026-0007` 的审查月份后和解日期核验。

标准义务必须取 `BREWPUB` 和 `ALL` 的义务：`BREW_PRODUCTION`、`BREW_SAMPLES`、`BREW_TRAINING`、`PUBLIC_RECORDS`、`INCIDENT_REPORT`。场所特定控制为 `AGE_CHECK`、`LATE_NIGHT_DISORDER_MONITORING`、`QUARTERLY_INSPECTION_CONDITION`、`SECURITY_PLAN_LAPSE_REVIEW`，并都要求首 90 天检查。`TRAINING_STANDARD` 不应放入场所特定控制，因为数据库中其类别是 `standard-obligation`。

评估器有 7 个精确匹配评分点，原始权重分别为 2、2、2、2、3、2、2，覆盖建议、风险等级、核验缺口、标准义务、场所控制、记录请求和升级触发条件。

常见错误包括误用 `F-COM` 标准义务、把 `TRAINING_STANDARD` 当作场所控制、忽略待处理事件、遗漏高严重度深夜事件、在应受限制监控时直接拒绝，以及把没有地址匹配的续期记录强行纳入。

### 迁移设计

本训练任务强化与 `train_002` 和后续受限制酒类牌照测试任务共享的操作经验。它不是教程，而是正式业务任务；求解器需要通过实际尝试和对照答案来归纳：必须按当前申请的牌照类型选择标准义务，必须把同场所历史作为继任风险证据，不能把与既往风险重叠的控制措施直接视为充分，首 90 天问题要转换为结构化监控和升级条件。

### 构造记录

作者：`train_005` task-builder subagent。
创建日期：2026-07-07。
更新日期：2026-07-07。
主要变更：首次创建提示、答案模板、标准答案、精确匹配评估器和双语说明。
