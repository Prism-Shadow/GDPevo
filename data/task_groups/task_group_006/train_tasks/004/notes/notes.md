# Train 004 Notes: AX17 Tail-Lamp Variant Change Request

## English

Task purpose: build a modular procurement change-request task around `CR-LMP-228`, `PRG-AX17`, and the `LMP-228` AX17 tail-lamp variant. The solver sees only an English prompt, a small memo payload, and the shared ProcureOps API.

Source records used:
- Memo payload: `input/payloads/change_memo.json`, memo `MCR-AX17-TL-228`, quantity `781`, variant `AX17-TL-REV-B`.
- Program: `PRG-AX17`, budget cap `285000.00`, committed amount `216430.40`.
- Contract: `CR-LMP-228`, active fixed-price contract for `SUP-LUMA` / `LMP-228` / `PRG-AX17`, unit price `84.50`, ceiling `185000.00`.
- Existing non-cancelled contract POs: `PO-AX17-4481` subtotal `20280.00`, `PO-00027` subtotal `21125.00`, `PO-00031` subtotal `24589.50`. Total non-cancelled usage is `65994.50`.
- Cancelled contract POs excluded from usage: `PO-00008`, `PO-00041`.
- Approval event for source requisition `REQ-AX17-141`: latest event `APR-00001`, action `submitted`, actor `Compliance Desk`, date `2026-05-02`.
- Supplier `SUP-LUMA`: active, risk rating `watch`; open event set contains `VRE-00005`, but there are no open severe events.

Calculations:
- Contract headroom before change: `185000.00 - 65994.50 = 119005.50`.
- Requested subtotal: `781 * 84.50 = 65994.50`.
- Contract headroom after change: `119005.50 - 65994.50 = 53011.00`, so the contract ceiling check passes.
- Budget remaining: `285000.00 - 216430.40 = 68569.60`.
- Requested tax: `65994.50 * 7.25% = 4784.60`.
- Requested total: `65994.50 + 4784.60 = 70779.10`.
- Budget after change: `68569.60 - 70779.10 = -2209.50`, so the budget check fails.
- Maximum quantity under the current budget at the same unit price and tax basis is `756`.

Expected decision: `hold_for_budget_and_approval`. The contract itself covers the item and has ceiling headroom, and supplier risk is contextual only. The blockers are the negative program-budget result and the lack of a final approved approval event for `REQ-AX17-141`.

Scoring points:
- `SP1_identity_and_final_decision`, weight 2: exact match on change request identity fields and final decision.
- `SP2_contract_status_price_and_quantity`, weight 2: exact match on active contract, fixed price, unit price, ceiling, requested quantity/subtotal, and ceiling result.
- `SP3_contract_usage_and_headroom`, weight 3: exact match on non-cancelled contract usage and headroom before/after the change.
- `SP4_program_budget_exposure`, weight 3: exact match on the full budget object including remaining budget, tax, total, negative after-change amount, budget result, and max affordable quantity.
- `SP5_requisition_approval_state`, weight 2: exact match on latest source requisition approval event and failed approval flag.
- `SP6_supplier_risk_context_and_supporting_ids`, weight 1: exact match on supplier risk context and supporting PO/approval ID sets.
- `SP7_hold_actions_and_summary`, weight 2: exact match on required actions and summary.

Construction record: created for `task_group_006/train_tasks/004` on 2026-06-01. The task-specific design file requested by the builder prompt was not present under `6.1/006/task_factory/scratch`; the task was built from the workspace-level builder context, the explicit train_004 brief, and the shared environment data.

## 中文

任务目的：围绕 `CR-LMP-228`、`PRG-AX17` 和 `LMP-228` AX17 尾灯变体构造一个模块化采购变更请求任务。求解端只能看到英文 prompt、小型 memo payload 和共享 ProcureOps API。

使用的来源记录：
- Memo payload：`input/payloads/change_memo.json`，memo 为 `MCR-AX17-TL-228`，数量 `781`，变体 `AX17-TL-REV-B`。
- 项目：`PRG-AX17`，预算上限 `285000.00`，已承诺金额 `216430.40`。
- 合同：`CR-LMP-228`，覆盖 `SUP-LUMA` / `LMP-228` / `PRG-AX17` 的 active fixed-price 合同，单价 `84.50`，合同上限 `185000.00`。
- 已有且未取消的合同 PO：`PO-AX17-4481` 小计 `20280.00`，`PO-00027` 小计 `21125.00`，`PO-00031` 小计 `24589.50`。未取消用量合计 `65994.50`。
- 从合同用量中排除的已取消 PO：`PO-00008`、`PO-00041`。
- 来源请购单 `REQ-AX17-141` 的审批事件：最新事件 `APR-00001`，动作为 `submitted`，经办人为 `Compliance Desk`，日期 `2026-05-02`。
- 供应商 `SUP-LUMA`：状态 active，风险评级 `watch`；open 事件集合包含 `VRE-00005`，但没有 open severe 事件。

计算口径：
- 变更前合同余量：`185000.00 - 65994.50 = 119005.50`。
- 请求小计：`781 * 84.50 = 65994.50`。
- 变更后合同余量：`119005.50 - 65994.50 = 53011.00`，因此合同上限检查通过。
- 剩余预算：`285000.00 - 216430.40 = 68569.60`。
- 请求税额：`65994.50 * 7.25% = 4784.60`。
- 请求总额：`65994.50 + 4784.60 = 70779.10`。
- 变更后预算：`68569.60 - 70779.10 = -2209.50`，因此预算检查失败。
- 在当前预算、相同单价和税率口径下最多可采购数量为 `756`。

标准决策：`hold_for_budget_and_approval`。合同本身覆盖该物料且合同上限仍有余量，供应商风险仅作为背景信息。真正的阻塞点是项目预算超额，以及 `REQ-AX17-141` 没有最终 approved 审批事件。

评分点：
- `SP1_identity_and_final_decision`，权重 2：精确匹配变更请求身份字段和最终决策。
- `SP2_contract_status_price_and_quantity`，权重 2：精确匹配合同状态、固定价格、单价、上限、请求数量/小计和合同上限结果。
- `SP3_contract_usage_and_headroom`，权重 3：精确匹配未取消合同用量以及变更前后余量。
- `SP4_program_budget_exposure`，权重 3：精确匹配完整预算对象，包括剩余预算、税额、总额、负数的变更后预算、预算结果和最大可承受数量。
- `SP5_requisition_approval_state`，权重 2：精确匹配来源请购单最新审批事件和审批未通过标志。
- `SP6_supplier_risk_context_and_supporting_ids`，权重 1：精确匹配供应商风险背景和支撑 PO/审批 ID 集合。
- `SP7_hold_actions_and_summary`，权重 2：精确匹配所需动作和摘要。

构建记录：2026-06-01 创建于 `task_group_006/train_tasks/004`。builder prompt 要求的 task-specific design 文件未出现在 `6.1/006/task_factory/scratch` 下；本任务根据 workspace-level builder context、明确的 train_004 brief 和共享环境数据构建。
