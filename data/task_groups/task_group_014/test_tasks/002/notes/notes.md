# test_002 Notes: Peer-to-peer finalization board

## English

### Purpose

This formal test task asks a peer-to-peer coordinator to reconcile the `test_p2p_batch` board through the shared SQL service. Solver-visible files are intentionally concise: they provide the role, business goal, SQL endpoint placeholder, target scope payload, and required JSON shape. The detailed operating logic is retained here and in the evaluator.

### Data lineage

Target cases come from `authorization_requests.target_bucket = 'test_p2p_batch'`:

- `AUTH00019`
- `AUTH00020`
- `AUTH00021`
- `AUTH00022`
- `AUTH00023`
- `AUTH00024`

The canonical answer was derived from `authorization_requests`, `auth_lines`, `p2p_sessions`, `case_review_events`, `clinical_facts`, `evidence_documents`, `coverage_criteria`, `criteria_sources`, `members`, `plans`, `providers`, `facilities`, and `service_codes`.

### Solution basis

Clinical criteria source selection follows the train pattern: use the highest-precedence applicable criteria rows for the case plan type and service category, falling back to `ALL` criteria rows when there is no exact plan-type criteria set. The target cases all carry `SRC003` into final rationale because no applicable CMS or state Medicaid criteria rows exist for their target service-category combinations.

Evidence is treated as clearly supportive only when the fact value meets the required value, the linked document is current, and the confidence flag is clear. Stale, partial, conflicting, unclear, or missing facts do not support a full clinical approval.

The finalization interpretation used for the answer is:

- `AUTH00019`: completed session with new information. It supports a partial overturn but not full approval because the multi-service request still has unresolved DME and stale/missing clinical support. It queues a partial-approval letter with appeal rights.
- `AUTH00020`: completed session with no new information. Physical therapy criteria are not clearly met, so the adverse posture is upheld by MD-only finalization authority.
- `AUTH00021`: P2P is not completed and the session outcome requests additional information, so no adverse final is issued yet.
- `AUTH00022`: completed provider no-show with unresolved physical therapy criteria. The denial is upheld and appeal rights are queued.
- `AUTH00023`: advanced imaging requires MD review, and the medical-director review event requested more information. The case stays pending additional information instead of receiving an adverse final.
- `AUTH00024`: direct administrative finalization applies because the facility is outside the service area. The case is not a proper P2P reconsideration path even though a P2P row exists, and it queues an administrative denial with appeal rights.

Final rationale codes use the selected criteria source plus a compact finalization trigger. The pending-additional-information case driven by unresolved criteria uses `criteria_not_clearly_met_more_information_needed`, and `letter_authority_reason_code` mechanically joins the letter queue, adverse authority status, and final rationale code with double underscores.

### Transfer anchors

- `train_002`: transfers clinical criteria source selection, current/clear evidence sufficiency, nurse-versus-MD adverse authority, and P2P suitability logic.
- `train_001`: transfers administrative direct-path handling once a case has a nonclinical intake barrier such as out-of-service-area facility.

### Scoring goals

The evaluator uses ten exact-match structured business-result points:

- final board classifications by case, raw weight 1;
- criteria source and unresolved criteria gap keys by case, raw weight 2;
- P2P session and medical-director review-event trace by case, raw weight 3;
- additional-information and appeal-rights notice flags plus counts, raw weight 1;
- board metadata, finalization counts, and letter queue lists, raw weight 1;
- administrative source trace for facility, exception, and mandatory-MD flags, raw weight 1;
- criteria source precedence selection trace, raw weight 2;
- final rationale code, raw weight 3;
- finalization reason bundle, raw weight 3;
- letter-authority reason codes, raw weight 3.

### Construction record

The construction-visible SQLite database was inspected directly to compute the canonical answer. Solver-visible files disclose the fixed synthetic Basic Auth credentials for `<TASK_ENV_BASE_URL>/query`, but do not include machine-specific host, port, or database-path details, hidden answer paths, numbered SOPs, scoring logic, or full rule checklists.

## 中文

### 目的

这个正式测试任务要求 P2P 协调员通过共享 SQL 服务核对 `test_p2p_batch` 终结看板。面向解题者的文件刻意保持简洁：只提供角色、业务目标、SQL 端点占位符、目标范围载荷和所需 JSON 形状。详细操作逻辑保留在本说明和评估器中。

### 数据来源

目标病例来自 `authorization_requests.target_bucket = 'test_p2p_batch'`：

- `AUTH00019`
- `AUTH00020`
- `AUTH00021`
- `AUTH00022`
- `AUTH00023`
- `AUTH00024`

标准答案由 `authorization_requests`、`auth_lines`、`p2p_sessions`、`case_review_events`、`clinical_facts`、`evidence_documents`、`coverage_criteria`、`criteria_sources`、`members`、`plans`、`providers`、`facilities` 和 `service_codes` 推导。

### 解题依据

临床标准来源选择沿用训练任务模式：为病例的计划类型和服务类别选择适用且优先级最高的标准行；没有精确计划类型标准时，回退到 `ALL` 标准行。目标病例的服务类别没有适用的 CMS 或州 Medicaid 标准行，因此最终理由均携带 `SRC003`。

只有当事实值满足要求、关联文件为当前文件、且置信标记为 clear 时，证据才被视为明确支持。stale、partial、conflicting、unclear 或缺失事实都不能支持完整临床批准。

标准答案使用的终结解释为：

- `AUTH00019`：P2P 已完成且有新信息。新信息支持部分推翻，但多服务请求仍有 DME 未解决以及陈旧或缺失的临床支持，因此进入带申诉权的部分批准函队列。
- `AUTH00020`：P2P 已完成但没有新信息。物理治疗标准未被明确满足，因此由 MD-only 终结权限维持不利决定。
- `AUTH00021`：P2P 未完成且会话结果要求补充信息，所以暂不发出不利终结。
- `AUTH00022`：P2P 已完成但服务提供方未参加，且物理治疗标准仍未解决。维持拒绝并发送申诉权通知。
- `AUTH00023`：高级影像需要 MD 审核，且 medical-director 审核事件要求更多信息。因此病例保持补充信息待处理，而不是发出不利终结。
- `AUTH00024`：因机构不在服务区域内，适用直接行政终结。即使存在 P2P 行，它也不是合适的 P2P 复议路径，并进入带申诉权的行政拒绝函队列。

最终理由代码使用选定的标准来源加紧凑的终结触发因素。由于标准未明确满足而待补资料的病例使用 `criteria_not_clearly_met_more_information_needed`；`letter_authority_reason_code` 由函件队列、终结权限状态和最终理由代码用双下划线机械拼接。

### 迁移锚点

- `train_002`：迁移临床标准来源选择、当前且清晰的证据充分性、护士与 MD 的不利决定权限边界，以及 P2P 适用性逻辑。
- `train_001`：迁移当病例存在非临床准入障碍时的行政直接路径处理，例如机构不在服务区域内。

### 评分目标

评估器使用十个精确匹配的结构化业务结果点：

- 每个病例的最终看板分类，原始权重 1；
- 每个病例的标准来源和未解决的标准缺口 key，原始权重 2；
- 每个病例的 P2P 会话和 medical-director 审核事件追踪，原始权重 3；
- 需要补充信息和申诉权通知的病例及计数，原始权重 1；
- 看板元数据、终结计数和函件队列列表，原始权重 1；
- 机构、例外和强制 MD 标记的行政来源追踪，原始权重 1；
- 标准来源优先级选择追踪，原始权重 2；
- 最终理由代码，原始权重 3；
- 终结理由组合，原始权重 3；
- 函件和权限理由代码，原始权重 3。

### 构建记录

构建时直接检查了 construction-visible SQLite 数据库来计算标准答案。面向解题者的文件公开访问 `<TASK_ENV_BASE_URL>/query` 所需的固定合成 Basic Auth 凭据，但不包含机器相关的主机、端口或数据库路径信息、隐藏答案路径、编号 SOP、评分逻辑或完整规则清单。
