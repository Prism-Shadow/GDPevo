# test_003 Notes

## English

### Data and Source Lineage

This task is `test_003` for `task_group_019`, scenario `SCN_019_regulatory_licensing_eligibility_and_compliance_review`, using source examples `E001`, `E002`, and `E003`. It implements the restricted on-premises alcohol license review family described in `scratch/task_group_design.md`: a same-premises restricted-license review where proposed controls overlap prior failed controls and the reviewer must separate standard obligations, location-specific restrictions, verification gaps, and first-90-day inspection priorities.

The shared environment is Cascadia Licensing Review Portal (CLRP) in `task_group/task_group_019/env/`. Generated data comes from `env/data/clrp.db`, with public API surfaces documented in `env/data/public_manifest.json`. The construction manifest anchors the May 2026 alcohol review month to application `AA-2026-0036`, premises `PM-2026-036`, and issue tags `SAME_PREMISES_OVERLAP`, `CONTROL_OVERLAP`, and `VERIFICATION_GAP`.

Solver-visible files are `input/prompt.txt` and `input/payloads/answer_template.json`. The prompt gives `http://localhost:<PORT>`, the target IDs, and the required JSON result categories without giving a procedural checklist or the answer path.

### Task Definition and Material Map

The business task is to prepare a reviewer-ready restricted on-premises alcohol licensing review for application `AA-2026-0036`, premises `PM-2026-036`, review month `2026-05`.

Important CLRP records:

- `GET /api/alcohol/applications?review_month=2026-05` identifies the target as a `F-COM` application for `Foundry Room 36`, requested posture `restricted issuance`.
- `GET /api/alcohol/premises?premises_id=PM-2026-036` shows same address and overlapping service area as prior licensee `Signal Hospitality LLC`.
- `GET /api/alcohol/incidents?premises_id=PM-2026-036` returns six same-premises incidents. Two have unresolved or blank dispositions: `AI-2026-0071` and `AI-2026-0097`. Three are high severity: `AI-2026-0012`, `AI-2026-0071`, and `AI-2026-0111`.
- `GET /api/alcohol/settlements?premises_id=PM-2026-036` returns prior settlement `AS-2026-0012`, original posture `restricted issue`, final terms about noise abatement and quarterly inspection.
- `GET /api/alcohol/restrictions?premises_id=PM-2026-036` returns two premises-specific restrictions: `AR-2026-0023` `SECURITY_LOG` and `AR-2026-0024` `NO_AFTER_MIDNIGHT_SERVICE`.
- `GET /api/alcohol/standard-obligations?license_type=F-COM` returns `F_COM_FOOD`, `F_COM_SERVER`, `F_COM_MINORS`, plus all-license obligations `PUBLIC_RECORDS` and `INCIDENT_REPORT`.
- `GET /api/search/address?address=352%20Front%20St` returns only the target alcohol premises/application and no renewal rows, so successor risk is based on alcohol same-premises history, not renewal matching.

### Solution and Evaluation Basis

The standard answer recommends `ISSUE_RESTRICTED_WITH_MONITORING`. The file already has premises-specific controls, so it is not the standard-only follow-up posture from `train_002`; however, those controls overlap the same-premises risk pattern and do not erase the unresolved high-risk evidence. The answer therefore keeps the restricted issuance posture while making monitoring and verification explicit.

Risk assessment: `SAME_ADDRESS_OVERLAP`, prior licensee `Signal Hospitality LLC`, `HIGH` prior incident level, 6 total incidents, 2 unresolved/blank-disposition incidents, 3 high-severity incidents, `PRIOR_RESTRICTED_OR_DENIAL`, `OVERLAPS_PRIOR_FAILED_CONTROLS`, successor risk `HIGH`, and overall risk `SEVERE`.

Control classification separates F-COM/all-license standard obligations from premises-specific controls. Standard obligations are `F_COM_FOOD`, `F_COM_MINORS`, `F_COM_SERVER`, `INCIDENT_REPORT`, and `PUBLIC_RECORDS`. Location-specific restrictions are `NO_AFTER_MIDNIGHT_SERVICE` and `SECURITY_LOG`, both classified as overlapping prior failed controls because the premises risk summary and incident history show the same address/service-area operation had continuing security and disorder concerns.

Verification gaps are `CONTROL_EFFECTIVENESS_EVIDENCE_NOT_VERIFIED`, `PENDING_ASSAULT_CALL_DISPOSITION`, `PRIOR_RESTRICTED_SETTLEMENT_PACKET`, `SAME_PREMISES_SUCCESSOR_STATEMENT_MISSING`, and `SECURITY_PLAN_LAPSE_DISPOSITION_MISSING`. First-90-day inspection priorities are ranked: security log review, police call log review for assault history, after-midnight service log review, and F-COM standard obligation check.

The evaluator is `eval/evaluator.py`, invoked by `eval/eval.sh`. It uses eight exact-match scoring points with raw weights 2, 2, 2, 2, 2, 3, 3, and 3:

- Target identity and recommendation.
- Risk classifications.
- Incident counts and source IDs.
- Controls summary counts and separation/overlap flags.
- Standard obligation set with source IDs and evidence.
- Location-specific restriction set with overlap status and first-90-day focus.
- Verification-gap set with source IDs and statuses.
- Ranked inspection priorities with source IDs and timing.

Lists that are not business-ranked are normalized by stable code or source ID. The `inspection_priorities` list is ranked and evaluated by `priority_rank`.

### Transfer Design

Transfer anchors are `train_002` and `train_005`.

From `train_002`, solvers should transfer that requested restricted issuance is not enough by itself, standard obligations must not be mistaken for location-specific restrictions, same-premises history changes the recommendation, and first-90-day controls should address the unresolved risk pattern. `test_003` changes the target month, license type, evidence mix, and current control coverage: unlike `train_002`, this target has premises-specific controls.

From `train_005`, solvers should transfer the successor-risk framing, current license-type standard obligation lookup, control-overlap analysis, and conversion of unresolved same-premises evidence into structured verification and monitoring outputs. `test_003` changes from a March `BREWPUB` case to a May `F-COM` case, uses different incidents and settlement posture, has no renewal address match, and requires ranked inspection priorities instead of records requests/escalation triggers.

High-value scoring points depend on this transfer: recommendation posture, control classification, verification gaps, and inspection priorities. Task-specific exploration remains necessary because all target source IDs, incident counts, settlement details, and F-COM standard obligations differ from the train tasks.

### Construction Record

Author: task-builder subagent for `test_003`.
Created: 2026-07-07.
Updated: 2026-07-07.
Major changes: initial creation of prompt, answer template, standard answer, exact-match evaluator, and bilingual notes for the May 2026 restricted on-premises alcohol licensing review.

## 中文

### 数据与来源

本任务是 `task_group_019` 的 `test_003`，场景为 `SCN_019_regulatory_licensing_eligibility_and_compliance_review`，来源示例为 `E001`、`E002`、`E003`。任务属于 `scratch/task_group_design.md` 中的限制性店内酒类许可审查：同址经营风险较高，拟议控制与既往失效控制重叠，审查者需要区分标准义务、地点特定限制、核验缺口和首 90 天检查重点。

共享环境是 `task_group/task_group_019/env/` 下的 Cascadia Licensing Review Portal。生成数据位于 `env/data/clrp.db`，公开 API 记录在 `env/data/public_manifest.json`。构造清单将 2026 年 5 月酒类审查锚定到申请 `AA-2026-0036`、场所 `PM-2026-036`，问题标签为 `SAME_PREMISES_OVERLAP`、`CONTROL_OVERLAP`、`VERIFICATION_GAP`。

求解者可见文件为 `input/prompt.txt` 和 `input/payloads/answer_template.json`。提示中只给出 `http://localhost:<PORT>`、目标 ID 和 JSON 输出类别，没有给出流程清单或答案路径。

### 任务定义与材料地图

业务任务是为申请 `AA-2026-0036`、场所 `PM-2026-036`、审查月份 `2026-05` 准备审查员可用的限制性店内酒类许可审查结果。

关键 CLRP 记录如下：

- `GET /api/alcohol/applications?review_month=2026-05` 显示目标为 `F-COM` 申请，DBA 是 `Foundry Room 36`，请求姿态为限制性发证。
- `GET /api/alcohol/premises?premises_id=PM-2026-036` 显示该地点与前许可人 `Signal Hospitality LLC` 同地址且服务区域重叠。
- `GET /api/alcohol/incidents?premises_id=PM-2026-036` 返回 6 条同址事件。其中 `AI-2026-0071` 和 `AI-2026-0097` 为待处理或处分为空；`AI-2026-0012`、`AI-2026-0071`、`AI-2026-0111` 为高严重度事件。
- `GET /api/alcohol/settlements?premises_id=PM-2026-036` 返回既往和解 `AS-2026-0012`，原始姿态为 `restricted issue`，最终条款涉及噪声消减和季度检查。
- `GET /api/alcohol/restrictions?premises_id=PM-2026-036` 返回两个地点特定限制：`AR-2026-0023` 的 `SECURITY_LOG` 和 `AR-2026-0024` 的 `NO_AFTER_MIDNIGHT_SERVICE`。
- `GET /api/alcohol/standard-obligations?license_type=F-COM` 返回 `F_COM_FOOD`、`F_COM_SERVER`、`F_COM_MINORS`，以及所有牌照通用的 `PUBLIC_RECORDS`、`INCIDENT_REPORT`。
- `GET /api/search/address?address=352%20Front%20St` 只返回目标酒类场所和申请，没有续期记录，因此继任风险来自酒类同址历史，而不是续期匹配。

### 解答与评估依据

标准答案建议 `ISSUE_RESTRICTED_WITH_MONITORING`。目标文件已经存在地点特定控制，因此不同于 `train_002` 中只有标准义务覆盖的后续补件姿态；但这些控制与同址风险模式重叠，不能消除未解决的高风险证据。因此答案保留限制性发证方向，同时明确监控和核验要求。

风险评估为：`SAME_ADDRESS_OVERLAP`，前许可人为 `Signal Hospitality LLC`，既往事件等级 `HIGH`，事件总数 6，待处理或处分为空事件 2，高严重度事件 3，`PRIOR_RESTRICTED_OR_DENIAL`，`OVERLAPS_PRIOR_FAILED_CONTROLS`，继任风险 `HIGH`，整体风险 `SEVERE`。

控制分类将 `F-COM` 和通用标准义务与地点特定控制分开。标准义务为 `F_COM_FOOD`、`F_COM_MINORS`、`F_COM_SERVER`、`INCIDENT_REPORT`、`PUBLIC_RECORDS`。地点特定限制为 `NO_AFTER_MIDNIGHT_SERVICE` 和 `SECURITY_LOG`，二者都被归类为与既往失效控制重叠，因为场所风险摘要和事件历史显示同地址、同服务区域经营中持续存在安全和秩序问题。

核验缺口包括 `CONTROL_EFFECTIVENESS_EVIDENCE_NOT_VERIFIED`、`PENDING_ASSAULT_CALL_DISPOSITION`、`PRIOR_RESTRICTED_SETTLEMENT_PACKET`、`SAME_PREMISES_SUCCESSOR_STATEMENT_MISSING`、`SECURITY_PLAN_LAPSE_DISPOSITION_MISSING`。首 90 天检查重点依次为：安全日志复核、攻击/滋事类警方呼叫记录复核、午夜后服务日志复核、以及 `F-COM` 标准义务检查。

评估器为 `eval/evaluator.py`，由 `eval/eval.sh` 调用。它包含 8 个精确匹配评分点，原始权重分别为 2、2、2、2、2、3、3、3：

- 目标身份和推荐姿态。
- 风险分类。
- 事件计数和来源 ID。
- 控制摘要计数以及标准/地点特定分离与重叠标志。
- 标准义务集合及来源 ID、证据要求。
- 地点特定限制集合、重叠状态和首 90 天重点。
- 核验缺口集合、来源 ID 和状态。
- 排序后的检查重点、来源 ID 和时间安排。

非业务排序列表按稳定代码或来源 ID 规范化；`inspection_priorities` 是业务排序列表，按 `priority_rank` 评估。

### 迁移设计

迁移锚点为 `train_002` 和 `train_005`。

从 `train_002` 可迁移的经验包括：不能仅因申请请求限制性发证就认为控制充分；标准义务不能误当作地点特定限制；同址历史会改变审查建议；首 90 天控制应针对未解决风险模式。`test_003` 改变了目标月份、牌照类型、证据组合和当前控制覆盖情况：与 `train_002` 不同，本目标已有地点特定控制。

从 `train_005` 可迁移的经验包括：继任风险框架、按当前牌照类型查找标准义务、控制重叠分析，以及把未解决同址证据转换为结构化核验和监控输出。`test_003` 从 3 月 `BREWPUB` 个案改为 5 月 `F-COM` 个案，事件和和解姿态不同，没有续期地址匹配，并要求输出排序后的检查重点，而不是记录请求和升级触发条件。

高价值评分点依赖这些迁移经验：推荐姿态、控制分类、核验缺口和检查重点。任务本身仍需要新的数据探索，因为目标来源 ID、事件计数、和解细节和 `F-COM` 标准义务都与训练任务不同。

### 构造记录

作者：`test_003` task-builder subagent。
创建日期：2026-07-07。
更新日期：2026-07-07。
主要变更：首次创建 2026 年 5 月限制性店内酒类许可审查的提示、答案模板、标准答案、精确匹配评估器和双语说明。
