# Seasonal Dialysis Transfer Packet Review: Gulf Coast Winter Arrivals

## English Notes

Data lineage: this task belongs to `task_group_013`, scenario `SCN_013_healthcare_patient_intake_transfer`, with source examples `E001` through `E005`. It is the train task `train_003` described in `scratch/task_group_design.md`. The task uses generated environment data from `task_group/task_group_013/env/data/clinic.db`, especially `transfer_requests`, `documents`, `facility_capacity`, and `patients`. The solver-visible files are `input/prompt.txt` and `input/payloads/answer_template.json`.

Task definition: the solver reviews transfer batch `DIAL-WINTER-01` for seasonal in-center hemodialysis visitors. The expected answer is JSON with one row per transfer request and a cohort summary. The business outputs are document completeness, stale freshness-limited documents, missing required packet items, requested-start feasibility using chair capacity, final intake decision, and next-contact owner/route.

Scenario fit: the task is a direct packet-and-transfer readiness workflow from the healthcare intake scenario. It mirrors the E001 seasonal dialysis transfer packet problem while using the shared Cedar Ridge portal and generated records. It also connects to the broader task group convention that draft or voided artifacts do not satisfy packet/chart requirements and that routing depends on the operational blocker.

Material map: `GET /transfers?batch_id=DIAL-WINTER-01` identifies the six transfer requests and requested start dates. `GET /patients/{patient_id}` provides patient identity context. `GET /documents?transfer_id=...` provides packet artifacts, status, finalized flag, and received dates. `POST /query` can be used to aggregate rows from the same read-only SQLite data. `facility_capacity` records, available through SQL, determine open in-center hemodialysis chairs for each requested start date.

Solution basis: required packet items are face sheet, insurance proof, HBsAg, Hep B antibody/core, monthly labs, flu vaccine or proof, pneumonia vaccine or proof, TB/CXR entry, history and physical, medication list, allergy list, physician orders, vascular access report, treatment flowsheets, and transportation mode. Only final/finalized documents count. HBsAg, monthly labs, and the combined `ppd_or_cxr` TB/CXR item are fresh for 30 days. Hep B antibody/core and history/physical are fresh for 365 days. The combined `ppd_or_cxr` generated data intentionally uses 65-day near misses in this batch, so it is evaluated under the 30-day TB/CXR freshness check.

Gold answer summary: transfers `TR0001` through `TR0006` correspond to patients `P014` through `P019`. Only `TR0005` has all required packet items present and finalized, but it still has stale HBsAg and `ppd_or_cxr`. All six transfers have stale clinical freshness items, so the final intake decision is `clinical_review` for every patient. Requested start dates `2026-12-14`, `2026-12-16`, and `2026-12-18` have five open chairs across Cedar Ridge locations; `2026-12-08`, `2026-12-10`, and `2026-12-12` have no capacity row/open chair. Because every packet is clinically not ready, no transfer is ready on the requested start.

Evaluation basis: the evaluator has seven whole-point scoring dimensions with raw weights `[3, 3, 2, 2, 3, 2, 1]`:

- SP001, weight 3: packet completeness status for all six transfer patients.
- SP002, weight 3: stale-document detection for freshness-limited packet items.
- SP003, weight 2: missing required-document sets.
- SP004, weight 2: requested-start capacity status, open-chair total, and feasibility.
- SP005, weight 3: final intake decision for each patient.
- SP006, weight 2: next-contact owner and route for each non-accepted patient.
- SP007, weight 1: cohort summary counts.

Each scoring point is all-or-nothing. Lists are normalized as sets where appropriate. The evaluator embeds the gold answer and does not call the live environment.

Transfer design: as a train task, this example exposes transferable experience for the later dialysis test task: dialysis packet document categories, freshness windows, draft/finalized document handling, capacity-versus-readiness separation, `accept`/`hold`/`clinical_review` decision style, and contact routing. It is not a tutorial; the solver has to infer the working rules from the environment, prompt, and answer during few-shot skill generation.

Likely model pitfalls: treating draft documents as valid; using received date instead of requested start date for freshness age; considering `ppd_or_cxr` fresh for one year despite this generated task's TB/CXR freshness convention; ignoring transportation as a required transfer readiness item; marking patients as accepted because capacity exists even though stale clinical packet items remain; or failing to aggregate capacity across both Cedar Ridge locations.

Construction record: created by Codex task-builder for `train_003` on 2026-07-17. Files created under `task_group/task_group_013/train_tasks/003/` only. The final self-check evaluates `output/answer.json` to a score of 1.0.

## 中文说明

数据来源：本任务属于 `task_group_013`，场景为 `SCN_013_healthcare_patient_intake_transfer`，来源示例为 `E001` 到 `E005`。这是 `scratch/task_group_design.md` 中定义的训练任务 `train_003`。任务使用共享环境中生成的 `clinic.db` 数据，主要涉及 `transfer_requests`、`documents`、`facility_capacity` 和 `patients` 表。求解者可见材料只有 `input/prompt.txt` 和 `input/payloads/answer_template.json`。

任务定义：求解者需要审查 `DIAL-WINTER-01` 这一批冬季海湾地区透析转入申请。输出为 JSON，包括每个转入患者的文件完整性、过期文件、缺失文件、 requested start 与床位容量是否匹配、最终接收决定、下一步联系人/渠道，以及整批汇总。

场景匹配：该任务对应医疗转诊和入院协调中的透析转入包审核工作，与 E001 的季节性透析转入包场景一致，同时使用本任务组统一的 Cedar Ridge 门户和生成数据。它也强化了任务组内“草稿或作废文件不算有效文件”的通用约定。

材料说明：`GET /transfers?batch_id=DIAL-WINTER-01` 用于找到六条转入申请及 requested start date；`GET /patients/{patient_id}` 提供患者身份信息；`GET /documents?transfer_id=...` 提供文件类型、状态、finalized 标记和接收日期；`POST /query` 可用于读取同一只读 SQLite 数据；`facility_capacity` 表用于计算 requested start date 当天的开放透析椅位。

答案依据：有效转入包需要 face sheet、insurance proof、HBsAg、Hep B antibody/core、monthly labs、flu vaccine/proof、pneumonia vaccine/proof、TB/CXR 项、history and physical、medication list、allergy list、physician orders、vascular access report、treatment flowsheets 和 transportation mode。只有 final 且 finalized 的文件有效。HBsAg、monthly labs 和合并字段 `ppd_or_cxr` 的有效期按 30 天处理；Hep B antibody/core 和 history/physical 的有效期按 365 天处理。本批数据中特意设置了 65 天的 TB/CXR 近似过期样例，因此评估中 `ppd_or_cxr` 按 30 天新鲜度判断。

标准答案摘要：`TR0001` 到 `TR0006` 分别对应 `P014` 到 `P019`。只有 `TR0005` 的必需文件均存在且 finalized，但它仍有过期的 HBsAg 和 `ppd_or_cxr`。六名患者均存在临床新鲜度过期项，因此最终决定全部为 `clinical_review`。`2026-12-14`、`2026-12-16`、`2026-12-18` 在 Cedar Ridge 两个地点合计各有 5 个开放椅位；`2026-12-08`、`2026-12-10`、`2026-12-12` 没有可用容量。由于所有包都未达到临床就绪，requested start ready 计数为 0。

评估依据：评估器包含 7 个整点评分项，原始权重为 `[3, 3, 2, 2, 3, 2, 1]`，分别覆盖文件完整性、过期文件、缺失文件、requested start 可行性、最终决定、下一步联系人/渠道和批次汇总。每个评分项只有全得或不得分，不给小项内部分分。列表按集合方式归一化，评估器内置标准答案，不依赖运行中的环境。

迁移设计：作为训练任务，本任务为后续透析转入测试任务提供可迁移经验，包括透析转入包文件类别、新鲜度窗口、草稿文件处理、容量与文件就绪状态的区分、`accept`/`hold`/`clinical_review` 决策风格，以及联系路由。它不是教程；few-shot 技能生成需要从正式任务输入和标准答案中归纳这些规则。

常见错误：把 draft 文件当作有效文件；用当前日期而不是 requested start date 计算新鲜度；把本任务的 `ppd_or_cxr` 按一年有效期处理；忽略 transportation；仅因有容量就接受患者；或者只看单个地点而没有汇总两个 Cedar Ridge 地点的容量。

构建记录：由 Codex task-builder 于 2026-07-17 创建，仅写入 `task_group/task_group_013/train_tasks/003/`。最终自检中 `output/answer.json` 应得到 1.0 分。
