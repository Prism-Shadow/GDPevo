# train_002 Notes: Nurse Clinical Review And MD Escalation Slate

## English

Task role: payer-side nurse reviewer completing preliminary recommendations for `train_clinical_batch`.

Construction-visible data sources used: `authorization_requests`, `auth_lines`, `service_codes`, `members`, `plans`, `criteria_sources`, `coverage_criteria`, `clinical_facts`, and `evidence_documents` in the shared SQLite database.

Target cases: `AUTH00007`, `AUTH00008`, `AUTH00009`, `AUTH00010`, `AUTH00011`, and `AUTH00012`.

Solution basis:

- Criteria source selection uses the lowest precedence source matching the service category and either exact plan type or `ALL`.
- Medicare Advantage physical therapy cases fall back to `SRC003` because the database has no CMS-specific physical therapy criterion row.
- A required criterion is counted as clearly met only when its fact value matches the required value, the linked document is current, and the confidence flag is `clear`.
- `AUTH00007` is the only clean nurse approval.
- `AUTH00008` is a noncovered experimental therapy with mandatory MD review, so it is not P2P-suitable.
- `AUTH00009`, `AUTH00010`, `AUTH00011`, and `AUTH00012` have clinically resolvable unclear, partial, stale, or conflicting evidence gaps and are P2P-suitable after MD escalation.

Scoring design: the evaluator has eight exact-match structured points with raw weights 1, 2, or 3. The points cover review date, nurse recommendation, MD escalation reason, criteria source, missing evidence keys, P2P suitability, approved units, and queue counts.

Construction record: files were created only under `train_tasks/002`. Solver-visible files disclose the fixed synthetic Basic Auth credentials for `<TASK_ENV_BASE_URL>/query`, but do not expose localhost, runtime ports, raw database paths, or direct-answer endpoints.

## 中文

任务角色：付款方使用管理护士审核员，为 `train_clinical_batch` 工作清单完成初步临床建议。

构建时使用的数据来源：共享 SQLite 数据库中的 `authorization_requests`、`auth_lines`、`service_codes`、`members`、`plans`、`criteria_sources`、`coverage_criteria`、`clinical_facts` 和 `evidence_documents`。

目标病例：`AUTH00007`、`AUTH00008`、`AUTH00009`、`AUTH00010`、`AUTH00011` 和 `AUTH00012`。

答案依据：

- 标准来源选择使用与服务类别匹配、且计划类型为精确匹配或 `ALL` 的最低优先级来源。
- Medicare Advantage 的物理治疗病例回退到 `SRC003`，因为数据库中没有 CMS 专属的物理治疗标准行。
- 必需标准只有在事实值等于要求值、关联文档为当前文档、且置信标记为 `clear` 时才算明确满足。
- `AUTH00007` 是唯一可由护士直接批准的病例。
- `AUTH00008` 是未覆盖的实验性治疗，并且要求 MD 审核，因此不适合 P2P。
- `AUTH00009`、`AUTH00010`、`AUTH00011` 和 `AUTH00012` 存在可通过医生沟通或补充当前证据解决的临床证据缺口，因此 MD 升级后适合 P2P。

评分设计：评估器包含八个精确匹配的结构化业务结果点，原始权重为 1、2 或 3。评分点覆盖审核日期、护士建议、MD 升级原因、标准来源、缺失证据键、P2P 适用性、批准单位数和队列计数。

构建记录：所有文件仅创建在 `train_tasks/002` 下。求解器可见文件公开访问 `<TASK_ENV_BASE_URL>/query` 所需的固定合成 Basic Auth 凭据，但不暴露 localhost、运行时端口、原始数据库路径或直接答案接口。
