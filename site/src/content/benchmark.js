export const modes = ["base", "demo", "reflect"];

const v1LeaderboardRuns = [
  {
    model: "GPT-5.5",
    harness: "Codex",
    thinking: "xhigh",
    method: "skill-creator",
    modes: {
      base: { acc: 46.72, std: 5.13, lift: 0, rounds: 14.91, tokens: 735.3, cost: 1.137 },
      fewshot: { acc: 64.91, std: 6.36, lift: 18.19, rounds: 11.58, tokens: 451.7, cost: 0.805 },
      self: { acc: 54.99, std: 8.73, lift: 8.27, rounds: 9.71, tokens: 344.3, cost: 0.771 },
      "reflect-3": { acc: 57.45, std: 7.62, lift: 10.73, rounds: 10.83, tokens: 399.4, cost: 0.844 }
    }
  },
  {
    model: "Opus 4.8",
    harness: "Claude Code",
    thinking: "xhigh",
    method: "skill-creator",
    modes: {
      base: { acc: 49.11, std: 5.25, lift: 0, rounds: 14.62, tokens: 385.8, cost: 0.607 },
      fewshot: { acc: 70.9, std: 6.38, lift: 21.79, rounds: 11.1, tokens: 347.3, cost: 0.549 },
      self: { acc: 57.37, std: 6.79, lift: 8.26, rounds: 11.78, tokens: 433.9, cost: 0.61 },
      "reflect-3": { acc: 62.72, std: 6.68, lift: 13.62, rounds: 12.15, tokens: 433.4, cost: 0.605 }
    }
  },
  {
    model: "Opus 4.6",
    harness: "Panofy",
    thinking: "high",
    method: "agent-training",
    modes: {
      base: { acc: 50.4, std: 6.99, lift: 0, rounds: 15.16, tokens: 379.3, cost: 0.752 },
      fewshot: { acc: 71.47, std: 4.93, lift: 21.07, rounds: 13.48, tokens: 385.5, cost: 0.814 },
      self: { acc: 58.39, std: 5.74, lift: 7.99, rounds: 12.51, tokens: 341.8, cost: 0.707 },
      "reflect-3": { acc: 59.82, std: 7.31, lift: 9.41, rounds: 14.37, tokens: 394.8, cost: 0.767 }
    }
  },
  {
    model: "GLM-5.2",
    harness: "Claude Code",
    thinking: "max",
    method: "skill-creator",
    modes: {
      base: { acc: 47.73, std: 5.21, lift: 0, rounds: 17.57, tokens: 633.3, cost: 0.388 },
      fewshot: { acc: 69.55, std: 8.85, lift: 21.83, rounds: 15.49, tokens: 606.3, cost: 0.34 },
      self: { acc: 55.91, std: 7.84, lift: 8.18, rounds: 15.98, tokens: 634.8, cost: 0.348 },
      "reflect-3": { acc: 63.35, std: 7.51, lift: 15.62, rounds: 15.36, tokens: 572.6, cost: 0.324 }
    }
  },
  {
    model: "Kimi K2.6",
    harness: "Claude Code",
    thinking: "enabled",
    method: "skill-creator",
    modes: {
      base: { acc: 25.14, std: 12.15, lift: 0, rounds: 46.24, tokens: 1226.7, cost: 0.338 },
      fewshot: { acc: 30.48, std: 13.22, lift: 5.34, rounds: 37.87, tokens: 977, cost: 0.288 },
      self: { acc: 29.16, std: 14.18, lift: 4.02, rounds: 32.67, tokens: 821.6, cost: 0.25 },
      "reflect-3": { acc: 32.68, std: 14.25, lift: 7.54, rounds: 31.68, tokens: 950.5, cost: 0.28 }
    }
  },
  {
    model: "DeepSeek V4 Pro",
    harness: "Claude Code",
    thinking: "max",
    method: "skill-creator",
    modes: {
      base: { acc: 46.06, std: 6.9, lift: 0, rounds: 13.22, tokens: 503.4, cost: 0.031 },
      fewshot: { acc: 54.8, std: 9.65, lift: 8.74, rounds: 11.46, tokens: 439.9, cost: 0.032 },
      self: { acc: 48.69, std: 8.75, lift: 2.63, rounds: 10.53, tokens: 405.7, cost: 0.032 },
      "reflect-3": { acc: 49.22, std: 8.67, lift: 3.16, rounds: 10.26, tokens: 383.8, cost: 0.031 }
    }
  }
];

const v2LeaderboardRuns = [
  {
    model: "GPT-5.5",
    harness: "Codex",
    thinking: "xhigh",
    method: "skill-creator",
    modes: {
      base: { acc: 42.96, std: 4.47, lift: 0, rounds: 15.56, tokens: 588.3, cost: 1.043 },
      fewshot: { acc: 52.46, std: 5.62, lift: 9.5, rounds: 12.7, tokens: 424.0, cost: 0.861 },
      self: { acc: 46.98, std: 6.32, lift: 4.02, rounds: 13.38, tokens: 427.3, cost: 0.851 },
      "reflect-3": { acc: 47.13, std: 7.42, lift: 4.17, rounds: 14.24, tokens: 475.3, cost: 0.901 }
    }
  }
];

export const leaderboardModes = ["base", "fewshot", "self", "reflect-3"];

function createLeaderboardRows(version, runs) {
  return runs.flatMap((run) =>
    leaderboardModes.map((mode) => ({
      id: `${version}-${run.harness}-${run.model}-${mode}`.toLowerCase().replaceAll(/[^a-z0-9]+/g, "-"),
      model: run.model,
      harness: run.harness,
      thinking: run.thinking,
      method: run.method,
      mode,
      ...run.modes[mode]
    }))
  );
}

export const leaderboardVersions = {
  v1: {
    label: "V1",
    taskRange: "001–012",
    rows: createLeaderboardRows("v1", v1LeaderboardRuns)
  },
  v2: {
    label: "V2",
    taskRange: "013–024",
    rows: createLeaderboardRows("v2", v2LeaderboardRuns)
  }
};

export const harnesses = [
  { key: "codex", harness: "Codex", model: "GPT-5.5", thinking: "xhigh" },
  { key: "claude", harness: "Claude Code", model: "Opus 4.8", thinking: "xhigh" },
  { key: "panofy", harness: "Panofy", model: "Opus 4.6", thinking: "high" }
];

export const resultGroups = [
  { id: "01", domain: "CRM", en: "Lead capture", zh: "线索捕获", codex: [44.43, 48.12, 57.46], claude: [48.75, 81.96, 75.47], panofy: [63.74, 85.28, 82.26] },
  { id: "02", domain: "CRM", en: "B2B quote", zh: "B2B 报价", codex: [41.62, 51.17, 60.41], claude: [42.74, 58.48, 46.53], panofy: [43.85, 58.93, 51.51] },
  { id: "03", domain: "CRM", en: "Service ticket", zh: "服务工单", codex: [57.84, 78.11, 71.69], claude: [46.69, 70.89, 63.92], panofy: [58.58, 73.41, 58.00] },
  { id: "04", domain: "CRM", en: "Churn analytics", zh: "流失分析", codex: [31.73, 60.94, 59.95], claude: [25.24, 54.55, 54.28], panofy: [18.82, 59.53, 57.06] },
  { id: "05", domain: "ERP", en: "Expense control", zh: "费用控制", codex: [35.09, 52.45, 46.51], claude: [51.15, 57.96, 59.26], panofy: [41.05, 60.51, 62.85] },
  { id: "06", domain: "ERP", en: "Procurement", zh: "采购收货", codex: [66.28, 72.39, 71.76], claude: [67.98, 72.98, 72.54], panofy: [64.83, 72.24, 70.39] },
  { id: "07", domain: "ERP", en: "Inventory", zh: "库存履约", codex: [38.40, 54.31, 54.49], claude: [39.54, 55.76, 57.10], panofy: [36.39, 41.88, 51.15] },
  { id: "08", domain: "Finance", en: "Advisory & tax", zh: "理财税务", codex: [70.57, 93.18, 93.05], claude: [66.89, 93.60, 90.94], panofy: [49.18, 73.36, 79.36] },
  { id: "09", domain: "Finance", en: "Ops modeling", zh: "运营建模", codex: [42.76, 92.47, 80.94], claude: [51.76, 100.00, 80.00], panofy: [62.39, 89.73, 92.47] },
  { id: "10", domain: "Finance", en: "Investment", zh: "投资策略", codex: [60.76, 71.05, 73.77], claude: [58.60, 63.45, 75.07], panofy: [50.73, 65.18, 63.90] },
  { id: "11", domain: "Finance", en: "Credit risk", zh: "信用风险", codex: [45.68, 56.48, 65.41], claude: [41.56, 63.48, 60.82], panofy: [48.91, 56.38, 61.07] },
  { id: "12", domain: "ERP", en: "HR lifecycle", zh: "HR 流程", codex: [45.08, 61.24, 70.10], claude: [48.41, 77.66, 79.30], panofy: [63.59, 82.43, 85.77] }
];

export const taskGroups = [
  { id: "001", label: "01", domain: "CRM", en: "Marketing lead capture", zh: "市场营销线索捕获" },
  { id: "002", label: "02", domain: "CRM", en: "B2B quote & account response", zh: "B2B 报价与客户响应" },
  { id: "003", label: "03", domain: "CRM", en: "Service ticket resolution", zh: "服务工单处理" },
  { id: "004", label: "04", domain: "CRM", en: "Retention & churn analytics", zh: "留存与流失分析" },
  { id: "005", label: "05", domain: "ERP", en: "Finance expense control & close", zh: "费用控制与账务结算" },
  { id: "006", label: "06", domain: "ERP", en: "Procurement, supplier & receiving", zh: "采购、供应商与收货" },
  { id: "007", label: "07", domain: "ERP", en: "Inventory & order fulfillment", zh: "库存与订单履约" },
  { id: "008", label: "08", domain: "Finance", en: "Personal advisory, tax & estate", zh: "个人理财、税务与遗产规划" },
  { id: "009", label: "09", domain: "Finance", en: "Operational modeling & reporting", zh: "运营建模与管理报表" },
  { id: "010", label: "10", domain: "Finance", en: "Investment strategy & portfolio risk", zh: "投资策略与组合风险" },
  { id: "011", label: "11", domain: "Finance", en: "Credit risk & lending committee", zh: "信用风险与信贷委员会" },
  { id: "012", label: "12", domain: "ERP", en: "HR employee lifecycle & policy", zh: "HR 员工流程与制度" }
];

const taskTopicSource = {
  "001": [
    ["train_001", "Train", "Event sponsor handoff", "Validate event attendance, sponsor status, qualified leads, and the next CRM follow-up."],
    ["train_002", "Train", "Exhibitor lead qualification", "Rank booth leads by fit, urgency, and account context before assigning sales ownership."],
    ["train_003", "Train", "Webinar import cleanup", "Deduplicate imported attendees and reconcile form answers with existing company records."],
    ["train_004", "Train", "Field-day campaign review", "Turn scattered event activity into clean campaign outcomes and follow-up queues."],
    ["train_005", "Train", "Target-account prospecting", "Identify the strongest prospects in a niche segment and prepare CRM-ready outreach notes."],
    ["test_001", "Test", "Executive forum handoff", "Audit a new event pipeline and decide which accounts deserve immediate sales action."],
    ["test_002", "Test", "Partner expo qualification", "Separate real opportunities from lookalike records after a partner-led marketing event."],
    ["test_003", "Test", "Imported lead normalization", "Clean a messy lead import and connect attendees to the right companies and campaigns."],
    ["test_004", "Test", "Industrial demo follow-up", "Reconcile demo attendance, sponsor signals, and account history into follow-up priorities."],
    ["test_005", "Test", "Regional account shortlist", "Build a prioritized prospect list using firmographic clues and recent engagement signals."]
  ],
  "002": [
    ["train_001", "Train", "Renewal quote triage", "Review a customer request and assemble the right quote details from account context."],
    ["train_002", "Train", "Enterprise upsell response", "Check contract terms, usage signals, and open opportunities before drafting a response."],
    ["train_003", "Train", "Procurement email routing", "Classify buyer questions and attach the right commercial owner and next step."],
    ["train_004", "Train", "Discount exception review", "Decide whether a requested discount fits policy, deal stage, and customer history."],
    ["train_005", "Train", "Account expansion brief", "Summarize renewal risk, expansion fit, and quote blockers for the account team."],
    ["test_001", "Test", "Quote revision request", "Resolve a changed scope request while preserving pricing, approval, and CRM consistency."],
    ["test_002", "Test", "Buyer objection response", "Use account records to answer procurement concerns without inventing commercial terms."],
    ["test_003", "Test", "Contract-change handoff", "Find the correct owner and required evidence for a contract or quote adjustment."],
    ["test_004", "Test", "Multi-site account quote", "Combine subsidiary records, seat counts, and timing into a clean quote recommendation."],
    ["test_005", "Test", "Escalation-ready account note", "Prepare a concise response plan for a customer whose quote needs extra approval."]
  ],
  "003": [
    ["train_001", "Train", "Priority ticket routing", "Read a support case and assign severity, owner, and the next customer action."],
    ["train_002", "Train", "SLA breach investigation", "Use ticket history to explain whether a service-level deadline was missed."],
    ["train_003", "Train", "Bug-report consolidation", "Merge related complaints into a clean support summary without losing customer impact."],
    ["train_004", "Train", "Escalation evidence pack", "Collect reproduction steps, account details, and recent support notes for engineering."],
    ["train_005", "Train", "Resolution quality check", "Verify whether a proposed response actually addresses the customer issue."],
    ["test_001", "Test", "Refund-risk support case", "Identify support history, promised actions, and the right path to preserve the account."],
    ["test_002", "Test", "Outage communication draft", "Summarize customer impact and produce a grounded update from service records."],
    ["test_003", "Test", "Duplicate-ticket cleanup", "Find duplicate cases and consolidate status, ownership, and customer-facing commitments."],
    ["test_004", "Test", "Technical escalation triage", "Decide if a case requires engineering escalation and list the missing diagnostics."],
    ["test_005", "Test", "Close-ready ticket audit", "Check whether a ticket can be closed or needs one more customer-confirmed step."]
  ],
  "004": [
    ["train_001", "Train", "At-risk account scan", "Detect churn risk from usage drops, support history, renewal timing, and stakeholder signals."],
    ["train_002", "Train", "Retention playbook selection", "Choose a save motion based on contract value, adoption pattern, and open issues."],
    ["train_003", "Train", "Customer health explanation", "Turn mixed account signals into a clear health score rationale."],
    ["train_004", "Train", "Renewal objection map", "Connect cancellation language to the right product, price, or support concern."],
    ["train_005", "Train", "Win-back segmenting", "Identify which former customers are realistic candidates for reactivation."],
    ["test_001", "Test", "Executive churn brief", "Summarize why a customer may leave and which actions are most time-sensitive."],
    ["test_002", "Test", "Usage-cohort comparison", "Compare similar customers to separate normal seasonality from real disengagement."],
    ["test_003", "Test", "Retention owner assignment", "Route each account to the correct success, sales, or support owner."],
    ["test_004", "Test", "Cancellation pattern review", "Extract repeated churn drivers from a set of recent customer records."],
    ["test_005", "Test", "Save-plan prioritization", "Rank at-risk customers by revenue impact and probability of recovery."]
  ],
  "005": [
    ["train_001", "Train", "Expense-policy audit", "Check employee expenses against category rules, limits, receipts, and approval status."],
    ["train_002", "Train", "Month-end close cleanup", "Find close blockers caused by unmatched invoices, late approvals, or miscoded items."],
    ["train_003", "Train", "Vendor invoice exception", "Resolve invoice mismatches by comparing purchase, receipt, and payment records."],
    ["train_004", "Train", "Card-spend reconciliation", "Match card transactions to employees, projects, and policy-compliant documentation."],
    ["train_005", "Train", "Accrual review", "Identify expenses that should be accrued before the reporting period closes."],
    ["test_001", "Test", "Late expense triage", "Decide which late claims can be approved and which need finance follow-up."],
    ["test_002", "Test", "Close variance explanation", "Explain budget variance using invoices, expense categories, and timing differences."],
    ["test_003", "Test", "Duplicate payment check", "Detect duplicate or suspicious payments across similar vendor records."],
    ["test_004", "Test", "Department spend review", "Summarize spend exceptions for a department head before close."],
    ["test_005", "Test", "Approval-chain repair", "Find missing approvals and route finance items to the correct approver."]
  ],
  "006": [
    ["train_001", "Train", "Purchase-order matching", "Match requested items, POs, receipts, and supplier invoices."],
    ["train_002", "Train", "Supplier onboarding check", "Verify required vendor records, tax forms, risk flags, and payment terms."],
    ["train_003", "Train", "Receiving discrepancy", "Resolve quantity or item mismatches between warehouse receipt and purchase order."],
    ["train_004", "Train", "Vendor performance review", "Compare late deliveries, defect notes, and contract terms for supplier follow-up."],
    ["train_005", "Train", "Emergency reorder decision", "Determine whether a rush purchase is justified by demand and stock status."],
    ["test_001", "Test", "Invoice hold release", "Decide what evidence is needed before releasing a blocked supplier invoice."],
    ["test_002", "Test", "Supplier substitution request", "Evaluate an alternate supplier using price, availability, and compliance context."],
    ["test_003", "Test", "Partial receipt reconciliation", "Update receiving status when only part of a purchase order arrives."],
    ["test_004", "Test", "Procurement exception summary", "Prepare a clean exception list for finance and operations review."],
    ["test_005", "Test", "Contract-term validation", "Check whether a purchasing decision follows negotiated supplier terms."]
  ],
  "007": [
    ["train_001", "Train", "Stockout prevention", "Spot items at risk of stockout and recommend reorder priorities."],
    ["train_002", "Train", "Order allocation review", "Allocate limited inventory across customer orders using priority and due dates."],
    ["train_003", "Train", "Warehouse transfer plan", "Move stock between locations to cover demand without creating new gaps."],
    ["train_004", "Train", "Backorder communication", "Summarize delayed orders and prepare accurate customer-facing status updates."],
    ["train_005", "Train", "Fulfillment exception audit", "Identify orders blocked by address, payment, inventory, or shipping issues."],
    ["test_001", "Test", "Demand spike response", "Decide how to fulfill urgent demand when inventory is split across sites."],
    ["test_002", "Test", "Aged inventory cleanup", "Find slow-moving items and suggest transfer, markdown, or hold actions."],
    ["test_003", "Test", "Shipment priority queue", "Rank open shipments by service level, customer importance, and promised date."],
    ["test_004", "Test", "Inventory count variance", "Explain count differences using recent receipts, shipments, and adjustments."],
    ["test_005", "Test", "Order rescue plan", "Create the next best action for orders that are close to missing fulfillment SLA."]
  ],
  "008": [
    ["train_001", "Train", "Tax-sensitive income review", "Assess income, deductions, and deadlines before recommending planning steps."],
    ["train_002", "Train", "Estate document checklist", "Identify missing estate-planning documents and beneficiary conflicts."],
    ["train_003", "Train", "Retirement cash-flow snapshot", "Summarize assets, spending, and timeline to guide retirement advice."],
    ["train_004", "Train", "Capital-gains planning", "Evaluate realized gains, holding periods, and tax-loss harvesting opportunities."],
    ["train_005", "Train", "Family advisory brief", "Turn scattered household records into an adviser-ready planning memo."],
    ["test_001", "Test", "Year-end tax action list", "Prioritize tax moves before filing or year-end deadlines."],
    ["test_002", "Test", "Trust and beneficiary review", "Spot mismatches between estate wishes, account titling, and beneficiary records."],
    ["test_003", "Test", "Liquidity-needs analysis", "Determine whether planned withdrawals can cover spending without disrupting strategy."],
    ["test_004", "Test", "Charitable giving scenario", "Compare charitable options using tax impact, timing, and portfolio context."],
    ["test_005", "Test", "Adviser meeting prep", "Prepare the key questions and recommendations for a personal finance review."]
  ],
  "009": [
    ["train_001", "Train", "Revenue-forecast refresh", "Update a forecast from actuals, pipeline changes, and seasonality notes."],
    ["train_002", "Train", "Operating KPI deck", "Choose the right metrics and explain movement for a management update."],
    ["train_003", "Train", "Budget variance bridge", "Explain the difference between plan and actuals across drivers."],
    ["train_004", "Train", "Scenario model check", "Evaluate upside and downside assumptions for a business scenario."],
    ["train_005", "Train", "Monthly report QA", "Find inconsistent totals, stale assumptions, and narrative gaps in a report."],
    ["test_001", "Test", "Board metric summary", "Turn operating data into a concise performance narrative for leadership."],
    ["test_002", "Test", "Forecast-risk callout", "Identify which assumptions create the largest risk to the next forecast."],
    ["test_003", "Test", "Department model reconciliation", "Align headcount, spend, and revenue assumptions across operating teams."],
    ["test_004", "Test", "Executive variance note", "Explain a surprising variance without overclaiming from incomplete data."],
    ["test_005", "Test", "Report correction plan", "Prioritize corrections needed before a financial model can be shared."]
  ],
  "010": [
    ["train_001", "Train", "Portfolio risk scan", "Measure concentration, drawdown exposure, and asset-class imbalance."],
    ["train_002", "Train", "Rebalancing recommendation", "Suggest trades that bring a portfolio closer to target allocation."],
    ["train_003", "Train", "Investment memo review", "Compare thesis, risk, valuation, and time horizon before recommending action."],
    ["train_004", "Train", "Stress-scenario summary", "Explain how a portfolio might behave under rate, inflation, or market shocks."],
    ["train_005", "Train", "Manager due-diligence notes", "Summarize performance, fees, mandate fit, and red flags for a fund manager."],
    ["test_001", "Test", "Risk-budget adjustment", "Decide how to adjust exposure when risk budget or client constraints change."],
    ["test_002", "Test", "Portfolio drift diagnosis", "Find which positions caused allocation drift and what to do next."],
    ["test_003", "Test", "Strategy comparison brief", "Compare candidate strategies using return drivers and downside controls."],
    ["test_004", "Test", "Liquidity stress review", "Check whether portfolio liquidity matches expected withdrawal needs."],
    ["test_005", "Test", "Committee-ready recommendation", "Prepare an investment action with supporting risk and rationale."]
  ],
  "011": [
    ["train_001", "Train", "Borrower risk summary", "Review financials, collateral, covenants, and recent performance for credit risk."],
    ["train_002", "Train", "Loan exception triage", "Identify missing documents and policy exceptions before committee review."],
    ["train_003", "Train", "Covenant breach analysis", "Explain whether a borrower has breached terms and what mitigation is needed."],
    ["train_004", "Train", "Lending memo preparation", "Condense borrower strengths, weaknesses, and proposed terms into a committee memo."],
    ["train_005", "Train", "Portfolio watchlist update", "Rank credits by deterioration signals and required monitoring actions."],
    ["test_001", "Test", "Renewal credit review", "Assess whether a loan renewal fits risk appetite and updated borrower data."],
    ["test_002", "Test", "Collateral sufficiency check", "Evaluate collateral coverage under updated values and outstanding exposure."],
    ["test_003", "Test", "Committee question pack", "Prepare likely committee questions from weaknesses in the credit file."],
    ["test_004", "Test", "Risk-rating adjustment", "Decide whether borrower risk rating should change based on new signals."],
    ["test_005", "Test", "Approval-condition drafting", "Write clear conditions needed before credit approval can proceed."]
  ],
  "012": [
    ["train_001", "Train", "Onboarding readiness audit", "Check whether a new hire has the right documents, systems, and manager actions."],
    ["train_002", "Train", "Leave-policy interpretation", "Apply company policy to a leave request with timing and eligibility constraints."],
    ["train_003", "Train", "Compensation-change routing", "Route a pay or role change through the correct approval and record updates."],
    ["train_004", "Train", "Employee-relations case summary", "Summarize a sensitive HR case with facts, dates, and required next steps."],
    ["train_005", "Train", "Offboarding checklist repair", "Find missing offboarding actions across IT, payroll, manager, and compliance."],
    ["test_001", "Test", "Internal transfer review", "Validate transfer eligibility and identify changes needed in HR systems."],
    ["test_002", "Test", "Policy exception decision", "Decide whether an exception request fits documented HR policy and precedent."],
    ["test_003", "Test", "Performance-cycle cleanup", "Identify missing reviews, calibration blockers, and manager follow-ups."],
    ["test_004", "Test", "Benefits enrollment case", "Resolve benefit eligibility and enrollment timing from employee records."],
    ["test_005", "Test", "Termination-risk handoff", "Prepare a compliant handoff for a complex employee exit."]
  ]
};

const taskTopicTranslations = {
  "001": {
    train_001: ["活动赞助商交接", "验证活动出席、赞助商身份、合格线索和下一步 CRM 跟进。"],
    train_002: ["展商线索资格判定", "在分配销售负责人前，根据匹配度、紧急度和客户上下文对展台线索排序。"],
    train_003: ["网络研讨会导入清洗", "对导入的参会者去重，并将表单答案与现有公司记录核对。"],
    train_004: ["现场活动营销复盘", "将零散的活动行为整理成清晰的营销结果和跟进队列。"],
    train_005: ["目标客户挖掘", "识别细分市场中最强的潜在客户，并准备可写入 CRM 的外联备注。"],
    test_001: ["高管论坛交接", "审计新的活动线索流水线，并决定哪些客户值得立即销售跟进。"],
    test_002: ["合作伙伴展会资格判定", "在合作伙伴主导的营销活动后，将真实机会与相似记录区分开。"],
    test_003: ["导入线索标准化", "清洗混乱的线索导入数据，并将参会者连接到正确的公司和活动。"],
    test_004: ["工业演示跟进", "整合演示出席、赞助商信号和客户历史，形成跟进优先级。"],
    test_005: ["区域客户短名单", "利用企业画像线索和近期互动信号，生成优先级排序的潜在客户列表。"]
  },
  "002": {
    train_001: ["续约报价分诊", "审核客户请求，并根据账户上下文整理正确的报价细节。"],
    train_002: ["企业追加销售响应", "在起草回复前，检查合同条款、使用信号和未结商机。"],
    train_003: ["采购邮件路由", "分类买方问题，并附上正确的商务负责人和下一步。"],
    train_004: ["折扣例外审核", "判断请求的折扣是否符合政策、交易阶段和客户历史。"],
    train_005: ["账户扩展简报", "为账户团队总结续约风险、扩展匹配度和报价阻塞点。"],
    test_001: ["报价修订请求", "在保持价格、审批和 CRM 一致性的前提下处理范围变更请求。"],
    test_002: ["买方异议回复", "使用账户记录回答采购疑虑，且不编造商务条款。"],
    test_003: ["合同变更交接", "为合同或报价调整找到正确负责人和所需证据。"],
    test_004: ["多站点账户报价", "整合子公司记录、席位数量和时间安排，形成清晰的报价建议。"],
    test_005: ["可升级账户备注", "为需要额外审批的客户报价准备简洁的响应计划。"]
  },
  "003": {
    train_001: ["高优先级工单路由", "阅读支持案例，并分配严重级别、负责人和下一步客户动作。"],
    train_002: ["SLA 违约调查", "使用工单历史解释服务级别截止时间是否被错过。"],
    train_003: ["缺陷报告合并", "将相关投诉合并成清晰的支持摘要，同时保留客户影响。"],
    train_004: ["升级证据包", "为工程团队收集复现步骤、账户细节和近期支持备注。"],
    train_005: ["解决质量检查", "验证拟定回复是否真正解决了客户问题。"],
    test_001: ["退款风险支持案例", "识别支持历史、承诺动作和保留账户的正确路径。"],
    test_002: ["故障沟通草稿", "总结客户影响，并基于服务记录产出可靠更新。"],
    test_003: ["重复工单清理", "找出重复案例，并合并状态、归属和面向客户的承诺。"],
    test_004: ["技术升级分诊", "判断案例是否需要工程升级，并列出缺失的诊断信息。"],
    test_005: ["可关闭工单审计", "检查工单能否关闭，还是需要客户确认的最后一步。"]
  },
  "004": {
    train_001: ["风险账户扫描", "从使用量下降、支持历史、续约时间和干系人信号中发现流失风险。"],
    train_002: ["留存方案选择", "根据合同价值、采用模式和未解决问题选择挽留动作。"],
    train_003: ["客户健康度解释", "将混合账户信号转化为清晰的健康评分依据。"],
    train_004: ["续约异议映射", "把取消意向连接到正确的产品、价格或支持问题。"],
    train_005: ["赢回客户分层", "识别哪些流失客户是现实可行的重新激活对象。"],
    test_001: ["高管流失简报", "总结客户可能流失的原因，以及哪些动作最具时效性。"],
    test_002: ["使用队列对比", "比较相似客户，将正常季节性波动与真实流失区分开。"],
    test_003: ["留存负责人分配", "将每个账户路由给正确的客户成功、销售或支持负责人。"],
    test_004: ["取消模式复盘", "从近期客户记录中提取反复出现的流失驱动因素。"],
    test_005: ["挽留计划优先级", "按收入影响和恢复概率对风险客户排序。"]
  },
  "005": {
    train_001: ["费用政策审计", "按照类别规则、限额、凭证和审批状态检查员工费用。"],
    train_002: ["月结清理", "找出未匹配发票、延迟审批或编码错误导致的关账阻塞点。"],
    train_003: ["供应商发票例外", "通过比较采购、收货和付款记录解决发票不匹配。"],
    train_004: ["公司卡支出核对", "将卡交易匹配到员工、项目和符合政策的凭证。"],
    train_005: ["应计费用复核", "识别在报告期关闭前应计提的费用。"],
    test_001: ["逾期费用分诊", "判断哪些逾期报销可以批准，哪些需要财务跟进。"],
    test_002: ["关账差异解释", "使用发票、费用类别和时间差异解释预算差异。"],
    test_003: ["重复付款检查", "在相似供应商记录中检测重复或可疑付款。"],
    test_004: ["部门支出复盘", "在关账前为部门负责人总结支出例外。"],
    test_005: ["审批链修复", "找出缺失审批，并将财务事项路由给正确审批人。"]
  },
  "006": {
    train_001: ["采购订单匹配", "匹配申请物料、采购订单、收货记录和供应商发票。"],
    train_002: ["供应商准入检查", "验证必需的供应商记录、税务表单、风险标记和付款条款。"],
    train_003: ["收货差异处理", "解决仓库收货与采购订单之间的数量或物料不匹配。"],
    train_004: ["供应商绩效复盘", "比较延迟交付、缺陷备注和合同条款，以便供应商跟进。"],
    train_005: ["紧急补货决策", "根据需求和库存状态判断紧急采购是否合理。"],
    test_001: ["发票冻结解除", "判断在释放被冻结供应商发票前需要哪些证据。"],
    test_002: ["供应商替代请求", "根据价格、可用性和合规上下文评估替代供应商。"],
    test_003: ["部分收货核对", "在采购订单仅部分到货时更新收货状态。"],
    test_004: ["采购例外摘要", "为财务和运营复核准备清晰的例外清单。"],
    test_005: ["合同条款校验", "检查采购决策是否遵循已谈判的供应商条款。"]
  },
  "007": {
    train_001: ["缺货预防", "发现有缺货风险的物料，并推荐补货优先级。"],
    train_002: ["订单分配复核", "基于优先级和到期日期在客户订单之间分配有限库存。"],
    train_003: ["仓库调拨计划", "在不制造新缺口的前提下，在地点之间调拨库存以覆盖需求。"],
    train_004: ["延期订单沟通", "总结延迟订单，并准备准确的客户状态更新。"],
    train_005: ["履约例外审计", "识别因地址、付款、库存或配送问题受阻的订单。"],
    test_001: ["需求激增响应", "在库存分散于多个站点时决定如何满足紧急需求。"],
    test_002: ["呆滞库存清理", "找出周转缓慢的物料，并建议调拨、降价或冻结动作。"],
    test_003: ["发货优先队列", "按服务级别、客户重要性和承诺日期对未结发货排序。"],
    test_004: ["库存盘点差异", "用近期收货、发货和调整解释盘点差异。"],
    test_005: ["订单抢救计划", "为接近错过履约 SLA 的订单制定下一步最佳动作。"]
  },
  "008": {
    train_001: ["税务敏感收入复核", "在建议规划步骤前评估收入、扣除项和截止日期。"],
    train_002: ["遗产文件清单", "识别缺失的遗产规划文件和受益人冲突。"],
    train_003: ["退休现金流快照", "总结资产、支出和时间线，以支持退休建议。"],
    train_004: ["资本利得规划", "评估已实现收益、持有期和税损收割机会。"],
    train_005: ["家庭顾问简报", "将分散的家庭记录整理成顾问可用的规划备忘录。"],
    test_001: ["年末税务行动清单", "在申报或年末截止日期前排列税务动作优先级。"],
    test_002: ["信托和受益人复核", "发现遗产意愿、账户登记和受益人记录之间的不匹配。"],
    test_003: ["流动性需求分析", "判断计划提款能否覆盖支出且不破坏投资策略。"],
    test_004: ["慈善捐赠场景", "根据税务影响、时间安排和投资组合上下文比较慈善选项。"],
    test_005: ["顾问会议准备", "为个人理财复盘准备关键问题和建议。"]
  },
  "009": {
    train_001: ["收入预测刷新", "根据实际值、管道变化和季节性备注更新预测。"],
    train_002: ["运营 KPI 汇报材料", "为管理层更新选择正确指标并解释变化。"],
    train_003: ["预算差异桥接", "按驱动因素解释计划与实际之间的差异。"],
    train_004: ["情景模型检查", "评估业务情景中的上行情形和下行情形假设。"],
    train_005: ["月度报告质检", "找出报告中的总数不一致、过期假设和叙事缺口。"],
    test_001: ["董事会指标摘要", "将运营数据转化为面向领导层的简洁表现叙事。"],
    test_002: ["预测风险提示", "识别哪些假设给下一版预测带来最大风险。"],
    test_003: ["部门模型核对", "对齐运营团队之间的人数、支出和收入假设。"],
    test_004: ["高管差异说明", "在数据不完整时解释意外差异且不过度推断。"],
    test_005: ["报告修正计划", "确定财务模型共享前最需要优先修正的问题。"]
  },
  "010": {
    train_001: ["投资组合风险扫描", "衡量集中度、回撤暴露和资产类别失衡。"],
    train_002: ["再平衡建议", "建议让投资组合更接近目标配置的交易。"],
    train_003: ["投资备忘录复核", "在建议动作前比较投资逻辑、风险、估值和时间周期。"],
    train_004: ["压力情景摘要", "解释投资组合在利率、通胀或市场冲击下可能如何表现。"],
    train_005: ["管理人尽调备注", "为基金管理人总结业绩、费用、授权匹配度和风险信号。"],
    test_001: ["风险预算调整", "在风险预算或客户约束变化时决定如何调整敞口。"],
    test_002: ["组合漂移诊断", "找出哪些持仓导致配置漂移以及下一步应做什么。"],
    test_003: ["策略对比简报", "使用收益驱动因素和下行控制比较候选策略。"],
    test_004: ["流动性压力复核", "检查投资组合流动性是否匹配预期提款需求。"],
    test_005: ["委员会可用建议", "准备带有风险和理由支撑的投资动作。"]
  },
  "011": {
    train_001: ["借款人风险摘要", "复核财务、抵押品、契约和近期表现以评估信用风险。"],
    train_002: ["贷款例外分诊", "在委员会复核前识别缺失文件和政策例外。"],
    train_003: ["契约违约分析", "解释借款人是否违反条款以及需要哪些缓释措施。"],
    train_004: ["信贷备忘录准备", "将借款人优势、劣势和拟议条款压缩成委员会备忘录。"],
    train_005: ["组合观察名单更新", "按恶化信号和所需监控动作对信用项目排序。"],
    test_001: ["续贷信用复核", "评估贷款续期是否符合风险偏好和更新后的借款人数据。"],
    test_002: ["抵押品充足性检查", "在更新价值和未偿敞口下评估抵押品覆盖度。"],
    test_003: ["委员会问题包", "根据授信文件中的弱点准备可能的委员会问题。"],
    test_004: ["风险评级调整", "根据信号判断借款人风险评级是否应调整。"],
    test_005: ["审批条件起草", "写出信贷审批继续前需要满足的清晰条件。"]
  },
  "012": {
    train_001: ["入职准备审计", "检查新员工是否具备正确文件、系统和经理动作。"],
    train_002: ["休假政策解释", "在时间和资格约束下将公司政策应用到休假请求。"],
    train_003: ["薪酬变更路由", "将薪酬或岗位变更路由到正确审批和记录更新流程。"],
    train_004: ["员工关系案例摘要", "用事实、日期和所需下一步总结敏感 HR 案例。"],
    train_005: ["离职清单修复", "找出 IT、薪资、经理和合规之间缺失的离职动作。"],
    test_001: ["内部调岗复核", "验证调岗资格，并识别 HR 系统中需要变更的内容。"],
    test_002: ["政策例外决策", "判断例外请求是否符合书面 HR 政策和先例。"],
    test_003: ["绩效周期清理", "识别缺失评审、校准阻塞点和经理跟进事项。"],
    test_004: ["福利登记案例", "根据员工记录解决福利资格和登记时间问题。"],
    test_005: ["离职风险交接", "为复杂员工退出准备合规交接。"]
  }
};

export const taskTopics = Object.fromEntries(
  Object.entries(taskTopicSource).map(([groupId, topics]) => [
    groupId,
    topics.map(([id, kind, title, desc]) => {
      const [zhTitle, zhDesc] = taskTopicTranslations[groupId]?.[id] ?? [title, desc];
      return {
        id,
        kind,
        title: { en: title, zh: zhTitle },
        desc: { en: desc, zh: zhDesc }
      };
    })
  ])
);
