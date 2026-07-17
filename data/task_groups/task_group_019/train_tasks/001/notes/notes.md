# train_001 Hidden Notes / train_001 隐藏说明

## English

### Data and Lineage

This task belongs to `task_group_019`, scenario `SCN_019_regulatory_licensing_eligibility_and_compliance_review`, with source examples `E001`, `E002`, and `E003`. Its direct family anchor is `E001`, the contractor eligibility review example. The shared environment is the Cascadia Licensing Review Portal (CLRP) under `task_group/task_group_019/env/`. Solver-visible materials are `input/prompt.txt`, `input/payloads/answer_template.json`, and `input/payloads/endpoint_reference.json`.

The target batch is Harbor State contractor batch `HS-2026-Q1A`. The review cutoff is `2026-03-01`; records with later event, notice, or effective dates are out of scope for the standard answer. The task uses the shared CLRP contractor API, not local env files. Construction used `construction_manifest.json` only to confirm the intended anchor records; the answer is grounded in the public CLRP rows.

### Task Definition and Scenario Fit

The solver acts as a licensing reviewer producing a formal structured eligibility result for all 12 applications in `HS-2026-Q1A`. The required business outputs are per-application `APPROVE`, `HOLD`, or `DENY` determinations, controlled reason codes, next actions, deficiency counts, and a bulletin-impact summary.

This matches the scenario because the work requires multi-source administrative licensing reconciliation: pending applications, bonds, insurance policies, violations, complaints, field notes, correspondence, and effective regulatory bulletins. The output is reviewer-ready structured decision data rather than a narrative memo.

### Material Map

Key solver-facing CLRP resources:

- `/api/contractors/applications?batch_id=HS-2026-Q1A` and `/exports/contractor_batch_HS-2026-Q1A.csv`: target application roster and application attributes.
- `/api/contractors/bonds?name=...`: bond amount/status evidence, including shortfall and cancellation records.
- `/api/contractors/insurance?name=...`: carrier, policy, coverage, and verification status.
- `/api/contractors/violations?name=...`: adverse conduct and unresolved penalty evidence.
- `/api/contractors/complaints?name=...`: context for complaints; not every complaint is a scored deficiency.
- `/api/contractors/field-notes?name=...`: open inspector holds and clearance recommendations.
- `/api/contractors/correspondence?batch_id=HS-2026-Q1A`: material notices and distractor correspondence.
- `/api/contractors/bulletins?effective_on=2026-03-01`: effective bulletins through the review cutoff.

### Solution and Evaluation Basis

The standard answer contains 12 `application_decisions`, `deficiency_counts`, and `bulletin_impacts`.

Decision basis:

- `CA-2026-0001`, `CA-2026-0008`, and `CA-2026-0011` are approved. Their resolved or out-of-scope noise does not create a material hold at the cutoff.
- `CA-2026-0002` is held for `BOND_SHORTFALL`; Plumbing bulletin `CB-2026-008` raised the current bond minimum above the active bond amount.
- `CA-2026-0003` is held for `INSURANCE_VERIFY`; carrier verification remains pending in the policy/correspondence evidence by the cutoff.
- `CA-2026-0004` is held for `UNRESOLVED_PENALTY`; the unresolved penalty and AG referral require reviewer resolution before issuance.
- `CA-2026-0005` is held for `FIELD_NOTE_HOLD`; the open inspector hold requires clearance.
- `CA-2026-0006` is held for `BOND_CANCELLED`; the bond cancellation date is before the cutoff.
- `CA-2026-0007` is held for `EXPERIENCE_VERIFY`; the principal has insufficient documented qualifying experience for clearance.
- `CA-2026-0009` is held for `BOND_SHORTFALL` and `INSURANCE_VERIFY`; Roofing bulletins `CB-2026-004` and `CB-2026-005` are the controlling bulletin impacts.
- `CA-2026-0010` is denied for `DISQUALIFYING_CONDUCT`; the adverse background status and fraudulent-registration history support denial rather than a curable hold.
- `CA-2026-0012` is held for `UNRESOLVED_PENALTY` and `FIELD_NOTE_HOLD`; both the unresolved penalty/AG referral and the open inspector hold remain unresolved.

Deficiency counts are `APPROVE=3`, `HOLD=8`, and `DENY=1`. Reason-code counts are exact in `output/answer.json`. Bulletin impacts consider `CB-2026-001` through `CB-2026-011` as applicable at the cutoff. `CA-2026-0002` and `CA-2026-0009` are changed by 2026 bulletins. The bulletin rule-type deficiency counts are `BOND_MINIMUM=2`, `INSURANCE_MINIMUM=1`, `EXAM_MINIMUM=0`, and `EXPERIENCE_MINIMUM=0`.

The evaluator has 8 exact-match scoring points with raw weights 1, 2, or 3:

- `SP001`, weight 1: exact application coverage and ordering.
- `SP002`, weight 3: exact determination map for all 12 applications.
- `SP003`, weight 2: exact clean approval cases.
- `SP004`, weight 2: exact bond-related hold results and actions.
- `SP005`, weight 2: exact insurance-verification hold results and actions.
- `SP006`, weight 3: exact penalty, field-note, and denial cases.
- `SP007`, weight 2: exact `deficiency_counts`.
- `SP008`, weight 3: exact `bulletin_impacts`.

Likely model pitfalls include using local env files instead of the API, overlooking batch cutoff dates, treating every historical complaint or resolved violation as a deficiency, missing correspondence/field-note overrides, treating bond cancellation like a simple shortfall, applying post-cutoff bulletins, or omitting required zero-count enum keys.

### Transfer Design

This is a train task, not a tutorial. Blind attempts and answer comparison should teach transferable experience for later contractor tasks: use the shared CLRP API, separate effective bulletin changes from ordinary defects, distinguish holds from denial, use controlled reason codes, reconcile bond and insurance records against the application roster, and avoid counting out-of-scope or non-material noise as business deficiencies. The train-derived lesson should transfer especially to contractor test tasks that require bulletin-scope counts, bond cancellation versus shortfall distinctions, field-note holds, and aggregate deficiency counts.

### Construction Record

Author: Codex task-builder subagent for `task_group_019/train_001`.

Created: 2026-07-07.

Updated: 2026-07-07.

Major changes: Created solver prompt, endpoint payload, answer template, standard answer, exact-match evaluator, and bilingual notes for the contractor batch eligibility review task.

## 中文

### 数据来源与谱系

本任务属于 `task_group_019`，场景为 `SCN_019_regulatory_licensing_eligibility_and_compliance_review`，来源 examples 为 `E001`、`E002`、`E003`。直接业务锚点是 `E001` 的 contractor eligibility review。共享环境是 `task_group/task_group_019/env/` 下的 Cascadia Licensing Review Portal（CLRP）。求解器可见材料为 `input/prompt.txt`、`input/payloads/answer_template.json` 和 `input/payloads/endpoint_reference.json`。

目标批次是 Harbor State contractor batch `HS-2026-Q1A`。审查截止日是 `2026-03-01`；晚于该日期的事件、通知或生效日期不进入标准答案。任务要求使用共享 CLRP contractor API，而不是本地环境文件。构造时只用 `construction_manifest.json` 确认锚点记录，最终答案依据公开 API 中可见的业务记录。

### 任务定义与场景适配

求解器扮演 licensing reviewer，为 `HS-2026-Q1A` 的 12 个申请生成正式结构化资格审查结果。业务输出包括每个申请的 `APPROVE`、`HOLD` 或 `DENY` 决定、受控 reason code、下一步动作、缺陷计数和 bulletin impact 汇总。

该任务符合本场景，因为它要求跨多个行政许可数据源进行核对：申请记录、bond、insurance、violations、complaints、field notes、correspondence 和已生效 bulletins。输出是可评测的审查决策数据，而不是自由文本总结。

### 材料地图

关键 CLRP 资源如下：

- `/api/contractors/applications?batch_id=HS-2026-Q1A` 和 `/exports/contractor_batch_HS-2026-Q1A.csv`：目标申请清单和基础属性。
- `/api/contractors/bonds?name=...`：bond 金额、状态、shortfall 和 cancellation 证据。
- `/api/contractors/insurance?name=...`：carrier、policy、coverage 和 verification status。
- `/api/contractors/violations?name=...`：不利行为和 unresolved penalty 证据。
- `/api/contractors/complaints?name=...`：投诉背景；并非每条投诉都是计分缺陷。
- `/api/contractors/field-notes?name=...`：open inspector hold 和 clearance 建议。
- `/api/contractors/correspondence?batch_id=HS-2026-Q1A`：material notice 和干扰性 correspondence。
- `/api/contractors/bulletins?effective_on=2026-03-01`：审查截止日前已经生效的 bulletins。

### 解答与评测依据

标准答案包含 12 条 `application_decisions`、`deficiency_counts` 和 `bulletin_impacts`。

决策依据如下：

- `CA-2026-0001`、`CA-2026-0008`、`CA-2026-0011` 为 approve；已解决或截止日外的噪声记录不构成 material hold。
- `CA-2026-0002` 因 `BOND_SHORTFALL` hold；Plumbing bulletin `CB-2026-008` 使当前最低 bond 要求高于 active bond amount。
- `CA-2026-0003` 因 `INSURANCE_VERIFY` hold；截至审查日，policy/correspondence 证据中 carrier verification 仍为 pending。
- `CA-2026-0004` 因 `UNRESOLVED_PENALTY` hold；未解决罚款和 AG referral 需要先处理。
- `CA-2026-0005` 因 `FIELD_NOTE_HOLD` hold；open inspector hold 需要 clearance。
- `CA-2026-0006` 因 `BOND_CANCELLED` hold；bond cancellation date 在截止日前。
- `CA-2026-0007` 因 `EXPERIENCE_VERIFY` hold；principal 的 qualifying experience 记录不足以直接 clearance。
- `CA-2026-0009` 因 `BOND_SHORTFALL` 和 `INSURANCE_VERIFY` hold；Roofing bulletins `CB-2026-004` 和 `CB-2026-005` 是主要 bulletin impact。
- `CA-2026-0010` 因 `DISQUALIFYING_CONDUCT` deny；adverse background status 与 fraudulent-registration history 支持 denial，而非可补正 hold。
- `CA-2026-0012` 因 `UNRESOLVED_PENALTY` 和 `FIELD_NOTE_HOLD` hold；罚款/AG referral 与 open inspector hold 均未解决。

缺陷计数为 `APPROVE=3`、`HOLD=8`、`DENY=1`。reason-code 计数以 `output/answer.json` 为准。Bulletin impact 使用截止日前适用的 `CB-2026-001` 至 `CB-2026-011`。`CA-2026-0002` 和 `CA-2026-0009` 是受 2026 bulletin 改变的申请。bulletin rule-type 缺陷计数为 `BOND_MINIMUM=2`、`INSURANCE_MINIMUM=1`、`EXAM_MINIMUM=0`、`EXPERIENCE_MINIMUM=0`。

评测器包含 8 个 exact-match 计分点，原始权重均为 1、2 或 3：

- `SP001`，权重 1：申请覆盖范围和顺序完全正确。
- `SP002`，权重 3：12 个申请的 determination map 完全正确。
- `SP003`，权重 2：clean approval cases 完全正确。
- `SP004`，权重 2：bond-related hold 结果和动作完全正确。
- `SP005`，权重 2：insurance-verification hold 结果和动作完全正确。
- `SP006`，权重 3：penalty、field-note 和 denial cases 完全正确。
- `SP007`，权重 2：`deficiency_counts` 完全一致。
- `SP008`，权重 3：`bulletin_impacts` 完全一致。

常见失败点包括使用本地 env 文件而不是 API、忽略 batch cutoff date、把每条历史 complaint 或 resolved violation 都当作缺陷、漏掉 correspondence/field-note 对决策的影响、把 bond cancellation 当成普通 shortfall、应用 cutoff 之后的 bulletins、或遗漏受控枚举中的零计数字段。

### 迁移设计

这是 train task，不是教程。通过盲解和对照标准答案，模型应学到可迁移经验：使用共享 CLRP API，将有效 bulletin changes 与普通缺陷分开，区分 hold 与 denial，用受控 reason codes，依据申请清单核对 bond/insurance，并避免把截止日外或非 material 噪声当作业务缺陷。这些经验会迁移到后续 contractor test tasks，尤其是 bulletin-scope counts、bond cancellation 与 shortfall 区分、field-note holds 和 aggregate deficiency counts。

### 构造记录

作者：Codex task-builder subagent for `task_group_019/train_001`。

创建日期：2026-07-07。

更新日期：2026-07-07。

主要变更：创建 contractor batch eligibility review 的 solver prompt、endpoint payload、answer template、standard answer、exact-match evaluator 和双语 notes。
