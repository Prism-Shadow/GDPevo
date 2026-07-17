# Train 001 Notes / 训练 001 说明

## English

Task purpose: this train task asks the solver to assemble a sourcing nomination readiness packet for PRG-AX17 using the shared ProcureOps endpoints. It is anchored in the supplier nomination workflow from the procurement/source-to-contract scenario, but the expected answer is structured operational evidence rather than process prose.

Source data: the prompt gives only the API base URL and a small local memo naming two package anchors. The answer requires API lookups across programs, requisitions, items, suppliers, contracts, purchase orders, receipts, AP invoices, budget snapshots, approval events, and vendor-risk events. The API, not the memo, is authoritative.

Gold derivation: PRG-AX17 is owned by Elena Marsh. Budget headroom is 285000.00 minus 216430.40, or 68569.60. The packet is not ready overall because DRV-AX17 is on hold. LMP-228 maps to SUP-LUMA, has active commercial basis CR-LMP-228, has PO-AX17-4481, and has receipt evidence RCV-BLUE-14 by 2026-06-01. It remains at risk because SUP-LUMA has watch risk, open supplier-risk event VRE-00005, and AP holds AP-00001 and AP-LUMA-7714. DRV-AX17 maps to SUP-VANTIX, but PO-AX17-4519 has no contract, no receipt by 2026-06-01, AP-VANTIX-2188 is pending receipt, VRE-00009 is open for the supplier, and the PO due date is after the requisition need-by date; the line is therefore held.

Transfer value: solvers should learn to reconcile local package anchors with live ERP-style records, separate conditional readiness from hard holds, use an as-of date for evidence, and report controlled structured decisions rather than free-form sourcing advice.

Evaluation: the evaluator uses seven exact-match scoring points with raw weights 1, 2, 2, 2, 2, 2, and 1. List-like fields are normalized as sets, and nomination lines are matched by SKU.

## 中文

任务目的：本训练任务要求求解器基于共享 ProcureOps 端点，为 PRG-AX17 生成供应商 nomination readiness packet。它来自采购/source-to-contract 场景中的供应商提名流程，但标准答案是结构化运营证据，而不是流程建议长文。

数据来源：提示词只给 API 地址和一个很小的本地备忘录，备忘录只标出两个 package anchor。答案需要跨 programs、purchase requisitions、items、suppliers、contracts、purchase orders、receipts、AP invoices、budget snapshots、approval events 和 vendor risk events 查询。权威来源是 API，而不是本地备忘录。

标准答案推导：PRG-AX17 的负责人是 Elena Marsh。预算余量为 285000.00 减 216430.40，即 68569.60。整体状态为 not_ready，因为 DRV-AX17 必须 hold。LMP-228 对应 SUP-LUMA，有有效商业依据 CR-LMP-228，有 PO-AX17-4481，并且截至 2026-06-01 有 RCV-BLUE-14 作为收货证据；但由于 SUP-LUMA 为 watch 风险、有开放供应商风险事件 VRE-00005、且 AP-00001 和 AP-LUMA-7714 仍在 hold，所以只能 conditional_nomination。DRV-AX17 对应 SUP-VANTIX，但 PO-AX17-4519 没有合同、截至 2026-06-01 没有收货、AP-VANTIX-2188 为 pending receipt、供应商存在开放风险事件 VRE-00009，且 PO 到期日晚于 requisition 的 need-by 日期，因此该行 hold。

迁移价值：求解器应学习如何把本地 package anchor 与实时 ERP 记录对齐，区分 conditional readiness 和 hard hold，按 as-of date 判断证据，并用受控结构化字段输出决策，而不是自由文本采购建议。

评估方式：评估器使用 7 个 exact-match 评分点，原始权重为 1、2、2、2、2、2、1。列表字段按集合归一化，nomination lines 按 SKU 匹配。
