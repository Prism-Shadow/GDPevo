import json
import random
import sqlite3
from pathlib import Path


SEED = 20020
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
DB_PATH = DATA_DIR / "ma_workbench.db"


SCHEMA = [
    """CREATE TABLE deals (
        deal_id TEXT PRIMARY KEY,
        project_name TEXT NOT NULL,
        transaction_type TEXT NOT NULL,
        client_side TEXT NOT NULL,
        client_name TEXT NOT NULL,
        counterparty_name TEXT NOT NULL,
        target_name TEXT NOT NULL,
        industry TEXT NOT NULL,
        headline_value INTEGER,
        upfront_cash INTEGER,
        stock_value INTEGER,
        milestone_value INTEGER,
        currency TEXT NOT NULL,
        signing_date TEXT,
        meeting_date TEXT,
        playbook_id TEXT,
        policy_id TEXT,
        status TEXT NOT NULL,
        strategic_context TEXT
    )""",
    """CREATE TABLE draft_terms (
        term_id TEXT PRIMARY KEY,
        deal_id TEXT NOT NULL,
        category TEXT NOT NULL,
        draft_value TEXT,
        numeric_value REAL,
        unit TEXT,
        basis TEXT,
        source_document TEXT,
        clause_ref TEXT,
        counterparty_rationale TEXT,
        last_updated TEXT,
        staleness_flag TEXT
    )""",
    """CREATE TABLE playbook_rules (
        playbook_id TEXT NOT NULL,
        category TEXT NOT NULL,
        preferred_position TEXT,
        fallback_position TEXT,
        limit_value REAL,
        limit_unit TEXT,
        basis TEXT,
        required_action TEXT,
        risk_default TEXT,
        notes TEXT
    )""",
    """CREATE TABLE policy_thresholds (
        policy_id TEXT NOT NULL,
        category TEXT NOT NULL,
        policy_standard TEXT,
        threshold_value REAL,
        threshold_unit TEXT,
        basis TEXT,
        approval_required TEXT,
        restricted_flag TEXT,
        notes TEXT
    )""",
    """CREATE TABLE benchmarks (
        benchmark_id TEXT PRIMARY KEY,
        deal_id TEXT NOT NULL,
        category TEXT NOT NULL,
        metric TEXT NOT NULL,
        sample_size INTEGER,
        median_value REAL,
        mean_value REAL,
        upper_quartile REAL,
        notable_precedent TEXT,
        notes TEXT
    )""",
    """CREATE TABLE risk_estimates (
        estimate_id TEXT PRIMARY KEY,
        deal_id TEXT NOT NULL,
        category TEXT NOT NULL,
        exposure_low INTEGER,
        exposure_high INTEGER,
        confidence TEXT,
        method TEXT,
        notes TEXT
    )""",
    """CREATE TABLE cap_table (
        deal_id TEXT NOT NULL,
        holder TEXT NOT NULL,
        security_class TEXT NOT NULL,
        shares INTEGER,
        as_converted_shares INTEGER,
        fully_diluted_pct REAL,
        role_notes TEXT
    )""",
    """CREATE TABLE consents (
        consent_id TEXT PRIMARY KEY,
        deal_id TEXT NOT NULL,
        contract_name TEXT NOT NULL,
        counterparty TEXT NOT NULL,
        consent_type TEXT NOT NULL,
        required_for_closing TEXT,
        risk_rating TEXT,
        amount_at_risk INTEGER,
        notes TEXT
    )""",
    """CREATE TABLE employees (
        employee_id TEXT PRIMARY KEY,
        deal_id TEXT NOT NULL,
        employee_group TEXT NOT NULL,
        count INTEGER,
        draft_treatment TEXT,
        playbook_requirement TEXT,
        pto_liability INTEGER,
        service_credit_required TEXT,
        warn_risk TEXT,
        notes TEXT
    )""",
    """CREATE TABLE material_contracts (
        contract_id TEXT PRIMARY KEY,
        deal_id TEXT NOT NULL,
        contract_name TEXT NOT NULL,
        contract_type TEXT NOT NULL,
        annual_revenue INTEGER,
        anti_assignment TEXT,
        change_of_control TEXT,
        consent_required TEXT,
        notes TEXT
    )""",
    """CREATE TABLE regulatory (
        deal_id TEXT PRIMARY KEY,
        hsr_required TEXT,
        threshold_basis TEXT,
        regulatory_approval TEXT,
        hell_or_high_water_required TEXT,
        notes TEXT
    )""",
    """CREATE TABLE diligence_findings (
        finding_id TEXT PRIMARY KEY,
        deal_id TEXT NOT NULL,
        topic TEXT NOT NULL,
        severity TEXT NOT NULL,
        amount INTEGER,
        source TEXT,
        notes TEXT
    )""",
    """CREATE TABLE deal_notes (
        note_id TEXT PRIMARY KEY,
        deal_id TEXT NOT NULL,
        author TEXT NOT NULL,
        note_date TEXT,
        topic TEXT NOT NULL,
        content TEXT,
        source_document TEXT
    )""",
    """CREATE TABLE documents (
        document_id TEXT PRIMARY KEY,
        deal_id TEXT NOT NULL,
        document_type TEXT NOT NULL,
        title TEXT NOT NULL,
        summary TEXT,
        version TEXT,
        effective_date TEXT
    )""",
]


PLAYBOOK_RULES = [
    (
        "PB_SELLER_A",
        "financing_condition",
        "No buyer financing condition.",
        "Reverse break-up fee of at least 6.0% of enterprise value.",
        6.0,
        "percent_points",
        "enterprise value",
        "Escalate if condition remains without adequate fee.",
        "High",
        "Seller form rejects conditional closing risk.",
    ),
    (
        "PB_SELLER_A",
        "indemnity_cap",
        "General indemnity cap no higher than 10.0% of purchase price.",
        "Cap may reach 12.5% only for verified customer concentration risk.",
        10.0,
        "percent_points",
        "purchase price",
        "Escalate caps above fallback.",
        "Medium",
        "Special indemnities may be uncapped only for tax and fraud.",
    ),
    (
        "PB_SELLER_A",
        "survival_period",
        "General representations survive 12 months.",
        "Fallback 15 months for customer contracts only.",
        15.0,
        "months",
        "general representations",
        "Escalate longer periods.",
        "Medium",
        "Fundamental reps may survive statute of limitations.",
    ),
    (
        "PB_SELLER_A",
        "escrow",
        "Escrow no more than 8.0% of purchase price.",
        "Fallback 10.0% with 12 month release.",
        10.0,
        "percent_points",
        "purchase price",
        "Escalate higher escrow or longer release.",
        "Medium",
        "Escrow must step down after resolved consents.",
    ),
    (
        "PB_SELLER_A",
        "transition_services",
        "Transition services should not exceed 6 months.",
        "Fallback 9 months if monthly fees cover stranded cost.",
        9.0,
        "months",
        "post-closing operations",
        "Escalate longer or below-cost support.",
        "High",
        "Carveout services must have clean termination rights.",
    ),
    (
        "PB_BUYER_A",
        "indemnity_cap",
        "General indemnity cap at least 12.0% of purchase price.",
        "Fallback 10.0% with special indemnity for identified findings.",
        10.0,
        "percent_points",
        "purchase price",
        "Escalate lower cap.",
        "Medium",
        "Buyer position seeks meaningful recourse.",
    ),
    (
        "PB_BUYER_A",
        "survival_period",
        "General representations survive at least 18 months.",
        "Fallback 15 months if escrow is 10.0% or higher.",
        15.0,
        "months",
        "general representations",
        "Escalate shorter periods.",
        "Medium",
        "Short survival requires diligence holdback.",
    ),
    (
        "PB_BUYER_A",
        "materiality_scrape",
        "Full materiality scrape for breach and damages.",
        "Fallback breach-only scrape.",
        None,
        None,
        "indemnity claims",
        "Escalate no scrape.",
        "High",
        "No double materiality in loss calculation.",
    ),
    (
        "PB_BUYER_A",
        "consent_closing_condition",
        "Material third-party consents required before closing.",
        "Fallback closing condition for top ten revenue contracts.",
        10.0,
        "contracts",
        "material contracts",
        "Escalate waiver of material consents.",
        "High",
        "Buyer should avoid inheriting termination exposure.",
    ),
    (
        "PB_BUYER_A",
        "employee_service_credit",
        "Credit prior service and honor accrued PTO.",
        "Fallback service credit for benefits eligibility only.",
        None,
        None,
        "continuing employees",
        "Escalate broad disclaimers.",
        "Medium",
        "Employee treatment should match integration plan.",
    ),
    (
        "PB_SELLER_B",
        "financing_condition",
        "Financing condition allowed only with 5.0% reverse fee.",
        "Reverse fee may be 4.0% for strategic buyers.",
        4.0,
        "percent_points",
        "enterprise value",
        "Review with deal lead.",
        "Medium",
        "Secondary seller playbook for smaller divestitures.",
    ),
    (
        "PB_BUYER_B",
        "survival_period",
        "General representations survive 15 months.",
        "Fallback 12 months with no basket increase.",
        12.0,
        "months",
        "general representations",
        "Review with diligence lead.",
        "Medium",
        "Secondary buyer playbook for low-risk targets.",
    ),
]


POLICY_THRESHOLDS = [
    (
        "POL_MA_2025_A",
        "reverse_termination_fee",
        "Buyer reverse termination fee must not exceed 4.0% of equity value.",
        4.0,
        "percent_points",
        "equity value",
        "M&A Committee",
        "yes",
        "Board Policy No. BD-2024-07 Section 4.3.",
    ),
    (
        "POL_MA_2025_A",
        "fiduciary_out",
        "Fiduciary out must include superior proposal and intervening event triggers with a 5 business-day match right.",
        None,
        None,
        "public-company merger covenant",
        "M&A Committee",
        "yes",
        "Removal of either trigger requires committee approval.",
    ),
    (
        "POL_MA_2025_A",
        "rw_survival",
        "Representations must not survive longer than 15 months.",
        15.0,
        "months",
        "all representations",
        "M&A Committee",
        "yes",
        "Longer general or fundamental survival requires escalation.",
    ),
    (
        "POL_MA_2025_A",
        "mae_carveouts",
        "MAE carve-outs limited to general economic or financial-market conditions and natural disasters or acts of terrorism.",
        2.0,
        "carveouts",
        "approved list",
        "M&A Committee",
        "yes",
        "Additional carve-outs require specific justification.",
    ),
    (
        "POL_MA_2025_A",
        "termination_fee",
        "Company termination fee must not exceed 3.0% of equity value.",
        3.0,
        "percent_points",
        "equity value",
        "General Counsel",
        "no",
        "Near-threshold rows should be checked against equity value.",
    ),
    (
        "POL_MA_2025_A",
        "voting_agreements",
        "Lock-up and voting agreements should not cover more than 35.0% of fully diluted shares.",
        35.0,
        "percent_points",
        "fully diluted shares",
        "M&A Committee",
        "yes",
        "Higher support creates deal protection risk.",
    ),
    (
        "POL_MA_2025_B",
        "reverse_termination_fee",
        "Buyer reverse termination fee must not exceed 4.5% of equity value.",
        4.5,
        "percent_points",
        "equity value",
        "M&A Committee",
        "yes",
        "Legacy policy for pre-2025 launches.",
    ),
    (
        "POL_MA_2025_B",
        "rw_survival",
        "Representations must not survive longer than 18 months.",
        18.0,
        "months",
        "all representations",
        "General Counsel",
        "no",
        "Legacy policy permits longer survival.",
    ),
]


TARGET_DEALS = [
    {
        "deal": (
            "PRJ_JUNIPER",
            "Project Juniper",
            "Asset purchase agreement",
            "seller",
            "Calyx Systems Inc.",
            "Northstar Holdings LLC",
            "Juniper Field Services",
            "industrial technology",
            286000000,
            246000000,
            0,
            40000000,
            "USD",
            "2025-05-19",
            None,
            "PB_SELLER_A",
            None,
            "draft review",
            "Seller is divesting a non-core services unit while preserving customer relationships.",
        ),
        "task_use": "train_001",
        "terms": [
            (
                "financing_condition",
                "Buyer draft includes a debt financing condition through closing.",
                None,
                "boolean",
                "closing condition",
                "Buyer APA",
                "Section 7.2(e)",
                "Buyer says lender approval is needed after diligence refresh.",
                "2025-05-11",
                "current",
            ),
            (
                "reverse_break_fee",
                "No reverse break-up fee is provided if financing fails.",
                0,
                "percent_points",
                "enterprise value",
                "Buyer APA",
                "Section 8.3",
                "Buyer says a fee would duplicate debt commitment costs.",
                "2025-05-11",
                "current",
            ),
            (
                "indemnity_cap",
                "General indemnity cap is 18.0% of purchase price.",
                18.0,
                "percent_points",
                "purchase price",
                "Buyer APA",
                "Article IX",
                "Buyer cites aging customer equipment warranty claims.",
                "2025-05-13",
                "current",
            ),
            (
                "survival_period",
                "General representations survive 24 months.",
                24.0,
                "months",
                "general representations",
                "Buyer APA",
                "Section 9.1",
                "Buyer wants two audit cycles.",
                "2025-05-13",
                "current",
            ),
            (
                "escrow",
                "Escrow equals 14.0% of purchase price for 18 months.",
                14.0,
                "percent_points",
                "purchase price",
                "Buyer APA",
                "Section 2.7",
                "Buyer links escrow to retained warranty exposure.",
                "2025-05-12",
                "current",
            ),
        ],
    },
    {
        "deal": (
            "PRJ_MERIDIAN",
            "Project Meridian",
            "Stock purchase agreement",
            "buyer",
            "Verdantis Therapeutics plc",
            "Callix Ventures LP",
            "Meridian BioAnalytics",
            "biotechnology",
            420000000,
            330000000,
            90000000,
            0,
            "USD",
            "2025-06-04",
            None,
            "PB_BUYER_A",
            None,
            "negotiation",
            "Buyer seeks clean ownership of a diagnostics platform ahead of a product launch.",
        ),
        "task_use": "train_002",
        "terms": [
            (
                "indemnity_cap",
                "Seller proposes a 6.0% general indemnity cap.",
                6.0,
                "percent_points",
                "purchase price",
                "Seller SPA",
                "Section 9.4",
                "Seller says the target has completed a quality-of-earnings review.",
                "2025-05-28",
                "current",
            ),
            (
                "survival_period",
                "General representations survive 12 months.",
                12.0,
                "months",
                "general representations",
                "Seller SPA",
                "Section 9.1",
                "Seller wants a short tail before fund distribution.",
                "2025-05-28",
                "current",
            ),
            (
                "materiality_scrape",
                "No materiality scrape applies to breach or damages.",
                None,
                "text",
                "indemnity claims",
                "Seller SPA",
                "Section 9.2",
                "Seller says scrape language creates double recovery.",
                "2025-05-28",
                "current",
            ),
            (
                "consent_closing_condition",
                "Only two named consents are closing conditions.",
                2.0,
                "contracts",
                "material contracts",
                "Seller SPA",
                "Section 6.2",
                "Seller views other consents as operational notices.",
                "2025-05-29",
                "current",
            ),
            (
                "employee_service_credit",
                "Draft disclaims prior service credit for benefits eligibility.",
                None,
                "text",
                "continuing employees",
                "Seller SPA",
                "Section 5.8",
                "Seller says benefits transition is buyer's integration issue.",
                "2025-05-29",
                "current",
            ),
        ],
    },
    {
        "deal": (
            "PRJ_LYRA",
            "Project Lyra",
            "Public company merger",
            "buyer",
            "Verdantis Therapeutics plc",
            "Calyx Biologics Inc.",
            "Lyra Oncology Platform",
            "biotechnology",
            1120000000,
            705000000,
            415000000,
            0,
            "USD",
            "2025-07-02",
            "2025-07-14",
            None,
            "POL_MA_2025_A",
            "committee escalation",
            "Counterparty is running a limited auction and has asked for rapid approval of four non-standard provisions.",
        ),
        "task_use": "train_003",
        "terms": [
            (
                "reverse_termination_fee",
                "Buyer reverse termination fee is 5.5% of equity value, equal to 61.6 million dollars.",
                5.5,
                "percent_points",
                "equity value",
                "Merger Agreement Draft",
                "Article VIII",
                "Calyx wants a strong remedy because Verdantis requires financing approvals.",
                "2025-07-08",
                "current",
            ),
            (
                "fiduciary_out",
                "Fiduciary out retains superior proposal trigger but removes intervening event trigger; match right remains 5 business days.",
                1.0,
                "restricted_change",
                "public-company merger covenant",
                "Merger Agreement Draft",
                "Section 5.4",
                "Calyx says deal certainty is essential in the auction.",
                "2025-07-08",
                "current",
            ),
            (
                "rw_survival",
                "Fundamental representations survive 24 months and general representations survive 18 months.",
                24.0,
                "months",
                "all representations",
                "Merger Agreement Draft",
                "Article IX",
                "Calyx says public-company diligence must have a longer post-closing tail.",
                "2025-07-08",
                "current",
            ),
            (
                "mae_carveouts",
                "Draft adds changes in Law or GAAP, pandemic or public-health emergency, and industry-wide biotech changes.",
                3.0,
                "additional_carveouts",
                "approved list",
                "MAE Appendix",
                "Definition of MAE",
                "Calyx says biotech valuation volatility should not create walk rights.",
                "2025-07-08",
                "current",
            ),
            (
                "termination_fee",
                "Company termination fee is 2.9% of equity value.",
                2.9,
                "percent_points",
                "equity value",
                "Merger Agreement Draft",
                "Section 8.2",
                "Calyx says fee matches public deal precedents.",
                "2025-07-01",
                "stale",
            ),
        ],
    },
    {
        "deal": (
            "PRJ_ORION",
            "Project Orion",
            "Carveout asset purchase agreement",
            "seller",
            "Orion GridWorks Inc.",
            "Palisade Infrastructure Partners",
            "Orion Grid Services Division",
            "energy infrastructure",
            198000000,
            178000000,
            0,
            20000000,
            "USD",
            "2025-04-22",
            None,
            "PB_SELLER_A",
            None,
            "transition schedule review",
            "Seller must separate shared billing, dispatch, and field-support functions.",
        ),
        "task_use": "train_004",
        "terms": [
            (
                "transition_services",
                "Buyer asks for 15 months of billing, dispatch, and HR transition services at cost.",
                15.0,
                "months",
                "post-closing operations",
                "Carveout APA",
                "Exhibit TSA",
                "Buyer says migration cannot finish before utility customer renewal season.",
                "2025-04-17",
                "current",
            ),
            (
                "stranded_cost_reimbursement",
                "Fees reimburse direct cost only and exclude 3.8 million dollars of stranded overhead.",
                3800000,
                "dollars",
                "seller overhead",
                "TSA Budget",
                "Schedule 1.3",
                "Buyer says overhead remains with seller after separation.",
                "2025-04-17",
                "current",
            ),
            (
                "customer_consent_condition",
                "Buyer can terminate if any top five utility customer consent is not obtained.",
                5.0,
                "contracts",
                "utility customer contracts",
                "Carveout APA",
                "Section 6.2",
                "Buyer says customer approvals are business critical.",
                "2025-04-18",
                "current",
            ),
            (
                "employee_transfer",
                "Buyer may cherry-pick field engineers and reject accrued PTO liability.",
                1240000,
                "dollars",
                "continuing employees",
                "Employee Matters Schedule",
                "Section 5.7",
                "Buyer says workforce selection remains open pending project awards.",
                "2025-04-18",
                "current",
            ),
        ],
    },
    {
        "deal": (
            "PRJ_ASTER",
            "Project Aster",
            "Stock purchase agreement",
            "buyer",
            "Aster Health Group",
            "Ridgeway Capital",
            "Aster Revenue Cycle Software",
            "healthcare software",
            365000000,
            265000000,
            100000000,
            0,
            "USD",
            "2025-08-05",
            None,
            "PB_BUYER_A",
            None,
            "buyer draft markup",
            "Buyer is acquiring a revenue-cycle platform with known provider-contract consent gaps.",
        ),
        "task_use": "train_005",
        "terms": [
            (
                "indemnity_cap",
                "Seller cap is 8.0% with a separate 12.0 million dollar privacy special indemnity.",
                8.0,
                "percent_points",
                "purchase price",
                "Seller SPA",
                "Article IX",
                "Seller points to cyber insurance as supplemental recovery.",
                "2025-07-29",
                "current",
            ),
            (
                "survival_period",
                "General representations survive 15 months.",
                15.0,
                "months",
                "general representations",
                "Seller SPA",
                "Section 9.1",
                "Seller accepts buyer fallback but resists longer survival.",
                "2025-07-29",
                "current",
            ),
            (
                "materiality_scrape",
                "Draft has breach-only materiality scrape and excludes damages scrape.",
                None,
                "text",
                "indemnity claims",
                "Seller SPA",
                "Section 9.2",
                "Seller says damages scrape inflates small reimbursement claims.",
                "2025-07-30",
                "current",
            ),
            (
                "consent_closing_condition",
                "Closing condition covers top ten revenue contracts but excludes payer gateway agreements.",
                10.0,
                "contracts",
                "material contracts",
                "Seller SPA",
                "Section 6.2",
                "Seller says payer gateways are assignable by notice.",
                "2025-07-30",
                "current",
            ),
        ],
    },
    {
        "deal": (
            "PRJ_KEYSTONE",
            "Project Keystone",
            "Asset purchase agreement",
            "seller",
            "Keystone Instruments LLC",
            "Harbor North Holdings",
            "Keystone Flow Controls",
            "industrial manufacturing",
            248000000,
            228000000,
            0,
            20000000,
            "USD",
            "2025-09-18",
            None,
            "PB_SELLER_A",
            None,
            "seller issue review",
            "Seller needs a prioritized response to buyer risk shifting in an equipment carveout.",
        ),
        "task_use": "test_001",
        "terms": [
            (
                "financing_condition",
                "Buyer keeps a financing condition until debt syndication closes.",
                None,
                "boolean",
                "closing condition",
                "Buyer APA",
                "Section 7.2",
                "Buyer says lenders require consent packages before funding.",
                "2025-09-08",
                "current",
            ),
            (
                "reverse_break_fee",
                "Reverse break-up fee is 2.0% of enterprise value.",
                2.0,
                "percent_points",
                "enterprise value",
                "Buyer APA",
                "Section 8.3",
                "Buyer says the partial fee is market for financial sponsors.",
                "2025-09-08",
                "current",
            ),
            (
                "indemnity_cap",
                "General indemnity cap is 16.0% of purchase price.",
                16.0,
                "percent_points",
                "purchase price",
                "Buyer APA",
                "Article IX",
                "Buyer cites open customer acceptance claims.",
                "2025-09-09",
                "current",
            ),
            (
                "escrow",
                "Escrow is 12.0% for 18 months.",
                12.0,
                "percent_points",
                "purchase price",
                "Escrow Schedule",
                "Section 2.8",
                "Buyer links escrow to warranty reserve gaps.",
                "2025-09-09",
                "current",
            ),
        ],
    },
    {
        "deal": (
            "PRJ_VEGA",
            "Project Vega",
            "Public company merger",
            "buyer",
            "Verdantis Therapeutics plc",
            "Vega BioSystems Inc.",
            "Vega Gene Editing Platform",
            "biotechnology",
            980000000,
            590000000,
            390000000,
            0,
            "USD",
            "2025-10-03",
            "2025-10-16",
            None,
            "POL_MA_2025_A",
            "committee escalation",
            "Counterparty insists on broader certainty terms because a rival bidder remains active.",
        ),
        "task_use": "test_002",
        "terms": [
            (
                "reverse_termination_fee",
                "Buyer reverse termination fee is 4.8% of equity value.",
                4.8,
                "percent_points",
                "equity value",
                "Merger Agreement Draft",
                "Article VIII",
                "Vega wants protection for regulatory financing risk.",
                "2025-10-08",
                "current",
            ),
            (
                "fiduciary_out",
                "Draft removes intervening event trigger and shortens board change process to superior proposal only.",
                1.0,
                "restricted_change",
                "public-company merger covenant",
                "Merger Agreement Draft",
                "Section 5.4",
                "Vega says certainty supports the negotiated price.",
                "2025-10-08",
                "current",
            ),
            (
                "rw_survival",
                "Fundamental representations survive 21 months and general representations survive 17 months.",
                21.0,
                "months",
                "all representations",
                "Merger Agreement Draft",
                "Article IX",
                "Vega says FDA diligence needs more time.",
                "2025-10-08",
                "current",
            ),
            (
                "mae_carveouts",
                "Draft adds pandemic, clinical-trial hold, and sector-wide regulatory change carve-outs.",
                3.0,
                "additional_carveouts",
                "approved list",
                "MAE Appendix",
                "Definition of MAE",
                "Vega says biotech regulatory risk is outside company control.",
                "2025-10-08",
                "current",
            ),
        ],
    },
    {
        "deal": (
            "PRJ_HELIX",
            "Project Helix",
            "Stock purchase agreement",
            "buyer",
            "Helix Diagnostics Corp.",
            "Westward Ventures",
            "Helix Clinical Labs",
            "life sciences services",
            510000000,
            410000000,
            100000000,
            0,
            "USD",
            "2025-11-07",
            None,
            "PB_BUYER_A",
            None,
            "closing package review",
            "Buyer must decide whether remaining consents and employee matters can close on schedule.",
        ),
        "task_use": "test_003",
        "terms": [
            (
                "consent_closing_condition",
                "Draft permits closing with four unresolved top ten customer consents if seller delivers notices.",
                4.0,
                "contracts",
                "material contracts",
                "SPA Closing Draft",
                "Section 6.2",
                "Seller says notices are sufficient under the contracts.",
                "2025-11-01",
                "current",
            ),
            (
                "indemnity_cap",
                "General indemnity cap is 9.0% with a 15.0 million dollar special indemnity.",
                9.0,
                "percent_points",
                "purchase price",
                "SPA Closing Draft",
                "Article IX",
                "Seller says special indemnity should cover known issues.",
                "2025-11-01",
                "current",
            ),
            (
                "employee_service_credit",
                "Draft credits prior service only for senior lab employees and excludes contractors converting at closing.",
                None,
                "text",
                "continuing employees",
                "Employee Matters Schedule",
                "Section 5.8",
                "Seller says contractors are outside the benefit plan.",
                "2025-11-02",
                "current",
            ),
        ],
    },
    {
        "deal": (
            "PRJ_NIMBUS",
            "Project Nimbus",
            "Carveout asset purchase agreement",
            "seller",
            "Nimbus Cloud Systems",
            "Cedarline Capital",
            "Nimbus Edge Hosting Unit",
            "cloud infrastructure",
            620000000,
            520000000,
            0,
            100000000,
            "USD",
            "2025-12-12",
            None,
            "PB_SELLER_A",
            None,
            "carveout transition negotiation",
            "Seller is separating shared identity, billing, and support systems from a hosted-services business.",
        ),
        "task_use": "test_004",
        "terms": [
            (
                "transition_services",
                "Buyer asks for 18 months of identity, billing, and tier-two support at fixed below-cost fees.",
                18.0,
                "months",
                "post-closing operations",
                "Carveout APA",
                "Exhibit TSA",
                "Buyer says customer migration will occur in phases.",
                "2025-12-03",
                "current",
            ),
            (
                "stranded_cost_reimbursement",
                "Fixed fees leave 9.4 million dollars of unrecovered stranded costs.",
                9400000,
                "dollars",
                "seller overhead",
                "TSA Budget",
                "Schedule 2.1",
                "Buyer says stranded costs should be shared as purchase price consideration.",
                "2025-12-03",
                "current",
            ),
            (
                "customer_consent_condition",
                "Buyer can delay closing if any of the top eight enterprise consents remains outstanding.",
                8.0,
                "contracts",
                "enterprise customer contracts",
                "Carveout APA",
                "Section 6.2",
                "Buyer says service interruption risk is unacceptable.",
                "2025-12-04",
                "current",
            ),
        ],
    },
    {
        "deal": (
            "PRJ_ROOK",
            "Project Rook",
            "Public company merger",
            "buyer",
            "Rook Mobility plc",
            "AnchorGate Partners",
            "Rook Autonomous Fleet",
            "mobility technology",
            760000000,
            455000000,
            305000000,
            0,
            "USD",
            "2026-01-09",
            "2026-01-23",
            None,
            "POL_MA_2025_A",
            "negotiation priority matrix",
            "Legal team must rank committee-sensitive negotiation points before the next board call.",
        ),
        "task_use": "test_005",
        "terms": [
            (
                "reverse_termination_fee",
                "Buyer reverse termination fee is 4.2% of equity value.",
                4.2,
                "percent_points",
                "equity value",
                "Merger Agreement Draft",
                "Article VIII",
                "AnchorGate says financing and fleet-regulatory approvals justify the fee.",
                "2026-01-13",
                "current",
            ),
            (
                "termination_fee",
                "Company termination fee is 3.4% of equity value.",
                3.4,
                "percent_points",
                "equity value",
                "Merger Agreement Draft",
                "Section 8.2",
                "AnchorGate wants reciprocal deal protection.",
                "2026-01-13",
                "current",
            ),
            (
                "voting_agreements",
                "Sponsor lock-up covers 41.0% of fully diluted shares.",
                41.0,
                "percent_points",
                "fully diluted shares",
                "Support Agreement",
                "Section 1.2",
                "AnchorGate says locked support is needed to deter topping bids.",
                "2026-01-13",
                "current",
            ),
            (
                "mae_carveouts",
                "Draft adds autonomous vehicle regulation and supply-chain disruption carve-outs.",
                2.0,
                "additional_carveouts",
                "approved list",
                "MAE Appendix",
                "Definition of MAE",
                "AnchorGate says both risks are sector-wide.",
                "2026-01-13",
                "current",
            ),
        ],
    },
]


INDUSTRIES = [
    "industrial technology",
    "biotechnology",
    "healthcare software",
    "energy infrastructure",
    "cloud infrastructure",
    "financial services",
    "logistics",
    "consumer products",
]
CLIENTS = [
    "Verdantis Therapeutics plc",
    "Calyx Systems Inc.",
    "Aster Health Group",
    "Keystone Instruments LLC",
    "Nimbus Cloud Systems",
    "Rook Mobility plc",
    "Mariner Analytics",
    "Oakline Industrial",
]
COUNTERPARTIES = [
    "Palisade Infrastructure Partners",
    "Harbor North Holdings",
    "Cedarline Capital",
    "Ridgeway Capital",
    "AnchorGate Partners",
    "Westward Ventures",
    "Northstar Holdings LLC",
    "Bluewater Strategic",
]
PROJECT_WORDS = [
    "Junia",
    "Meridian North",
    "Lyric",
    "Oriel",
    "Astoria",
    "Keystone West",
    "Vega Minor",
    "Helio",
    "Nimbus East",
    "Rookery",
    "Cedar",
    "Quartz",
    "Harbor",
    "Willow",
    "Summit",
    "Lattice",
]


def main():
    random.seed(SEED)
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if DB_PATH.exists():
        DB_PATH.unlink()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        build_schema(conn)
        insert_reference_data(conn)
        target_ids = insert_target_deals(conn)
        distractor_ids = insert_distractor_deals(conn, 75)
        conn.commit()
        write_manifests(conn, target_ids, distractor_ids)
    finally:
        conn.close()


def build_schema(conn):
    cur = conn.cursor()
    for table in [
        "deals",
        "draft_terms",
        "playbook_rules",
        "policy_thresholds",
        "benchmarks",
        "risk_estimates",
        "cap_table",
        "consents",
        "employees",
        "material_contracts",
        "regulatory",
        "diligence_findings",
        "deal_notes",
        "documents",
    ]:
        cur.execute(f"DROP TABLE IF EXISTS {table}")
    for statement in SCHEMA:
        cur.execute(statement)


def insert_reference_data(conn):
    conn.executemany("INSERT INTO playbook_rules VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", PLAYBOOK_RULES)
    conn.executemany("INSERT INTO policy_thresholds VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", POLICY_THRESHOLDS)


def insert_target_deals(conn):
    target_ids = []
    for spec in TARGET_DEALS:
        deal = spec["deal"]
        deal_id = deal[0]
        target_ids.append(deal_id)
        conn.execute("INSERT INTO deals VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", deal)
        insert_terms(conn, deal_id, spec["terms"])
        insert_common_records(conn, deal_id, deal, target=True)
    return target_ids


def insert_terms(conn, deal_id, terms):
    rows = []
    for idx, term in enumerate(terms, 1):
        rows.append((f"TERM_{deal_id}_{idx:02d}", deal_id) + term)
    conn.executemany("INSERT INTO draft_terms VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", rows)


def insert_common_records(conn, deal_id, deal, target=False):
    value = deal[8] or 100000000
    project_name = deal[1]
    transaction_type = deal[2]
    industry = deal[7]
    target_name = deal[6]
    high = "High" if target else random.choice(["Low", "Medium", "High"])

    documents = [
        (
            f"DOC_{deal_id}_01",
            deal_id,
            "draft agreement",
            f"{project_name} draft agreement",
            f"Current transaction draft for {target_name}.",
            "v2.1" if target else "v1.4",
            deal[13] or "2025-06-01",
        ),
        (
            f"DOC_{deal_id}_02",
            deal_id,
            "negotiation notes",
            f"{project_name} negotiation tracker",
            "Open legal and business points from counsel calls.",
            "v1.0",
            "2025-06-03",
        ),
        (
            f"DOC_{deal_id}_03",
            deal_id,
            "financial analysis",
            f"{project_name} exposure model",
            "Finance model for selected agreement positions.",
            "v0.9",
            "2025-06-05",
        ),
    ]
    conn.executemany("INSERT INTO documents VALUES (?, ?, ?, ?, ?, ?, ?)", documents)

    benchmarks = [
        (
            f"BM_{deal_id}_01",
            deal_id,
            "termination economics",
            "fee percent of equity value",
            42,
            3.2,
            3.5,
            4.1,
            "Ridgeway-Marlowe 2024",
            "Strategic transactions cluster below sponsor auctions.",
        ),
        (
            f"BM_{deal_id}_02",
            deal_id,
            "indemnity",
            "general cap percent of purchase price",
            36,
            10.0,
            10.8,
            12.5,
            "Oakline-Cedar 2025",
            "Carveout deals show higher upper quartile.",
        ),
        (
            f"BM_{deal_id}_03",
            deal_id,
            "survival",
            "general representation survival months",
            39,
            15.0,
            15.6,
            18.0,
            "Harbor-Northstar 2024",
            "Biotech and regulated assets skew longer.",
        ),
    ]
    conn.executemany("INSERT INTO benchmarks VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", benchmarks)

    risks = [
        (
            f"RSK_{deal_id}_01",
            deal_id,
            "closing certainty",
            int(value * 0.015),
            int(value * 0.045),
            "medium",
            "outside counsel scenario range",
            "Exposure reflects delay, financing, and consent failure risk.",
        ),
        (
            f"RSK_{deal_id}_02",
            deal_id,
            "indemnity leakage",
            int(value * 0.008),
            int(value * 0.028),
            "medium",
            "claims history and cap sensitivity",
            "Model excludes fraud and intentional breach claims.",
        ),
        (
            f"RSK_{deal_id}_03",
            deal_id,
            "transition disruption",
            int(value * 0.004),
            int(value * 0.018),
            "low" if not target else "medium",
            "operational separation estimate",
            "Higher for carveout transition-services packages.",
        ),
    ]
    conn.executemany("INSERT INTO risk_estimates VALUES (?, ?, ?, ?, ?, ?, ?, ?)", risks)

    cap_rows = [
        (
            deal_id,
            "Founders and executives",
            "common stock",
            8400000,
            8400000,
            0.185,
            "Management rollover and support obligations under review.",
        ),
        (
            deal_id,
            "Lead investor group",
            "preferred stock",
            12600000,
            15500000,
            0.341,
            "Investor consent may be needed for drag-along or support agreement.",
        ),
        (
            deal_id,
            "Employee option pool",
            "options",
            4200000,
            4200000,
            0.092,
            "Includes unvested options and retention grant pool.",
        ),
        (
            deal_id,
            "Public or minority holders",
            "common stock",
            17300000,
            17300000,
            0.382,
            "Dispersed holders; proxy timing may affect closing.",
        ),
    ]
    conn.executemany("INSERT INTO cap_table VALUES (?, ?, ?, ?, ?, ?, ?)", cap_rows)

    consents = [
        (
            f"CNS_{deal_id}_01",
            deal_id,
            "Master Commercial Agreement",
            "Apex Customer Group",
            "change of control",
            "yes",
            high,
            int(value * 0.055),
            "Top revenue relationship; counterparty has termination leverage.",
        ),
        (
            f"CNS_{deal_id}_02",
            deal_id,
            "Cloud Services Agreement",
            "HelioCloud Services",
            "assignment",
            "no",
            "Medium",
            int(value * 0.012),
            "Notice covenant and data-processing addendum require coordination.",
        ),
        (
            f"CNS_{deal_id}_03",
            deal_id,
            "Facility Lease",
            "North Pier Properties",
            "landlord consent",
            "yes" if target else "no",
            "Low",
            850000,
            "Landlord response is pending but lease has reasonable-consent language.",
        ),
    ]
    conn.executemany("INSERT INTO consents VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", consents)

    employees = [
        (
            f"EMP_{deal_id}_01",
            deal_id,
            "executives",
            8,
            "Offer letters with 12 month severance protection.",
            "Preserve key retention terms through closing.",
            420000,
            "yes",
            "low",
            "Equity rollover is addressed separately.",
        ),
        (
            f"EMP_{deal_id}_02",
            deal_id,
            "engineering and product",
            86 if "software" in industry or "cloud" in industry else 42,
            "Comparable base salary and benefits.",
            "Credit prior service for benefits eligibility.",
            1860000,
            "yes",
            "medium",
            "Several employees are in states with notice timing requirements.",
        ),
        (
            f"EMP_{deal_id}_03",
            deal_id,
            "field and operations",
            124 if "industrial" in industry or "energy" in industry else 37,
            "Buyer may select continuing employees.",
            "Define transfer process and accrued PTO allocation.",
            1240000,
            "yes",
            "medium",
            "Selection rights may create retention risk.",
        ),
    ]
    conn.executemany("INSERT INTO employees VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", employees)

    contracts = [
        (
            f"MAT_{deal_id}_01",
            deal_id,
            "Apex Customer Master Agreement",
            "customer",
            int(value * 0.085),
            "yes",
            "yes",
            "yes",
            "Largest customer agreement with termination leverage.",
        ),
        (
            f"MAT_{deal_id}_02",
            deal_id,
            "Core Platform License",
            "technology license",
            int(value * 0.018),
            "yes",
            "no",
            "notice only",
            "License follows the business but requires prompt notice.",
        ),
        (
            f"MAT_{deal_id}_03",
            deal_id,
            "Strategic Supply Agreement",
            "supplier",
            int(value * 0.026),
            "no",
            "yes",
            "yes" if target else "no",
            "Supplier consent affects post-closing margin assumptions.",
        ),
    ]
    conn.executemany("INSERT INTO material_contracts VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", contracts)

    conn.execute(
        "INSERT INTO regulatory VALUES (?, ?, ?, ?, ?, ?)",
        (
            deal_id,
            "yes" if value >= 125000000 else "no",
            "size-of-transaction" if value >= 125000000 else "below threshold",
            "HSR and industry review"
            if transaction_type.lower().startswith("public")
            else "HSR only"
            if value >= 125000000
            else "none expected",
            "no" if target else random.choice(["no", "limited covenant"]),
            "Regulatory covenant should align with business appetite and remedy cap.",
        ),
    )

    findings = [
        (
            f"FND_{deal_id}_01",
            deal_id,
            "customer concentration",
            "High" if target else random.choice(["Low", "Medium", "High"]),
            int(value * 0.035),
            "diligence report",
            "Top three customers represent a significant share of trailing revenue.",
        ),
        (
            f"FND_{deal_id}_02",
            deal_id,
            "privacy and security",
            "Medium",
            int(value * 0.012),
            "data room Q&A",
            "Open remediation items remain for vendor access reviews.",
        ),
        (
            f"FND_{deal_id}_03",
            deal_id,
            "working capital",
            "Medium",
            int(value * 0.006),
            "finance memo",
            "Seasonal working capital target may need a collar.",
        ),
    ]
    conn.executemany("INSERT INTO diligence_findings VALUES (?, ?, ?, ?, ?, ?, ?)", findings)

    notes = [
        (
            f"NOTE_{deal_id}_01",
            deal_id,
            "Maya Patel",
            "2025-06-06",
            "negotiation posture",
            "Business team wants legal to separate must-have protections from tradeable terms.",
            "deal team call",
        ),
        (
            f"NOTE_{deal_id}_02",
            deal_id,
            "Evan Brooks",
            "2025-06-07",
            "counterparty rationale",
            "Counterparty is using timing pressure to support broader buyer protections.",
            "counsel call notes",
        ),
        (
            f"NOTE_{deal_id}_03",
            deal_id,
            "Nora Singh",
            "2025-06-08",
            "diligence follow-up",
            "Finance asked counsel to quantify contract consent and indemnity exposure.",
            "finance follow-up email",
        ),
    ]
    conn.executemany("INSERT INTO deal_notes VALUES (?, ?, ?, ?, ?, ?, ?)", notes)


def insert_distractor_deals(conn, count):
    distractor_ids = []
    used = {spec["deal"][0] for spec in TARGET_DEALS}
    for idx in range(1, count + 1):
        deal_id = f"PRJ_D{idx:03d}"
        while deal_id in used:
            idx += 1
            deal_id = f"PRJ_D{idx:03d}"
        used.add(deal_id)
        distractor_ids.append(deal_id)
        value = random.randrange(45, 900) * 1000000
        transaction_type = random.choice(
            [
                "Stock purchase agreement",
                "Asset purchase agreement",
                "Public company merger",
                "Carveout asset purchase agreement",
            ]
        )
        client_side = random.choice(["buyer", "seller"])
        playbook_id = None
        policy_id = None
        if "merger" in transaction_type.lower():
            policy_id = random.choice(["POL_MA_2025_A", "POL_MA_2025_B", None])
        else:
            playbook_id = random.choice(["PB_SELLER_A", "PB_BUYER_A", "PB_SELLER_B", "PB_BUYER_B"])
        name_word = PROJECT_WORDS[(idx - 1) % len(PROJECT_WORDS)]
        deal = (
            deal_id,
            f"Project {name_word}",
            transaction_type,
            client_side,
            random.choice(CLIENTS),
            random.choice(COUNTERPARTIES),
            f"{name_word} Operating Assets",
            random.choice(INDUSTRIES),
            value,
            int(value * random.uniform(0.55, 0.95)),
            int(value * random.uniform(0.0, 0.35)),
            int(value * random.uniform(0.0, 0.18)),
            "USD",
            f"2025-{random.randint(1, 12):02d}-{random.randint(2, 26):02d}",
            f"2025-{random.randint(1, 12):02d}-{random.randint(2, 26):02d}" if policy_id else None,
            playbook_id,
            policy_id,
            random.choice(["draft review", "negotiation", "diligence", "closing package", "committee review"]),
            random.choice(
                [
                    "Team is reconciling legal positions against commercial urgency.",
                    "Deal has similar economics but different risk allocation from target matters.",
                    "Records include stale and duplicate rows from earlier drafts.",
                    "Business sponsor wants a concise view of consent and closing risk.",
                ]
            ),
        )
        conn.execute("INSERT INTO deals VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", deal)
        insert_terms(conn, deal_id, distractor_terms(deal_id, transaction_type, playbook_id, policy_id))
        insert_common_records(conn, deal_id, deal, target=False)
    return distractor_ids


def distractor_terms(deal_id, transaction_type, playbook_id, policy_id):
    stale = random.choice(["current", "stale"])
    if policy_id:
        fee = round(random.choice([3.8, 3.95, 4.0, 4.1, 4.45, 4.6]), 2)
        survival = random.choice([12, 15, 16, 18, 21])
        return [
            (
                "reverse_termination_fee",
                f"Buyer reverse termination fee is {fee}% of equity value.",
                fee,
                "percent_points",
                "equity value",
                "Merger Draft",
                "Article VIII",
                "Counterparty cites certainty needs.",
                "2025-06-01",
                stale,
            ),
            (
                "termination_fee",
                f"Company termination fee is {round(random.uniform(2.4, 3.5), 2)}% of equity value.",
                round(random.uniform(2.4, 3.5), 2),
                "percent_points",
                "equity value",
                "Merger Draft",
                "Section 8.2",
                "Counterparty wants reciprocal deal protection.",
                "2025-06-01",
                "current",
            ),
            (
                "rw_survival",
                f"Representations survive {survival} months.",
                float(survival),
                "months",
                "all representations",
                "Merger Draft",
                "Article IX",
                "Counterparty says diligence timing supports the period.",
                "2025-05-24",
                "current",
            ),
            (
                "mae_carveouts",
                "Draft contains a near-standard MAE definition with one disputed carve-out.",
                1.0,
                "additional_carveouts",
                "approved list",
                "Merger Draft",
                "Definition of MAE",
                "Counterparty says the change is market.",
                "2025-05-24",
                stale,
            ),
        ]
    if playbook_id and "BUYER" in playbook_id:
        cap = random.choice([7.5, 9.5, 10.0, 11.0, 12.0])
        survival = random.choice([12, 14, 15, 18])
        return [
            (
                "indemnity_cap",
                f"General indemnity cap is {cap}% of purchase price.",
                cap,
                "percent_points",
                "purchase price",
                "SPA Draft",
                "Article IX",
                "Seller says risk is covered by diligence.",
                "2025-05-20",
                "current",
            ),
            (
                "survival_period",
                f"General representations survive {survival} months.",
                float(survival),
                "months",
                "general representations",
                "SPA Draft",
                "Section 9.1",
                "Seller wants fund distribution certainty.",
                "2025-05-20",
                stale,
            ),
            (
                "materiality_scrape",
                random.choice(
                    ["Full materiality scrape.", "Breach-only materiality scrape.", "No materiality scrape."]
                ),
                None,
                "text",
                "indemnity claims",
                "SPA Draft",
                "Section 9.2",
                "Seller says buyer should not double count materiality.",
                "2025-05-20",
                "current",
            ),
            (
                "consent_closing_condition",
                "Closing condition covers selected customer consents only.",
                float(random.choice([3, 5, 10])),
                "contracts",
                "material contracts",
                "SPA Draft",
                "Section 6.2",
                "Seller says the rest can follow after closing.",
                "2025-05-21",
                "current",
            ),
        ]
    fee = random.choice([0.0, 2.0, 4.0, 6.0])
    escrow = random.choice([7.0, 8.0, 10.0, 12.0])
    return [
        (
            "financing_condition",
            random.choice(
                ["No financing condition.", "Buyer financing condition remains until commitment letter delivery."]
            ),
            None,
            "boolean",
            "closing condition",
            "APA Draft",
            "Section 7.2",
            "Buyer says funding certainty depends on consents.",
            "2025-05-19",
            "current",
        ),
        (
            "reverse_break_fee",
            f"Reverse break-up fee is {fee}% of enterprise value.",
            fee,
            "percent_points",
            "enterprise value",
            "APA Draft",
            "Section 8.3",
            "Buyer says fee should match debt costs.",
            "2025-05-19",
            stale,
        ),
        (
            "escrow",
            f"Escrow is {escrow}% for 12 months.",
            escrow,
            "percent_points",
            "purchase price",
            "Escrow Schedule",
            "Section 2.8",
            "Buyer links escrow to diligence holdback.",
            "2025-05-20",
            "current",
        ),
        (
            "survival_period",
            f"General representations survive {random.choice([12, 15, 18, 24])} months.",
            float(random.choice([12, 15, 18, 24])),
            "months",
            "general representations",
            "APA Draft",
            "Article IX",
            "Buyer wants post-closing audit coverage.",
            "2025-05-20",
            "current",
        ),
    ]


def write_manifests(conn, target_ids, distractor_ids):
    cur = conn.cursor()
    counts = {}
    for table in [
        "deals",
        "draft_terms",
        "playbook_rules",
        "policy_thresholds",
        "benchmarks",
        "risk_estimates",
        "cap_table",
        "consents",
        "employees",
        "material_contracts",
        "regulatory",
        "diligence_findings",
        "deal_notes",
        "documents",
    ]:
        counts[table] = cur.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
    manifest = {
        "task_group_id": "task_group_020",
        "seed": SEED,
        "database": "data/ma_workbench.db",
        "generated_at": "2026-07-18T00:00:00Z",
        "state_mode": "read_only",
        "query_token": "deal-workbench-readonly",
        "counts": counts,
        "public_entry_points": [
            line.strip()
            for line in (BASE_DIR / "endpoints.txt").read_text(encoding="utf-8").splitlines()
            if line.strip()
        ],
    }
    construction = {
        "task_group_id": "task_group_020",
        "seed": SEED,
        "target_deals": {
            spec["deal"][0]: {
                "project_name": spec["deal"][1],
                "task_use": spec["task_use"],
                "playbook_id": spec["deal"][15],
                "policy_id": spec["deal"][16],
                "status": spec["deal"][17],
                "primary_term_categories": [term[0] for term in spec["terms"]],
            }
            for spec in TARGET_DEALS
        },
        "distractor_deal_count": len(distractor_ids),
        "notes": "Construction hints are for builders only. Solvers discover records through the web app and APIs.",
    }
    (DATA_DIR / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")
    (DATA_DIR / "construction_manifest.json").write_text(
        json.dumps(construction, indent=2, sort_keys=True), encoding="utf-8"
    )


if __name__ == "__main__":
    main()
