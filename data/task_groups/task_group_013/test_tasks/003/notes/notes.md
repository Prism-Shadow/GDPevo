# Seasonal Dialysis Transfer Packet Review: Summer Coastal Transfers

## English Notes

Data lineage: this task belongs to `task_group_013`, scenario `SCN_013_healthcare_patient_intake_transfer`, with source examples `E001` through `E005`. It is the test task `test_003` described in `scratch/task_group_design.md`. The task uses generated environment data from `task_group/task_group_013/env/data/clinic.db`, especially `transfer_requests`, `documents`, `facility_capacity`, and `patients`. The solver-visible files are `input/prompt.txt` and `input/payloads/answer_template.json`.

Task definition: the solver reviews transfer batch `DIAL-SUMMER-02` for seasonal in-center hemodialysis visitors. The expected answer is JSON with one row per transfer request and a batch summary. The business outputs are packet completeness, stale freshness-limited documents, missing required packet items, requested-start feasibility using chair capacity, final intake decision, and next-contact owner/route.

Scenario fit: this is a direct healthcare transfer-intake workflow. It follows the same operational family as the E001 seasonal dialysis packet review and the train dialysis task while using a different season, coastal transfer dates, different missing/draft documents, and different facility capacity. It also uses the task-group convention that draft or voided documents do not satisfy readiness requirements.

Material map: `GET /transfers?batch_id=DIAL-SUMMER-02` identifies transfers `TR0007` through `TR0012`, their patients, requested start dates, modality, requested days, and transportation. `GET /patients/{patient_id}` provides patient identity context. `GET /documents?transfer_id=...` provides packet documents, final/draft status, finalized flag, and received dates. `POST /query` can be used to aggregate from the same read-only SQLite data. The `facility_capacity` table determines open in-center hemodialysis chairs across Cedar Ridge locations for each requested start date.

Solution basis: the required packet items are face sheet, insurance proof, HBsAg, Hep B antibody/core, monthly labs, flu vaccine or proof, pneumonia vaccine or proof, `ppd_or_cxr`, history and physical, medication list, allergy list, physician orders, vascular access report, treatment flowsheets, and transportation. Only documents with final status and `finalized=1` count. HBsAg, monthly labs, and `ppd_or_cxr` are fresh for 30 days. Hep B antibody/core and history/physical are fresh for 365 days. Freshness is judged against each transfer's requested start date.

Gold answer summary: no summer transfer has a complete current packet. `TR0007` is missing final HBsAg and pneumonia vaccine and has stale Hep B antibody/core, monthly labs, and `ppd_or_cxr`. `TR0008` is missing final allergy list and has stale HBsAg, monthly labs, and `ppd_or_cxr`. `TR0009` is missing flu vaccine, Hep B antibody/core, and pneumonia vaccine and has stale HBsAg, H&P, monthly labs, and `ppd_or_cxr`. `TR0010` has capacity on `2026-07-20` but lacks physician orders, transportation, treatment flowsheets, vascular access report, and has stale `ppd_or_cxr`. `TR0011` is missing face sheet and vascular access report and has stale HBsAg, H&P, monthly labs, and `ppd_or_cxr`. `TR0012` has capacity on `2026-07-24` but is missing final HBsAg and treatment flowsheets and has stale monthly labs and `ppd_or_cxr`.

Capacity basis: requested starts `2026-07-20` and `2026-07-24` each have seven open chairs across Cedar Ridge locations. Requested starts `2026-07-14`, `2026-07-16`, `2026-07-18`, and `2026-07-22` have no open capacity rows for the modality. Because every packet has clinical freshness or required-document problems, every transfer is `clinical_review`, no transfer is ready on the requested start, and the next contact is the clinical nurse by fax to the referring facility.

Evaluation basis: the evaluator has seven whole-point scoring dimensions with raw weights `[3, 3, 2, 2, 3, 2, 1]`:

- SP001, weight 3: packet completeness status for all six transfer patients.
- SP002, weight 3: stale-document detection for freshness-limited packet items.
- SP003, weight 2: missing required-document sets.
- SP004, weight 2: requested-start capacity status, open-chair total, and feasibility.
- SP005, weight 3: final intake decision for each patient.
- SP006, weight 2: next-contact owner and route for each non-accepted patient.
- SP007, weight 1: batch summary counts.

Each scoring point is all-or-nothing. Lists are normalized as sets where appropriate. The evaluator embeds the gold answer and does not call the live environment. The standard answer self-scores to 1.0 under the evaluator.

Transfer design and train anchors: `train_003` is the primary anchor for the dialysis transfer checklist, freshness windows, final-versus-draft handling, capacity aggregation, feasibility labels, and `clinical_review` routing when clinical packet items are stale or missing. `train_005` reinforces the broader routing habit that the owner and correspondence path should follow the dominant blocker rather than only the task label. The high-value transfer-dependent goals are SP001, SP002, SP005, and SP006. SP003 and SP004 add task-specific exploration difficulty because the missing/draft summer documents and July capacity pattern differ from the winter train batch. SP007 checks aggregation after the patient-level work.

Likely model pitfalls: treating draft HBsAg, face sheet, allergy list, physician orders, vascular access report, or treatment flowsheets as valid; using today's date rather than the requested start date for freshness; using a one-year window for the generated `ppd_or_cxr` field; failing to add capacity across Cedar Ridge locations; accepting `TR0010` or `TR0012` because capacity exists; or routing capacity-unavailable cases to scheduling even though all cases also have clinical packet problems.

Construction record: created by Codex task-builder for `test_003` on 2026-07-17. Files created under `task_group/task_group_013/test_tasks/003/` only.

## 中文说明

数据来源：本任务属于 `task_group_013`，场景为 `SCN_013_healthcare_patient_intake_transfer`，来源示例为 `E001` 到 `E005`。这是 `scratch/task_group_design.md` 中定义的测试任务 `test_003`。任务使用共享环境中生成的 `clinic.db` 数据，主要涉及 `transfer_requests`、`documents`、`facility_capacity` 和 `patients` 表。求解者可见材料只有 `input/prompt.txt` 和 `input/payloads/answer_template.json`。

任务定义：求解者需要审查 `DIAL-SUMMER-02` 这一批夏季海岸透析转入申请。输出为 JSON，包括每个转入患者的文件完整性、过期文件、缺失文件、requested start 与椅位容量是否匹配、最终接收决定、下一步联系人/渠道，以及整批汇总。

场景匹配：该任务属于医疗转入 intake 工作流，与 E001 的季节性透析转入包审核和训练任务 `train_003` 属于同一操作族。它改变了季节、日期、缺失/草稿文件和容量模式，但保留了共享环境和同一类业务判断。任务也沿用本任务组“草稿或作废文件不算有效文件”的约定。

材料说明：`GET /transfers?batch_id=DIAL-SUMMER-02` 用于找到 `TR0007` 到 `TR0012` 六条转入申请及对应患者、requested start date、模式、申请透析日和交通方式；`GET /patients/{patient_id}` 提供身份背景；`GET /documents?transfer_id=...` 提供文档类型、final/draft 状态、finalized 标记和接收日期；`POST /query` 可用于读取同一只读 SQLite 数据；`facility_capacity` 表用于计算各 requested start date 当天 Cedar Ridge 所有地点的开放透析椅位。

答案依据：有效转入包需要 face sheet、insurance proof、HBsAg、Hep B antibody/core、monthly labs、flu vaccine/proof、pneumonia vaccine/proof、`ppd_or_cxr`、history and physical、medication list、allergy list、physician orders、vascular access report、treatment flowsheets 和 transportation。只有 final 且 finalized 的文件有效。HBsAg、monthly labs 和 `ppd_or_cxr` 的有效期为 30 天；Hep B antibody/core 和 history/physical 的有效期为 365 天。新鲜度相对于每条转入申请的 requested start date 判断。

标准答案摘要：夏季批次中没有任何患者拥有完整且新鲜的转入包。`TR0007` 缺 final HBsAg 和 pneumonia vaccine，且 Hep B antibody/core、monthly labs、`ppd_or_cxr` 过期。`TR0008` 缺 final allergy list，且 HBsAg、monthly labs、`ppd_or_cxr` 过期。`TR0009` 缺 flu vaccine、Hep B antibody/core 和 pneumonia vaccine，且 HBsAg、H&P、monthly labs、`ppd_or_cxr` 过期。`TR0010` 在 `2026-07-20` 有容量，但缺 physician orders、transportation、treatment flowsheets、vascular access report，且 `ppd_or_cxr` 过期。`TR0011` 缺 face sheet 和 vascular access report，且 HBsAg、H&P、monthly labs、`ppd_or_cxr` 过期。`TR0012` 在 `2026-07-24` 有容量，但缺 final HBsAg 和 treatment flowsheets，且 monthly labs、`ppd_or_cxr` 过期。

容量依据：`2026-07-20` 和 `2026-07-24` 两个 requested start date 在 Cedar Ridge 所有地点合计各有 7 个开放椅位。`2026-07-14`、`2026-07-16`、`2026-07-18` 和 `2026-07-22` 对应模式没有可用容量。由于所有转入申请都存在临床新鲜度或必需文档问题，最终决定全部为 `clinical_review`，没有任何患者能在 requested start 当天就绪，下一步联系人均为 clinical nurse，渠道为向转出机构传真。

评估依据：评估器包含 7 个整点评分项，原始权重为 `[3, 3, 2, 2, 3, 2, 1]`，分别覆盖文件完整性、过期文件、缺失文件、requested start 可行性、最终决定、下一步联系人/渠道和批次汇总。每个评分项只有全得或不得分，不给小项内部分分。列表按集合方式归一化，评估器内置标准答案，不依赖运行中的环境。标准答案在该评估器下自评分为 1.0。

迁移设计与训练锚点：`train_003` 是主要训练锚点，提供透析转入包清单、新鲜度窗口、final 与 draft 的处理、容量汇总、feasibility 标签，以及临床文件过期或缺失时走 `clinical_review` 的路由经验。`train_005` 进一步强化“下一步 owner 和函件路径应跟随主导阻塞原因”的一般路由习惯。高价值迁移评分项是 SP001、SP002、SP005 和 SP006。SP003 与 SP004 包含测试任务本身的探索难度，因为夏季批次的缺失/草稿文件和七月容量模式不同于冬季训练批次。SP007 评估患者级结论后的汇总能力。

常见错误：把 draft 的 HBsAg、face sheet、allergy list、physician orders、vascular access report 或 treatment flowsheets 当成有效文件；用今天日期而不是 requested start date 判断新鲜度；把本生成环境中的 `ppd_or_cxr` 当作一年有效；没有汇总 Cedar Ridge 多个地点的容量；因为 `TR0010` 或 `TR0012` 有容量就误判为可接受；或把容量不可用病例交给 scheduling，但忽略所有病例同时都有临床包问题。

构建记录：由 Codex task-builder 于 2026-07-17 创建，仅写入 `task_group/task_group_013/test_tasks/003/`。
