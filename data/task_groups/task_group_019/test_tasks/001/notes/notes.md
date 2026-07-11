# test_001 Hidden Notes / test_001 隐藏说明

## English

### Data and lineage

This task belongs to `task_group_019`, scenario `SCN_019_regulatory_licensing_eligibility_and_compliance_review`, using source examples `E001`, `E002`, and `E003`. Its direct source-family anchor is `E001`, the contractor eligibility review workflow. The transfer anchors inside the task group are `train_001` and `train_004`, both contractor registration eligibility screens.

The shared environment is Cascadia Licensing Review Portal (CLRP) under `task_group/task_group_019/env/`. The target batch is `HS-2026-Q2A`, exposed through `/api/contractors/applications?batch_id=HS-2026-Q2A` and `/exports/contractor_batch_HS-2026-Q2A.csv`. The review cutoff is `2026-06-20`, so all 2026 contractor bulletins `CB-2026-001` through `CB-2026-020` are applicable for bulletin-impact reporting. Solver-visible files are `input/prompt.txt`, `input/payloads/answer_template.json`, and `input/payloads/endpoint_reference.json`.

### Task definition and scenario fit

The solver acts as a Harbor State licensing reviewer. The required output is a structured JSON eligibility package with `application_decisions` for all 14 Q2A applications, aggregate `deficiency_counts`, and `bulletin_impacts`.

This fits the scenario because the work is a multi-source administrative eligibility review. The reviewer must reconcile application rows, bonds, insurance, current bulletins, violations, field notes, and correspondence. The final product is controlled decision data, not a narrative memo.

### Material map

Key CLRP resources:

- `/api/contractors/applications?batch_id=HS-2026-Q2A` and `/exports/contractor_batch_HS-2026-Q2A.csv`: target roster, trades, application dates, declared bond and insurance, experience, background status, and prior registration flags.
- `/api/contractors/bonds?name=...`: active, short, and cancelled bonds.
- `/api/contractors/insurance?name=...`: insurance status, coverage, policy, and carrier verification.
- `/api/contractors/violations?name=...`: unresolved penalties and disqualifying conduct evidence.
- `/api/contractors/field-notes?name=...`: inspector open holds and nonblocking document-check noise.
- `/api/contractors/correspondence?batch_id=HS-2026-Q2A`: batch-linked material correspondence and distractor uploads/address corrections.
- `/api/contractors/bulletins?effective_on=2026-06-20`: all effective contractor bulletins used for scoped impact reporting.

### Solution basis

The standard answer contains 14 application decisions.

Important decisions:

- `CA-2026-0024`, `CA-2026-0034`, and `CA-2026-0036` are `APPROVE` with `NO_DEFICIENCY`. Their stale or nonblocking notes do not create a current hold.
- `CA-2026-0025` is a combined `HOLD` for `BOND_SHORTFALL` and `UNRESOLVED_PENALTY`. The Electrical bond is below the current `CB-2026-006` amount, and the unresolved penalty is material under `CB-2026-016`.
- `CA-2026-0026` is held for `INSURANCE_VERIFY` because the active policy has a carrier mismatch.
- `CA-2026-0027` is held for `CORRESPONDENCE_HOLD`; the material follow-up received after filing is in scope under `CB-2026-017`.
- `CA-2026-0028` is held for `UNRESOLVED_PENALTY` and `FIELD_NOTE_HOLD`. The open inspector hold is material under `CB-2026-020`.
- `CA-2026-0029` is held for `INSURANCE_VERIFY`; the Electrical policy is expired/stale, and `CB-2026-007` is the relevant insurance bulletin.
- `CA-2026-0030` is held for `UNRESOLVED_PENALTY`.
- `CA-2026-0031` is held for `BOND_CANCELLED` and `UNRESOLVED_PENALTY`; the cancellation is a replacement-bond issue and the penalty is separately material.
- `CA-2026-0032` is `DENY` for `DISQUALIFYING_CONDUCT`. The adverse background status, prior registration ID, high-severity unresolved fraudulent-registration violation, and AG referral make denial controlling. Curable defects are not stacked as separate reason codes for this denial, matching `train_001`.
- `CA-2026-0033` is held for `EXPERIENCE_VERIFY`; the Electrical principal has only one year of documented experience.
- `CA-2026-0035` is held for `BOND_SHORTFALL` and `INSURANCE_VERIFY`. The Concrete bond fails `CB-2026-003`; the insurance policy remains pending verification.
- `CA-2026-0037` is held for `UNRESOLVED_PENALTY` and `ADVERSE_PRIOR_REGISTRATION`.

Counts are exact in `output/answer.json`: 14 applications reviewed, 3 approvals, 10 holds, and 1 denial. Reason-code counts are `NO_DEFICIENCY=3`, `BOND_SHORTFALL=2`, `BOND_CANCELLED=1`, `INSURANCE_VERIFY=3`, `UNRESOLVED_PENALTY=5`, `FIELD_NOTE_HOLD=1`, `DISQUALIFYING_CONDUCT=1`, `EXPERIENCE_VERIFY=1`, `CORRESPONDENCE_HOLD=1`, `ADVERSE_PRIOR_REGISTRATION=1`, and zero for exam-score and financial-statement deficiencies.

Bulletin impacts treat an application as changed by a 2026 bulletin when at least one scored deficiency or hold basis is driven by a current effective bulletin. The changed set is `CA-2026-0025`, `CA-2026-0027`, `CA-2026-0028`, `CA-2026-0029`, `CA-2026-0030`, `CA-2026-0031`, `CA-2026-0035`, and `CA-2026-0037`. Rule-type counts are `BOND_MINIMUM=2`, `INSURANCE_MINIMUM=1`, `BACKGROUND_SCREENING=5`, `CORRESPONDENCE_REVIEW=1`, `FIELD_NOTE_REVIEW=1`, and zero for exam and experience minimums.

### Evaluation basis

The evaluator has 8 exact-match scoring points with raw weights 1, 2, or 3:

- `SP001`, weight 1: correct batch metadata and exact 14-application coverage/order.
- `SP002`, weight 3: exact determination map for all 14 applications.
- `SP003`, weight 2: clean approval cases with no-deficiency actions.
- `SP004`, weight 3: scoped bond and insurance hold results, primary bulletin IDs, and next actions.
- `SP005`, weight 2: correspondence and field-note override holds.
- `SP006`, weight 3: unresolved-penalty, adverse-registration, and disqualifying-conduct results.
- `SP007`, weight 2: exact `deficiency_counts`.
- `SP008`, weight 3: exact `bulletin_impacts`.

Most score is assigned to transfer-heavy and data-exploration business results. The evaluator normalizes ordering inside reason-code and bulletin-ID lists but requires exact stable IDs, enums, counts, and aggregate objects.

Likely pitfalls include using only the application CSV, overlooking insurance status rows for clean-looking files, treating every old field-note string as a current hold, missing batch-linked material correspondence, treating bond cancellation as a shortfall, stacking curable defects on a denial, or omitting zero-count reason-code keys.

### Transfer design

This test is transfer-aligned with `train_001` and `train_004` but is not a template copy. From `train_001`, a solver can transfer the output shape, batch-wide decision habit, controlled reason codes, bond shortfall versus bond cancellation distinction, insurance verification holds, clean-file handling, and bulletin-impact aggregation. From `train_004`, a solver can transfer adverse prior registration handling, material correspondence treatment, manual-review style judgment for unresolved penalties, and the need to avoid overreacting to closed or nonblocking noise.

The changed elements are the Q2A roster, the later cutoff, broader active bulletin set, more mixed clean-looking applications, and combined deficiencies. High-value scoring points `SP004`, `SP005`, `SP006`, and `SP008` depend strongly on train-derived source precedence and business judgment, while `SP002`, `SP003`, and `SP007` also require substantial task-specific data exploration across CLRP.

### Construction record

Author: Codex task-builder subagent for `task_group_019/test_001`.

Created: 2026-07-07.

Updated: 2026-07-07.

Major changes: Created solver prompt, endpoint reference, answer template, standard answer, exact-match evaluator, and bilingual notes for the Q2A contractor eligibility review task.

## 中文

### 数据来源与谱系

本任务属于 `task_group_019`，场景为 `SCN_019_regulatory_licensing_eligibility_and_compliance_review`，来源样例为 `E001`、`E002`、`E003`。直接业务来源是 `E001` 的承包商资格审查流程。任务组内部的迁移锚点是 `train_001` 和 `train_004`，二者都是承包商注册资格筛查任务。

共享环境是 Cascadia Licensing Review Portal（CLRP），位于 `task_group/task_group_019/env/`。目标批次为 `HS-2026-Q2A`，可通过 `/api/contractors/applications?batch_id=HS-2026-Q2A` 和 `/exports/contractor_batch_HS-2026-Q2A.csv` 获取。审查截止日为 `2026-06-20`，因此 `CB-2026-001` 到 `CB-2026-020` 的 2026 年承包商公告都进入 bulletin impact 汇总。求解器可见文件是 `input/prompt.txt`、`input/payloads/answer_template.json` 和 `input/payloads/endpoint_reference.json`。

### 任务定义与场景适配

求解器扮演 Harbor State 许可审查员。要求输出结构化 JSON，包含 Q2A 全部 14 个申请的 `application_decisions`、聚合的 `deficiency_counts` 和 `bulletin_impacts`。

该任务符合场景，因为它要求跨多个行政许可数据源进行资格审查：申请记录、保证金、保险、当前公告、违规记录、现场记录和往来函件。最终产物是受控决策数据，而不是自由文本备忘录。

### 材料地图

关键 CLRP 资源包括：

- `/api/contractors/applications?batch_id=HS-2026-Q2A` 和 `/exports/contractor_batch_HS-2026-Q2A.csv`：目标清单、行业、申请日期、申报保证金和保险、经验、背景状态和既往注册标记。
- `/api/contractors/bonds?name=...`：有效、金额不足和已取消的保证金。
- `/api/contractors/insurance?name=...`：保险状态、保额、保单和承保机构核验。
- `/api/contractors/violations?name=...`：未解决罚款和取消资格行为证据。
- `/api/contractors/field-notes?name=...`：检查员开放暂停项和非阻断性文件检查噪声。
- `/api/contractors/correspondence?batch_id=HS-2026-Q2A`：批次相关的实质性函件和干扰性的上传、地址更正。
- `/api/contractors/bulletins?effective_on=2026-06-20`：用于 scoped impact 汇总的全部已生效承包商公告。

### 解答依据

标准答案包含 14 条申请决策。

关键判定如下：

- `CA-2026-0024`、`CA-2026-0034`、`CA-2026-0036` 为 `APPROVE` 且原因是 `NO_DEFICIENCY`。陈旧或非阻断性记录不构成当前 hold。
- `CA-2026-0025` 因 `BOND_SHORTFALL` 和 `UNRESOLVED_PENALTY` 组合 hold。Electrical 保证金低于 `CB-2026-006` 当前金额，未解决罚款在 `CB-2026-016` 下具有实质性。
- `CA-2026-0026` 因 `INSURANCE_VERIFY` hold，因为有效保单存在承保机构不一致。
- `CA-2026-0027` 因 `CORRESPONDENCE_HOLD` hold；申请后收到的实质性跟进在 `CB-2026-017` 下需要审查。
- `CA-2026-0028` 因 `UNRESOLVED_PENALTY` 和 `FIELD_NOTE_HOLD` hold；开放检查员暂停项在 `CB-2026-020` 下具有实质性。
- `CA-2026-0029` 因 `INSURANCE_VERIFY` hold；Electrical 保单过期且 stale，相关保险公告为 `CB-2026-007`。
- `CA-2026-0030` 因 `UNRESOLVED_PENALTY` hold。
- `CA-2026-0031` 因 `BOND_CANCELLED` 和 `UNRESOLVED_PENALTY` hold；保证金取消需要替换，罚款问题也单独具有实质性。
- `CA-2026-0032` 因 `DISQUALIFYING_CONDUCT` 直接 `DENY`。不利背景状态、既往注册号、高严重性未解决 fraudulent-registration 违规和 AG referral 使拒绝成为控制性结论。与 `train_001` 一致，该拒绝项不再叠加可补正缺陷。
- `CA-2026-0033` 因 `EXPERIENCE_VERIFY` hold；Electrical 负责人只有一年记录经验。
- `CA-2026-0035` 因 `BOND_SHORTFALL` 和 `INSURANCE_VERIFY` hold。Concrete 保证金不满足 `CB-2026-003`，保险核验仍为 pending。
- `CA-2026-0037` 因 `UNRESOLVED_PENALTY` 和 `ADVERSE_PRIOR_REGISTRATION` hold。

计数以 `output/answer.json` 为准：审查 14 个申请，3 个 approve，10 个 hold，1 个 deny。reason code 计数为 `NO_DEFICIENCY=3`、`BOND_SHORTFALL=2`、`BOND_CANCELLED=1`、`INSURANCE_VERIFY=3`、`UNRESOLVED_PENALTY=5`、`FIELD_NOTE_HOLD=1`、`DISQUALIFYING_CONDUCT=1`、`EXPERIENCE_VERIFY=1`、`CORRESPONDENCE_HOLD=1`、`ADVERSE_PRIOR_REGISTRATION=1`，考试分数和财务报表缺陷均为 0。

Bulletin impact 中，如果某个已生效 2026 公告驱动了至少一个计分缺陷或 hold basis，就认为该申请受公告改变。changed set 为 `CA-2026-0025`、`CA-2026-0027`、`CA-2026-0028`、`CA-2026-0029`、`CA-2026-0030`、`CA-2026-0031`、`CA-2026-0035`、`CA-2026-0037`。rule type 计数为 `BOND_MINIMUM=2`、`INSURANCE_MINIMUM=1`、`BACKGROUND_SCREENING=5`、`CORRESPONDENCE_REVIEW=1`、`FIELD_NOTE_REVIEW=1`，考试和经验最低要求为 0。

### 评估依据

评估器包含 8 个精确匹配评分点，原始权重为 1、2 或 3：

- `SP001`，权重 1：批次元数据以及 14 个申请的覆盖范围和顺序完全正确。
- `SP002`，权重 3：全部 14 个申请的 determination map 完全正确。
- `SP003`，权重 2：无缺陷批准申请及其动作正确。
- `SP004`，权重 3：scoped bond 与 insurance hold、primary bulletin IDs 和 next actions 正确。
- `SP005`，权重 2：correspondence 和 field-note override hold 正确。
- `SP006`，权重 3：未解决罚款、不良既往注册和取消资格行为结果正确。
- `SP007`，权重 2：`deficiency_counts` 完全一致。
- `SP008`，权重 3：`bulletin_impacts` 完全一致。

大部分分数放在需要迁移和数据探索的业务结果上。评估器会归一化 reason-code 和 bulletin-ID 列表内部顺序，但稳定 ID、枚举、计数和聚合对象必须精确匹配。

常见失败包括只看 application CSV、漏掉看似干净文件中的保险状态、把每条旧 field-note 文本都当成当前 hold、漏掉批次关联的实质性函件、把 bond cancellation 当成 shortfall、在拒绝项上叠加可补正缺陷，或遗漏零计数字段。

### 迁移设计

本测试任务与 `train_001` 和 `train_004` 保持同分布迁移，但不是模板复制。模型可从 `train_001` 迁移输出结构、批次级决策习惯、受控 reason code、保证金不足和保证金取消的区分、保险核验 hold、干净文件处理和 bulletin impact 汇总。模型可从 `train_004` 迁移不良既往注册处理、实质性函件处理、未解决罚款的人工复核判断，以及不要对已关闭或非阻断性噪声过度反应。

变化点包括 Q2A 新清单、更晚截止日、更广的已生效公告集合、更多混合的 clean-looking applications，以及组合缺陷。高价值评分点 `SP004`、`SP005`、`SP006`、`SP008` 强依赖训练中学到的 source precedence 和业务判断；`SP002`、`SP003`、`SP007` 也需要在 CLRP 中进行大量本任务数据探索。

### 构造记录

作者：Codex task-builder subagent for `task_group_019/test_001`。

创建日期：2026-07-07。

更新日期：2026-07-07。

主要变更：创建 Q2A 承包商资格审查的 solver prompt、endpoint reference、answer template、standard answer、exact-match evaluator 和双语 notes。
