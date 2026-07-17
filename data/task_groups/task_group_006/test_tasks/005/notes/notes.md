# Test 005 Notes: NOVA Headlamp Redesign Price-Change Control

## English

Task purpose: this test task asks the solver to produce a structured post-nomination price-change control file for a NOVA headlamp redesign. The solver sees an English prompt, a small English memo, and the shared ProcureOps API. The task is anchored on `PRG-NOVA-31`, `CR-NOVA-311`, `REQ-NOVA-302`, and `PO-NOVA-3107`.

Data lineage and material map: `input/payloads/headlamp_price_change_memo.json` names the memo `PCR-NOVA-HL-311`, the redesign reference `HL-NOVA-REV-C`, the impacted quantity `180`, and the proposed unit price `154.24`. The authoritative records are in the shared environment: `/programs/PRG-NOVA-31`, `/contracts/CR-NOVA-311`, `/purchase_requisitions/REQ-NOVA-302`, `/purchase_orders?contract_id=CR-NOVA-311`, `/receipts?po_id=PO-NOVA-3107`, `/ap/invoices?supplier_id=SUP-HEXEL`, `/approval_events?object_id=REQ-NOVA-302`, `/budget_snapshots/BUD-PRG-NOVA-31`, `/suppliers/SUP-HEXEL`, and `/vendor_risk_events?supplier_id=SUP-HEXEL`.

Solution basis: the active indexed contract `CR-NOVA-311` covers `SUP-HEXEL` / `SEN-NOVA` for `PRG-NOVA-31` at a baseline unit price of `149.75` with a `240000.00` ceiling. The memo's proposed unit price is `154.24`, so the delta is `4.49`, an uplift of `3.00%`. For `180` impacted units, the incremental subtotal is `808.20`; tax at `7.25%` is `58.59`; freight is `0.00`; incremental total is `866.79`.

Contract usage uses all non-cancelled purchase orders against `CR-NOVA-311`, not only the named NOVA PO. The included PO set is `PO-NOVA-3107`, `PO-00013`, `PO-00026`, and `PO-00042`, totaling `81613.75`. There are no cancelled contract POs to exclude. Contract headroom before the change is `158386.25`, and after the incremental price-delta exposure it is `157578.05`, so the ceiling check passes.

Program budget uses `BUD-PRG-NOVA-31`: budget cap `420000.00`, committed amount `358204.15`, remaining budget `61795.85`, and budget after this incremental price change `60929.06`, so budget passes. `REQ-NOVA-302` is converted and its latest approval event is `APR-00002`, action `approved`, actor `Procurement Lead`, dated `2026-05-08`. The nominated PO is received, with as-of receipt evidence `RCV-GOLD-27`; `AP-HEXEL-3309` is the matched invoice. `AP-00002` carries the proposed price but has no receipt and should be controlled as an unmatched price-variance invoice rather than used as payment evidence.

Supplier risk: `SUP-HEXEL` is active with risk rating `medium`. As of `2026-06-01`, the open event set is `VRE-00032`, the monitoring event set is `VRE-00010`, and there are no severe open events as of the memo date. Later open high events in the data are not part of the as-of answer. Supplier risk therefore does not block the amendment.

Expected decision: `release_price_amendment`. Required actions are `issue_price_delta_amendment` and `block_unmatched_price_invoice`; blocker count is `0`, currency is `USD`, and the file is ready to release.

Scoring points use seven exact-match checks with train-design weights:
- `SP1_identity_and_final_decision`, weight 2.
- `SP2_contract_price_and_change_basis`, weight 2.
- `SP3_contract_usage_and_ceiling`, weight 3.
- `SP4_budget_incremental_exposure`, weight 3.
- `SP5_nomination_and_approval_evidence`, weight 2.
- `SP6_supplier_risk_and_invoice_control`, weight 1.
- `SP7_actions_and_summary`, weight 2.

Transfer design: train task `train_001` anchors nomination readiness, conditional evidence, supplier-risk context, and as-of evidence handling. Train task `train_003` anchors NOVA invoice and payment-control reconciliation, including `AP-HEXEL-3309` as releasable evidence. Train task `train_004` anchors post-nomination change-control calculations: contract usage from non-cancelled POs, budget exposure with tax, approval-state checks, and structured hold/release decisions. The test changes the entity set to NOVA, uses an indexed price-delta amendment rather than a fixed-price quantity amendment, and adds an unmatched price-variance invoice that must be controlled without blocking the commercial amendment.

Construction record: created by Codex for `task_group_006/test_tasks/005` on 2026-06-01. The task-specific `scratch/task_group_design.md` was not present in `6.1/006/task_factory/scratch`; construction used the workspace builder context, available guides, train anchors, and shared environment records. Solver-visible files are English-only and do not include scoring weights, hidden derivation, or SOP steps.

## 中文

任务目的：本测试任务要求求解者为 NOVA 头灯 redesign 的 post-nomination 价格变更生成结构化控制文件。求解者只能看到英文 prompt、一个很小的英文 memo，以及共享 ProcureOps API。任务锚点为 `PRG-NOVA-31`、`CR-NOVA-311`、`REQ-NOVA-302` 和 `PO-NOVA-3107`。

数据来源和材料映射：`input/payloads/headlamp_price_change_memo.json` 给出 memo `PCR-NOVA-HL-311`、redesign reference `HL-NOVA-REV-C`、受影响数量 `180` 和 proposed unit price `154.24`。权威数据来自共享环境，包括 program、contract、requisition、contract 相关 PO、receipt、AP invoice、approval event、budget snapshot、supplier 和 vendor risk event 等端点。

标准答案依据：有效 indexed 合同 `CR-NOVA-311` 覆盖 `SUP-HEXEL` / `SEN-NOVA` / `PRG-NOVA-31`，基准单价 `149.75`，合同上限 `240000.00`。memo 提出的新单价为 `154.24`，价差 `4.49`，涨幅 `3.00%`。受影响数量 `180`，增量小计 `808.20`，按 `7.25%` 计算税额 `58.59`，运费 `0.00`，增量总额 `866.79`。

合同用量口径继承训练任务的规则：按合同汇总所有未取消 PO，而不是只看 memo 中点名的 NOVA PO。纳入的 PO 为 `PO-NOVA-3107`、`PO-00013`、`PO-00026`、`PO-00042`，合计 `81613.75`，没有需要排除的 cancelled PO。变更前合同余量 `158386.25`，扣除价格差额增量后为 `157578.05`，合同上限检查通过。

项目预算使用 `BUD-PRG-NOVA-31`：预算上限 `420000.00`，已承诺金额 `358204.15`，剩余预算 `61795.85`，扣除本次价格变更增量后为 `60929.06`，预算检查通过。`REQ-NOVA-302` 已 converted，最新审批事件为 `APR-00002`，动作为 `approved`，审批人为 `Procurement Lead`，日期 `2026-05-08`。被提名 PO 已收货，截至 memo 日期的收货证据为 `RCV-GOLD-27`；`AP-HEXEL-3309` 是匹配发票。`AP-00002` 使用了新价格但没有 receipt，应作为 unmatched price-variance invoice 控制，而不能作为付款放行证据。

供应商风险：`SUP-HEXEL` 状态 active，风险评级 medium。截至 `2026-06-01`，open 事件为 `VRE-00032`，monitoring 事件为 `VRE-00010`，没有 severe open event。数据中晚于该日期的 high open event 不进入 as-of 答案。因此供应商风险不阻断本次 amendment。

预期决策：`release_price_amendment`。所需动作是 `issue_price_delta_amendment` 和 `block_unmatched_price_invoice`；阻断点数量为 `0`，币种 `USD`，可 release。

评分点使用 7 个 exact-match 检查，权重沿用变更控制训练设计：
- `SP1_identity_and_final_decision`，权重 2。
- `SP2_contract_price_and_change_basis`，权重 2。
- `SP3_contract_usage_and_ceiling`，权重 3。
- `SP4_budget_incremental_exposure`，权重 3。
- `SP5_nomination_and_approval_evidence`，权重 2。
- `SP6_supplier_risk_and_invoice_control`，权重 1。
- `SP7_actions_and_summary`，权重 2。

迁移设计：`train_001` 锚定 nomination readiness、条件性证据、供应商风险背景和 as-of 证据口径；`train_003` 锚定 NOVA 发票和付款控制核对，尤其是 `AP-HEXEL-3309` 的放行证据；`train_004` 锚定 post-nomination change-control 的合同用量、预算含税暴露、审批状态和结构化 hold/release 决策。本测试任务把对象切换到 NOVA，使用 indexed price-delta amendment，而不是 fixed-price quantity amendment，并加入一个未匹配的新价格发票，要求求解者控制该发票但不要错误阻断商业 amendment。

构建记录：Codex 于 2026-06-01 为 `task_group_006/test_tasks/005` 创建。本任务构建时，`6.1/006/task_factory/scratch` 下没有 task-specific `task_group_design.md`；因此使用 workspace builder context、已有 guide、训练任务锚点和共享环境记录完成。求解者可见文件保持英文，不泄露评分权重、隐藏推导或 SOP 步骤。
