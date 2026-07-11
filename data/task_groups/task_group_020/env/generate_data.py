#!/usr/bin/env python3
"""Generate deterministic data for the Aster Legal Deal Desk environment."""

from __future__ import annotations

import json
import random
from pathlib import Path


SEED = 20020
RNG = random.Random(SEED)
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
DATA_FILE = DATA_DIR / "dealdesk.json"
MANIFEST_FILE = DATA_DIR / "manifest.json"
NEUTRAL_REVIEW_NOTE = (
    "Review the draft value, playbook value, policy threshold, calculation base, source status, and related documents."
)

REQUIRED_DEAL_IDS = [
    "D-ALDER-447",
    "D-BRASS-219",
    "D-CYPRESS-735",
    "D-ORBIT-384",
    "D-HARBOR-562",
    "D-LUMEN-908",
    "D-QUARTZ-311",
    "D-NOVA-674",
    "D-KEPLER-155",
    "D-SOLSTICE-820",
]


def money(value: int | float | None) -> str:
    if value is None:
        return "not applicable"
    return f"${value:,.0f}"


def seller(name: str, role: str, percent: float, proceeds: int | float) -> dict:
    return {
        "name": name,
        "role": role,
        "ownership_percent": percent,
        "estimated_proceeds": proceeds,
    }


def rule(
    rule_id: str, topic: str, preferred: str, fallback: str, threshold: str, approval: str, triggers: list[str]
) -> dict:
    return {
        "rule_id": rule_id,
        "topic": topic,
        "preferred": preferred,
        "fallback_position": fallback,
        "threshold": threshold,
        "basis": "Applies to active drafts and latest written client instructions.",
        "approval_category": approval,
        "escalation_triggers": triggers,
    }


def clause_term(
    code: str,
    topic: str,
    draft: str,
    playbook: str,
    threshold: str,
    base: str,
    risk: str,
    status: str = "ACTIVE",
) -> dict:
    return {
        "clause_code": code,
        "topic": topic,
        "draft_value": draft,
        "playbook_value": playbook,
        "policy_threshold": threshold,
        "calculation_base": base,
        "risk_hint": NEUTRAL_REVIEW_NOTE,
        "version_status": status,
    }


def build_policies() -> list[dict]:
    return [
        {
            "policy_id": "P-BUYER-MIDMARKET-2026",
            "client": "Northstar Capital Partners",
            "policy_type": "BUYER_RISK_MEMO",
            "version": "2026.2",
            "effective_date": "2026-05-15",
            "title": "Northstar Buyer Risk Memo and SPA Playbook",
            "rules": [
                rule(
                    "BUY-MID-ESCROW",
                    "escrow",
                    "8%-10% general indemnity escrow.",
                    "Up to 12% if diligence flags are documented.",
                    "Committee approval above 12%.",
                    "Legal risk committee",
                    ["general escrow above 12%", "separate tax escrow above 3%"],
                ),
                rule(
                    "BUY-MID-CAP",
                    "indemnity cap",
                    "General cap at escrow amount.",
                    "Fallback to 12.5% of headline value.",
                    "Approval required above 12.5%.",
                    "Legal risk committee",
                    ["cap above 12.5%", "uncapped business reps"],
                ),
                rule(
                    "BUY-MID-BASKET",
                    "basket",
                    "0.75%-1.0% deductible basket.",
                    "Tipping basket only for fraud or fundamental reps.",
                    "Escalate if below 0.5% or tipping.",
                    "Deal lead",
                    ["basket below 0.5%", "tipping basket for general reps"],
                ),
                rule(
                    "BUY-MID-NWC",
                    "working capital",
                    "Target from trailing 12-month normalized average with a collar.",
                    "Dollar-for-dollar adjustment outside collar.",
                    "Escalate if target uses seller budget only.",
                    "Finance committee",
                    ["unverified NWC target", "collar above 1% enterprise value"],
                ),
                rule(
                    "BUY-MID-NONCOMPETE",
                    "non-compete",
                    "24 months, limited to products and territories used by target.",
                    "36 months only with founder employment covenant.",
                    "Escalate broad territory or more than 36 months.",
                    "Employment counsel",
                    ["worldwide scope", "more than 36 months"],
                ),
                rule(
                    "BUY-MID-CONSENTS",
                    "material consents",
                    "Specified material consents as closing conditions.",
                    "Post-closing covenant only for non-material contracts.",
                    "Escalate if top customer consent omitted.",
                    "Deal lead",
                    ["top five contract consent missing", "regulatory approval uncertain"],
                ),
                rule(
                    "BUY-MID-HSR",
                    "HSR",
                    "No filing condition unless antitrust counsel confirms thresholds met.",
                    "Include cooperation covenant where no filing is required.",
                    "Escalate unclear size-of-person analysis.",
                    "Regulatory counsel",
                    ["HSR condition without counsel memo", "missing antitrust memo"],
                ),
            ],
        },
        {
            "policy_id": "P-SELLER-APA-2026",
            "client": "Meridian Seller Desk",
            "policy_type": "SELLER_PLAYBOOK",
            "version": "2026.1",
            "effective_date": "2026-04-20",
            "title": "Seller APA Response Playbook",
            "rules": [
                rule(
                    "SELL-APA-FINANCING",
                    "financing condition",
                    "Reject financing conditions.",
                    "Only a reverse termination fee backed by creditworthy parent may be considered.",
                    "Any financing condition requires executive approval.",
                    "Executive committee",
                    ["financing condition", "lender diligence condition"],
                ),
                rule(
                    "SELL-APA-ESCROW",
                    "escrow",
                    "5%-7.5% general escrow.",
                    "10% only for identified indemnity issues.",
                    "Escalate above 10%.",
                    "Seller steering committee",
                    ["escrow above 10%", "escrow longer than survival"],
                ),
                rule(
                    "SELL-APA-CAP",
                    "indemnity cap",
                    "Cap at escrow amount.",
                    "Fallback 10%-12.5% for general reps.",
                    "Escalate above 12.5%.",
                    "Seller steering committee",
                    ["cap above 12.5%", "uncapped ordinary-course reps"],
                ),
                rule(
                    "SELL-APA-BASKET",
                    "basket",
                    "1% deductible basket with no tipping.",
                    "0.75% deductible for competitive process.",
                    "Escalate below 0.75% or tipping.",
                    "Deal lead",
                    ["tipping basket", "de minimis omitted"],
                ),
                rule(
                    "SELL-APA-NONCOMPETE",
                    "non-compete",
                    "No more than 3 years and limited to transferred business.",
                    "Narrow customer non-solicit can extend to 4 years.",
                    "Escalate worldwide or affiliate-wide restrictions.",
                    "Employment counsel",
                    ["worldwide non-compete", "affiliate-wide restriction"],
                ),
                rule(
                    "SELL-APA-EMPLOYEE",
                    "employee transfer",
                    "Buyer must offer comparable employment to business employees.",
                    "Seller can assist with transition communications.",
                    "Escalate if seller retains WARN or severance burden.",
                    "HR committee",
                    ["WARN burden retained", "no offer standard"],
                ),
                rule(
                    "SELL-APA-TSA",
                    "transition services",
                    "TSA must cover systems, finance, HR, and IT support where assets are carved out.",
                    "Short-form TSA may work only with complete standalone systems.",
                    "Escalate omitted TSA for non-standalone division.",
                    "Operations committee",
                    ["missing TSA", "unsupported ERP migration"],
                ),
                rule(
                    "SELL-APA-IP",
                    "IP transition",
                    "Limited transition license and clear retained-IP boundaries.",
                    "Trademark phase-out up to 9 months.",
                    "Escalate open-ended IP use.",
                    "IP counsel",
                    ["open-ended trademark use", "source code escrow without scope"],
                ),
            ],
        },
        {
            "policy_id": "P-PUBLIC-MERGER-COMMITTEE-2026",
            "client": "Aster Public Company Committee",
            "policy_type": "COMMITTEE_POLICY",
            "version": "2026.3",
            "effective_date": "2026-06-01",
            "title": "Public Merger Escalation and Market Check Policy",
            "rules": [
                rule(
                    "PUB-RTF",
                    "reverse termination fee",
                    "RTF at or below 5.0% of equity value.",
                    "5.5% only with superior regulatory covenant.",
                    "Board committee approval above 5.5%.",
                    "Board transaction committee",
                    ["RTF above 5.5%", "RTF not tied to buyer breach"],
                ),
                rule(
                    "PUB-FIDUCIARY",
                    "fiduciary out",
                    "Preserve board fiduciary-out and superior proposal termination right.",
                    "Matching rights no longer than four business days.",
                    "Escalate force-the-vote or blocked termination.",
                    "Board transaction committee",
                    ["fiduciary out blocked", "matching period above 4 business days"],
                ),
                rule(
                    "PUB-RW-SURVIVAL",
                    "R&W survival",
                    "No post-closing survival in public-style merger.",
                    "Special covenants may survive if not tied to damages cap.",
                    "Escalate buyer indemnity after closing.",
                    "Board transaction committee",
                    ["post-closing R&W survival", "indemnity escrow in public merger"],
                ),
                rule(
                    "PUB-MAE",
                    "MAE",
                    "Standard carve-outs for market, industry, law, war, pandemic, rates, cyber, and announcement effects, with disproportionate-effect qualifier.",
                    "Narrowing only with committee approval.",
                    "Escalate omitted market or industry carve-outs.",
                    "Board transaction committee",
                    ["restricted MAE carve-outs", "customer loss carve-out omitted"],
                ),
                rule(
                    "PUB-BREAKFEE",
                    "company break fee",
                    "2.5%-3.5% of equity value.",
                    "Up to 3.75% with go-shop.",
                    "Escalate above 3.75%.",
                    "Board transaction committee",
                    ["break fee above 3.75%", "expense reimbursement uncapped"],
                ),
            ],
        },
        {
            "policy_id": "P-CARVEOUT-OPS-2026",
            "client": "Atlas Industrial Holdings",
            "policy_type": "SELLER_PLAYBOOK",
            "version": "2026.1",
            "effective_date": "2026-03-10",
            "title": "Carve-Out APA Operating Playbook",
            "rules": [
                rule(
                    "CARVE-TSA",
                    "transition services",
                    "TSA baseline 9-12 months for ERP, payroll, finance, regulatory, and IT.",
                    "6 months only if buyer has migration plan and staffed PMO.",
                    "Escalate below 6 months.",
                    "Operations committee",
                    ["TSA below 6 months", "ERP support omitted"],
                ),
                rule(
                    "CARVE-EMPLOYEE",
                    "employee transfer",
                    "Buyer offers employment to all business employees on comparable terms.",
                    "Seller retains only listed excluded employees.",
                    "Escalate if WARN risk stays with seller.",
                    "HR committee",
                    ["WARN retained by seller", "no comparable-benefits covenant"],
                ),
                rule(
                    "CARVE-IP",
                    "IP transition",
                    "Narrow transitional trademark and retained-IP license.",
                    "Trademark phase-out up to 12 months.",
                    "Escalate broad source-code access.",
                    "IP counsel",
                    ["source code access", "open-ended trademark use"],
                ),
                rule(
                    "CARVE-NONCOMPETE",
                    "non-compete",
                    "Limited to divested line and existing geographies.",
                    "3 years maximum.",
                    "Escalate 5-year or affiliate-wide restrictions.",
                    "Employment counsel",
                    ["5-year non-compete", "affiliate-wide scope"],
                ),
                rule(
                    "CARVE-CLOSE",
                    "closing deadline",
                    "75-90 days where consents and TSA schedules remain open.",
                    "60 days with complete consent package.",
                    "Escalate less than 60 days.",
                    "Deal lead",
                    ["closing deadline below 60 days", "TSA unresolved"],
                ),
            ],
        },
        {
            "policy_id": "P-HYBRID-INVEST-2026",
            "client": "Kepler Growth Fund",
            "policy_type": "BUYER_RISK_MEMO",
            "version": "2026.2",
            "effective_date": "2026-05-28",
            "title": "Hybrid Acquisition and Minority Rollover Playbook",
            "rules": [
                rule(
                    "HYB-ESCROW",
                    "escrow",
                    "10% escrow for hybrid control investments.",
                    "12% fallback with identified revenue recognition risk.",
                    "Committee approval above 12%.",
                    "Investment committee",
                    ["escrow above 12%", "tax escrow above 3%"],
                ),
                rule(
                    "HYB-ROLLOVER",
                    "rollover",
                    "Rollover equity issued on same implied valuation as buyer cash.",
                    "Discount only for illiquidity approved by committee.",
                    "Escalate valuation mismatch above 2%.",
                    "Investment committee",
                    ["rollover valuation mismatch", "unapproved founder preference"],
                ),
                rule(
                    "HYB-GOVERNANCE",
                    "governance",
                    "Protective provisions for budget, debt, M&A, and related-party transactions.",
                    "Observer right acceptable for under 15% rollover.",
                    "Escalate vetoes over ordinary course.",
                    "Investment committee",
                    ["founder veto over budget", "deadlock buy-sell omitted"],
                ),
                rule(
                    "HYB-CAP",
                    "indemnity cap",
                    "General cap at escrow amount.",
                    "Fallback 12.5%.",
                    "Committee approval above 12.5%.",
                    "Investment committee",
                    ["cap above 12.5%", "uncapped SaaS revenue reps"],
                ),
            ],
        },
        {
            "policy_id": "P-ROLLOVER-SPA-2026",
            "client": "Solstice Strategic Capital",
            "policy_type": "BUYER_RISK_MEMO",
            "version": "2026.1",
            "effective_date": "2026-05-05",
            "title": "Rollover Stock Purchase Risk Allocation Standard",
            "rules": [
                rule(
                    "ROLL-CASH",
                    "cash and rollover mix",
                    "Cash and rollover allocation must match signed allocation schedule.",
                    "Seller note may offset cash only with written lender consent.",
                    "Escalate any unilateral note offset.",
                    "Credit committee",
                    ["note offset without consent", "rollover schedule mismatch"],
                ),
                rule(
                    "ROLL-NWC",
                    "working capital",
                    "NWC target from agreed peg and true-up at closing.",
                    "Collar permitted up to 0.75% of headline value.",
                    "Escalate collar above 0.75%.",
                    "Finance committee",
                    ["collar above 0.75%", "target based on stale balance sheet"],
                ),
                rule(
                    "ROLL-ESCROW",
                    "escrow",
                    "General escrow 10%; tax escrow 2%-3% if exposure identified.",
                    "Aggregate escrow above 13% requires committee.",
                    "Escalate aggregate above 13%.",
                    "Credit committee",
                    ["aggregate escrow above 13%", "tax exposure uncapped"],
                ),
                rule(
                    "ROLL-CAP",
                    "indemnity cap",
                    "Cap equals general escrow except fundamental and tax reps.",
                    "Fallback 12% of cash consideration.",
                    "Escalate cap based on headline instead of cash.",
                    "Credit committee",
                    ["cap based on headline value", "fundamental reps not capped separately"],
                ),
            ],
        },
        {
            "policy_id": "P-STANDARD-FORM-2026",
            "client": "Aster Legal Standard Forms",
            "policy_type": "STANDARD_FORM",
            "version": "2026.1",
            "effective_date": "2026-01-15",
            "title": "Generic M&A Form Library",
            "rules": [
                rule(
                    "FORM-ESCROW",
                    "escrow",
                    "Generic form uses 10% escrow.",
                    "Must defer to client playbook.",
                    "Template is not authority when client policy differs.",
                    "Drafting lead",
                    ["template conflicts with client instruction"],
                ),
                rule(
                    "FORM-NONCOMPETE",
                    "non-compete",
                    "Generic form has 5-year worldwide restriction.",
                    "Must be narrowed for enforceability and client policy.",
                    "Escalate before use in live draft.",
                    "Employment counsel",
                    ["template imported without tailoring"],
                ),
                rule(
                    "FORM-MAE",
                    "MAE",
                    "Generic private-target MAE language.",
                    "Do not use in public merger without committee policy.",
                    "Escalate public-company transaction mismatch.",
                    "Drafting lead",
                    ["wrong transaction form"],
                ),
            ],
        },
    ]


def required_deals() -> list[dict]:
    return [
        {
            "deal_id": "D-ALDER-447",
            "codename": "Alder Ridge",
            "client": "Northstar Capital Partners",
            "client_side": "BUYER",
            "structure": "STOCK_PURCHASE",
            "status": "draft mark-up pending",
            "target": "Alder Analytics, Inc.",
            "buyer": "NSCP Atlas Buyer, Inc.",
            "seller": "Alder Founder Group",
            "policy_id": "P-BUYER-MIDMARKET-2026",
            "headline_value": 184000000,
            "equity_value": 184000000,
            "industry": "Industrial Software",
            "signing_date": "2026-08-14",
            "closing_deadline": "2026-10-15",
            "economics": {
                "consideration_mix": {
                    "cash_at_close": 172500000,
                    "seller_note": 0,
                    "rollover_equity": 11500000,
                    "earnout": 0,
                },
                "working_capital": {
                    "target": 18600000,
                    "collar": 750000,
                    "mechanic": "Dollar-for-dollar adjustment outside collar.",
                },
                "escrows": {
                    "general_percent": 10.0,
                    "general_amount": 18400000,
                    "tax_percent": 2.5,
                    "tax_amount": 4600000,
                },
                "indemnity_cap_percent": 10.0,
                "basket": {"type": "deductible", "percent": 0.75, "de_minimis": 35000},
                "survival_periods": {"general_reps_months": 18, "tax_reps_months": 72, "fundamental_reps_months": 72},
                "break_fee_percent": None,
            },
            "parties": {
                "buyers": ["NSCP Atlas Buyer, Inc.", "Northstar Capital Partners Fund IV"],
                "sellers": [
                    seller("Alder Founder Trust", "founder seller", 44.2, 81328000),
                    seller("Gannet Ventures II, L.P.", "venture seller", 32.1, 59064000),
                    seller("Alder ESOP Rollover Pool", "employee rollover pool", 23.7, 43608000),
                ],
                "representatives": ["Aster Legal LLP", "Rook Financial Advisors"],
                "committee_members": ["Priya Shah", "Marcus Lee", "Elena Ortiz"],
                "key_employees": ["Mina Calder, founder/CTO", "Owen Petrie, VP Data"],
            },
            "schedules": {
                "cap_table": {
                    "status": "ACTIVE",
                    "as_of": "2026-06-30",
                    "sellers": ["Alder Founder Trust", "Gannet Ventures II, L.P.", "Alder ESOP Rollover Pool"],
                },
                "stale_cap_table": {
                    "status": "STALE",
                    "as_of": "2026-03-31",
                    "note": "Pre-option-exercise summary; superseded by June cap table.",
                },
                "material_contracts": [
                    {
                        "name": "ForgeWorks SaaS MSA",
                        "annual_revenue": 9300000,
                        "consent_required": True,
                        "condition_type": "closing",
                    },
                    {
                        "name": "Municipal Fleet Data License",
                        "annual_revenue": 7100000,
                        "consent_required": True,
                        "condition_type": "closing",
                    },
                    {
                        "name": "Northline Hosting Order",
                        "annual_revenue": 2400000,
                        "consent_required": False,
                        "condition_type": "covenant",
                    },
                ],
                "employment_terms": {
                    "founder_employment": "Two-year employment agreements for Calder and Petrie.",
                    "non_compete": "Draft asks 36 months; client accepts only if scope is target products and current territories.",
                },
                "transition_services": {"required": False, "note": "Standalone SaaS operations."},
                "ip_transition": {
                    "required": True,
                    "note": "Confirm assignment of fleet optimization patents and open-source schedule.",
                },
                "regulatory_status": {
                    "hsr_required": False,
                    "basis": "Antitrust memo says no HSR filing because size-of-person test is not met.",
                    "other_approvals": [],
                },
            },
            "draft_terms": {
                "escrow": "10% general escrow plus 2.5% tax escrow.",
                "nwc": "Target $18.6M, collar +/- $750k.",
                "consents": "ForgeWorks and Municipal Fleet consents are closing conditions.",
                "non_compete": "36 months for founders, narrowed to target products and current territories in latest mark-up.",
                "hsr": "No HSR condition; cooperation covenant only.",
            },
            "client_positions": {
                "preferred": "Preserve current economics, require two material consents, and keep no-HSR conclusion tied to counsel memo.",
                "fallback": "Can accept 36-month founder non-compete only with product and territory limits; no broad affiliate covenant.",
                "escalation": "Escalate if general escrow exceeds 10%, tax escrow exceeds 3%, or either material consent is moved to post-closing covenant.",
            },
            "negotiation_context": {
                "rationale": "Buyer values the fleet analytics dataset and needs customer consents before closing.",
                "batna": "Northstar can redirect to a smaller BoltCo add-on if founders widen restrictive covenants.",
                "ownership_dynamics": "Three seller groups have different rollover preferences.",
                "strategic_notes": "Active cap table is the June version; March version omits ESOP option exercises.",
            },
            "clause_terms": [
                clause_term(
                    "ESCROW",
                    "escrow",
                    "10% general escrow.",
                    "8%-10% general escrow.",
                    "Committee approval above 12%.",
                    "headline value",
                    "Within preferred range.",
                ),
                clause_term(
                    "TAX_ESCROW",
                    "tax escrow",
                    "2.5% separate tax escrow.",
                    "2%-3% where diligence identifies exposure.",
                    "Escalate above 3%.",
                    "headline value",
                    "Within policy if tied to disclosed state tax exposure.",
                ),
                clause_term(
                    "NWC",
                    "working capital",
                    "$18.6M target with +/- $750k collar.",
                    "Trailing 12-month normalized target with modest collar.",
                    "Escalate collar above 1% EV.",
                    "headline value",
                    "Finance schedule supports target.",
                ),
                clause_term(
                    "CONSENTS",
                    "material consents",
                    "ForgeWorks and Municipal Fleet consents as closing conditions.",
                    "Top material consents should be closing conditions.",
                    "Escalate if top-five customer consent omitted.",
                    "revenue concentration",
                    "Matches policy.",
                ),
                clause_term(
                    "HSR",
                    "HSR",
                    "No HSR condition, cooperation covenant only.",
                    "No filing condition unless counsel confirms filing required.",
                    "Escalate unclear size-of-person analysis.",
                    "regulatory memo",
                    "Counsel memo says no filing.",
                ),
                clause_term(
                    "NONCOMPETE",
                    "non-compete",
                    "36 months, target products and current territories.",
                    "24 months preferred; 36-month fallback with founder employment.",
                    "Escalate broad territory or above 36 months.",
                    "founder employment",
                    "Fallback position, no committee if scope remains narrow.",
                ),
                clause_term(
                    "BASKET",
                    "basket",
                    "0.75% deductible basket with $35k de minimis.",
                    "0.75%-1.0% deductible.",
                    "Escalate below 0.5% or tipping.",
                    "headline value",
                    "Within policy.",
                ),
                clause_term(
                    "SURVIVAL",
                    "survival",
                    "18 months general reps; 72 months tax and fundamental.",
                    "18 months general; statute/tax periods for tax.",
                    "Escalate business reps beyond 24 months.",
                    "representations",
                    "Within policy.",
                ),
            ],
        },
        {
            "deal_id": "D-BRASS-219",
            "codename": "Brass Foundry",
            "client": "BrassWorks Holdings",
            "client_side": "SELLER",
            "structure": "ASSET_PURCHASE",
            "status": "buyer draft received",
            "target": "Brass Precision Components Division",
            "buyer": "Vector Machine Group, LLC",
            "seller": "BrassWorks Holdings, Inc.",
            "policy_id": "P-SELLER-APA-2026",
            "headline_value": 236000000,
            "equity_value": 236000000,
            "industry": "Aerospace Components",
            "signing_date": "2026-09-03",
            "closing_deadline": "2026-11-18",
            "economics": {
                "consideration_mix": {
                    "cash_at_close": 236000000,
                    "seller_note": 0,
                    "rollover_equity": 0,
                    "earnout": 0,
                },
                "working_capital": {
                    "target": 32100000,
                    "collar": 1200000,
                    "mechanic": "Buyer draft lets buyer reset target after signing.",
                },
                "escrows": {"general_percent": 14.5, "general_amount": 34220000, "tax_percent": 0, "tax_amount": 0},
                "indemnity_cap_percent": 25.0,
                "basket": {"type": "tipping", "percent": 0.25, "de_minimis": None},
                "survival_periods": {
                    "seller_reps_months": 6,
                    "buyer_covenants_months": 6,
                    "fundamental_reps_months": 60,
                },
                "break_fee_percent": None,
            },
            "parties": {
                "buyers": ["Vector Machine Group, LLC", "Vector Acquisition DebtCo"],
                "sellers": [seller("BrassWorks Holdings, Inc.", "corporate seller", 100.0, 236000000)],
                "representatives": ["Aster Legal LLP", "Mason Bank"],
                "committee_members": ["Nora Kim", "Dale Wexler", "Imani Ford"],
                "key_employees": ["Tom Seiler, plant lead", "Renee Costa, HR transition lead"],
            },
            "schedules": {
                "cap_table": {"status": "ACTIVE", "as_of": "2026-07-15", "sellers": ["BrassWorks Holdings, Inc."]},
                "stale_cap_table": {
                    "status": "STALE",
                    "as_of": "2026-01-31",
                    "note": "Internal segment ledger before debt payoff allocation.",
                },
                "material_contracts": [
                    {
                        "name": "AeroLift Supply Agreement",
                        "annual_revenue": 28800000,
                        "consent_required": True,
                        "condition_type": "closing",
                    },
                    {
                        "name": "Defense Fastener IDIQ",
                        "annual_revenue": 16400000,
                        "consent_required": True,
                        "condition_type": "government notice",
                    },
                    {
                        "name": "Plant ERP Shared Services",
                        "annual_cost": 3700000,
                        "consent_required": False,
                        "condition_type": "TSA",
                    },
                ],
                "employment_terms": {
                    "employee_transfer": "Buyer draft requires all employees to transfer automatically with no comparable-offer covenant.",
                    "WARN": "Seller would retain WARN and severance risk under buyer draft.",
                },
                "transition_services": {
                    "required": True,
                    "status": "missing from buyer draft",
                    "needed_services": ["ERP", "payroll", "quality certifications", "IT helpdesk"],
                },
                "ip_transition": {
                    "required": True,
                    "note": "Buyer draft lacks license-back for retained brass alloy know-how and trademark phase-out.",
                },
                "regulatory_status": {
                    "hsr_required": False,
                    "basis": "Asset sale below reportable threshold after excluded liabilities.",
                    "other_approvals": ["Defense customer novation notice"],
                },
            },
            "draft_terms": {
                "financing_condition": "Buyer obligation conditioned on debt financing and lender diligence completion.",
                "escrow": "14.5% for 24 months.",
                "survival": "Seller reps survive 6 months; buyer assumed-liability covenant also 6 months.",
                "cap_basket": "25% cap, 0.25% tipping basket, no de minimis.",
                "non_compete": "Five-year worldwide non-compete covering affiliates and adjacent metal products.",
                "employee_transfer": "All employees deemed transferred; seller retains WARN and severance if any employee refuses.",
                "tsa": "No TSA exhibit.",
                "ip": "Assignment language only; no transition license-back or trademark phase-out.",
            },
            "client_positions": {
                "preferred": "Strike financing condition, reduce escrow to 7.5%, set cap at escrow, use 1% deductible basket, add TSA and employee offer standard.",
                "fallback": "Escrow may move to 10% if cap equals escrow and financing condition is removed.",
                "escalation": "Any financing condition, escrow over 10%, or missing TSA for shared ERP must go to seller steering committee.",
            },
            "negotiation_context": {
                "rationale": "Division depends on shared BrassWorks systems for at least two quarters after closing.",
                "batna": "Seller has a lower cash bid without financing contingency.",
                "ownership_dynamics": "Parent board wants clean liability exit and no retained employee exposure.",
                "strategic_notes": "Buyer added a generic template non-compete inconsistent with the seller playbook.",
            },
            "clause_terms": [
                clause_term(
                    "FINANCING",
                    "financing condition",
                    "Closing conditioned on buyer debt financing and lender diligence.",
                    "Reject financing conditions.",
                    "Executive approval for any financing condition.",
                    "closing certainty",
                    NEUTRAL_REVIEW_NOTE,
                ),
                clause_term(
                    "ESCROW",
                    "escrow",
                    "14.5% escrow for 24 months.",
                    "5%-7.5%; fallback 10% for identified issues.",
                    "Escalate above 10%.",
                    "headline value",
                    "Excessive escrow.",
                ),
                clause_term(
                    "SURVIVAL",
                    "survival",
                    "6 months for seller reps and buyer assumed-liability covenants.",
                    "Seller reps max 12 months; buyer covenants should survive transition obligations.",
                    "Escalate mismatch with TSA period.",
                    "operating covenants",
                    "Short buyer covenant survival leaves seller with stranded risk.",
                ),
                clause_term(
                    "CAP",
                    "indemnity cap",
                    "25% general indemnity cap.",
                    "Cap at escrow; fallback 10%-12.5%.",
                    "Escalate above 12.5%.",
                    "headline value",
                    "Seller-unfavorable cap.",
                ),
                clause_term(
                    "BASKET",
                    "basket",
                    "0.25% tipping basket; no de minimis.",
                    "1% deductible basket with de minimis.",
                    "Escalate below 0.75% or tipping.",
                    "headline value",
                    "Seller-unfavorable basket.",
                ),
                clause_term(
                    "NONCOMPETE",
                    "non-compete",
                    "5-year worldwide restriction covering affiliates and adjacent metal products.",
                    "3 years max, transferred business only.",
                    "Escalate worldwide or affiliate-wide.",
                    "restricted business",
                    "Overbroad.",
                ),
                clause_term(
                    "EMPLOYEE",
                    "employee transfer",
                    "Automatic transfer; seller keeps WARN and severance exposure.",
                    "Buyer comparable offers and buyer assumes employment liabilities.",
                    "Escalate WARN retained by seller.",
                    "employee census",
                    "Employee-transfer risk.",
                ),
                clause_term(
                    "TSA",
                    "transition services",
                    "No TSA exhibit included.",
                    "TSA required for ERP, payroll, quality, and IT.",
                    "Escalate omitted TSA.",
                    "carve-out operations",
                    "Missing TSA.",
                ),
                clause_term(
                    "IP",
                    "IP transition",
                    "Assignment only; no retained-IP boundaries or trademark phase-out.",
                    "Transition license and retained-IP boundaries required.",
                    "Escalate open-ended or missing licenses.",
                    "IP schedule",
                    "Weak IP transition.",
                ),
            ],
        },
        {
            "deal_id": "D-CYPRESS-735",
            "codename": "Cypress Halo",
            "client": "Helios Health Systems",
            "client_side": "BUYER",
            "structure": "MERGER",
            "status": "committee escalation draft",
            "target": "Cypress BioCloud, Inc.",
            "buyer": "Helios Health Systems, Inc.",
            "seller": "Cypress BioCloud public stockholders",
            "policy_id": "P-PUBLIC-MERGER-COMMITTEE-2026",
            "headline_value": 1180000000,
            "equity_value": 1180000000,
            "industry": "Health Technology",
            "signing_date": "2026-10-02",
            "closing_deadline": "2027-01-15",
            "economics": {
                "consideration_mix": {
                    "cash_at_close": 1180000000,
                    "seller_note": 0,
                    "rollover_equity": 0,
                    "earnout": 0,
                },
                "working_capital": {"target": None, "collar": None, "mechanic": "Public merger, no NWC true-up."},
                "escrows": {"general_percent": 0, "general_amount": 0, "tax_percent": 0, "tax_amount": 0},
                "indemnity_cap_percent": 0,
                "basket": {"type": "none", "percent": 0, "de_minimis": None},
                "survival_periods": {"r_and_w_survival_months": 24, "covenants_months": 24},
                "break_fee_percent": 3.25,
                "reverse_termination_fee_percent": 7.5,
            },
            "parties": {
                "buyers": ["Helios Health Systems, Inc.", "Helios Merger Sub, Inc."],
                "sellers": [seller("Cypress BioCloud public stockholders", "public stockholders", 100.0, 1180000000)],
                "representatives": ["Aster Legal LLP", "Barton & Cove"],
                "committee_members": ["Dr. Elaine Park", "Sanjay Mehta", "Carla Winthrop"],
                "key_employees": ["Dr. Nia Rowe, Chief Science Officer", "Luis Baird, Security Lead"],
            },
            "schedules": {
                "cap_table": {
                    "status": "ACTIVE",
                    "as_of": "2026-07-01",
                    "sellers": ["Public float", "Executive RSU holders", "Index funds"],
                },
                "stale_cap_table": {
                    "status": "STALE",
                    "as_of": "2025-12-31",
                    "note": "Pre-RSU vesting and before follow-on offering.",
                },
                "material_contracts": [
                    {
                        "name": "National Lab Genomics Platform",
                        "annual_revenue": 93000000,
                        "consent_required": False,
                        "condition_type": "notice",
                    },
                    {
                        "name": "Cloud Protected Health Data Addendum",
                        "annual_cost": 42000000,
                        "consent_required": True,
                        "condition_type": "security approval",
                    },
                ],
                "employment_terms": {
                    "retention": "Buyer wants retention for science and security leadership.",
                    "non_compete": "No broad public-company employee non-compete.",
                },
                "transition_services": {"required": False, "note": "Whole-company merger."},
                "ip_transition": {
                    "required": True,
                    "note": "Confirm genomic model ownership and government-funded IP boundaries.",
                },
                "regulatory_status": {
                    "hsr_required": True,
                    "basis": "Equity value exceeds threshold; healthcare data market overlap memo in progress.",
                    "other_approvals": ["State health data regulator notice"],
                },
            },
            "draft_terms": {
                "rtf": "7.5% reverse termination fee payable on regulatory failure and buyer breach.",
                "fiduciary_out": "Target board may change recommendation but cannot terminate for superior proposal after buyer match.",
                "survival": "Target R&W survive 24 months after closing with damages claim covenant.",
                "mae": "MAE excludes pandemic but omits market, industry, cyber incident, customer loss, and law-change carve-outs.",
                "break_fee": "3.25% company break fee.",
            },
            "client_positions": {
                "preferred": "Escalate RTF, restore full fiduciary-out termination right, remove post-closing R&W survival, and use full public-company MAE carve-outs.",
                "fallback": "RTF up to 5.5% only with superior regulatory efforts covenant and committee approval.",
                "escalation": "RTF over 5.5%, blocked fiduciary-out termination, public merger indemnity, and restricted MAE carve-outs are listed as committee review triggers.",
            },
            "negotiation_context": {
                "rationale": "Buyer needs health-data platform but board wants market-standard public merger risk allocation.",
                "batna": "Helios can pursue a private clinical data platform at lower antitrust risk.",
                "ownership_dynamics": "Target has activist pressure and large index-fund holders.",
                "strategic_notes": "Committee charter calls for a benchmark memo when the RTF is outside the stated policy range.",
            },
            "clause_terms": [
                clause_term(
                    "RTF",
                    "reverse termination fee",
                    "7.5% of equity value.",
                    "At or below 5.0%; 5.5% fallback with superior covenant.",
                    "Board approval above 5.5%.",
                    "equity value",
                    NEUTRAL_REVIEW_NOTE,
                ),
                clause_term(
                    "FIDUCIARY",
                    "fiduciary out",
                    "Board may change recommendation but cannot terminate for superior proposal after buyer match.",
                    "Preserve termination right; matching rights max four business days.",
                    "Escalate blocked termination.",
                    "board duties",
                    "Fiduciary-out limitation.",
                ),
                clause_term(
                    "RW_SURVIVAL",
                    "R&W survival",
                    "Target R&W survive 24 months after closing.",
                    "No post-closing survival in public-style merger.",
                    "Escalate any post-closing indemnity.",
                    "public merger form",
                    NEUTRAL_REVIEW_NOTE,
                ),
                clause_term(
                    "MAE",
                    "MAE",
                    "Pandemic carve-out only; omits market, industry, cyber, customer loss, and law-change carve-outs.",
                    "Standard full carve-outs with disproportionate-effect qualifier.",
                    "Escalate restricted MAE carve-outs.",
                    "deal certainty",
                    "Restricted MAE carve-outs.",
                ),
                clause_term(
                    "BREAKFEE",
                    "company break fee",
                    "3.25% of equity value.",
                    "2.5%-3.5% of equity value.",
                    "Escalate above 3.75%.",
                    "equity value",
                    "Within market range.",
                ),
                clause_term(
                    "REGULATORY",
                    "regulatory covenant",
                    "Reasonable best efforts; no divestiture obligation.",
                    "Hell-or-high-water only with board approval.",
                    "Escalate if RTF tied to weak covenant.",
                    "regulatory risk",
                    "Needs committee review with RTF.",
                ),
            ],
        },
        {
            "deal_id": "D-ORBIT-384",
            "codename": "Orbit Forge",
            "client": "Atlas Industrial Holdings",
            "client_side": "SELLER",
            "structure": "CARVE_OUT",
            "status": "redline round two",
            "target": "Orbit Forge Tools Business",
            "buyer": "ForgeLine Acquisition LLC",
            "seller": "Atlas Industrial Holdings, Inc.",
            "policy_id": "P-CARVEOUT-OPS-2026",
            "headline_value": 312000000,
            "equity_value": 312000000,
            "industry": "Industrial Manufacturing",
            "signing_date": "2026-09-19",
            "closing_deadline": "2026-10-31",
            "economics": {
                "consideration_mix": {
                    "cash_at_close": 302000000,
                    "seller_note": 10000000,
                    "rollover_equity": 0,
                    "earnout": 0,
                },
                "working_capital": {
                    "target": 44500000,
                    "collar": 1500000,
                    "mechanic": "Monthly true-up, buyer draft permits inventory reserve reset.",
                },
                "escrows": {"general_percent": 12.5, "general_amount": 39000000, "tax_percent": 0, "tax_amount": 0},
                "indemnity_cap_percent": 12.5,
                "basket": {"type": "deductible", "percent": 0.75, "de_minimis": 75000},
                "survival_periods": {"general_reps_months": 15, "fundamental_reps_months": 72},
                "break_fee_percent": None,
            },
            "parties": {
                "buyers": ["ForgeLine Acquisition LLC"],
                "sellers": [seller("Atlas Industrial Holdings, Inc.", "corporate seller", 100.0, 312000000)],
                "representatives": ["Aster Legal LLP", "Slate Ridge Advisors"],
                "committee_members": ["Sofia Marquez", "Graham Tilton", "Wei Zhang"],
                "key_employees": ["Hannah Pike, plant GM", "Darius Knox, ERP migration lead"],
            },
            "schedules": {
                "cap_table": {
                    "status": "ACTIVE",
                    "as_of": "2026-06-30",
                    "sellers": ["Atlas Industrial Holdings, Inc."],
                },
                "stale_cap_table": {
                    "status": "STALE",
                    "as_of": "2026-02-28",
                    "note": "Segment ledger before inventory reserve adjustment.",
                },
                "material_contracts": [
                    {
                        "name": "Titan Retail Supply Agreement",
                        "annual_revenue": 51000000,
                        "consent_required": True,
                        "condition_type": "closing",
                    },
                    {
                        "name": "ERP Master Services",
                        "annual_cost": 6200000,
                        "consent_required": False,
                        "condition_type": "TSA",
                    },
                    {
                        "name": "Union Maintenance CBA",
                        "annual_cost": 13400000,
                        "consent_required": True,
                        "condition_type": "labor notice",
                    },
                ],
                "employment_terms": {
                    "employee_transfer": "Buyer offers only 70% of business employees; seller retains severance for rejected employees.",
                    "WARN": "Plant headcount shift could trigger WARN if offers are not timely.",
                },
                "transition_services": {
                    "required": True,
                    "draft_duration_months": 3,
                    "required_duration_months": 12,
                    "needed_services": ["ERP", "payroll", "quality records", "IT", "procurement"],
                },
                "ip_transition": {
                    "required": True,
                    "note": "Buyer asks 18-month use of Atlas marks and access to retained tool-design source files.",
                },
                "regulatory_status": {
                    "hsr_required": True,
                    "basis": "Asset value reportable; no substantive overlap.",
                    "other_approvals": ["Union notice", "Titan Retail consent"],
                },
            },
            "draft_terms": {
                "tsa": "90-day TSA limited to accounting and payroll.",
                "employee": "Buyer required to offer jobs to only 70% of employees; seller retains WARN and severance.",
                "ip": "18-month trademark phase-out and broad design-file access.",
                "non_compete": "Five-year restriction on Atlas and affiliates for all industrial hand tools.",
                "escrow": "12.5% general escrow.",
                "closing_deadline": "October 31, 2026, 42 days after signing, while consents and TSA schedules remain open.",
            },
            "client_positions": {
                "preferred": "Extend TSA to 12 months, require comparable offers to business employees, narrow IP/trademark transition, and move closing deadline to at least 75 days.",
                "fallback": "TSA can be 9 months if buyer funds dedicated migration team.",
                "escalation": "TSA below 6 months, 5-year non-compete, or closing deadline below 60 days is listed for operations committee review.",
            },
            "negotiation_context": {
                "rationale": "The tool business is not standalone and needs Atlas systems after closing.",
                "batna": "Seller can pause process until buyer accepts more complete operating schedule.",
                "ownership_dynamics": "Atlas board prioritizes operational separation over headline price.",
                "strategic_notes": "Current deadline conflicts with consent calendar and TSA drafting status.",
            },
            "clause_terms": [
                clause_term(
                    "TSA",
                    "transition services",
                    "90 days, accounting and payroll only.",
                    "9-12 months for ERP, payroll, finance, regulatory, and IT.",
                    "Escalate below 6 months.",
                    "operating dependency",
                    "TSA deviation.",
                ),
                clause_term(
                    "EMPLOYEE",
                    "employee transfer",
                    "Buyer offers to 70% of business employees; seller retains WARN.",
                    "Comparable offers to all business employees; buyer assumes employment liabilities.",
                    "Escalate WARN retained by seller.",
                    "employee census",
                    "Employee risk.",
                ),
                clause_term(
                    "IP",
                    "IP transition",
                    "18-month trademark phase-out and broad design-file access.",
                    "Narrow transition license; trademark phase-out up to 12 months.",
                    "Escalate source-code or open-ended access.",
                    "retained IP",
                    "IP transition deviation.",
                ),
                clause_term(
                    "NONCOMPETE",
                    "non-compete",
                    "5-year restriction on Atlas and affiliates for all industrial hand tools.",
                    "3 years max, divested line and existing geographies.",
                    "Escalate 5-year or affiliate-wide.",
                    "restricted business",
                    "Overbroad non-compete.",
                ),
                clause_term(
                    "ESCROW",
                    "escrow",
                    "12.5% general escrow.",
                    "Seller carve-out target 10% or less.",
                    "Escalate above 10%.",
                    "headline value",
                    "Escrow deviation.",
                ),
                clause_term(
                    "CLOSE",
                    "closing deadline",
                    "42 days after signing.",
                    "75-90 days where consents and TSA schedules remain open.",
                    "Escalate below 60 days.",
                    "consent and TSA timeline",
                    "Closing deadline deviation.",
                ),
            ],
        },
        {
            "deal_id": "D-HARBOR-562",
            "codename": "Harbor Lantern",
            "client": "Northstar Capital Partners",
            "client_side": "BUYER",
            "structure": "STOCK_PURCHASE",
            "status": "first draft requested",
            "target": "HarborGrid Security, Inc.",
            "buyer": "NSCP Harbor Buyer, Inc.",
            "seller": "HarborGrid Seller Group",
            "policy_id": "P-BUYER-MIDMARKET-2026",
            "headline_value": 198500000,
            "equity_value": 198500000,
            "industry": "Cybersecurity",
            "signing_date": "2026-08-28",
            "closing_deadline": "2026-11-05",
            "economics": {
                "consideration_mix": {
                    "cash_at_close": 157000000,
                    "seller_note": 18500000,
                    "rollover_equity": 15000000,
                    "earnout": 8000000,
                },
                "working_capital": {
                    "target": 21400000,
                    "collar": 900000,
                    "mechanic": "Dollar-for-dollar outside collar; cash-free/debt-free.",
                },
                "escrows": {
                    "general_percent": 10.0,
                    "general_amount": 19850000,
                    "tax_percent": 2.0,
                    "tax_amount": 3970000,
                },
                "indemnity_cap_percent": 10.0,
                "basket": {"type": "deductible", "percent": 0.75, "de_minimis": 50000},
                "survival_periods": {"general_reps_months": 18, "tax_reps_months": 72, "fundamental_reps_months": 72},
                "break_fee_percent": None,
            },
            "parties": {
                "buyers": ["NSCP Harbor Buyer, Inc."],
                "sellers": [
                    seller("HarborGrid Founders LLC", "founder seller", 51.0, 101235000),
                    seller("Tern Cyber Fund I", "fund seller", 31.0, 61535000),
                    seller("Management Option Sellers", "management", 18.0, 35730000),
                ],
                "representatives": ["Aster Legal LLP", "Hale Security Advisors"],
                "committee_members": ["Priya Shah", "Lena Brook", "Omar Velez"],
                "key_employees": ["Ira Kent, founder CEO", "Sasha Ren, CISO"],
            },
            "schedules": {
                "cap_table": {
                    "status": "ACTIVE",
                    "as_of": "2026-07-10",
                    "sellers": ["HarborGrid Founders LLC", "Tern Cyber Fund I", "Management Option Sellers"],
                },
                "stale_cap_table": {
                    "status": "STALE",
                    "as_of": "2026-04-30",
                    "note": "Before option cancellation and rollover election.",
                },
                "material_contracts": [
                    {
                        "name": "Federal SOC Platform Order",
                        "annual_revenue": 33500000,
                        "consent_required": True,
                        "condition_type": "closing",
                    },
                    {
                        "name": "BlueBank MDR Agreement",
                        "annual_revenue": 11600000,
                        "consent_required": True,
                        "condition_type": "closing",
                    },
                    {
                        "name": "GovCloud Hosting Addendum",
                        "annual_cost": 5200000,
                        "consent_required": False,
                        "condition_type": "post-closing notice",
                    },
                ],
                "employment_terms": {
                    "founder_employment": "Founder CEO and CISO retention required.",
                    "non_compete": "24 months, cybersecurity threat detection only.",
                },
                "transition_services": {
                    "required": False,
                    "note": "Standalone systems; limited post-closing customer notice support.",
                },
                "ip_transition": {"required": True, "note": "Open-source audit and FedRAMP package assignment."},
                "regulatory_status": {
                    "hsr_required": False,
                    "basis": "Current regulatory analysis states no HSR filing is required because reportable thresholds are not met after debt adjustments.",
                    "other_approvals": ["Federal customer novation consent"],
                },
            },
            "draft_terms": {
                "first_draft_instruction": "Prepare buyer first draft with consideration split and seller allocation schedule.",
                "seller_allocations": "Cash, note, rollover, and earnout allocated across three seller groups per active cap table.",
                "escrow_cap_basket": "10% escrow/cap, 0.75% deductible basket, $50k de minimis.",
                "consents": "Federal SOC Platform and BlueBank consents as closing conditions.",
                "hsr": "Do not include HSR filing condition; include no-HSR risk memo override facts.",
            },
            "client_positions": {
                "preferred": "Use buyer form, align cap with escrow, include material consents, and include no-HSR memo facts.",
                "fallback": "Earnout covenant can be objective revenue-based if seller asks for operating covenant.",
                "escalation": "Escalate if seller asks to remove federal customer consent or add financing condition.",
            },
            "negotiation_context": {
                "rationale": "Buyer wants a clean first draft that captures cyber and federal customer risks.",
                "batna": "Northstar has exclusivity but can walk if federal customer consent is not a condition.",
                "ownership_dynamics": "Founders prefer rollover, fund prefers cash at close.",
                "strategic_notes": "Deal-specific regulatory instructions supersede generic HSR template language.",
            },
            "clause_terms": [
                clause_term(
                    "CONSIDERATION",
                    "consideration mix",
                    "Cash $157M, seller note $18.5M, rollover $15M, earnout $8M.",
                    "Allocation must follow active cap table and signed instructions.",
                    "Escalate allocation mismatch.",
                    "headline value",
                    "First-draft economics.",
                ),
                clause_term(
                    "ESCROW",
                    "escrow",
                    "10% general escrow plus 2% tax escrow.",
                    "8%-10% general; 2%-3% tax if exposure identified.",
                    "Escalate general above 12% or tax above 3%.",
                    "headline value",
                    "Within policy.",
                ),
                clause_term(
                    "CAP",
                    "indemnity cap",
                    "Cap equals 10% general escrow.",
                    "General cap at escrow amount.",
                    "Escalate above 12.5%.",
                    "headline value",
                    "Within policy.",
                ),
                clause_term(
                    "BASKET",
                    "basket",
                    "0.75% deductible; $50k de minimis.",
                    "0.75%-1.0% deductible.",
                    "Escalate below 0.5% or tipping.",
                    "headline value",
                    "Within policy.",
                ),
                clause_term(
                    "CONSENTS",
                    "material consents",
                    "Federal SOC Platform and BlueBank as closing conditions.",
                    "Top material consents should be closing conditions.",
                    "Escalate if top customer consent omitted.",
                    "revenue concentration",
                    "Required.",
                ),
                clause_term(
                    "HSR",
                    "HSR",
                    "No filing condition; include cooperation covenant and regulatory memo facts.",
                    "No filing condition unless thresholds met.",
                    "Escalate unclear counsel memo.",
                    "regulatory memo",
                    NEUTRAL_REVIEW_NOTE,
                ),
            ],
        },
        {
            "deal_id": "D-LUMEN-908",
            "codename": "Lumen Vale",
            "client": "Northstar Capital Partners",
            "client_side": "BUYER",
            "structure": "STOCK_PURCHASE",
            "status": "seller comments expected",
            "target": "Lumen Robotics, Inc.",
            "buyer": "NSCP Lumen Buyer, Inc.",
            "seller": "Lumen Robotics Securityholders",
            "policy_id": "P-BUYER-MIDMARKET-2026",
            "headline_value": 257500000,
            "equity_value": 257500000,
            "industry": "Automation",
            "signing_date": "2026-09-12",
            "closing_deadline": "2026-12-01",
            "economics": {
                "consideration_mix": {
                    "cash_at_close": 232500000,
                    "seller_note": 0,
                    "rollover_equity": 25000000,
                    "earnout": 0,
                },
                "working_capital": {
                    "target": 27800000,
                    "collar": 1000000,
                    "mechanic": "True-up against active July balance sheet.",
                },
                "escrows": {
                    "general_percent": 10.0,
                    "general_amount": 25750000,
                    "tax_percent": 2.5,
                    "tax_amount": 6437500,
                },
                "indemnity_cap_percent": 10.0,
                "basket": {"type": "deductible", "percent": 0.75, "de_minimis": 60000},
                "survival_periods": {"general_reps_months": 18, "tax_reps_months": 72, "fundamental_reps_months": 72},
                "break_fee_percent": None,
            },
            "parties": {
                "buyers": ["NSCP Lumen Buyer, Inc."],
                "sellers": [
                    seller("Lumen Founder Holdings", "founder seller", 39.5, 101712500),
                    seller("BrightPath Ventures III", "venture seller", 34.0, 87550000),
                    seller("Lumen Management Pool", "management", 26.5, 68237500),
                ],
                "representatives": ["Aster Legal LLP", "Kelvin Robotics Advisors"],
                "committee_members": ["Priya Shah", "Marcus Lee", "Ari Chen"],
                "key_employees": ["Dani Rowe, founder", "Victor Hsu, VP Controls"],
            },
            "schedules": {
                "cap_table": {
                    "status": "ACTIVE",
                    "as_of": "2026-07-31",
                    "sellers": ["Lumen Founder Holdings", "BrightPath Ventures III", "Lumen Management Pool"],
                    "note": "This active cap table supersedes the February export.",
                },
                "stale_cap_table": {
                    "status": "STALE",
                    "as_of": "2026-02-28",
                    "note": "Does not reflect option exercise and Bridge SAFE conversion.",
                },
                "material_contracts": [
                    {
                        "name": "OmniAuto Robotics Supply",
                        "annual_revenue": 39400000,
                        "consent_required": True,
                        "condition_type": "closing",
                    },
                    {
                        "name": "KiteRail Deployment Agreement",
                        "annual_revenue": 18500000,
                        "consent_required": True,
                        "condition_type": "closing",
                    },
                    {
                        "name": "SensorForge License",
                        "annual_cost": 6100000,
                        "consent_required": False,
                        "condition_type": "notice",
                    },
                ],
                "employment_terms": {
                    "founder_employment": "Founder and VP Controls sign retention agreements.",
                    "non_compete": "Draft 30 months, industrial robotic arms and warehouse controls only.",
                },
                "transition_services": {"required": False, "note": "Standalone operations with hosted ERP."},
                "ip_transition": {
                    "required": True,
                    "note": "Confirm assignment of controls patents and university license consent.",
                },
                "regulatory_status": {
                    "hsr_required": True,
                    "basis": "Antitrust memo indicates HSR filing required; no substantive issue expected.",
                    "other_approvals": ["University license consent"],
                },
            },
            "draft_terms": {
                "cap_table_priority": "Use July 31 active cap table; February cap table is stale.",
                "non_compete": "30 months, industrial robotic arms and warehouse controls only.",
                "consents": "OmniAuto, KiteRail, and university license consent are closing conditions.",
                "escrow": "10% general plus 2.5% tax.",
            },
            "client_positions": {
                "preferred": "Use active cap table, include non-compete with narrow product scope, require named consents as closing conditions.",
                "fallback": "Can accept post-closing notice for SensorForge only.",
                "escalation": "Escalate if seller relies on February cap table or moves OmniAuto/KiteRail consent post-close.",
            },
            "negotiation_context": {
                "rationale": "Buyer needs seller allocation accuracy and customer consents before closing.",
                "batna": "Northstar can delay signing until cap table audit is complete.",
                "ownership_dynamics": "SAFE conversion diluted founders and shifted proceeds to venture seller.",
                "strategic_notes": "Active cap table outranks stale export for all allocation math.",
            },
            "clause_terms": [
                clause_term(
                    "CAPTABLE",
                    "seller allocation",
                    "Allocations based on July 31 active cap table.",
                    "Latest active cap table controls.",
                    "Escalate stale allocation schedule.",
                    "headline value",
                    "Active cap table outranks stale.",
                ),
                clause_term(
                    "ESCROW",
                    "escrow",
                    "10% general escrow plus 2.5% tax escrow.",
                    "8%-10% general; 2%-3% tax if exposure identified.",
                    "Escalate above thresholds.",
                    "headline value",
                    "Within policy.",
                ),
                clause_term(
                    "NONCOMPETE",
                    "non-compete",
                    "30 months, industrial robotic arms and warehouse controls only.",
                    "24 months preferred; 36-month fallback with founder employment.",
                    "Escalate broad territory or above 36 months.",
                    "founder employment",
                    NEUTRAL_REVIEW_NOTE,
                ),
                clause_term(
                    "CONSENTS",
                    "material consents",
                    "OmniAuto, KiteRail, and university license consent as closing conditions.",
                    "Specified material consents as closing conditions.",
                    "Escalate if top customer consent omitted.",
                    "revenue concentration",
                    "Required conditions.",
                ),
                clause_term(
                    "HSR",
                    "HSR",
                    "HSR filing covenant included.",
                    "Include if antitrust counsel confirms thresholds met.",
                    "Escalate unclear memo.",
                    "regulatory memo",
                    "Counsel memo supports filing.",
                ),
            ],
        },
        {
            "deal_id": "D-QUARTZ-311",
            "codename": "Quartz Harbor",
            "client": "Meridian Seller Desk",
            "client_side": "SELLER",
            "structure": "ASSET_PURCHASE",
            "status": "seller issues list",
            "target": "Quartz Payments Processing Assets",
            "buyer": "Pinnacle BankTech LLC",
            "seller": "Quartz Commerce Group",
            "policy_id": "P-SELLER-APA-2026",
            "headline_value": 286000000,
            "equity_value": 286000000,
            "industry": "FinTech",
            "signing_date": "2026-09-24",
            "closing_deadline": "2026-12-20",
            "economics": {
                "consideration_mix": {
                    "cash_at_close": 276000000,
                    "seller_note": 10000000,
                    "rollover_equity": 0,
                    "earnout": 0,
                },
                "working_capital": {
                    "target": 38200000,
                    "collar": 950000,
                    "mechanic": "Buyer draft excludes deferred revenue from target.",
                },
                "escrows": {"general_percent": 13.0, "general_amount": 37180000, "tax_percent": 0, "tax_amount": 0},
                "indemnity_cap_percent": 20.0,
                "basket": {"type": "tipping", "percent": 0.5, "de_minimis": None},
                "survival_periods": {
                    "seller_reps_months": 24,
                    "buyer_covenants_months": 9,
                    "fundamental_reps_months": 72,
                },
                "break_fee_percent": None,
            },
            "parties": {
                "buyers": ["Pinnacle BankTech LLC"],
                "sellers": [seller("Quartz Commerce Group", "corporate seller", 100.0, 286000000)],
                "representatives": ["Aster Legal LLP", "Quill Bankers"],
                "committee_members": ["Nora Kim", "Imani Ford", "Alex Yu"],
                "key_employees": ["Marta Glass, payments ops", "Colin Drew, compliance lead"],
            },
            "schedules": {
                "cap_table": {"status": "ACTIVE", "as_of": "2026-07-20", "sellers": ["Quartz Commerce Group"]},
                "stale_cap_table": {
                    "status": "STALE",
                    "as_of": "2026-03-31",
                    "note": "Before processor reserve release.",
                },
                "material_contracts": [
                    {
                        "name": "BankNet Sponsorship Agreement",
                        "annual_revenue": 64000000,
                        "consent_required": True,
                        "condition_type": "closing",
                    },
                    {
                        "name": "CardOps Processor MSA",
                        "annual_cost": 21900000,
                        "consent_required": True,
                        "condition_type": "closing",
                    },
                    {
                        "name": "Payments Compliance Shared Service",
                        "annual_cost": 5100000,
                        "consent_required": False,
                        "condition_type": "TSA",
                    },
                ],
                "employment_terms": {
                    "employee_transfer": "Buyer has no comparable-benefits covenant and leaves WARN with seller.",
                    "WARN": "Payment ops reduction may trigger WARN.",
                },
                "transition_services": {
                    "required": True,
                    "status": "one-page placeholder",
                    "needed_services": [
                        "processor migration",
                        "KYC operations",
                        "chargeback support",
                        "compliance reporting",
                    ],
                },
                "ip_transition": {
                    "required": True,
                    "note": "Buyer asks perpetual use of Quartz marks and broad source repository access.",
                },
                "regulatory_status": {
                    "hsr_required": True,
                    "basis": "Reportable transaction; fintech compliance approvals separate.",
                    "other_approvals": ["Bank sponsor consent", "Processor consent"],
                },
            },
            "draft_terms": {
                "financing_condition": "Debt financing condition remains in section 8.2.",
                "escrow": "13% escrow for 24 months.",
                "survival_cap_basket": "24-month survival, 20% cap, 0.5% tipping basket, no de minimis.",
                "employee_tsa_warn": "No comparable offer covenant; seller keeps WARN; TSA placeholder only.",
                "mae": "MAE includes loss of any bank sponsor without materiality qualifier.",
                "ip": "Perpetual mark use and broad source repository access.",
            },
            "client_positions": {
                "preferred": "Reject financing condition, reduce escrow to 7.5%-10%, cap at escrow, 1% deductible basket with de minimis, add TSA and buyer employee obligations.",
                "fallback": "Can accept 10% escrow if cap equals escrow and de minimis is restored.",
                "escalation": "Financing conditions, escrow above 10%, retained WARN burden, and perpetual IP use are listed as committee review triggers.",
            },
            "negotiation_context": {
                "rationale": "Seller needs clean exit from payment operations and no retained employee or processor migration risk.",
                "batna": "Alternative processor buyer has less headline price but no financing condition.",
                "ownership_dynamics": "Parent board is focused on risk-adjusted proceeds.",
                "strategic_notes": "Buyer draft used generic template provisions inconsistent with seller APA playbook.",
            },
            "clause_terms": [
                clause_term(
                    "FINANCING",
                    "financing condition",
                    "Debt financing condition remains in section 8.2.",
                    "Reject financing conditions.",
                    "Executive approval for any financing condition.",
                    "closing certainty",
                    NEUTRAL_REVIEW_NOTE,
                ),
                clause_term(
                    "ESCROW",
                    "escrow",
                    "13% escrow for 24 months.",
                    "5%-7.5%; fallback 10%.",
                    "Escalate above 10%.",
                    "headline value",
                    "Excessive escrow.",
                ),
                clause_term(
                    "SURVIVAL",
                    "survival",
                    "Seller reps survive 24 months.",
                    "12 months or less for general seller reps.",
                    "Escalate above 12 months.",
                    "representations",
                    "Long survival.",
                ),
                clause_term(
                    "CAP",
                    "indemnity cap",
                    "20% general cap.",
                    "Cap at escrow; fallback 10%-12.5%.",
                    "Escalate above 12.5%.",
                    "headline value",
                    "Seller-unfavorable cap.",
                ),
                clause_term(
                    "BASKET",
                    "basket",
                    "0.5% tipping basket; no de minimis.",
                    "1% deductible with de minimis.",
                    "Escalate below 0.75% or tipping.",
                    "headline value",
                    "Seller-unfavorable basket and de minimis omission.",
                ),
                clause_term(
                    "EMPLOYEE",
                    "employee transfer",
                    "No comparable-benefits covenant; seller keeps WARN.",
                    "Buyer comparable offers and buyer assumes employment liabilities.",
                    "Escalate WARN retained by seller.",
                    "employee census",
                    "Employee/WARN risk.",
                ),
                clause_term(
                    "TSA",
                    "transition services",
                    "One-page placeholder only.",
                    "Detailed TSA for payment migration, KYC, chargebacks, and compliance.",
                    "Escalate omitted TSA.",
                    "carve-out operations",
                    "Missing TSA detail.",
                ),
                clause_term(
                    "MAE",
                    "MAE",
                    "Loss of any bank sponsor is MAE without materiality qualifier.",
                    "MAE should include materiality and buyer control exceptions.",
                    "Escalate sponsor-loss trigger without qualifier.",
                    "deal certainty",
                    "Buyer-favorable MAE.",
                ),
                clause_term(
                    "IP",
                    "IP transition",
                    "Perpetual use of Quartz marks and broad source repository access.",
                    "Transition license and retained-IP boundaries required.",
                    "Escalate open-ended IP use.",
                    "IP schedule",
                    "Weak IP transition.",
                ),
            ],
        },
        {
            "deal_id": "D-NOVA-674",
            "codename": "Nova Signal",
            "client": "Helios Health Systems",
            "client_side": "BUYER",
            "structure": "MERGER",
            "status": "board package in preparation",
            "target": "Nova Diagnostics, Inc.",
            "buyer": "Helios Health Systems, Inc.",
            "seller": "Nova Diagnostics public stockholders",
            "policy_id": "P-PUBLIC-MERGER-COMMITTEE-2026",
            "headline_value": 860000000,
            "equity_value": 860000000,
            "industry": "Diagnostics",
            "signing_date": "2026-10-18",
            "closing_deadline": "2027-02-01",
            "economics": {
                "consideration_mix": {
                    "cash_at_close": 860000000,
                    "seller_note": 0,
                    "rollover_equity": 0,
                    "earnout": 0,
                },
                "working_capital": {"target": None, "collar": None, "mechanic": "Public merger, no NWC true-up."},
                "escrows": {"general_percent": 0, "general_amount": 0, "tax_percent": 0, "tax_amount": 0},
                "indemnity_cap_percent": 0,
                "basket": {"type": "none", "percent": 0, "de_minimis": None},
                "survival_periods": {"r_and_w_survival_months": 18, "covenants_months": 24},
                "break_fee_percent": 3.6,
                "reverse_termination_fee_percent": 6.25,
            },
            "parties": {
                "buyers": ["Helios Health Systems, Inc.", "Nova Merger Sub, Inc."],
                "sellers": [seller("Nova Diagnostics public stockholders", "public stockholders", 100.0, 860000000)],
                "representatives": ["Aster Legal LLP", "Barton & Cove"],
                "committee_members": ["Dr. Elaine Park", "Carla Winthrop", "Mateo Silva"],
                "key_employees": ["Jan Amos, Chief Medical Officer", "Rina Patel, Regulatory Lead"],
            },
            "schedules": {
                "cap_table": {
                    "status": "ACTIVE",
                    "as_of": "2026-07-05",
                    "sellers": ["Public float", "Founder block", "Healthcare index funds"],
                },
                "stale_cap_table": {"status": "STALE", "as_of": "2025-12-31", "note": "Pre-founder secondary sale."},
                "material_contracts": [
                    {
                        "name": "MedLab Channel Agreement",
                        "annual_revenue": 124000000,
                        "consent_required": False,
                        "condition_type": "notice",
                    },
                    {
                        "name": "FDA Assay Collaboration",
                        "annual_revenue": 32000000,
                        "consent_required": True,
                        "condition_type": "agency notice",
                    },
                ],
                "employment_terms": {
                    "retention": "Key scientific employees have RSU acceleration concerns.",
                    "non_compete": "No broad employee non-compete.",
                },
                "transition_services": {"required": False, "note": "Whole-company merger."},
                "ip_transition": {"required": True, "note": "Diagnostic assay IP chain-of-title review pending."},
                "regulatory_status": {
                    "hsr_required": True,
                    "basis": "Reportable healthcare merger; regulatory risk moderate.",
                    "other_approvals": ["FDA collaboration notice"],
                },
            },
            "draft_terms": {
                "rtf": "6.25% RTF, payable for regulatory failure even absent buyer breach.",
                "fiduciary_out": "Superior proposal termination right blocked during six-business-day match period.",
                "survival": "Target R&W survive 18 months post-closing.",
                "mae": "MAE omits industry, reimbursement, cyber, and pandemic carve-outs; no disproportionate-effect qualifier.",
                "stockholder_context": "Founder block supports deal but activists argue fiduciary out is too narrow.",
            },
            "client_positions": {
                "preferred": "Reduce RTF to 5%, preserve fiduciary-out termination, remove R&W survival, add full MAE carve-outs.",
                "fallback": "Committee may approve 5.5% RTF with tighter regulatory covenant and market support.",
                "escalation": "RTF above 5.5%, blocked termination right, survival exposure, and restricted MAE carve-outs are listed as committee review triggers.",
            },
            "negotiation_context": {
                "rationale": "Strategic diagnostics expansion, but stockholder litigation risk is high.",
                "batna": "Helios can acquire an assay lab with lower public-company process risk.",
                "ownership_dynamics": "Founder block supports sale; activists may challenge deal protections.",
                "strategic_notes": "Benchmark set covers 2024-2026 public healthcare mergers and excludes stale 2019 sponsor deals.",
            },
            "clause_terms": [
                clause_term(
                    "RTF",
                    "reverse termination fee",
                    "6.25% of equity value, payable on regulatory failure absent buyer breach.",
                    "At or below 5.0%; 5.5% fallback with superior covenant.",
                    "Board approval above 5.5%.",
                    "equity value",
                    NEUTRAL_REVIEW_NOTE,
                ),
                clause_term(
                    "FIDUCIARY",
                    "fiduciary out",
                    "Termination blocked during six-business-day match period.",
                    "Termination right preserved; matching max four business days.",
                    "Escalate blocked termination or long match.",
                    "board duties",
                    "Fiduciary-out issue.",
                ),
                clause_term(
                    "RW_SURVIVAL",
                    "R&W survival",
                    "Target R&W survive 18 months post-closing.",
                    "No post-closing survival in public merger.",
                    "Escalate any survival exposure.",
                    "public merger form",
                    "Survival exposure.",
                ),
                clause_term(
                    "MAE",
                    "MAE",
                    "Omits industry, reimbursement, cyber, and pandemic carve-outs.",
                    "Full public-company carve-outs with disproportionate-effect qualifier.",
                    "Escalate restricted carve-outs.",
                    "deal certainty",
                    "Restricted MAE carve-outs.",
                ),
                clause_term(
                    "BREAKFEE",
                    "company break fee",
                    "3.6% of equity value.",
                    "2.5%-3.5%; up to 3.75% with go-shop.",
                    "Escalate above 3.75%.",
                    "equity value",
                    "Near high end of the documented fallback range.",
                ),
            ],
        },
        {
            "deal_id": "D-KEPLER-155",
            "codename": "Kepler Stone",
            "client": "Kepler Growth Fund",
            "client_side": "BUYER",
            "structure": "STOCK_PURCHASE",
            "status": "hybrid review",
            "target": "Kepler Metrics, Inc.",
            "buyer": "KGF Control Buyer, Inc.",
            "seller": "Kepler Metrics Securityholders",
            "policy_id": "P-HYBRID-INVEST-2026",
            "headline_value": 146000000,
            "equity_value": 146000000,
            "industry": "SaaS Analytics",
            "signing_date": "2026-08-30",
            "closing_deadline": "2026-10-30",
            "economics": {
                "consideration_mix": {
                    "cash_at_close": 106000000,
                    "seller_note": 0,
                    "rollover_equity": 40000000,
                    "earnout": 0,
                },
                "working_capital": {
                    "target": 14200000,
                    "collar": 500000,
                    "mechanic": "Dollar-for-dollar outside collar.",
                },
                "escrows": {
                    "general_percent": 12.0,
                    "general_amount": 17520000,
                    "tax_percent": 2.0,
                    "tax_amount": 2920000,
                },
                "indemnity_cap_percent": 15.0,
                "basket": {"type": "deductible", "percent": 0.75, "de_minimis": 30000},
                "survival_periods": {"general_reps_months": 18, "tax_reps_months": 72, "fundamental_reps_months": 72},
                "break_fee_percent": None,
            },
            "parties": {
                "buyers": ["KGF Control Buyer, Inc."],
                "sellers": [
                    seller("Kepler Founder LLC", "founder seller", 48.0, 70080000),
                    seller("MetricSeed Fund II", "fund seller", 37.0, 54020000),
                    seller("Kepler Optionholders", "management", 15.0, 21900000),
                ],
                "representatives": ["Aster Legal LLP", "North Channel Advisors"],
                "committee_members": ["Ruth Hall", "Devin Cho", "Mika Stone"],
                "key_employees": ["Neal Hart, founder", "Julia Park, CFO"],
            },
            "schedules": {
                "cap_table": {
                    "status": "ACTIVE",
                    "as_of": "2026-07-18",
                    "sellers": ["Kepler Founder LLC", "MetricSeed Fund II", "Kepler Optionholders"],
                },
                "stale_cap_table": {
                    "status": "STALE",
                    "as_of": "2026-05-01",
                    "note": "Before option cash-out and rollover election.",
                },
                "material_contracts": [
                    {
                        "name": "InsightCloud Enterprise Agreement",
                        "annual_revenue": 17600000,
                        "consent_required": True,
                        "condition_type": "closing",
                    },
                    {
                        "name": "RetailData Feed License",
                        "annual_cost": 2800000,
                        "consent_required": False,
                        "condition_type": "notice",
                    },
                ],
                "employment_terms": {
                    "founder_employment": "Founder remains CEO for 24 months.",
                    "non_compete": "36 months limited to SaaS analytics.",
                },
                "transition_services": {"required": False, "note": "Standalone SaaS."},
                "ip_transition": {"required": True, "note": "Confirm AI model training data permissions."},
                "regulatory_status": {
                    "hsr_required": False,
                    "basis": "No HSR filing under antitrust memo.",
                    "other_approvals": [],
                },
            },
            "draft_terms": {
                "escrow": "12% escrow tied to revenue recognition diligence; compare against the documented fallback authority.",
                "rollover": "Rollover equity issued at 3.5% lower implied valuation than cash consideration.",
                "cap": "15% general cap.",
                "governance": "Founder veto over annual budget and debt above $1M.",
                "tax_escrow": "2% separate tax escrow.",
            },
            "client_positions": {
                "preferred": "Accept 12% escrow as fallback due diligence risk, keep tax escrow, but escalate rollover valuation mismatch, 15% cap, and founder vetoes.",
                "fallback": "Cap may be 12.5%; rollover valuation mismatch up to 2% with committee approval.",
                "escalation": "Rollover discount above 2%, cap above 12.5%, and founder ordinary-course veto are listed as investment committee review triggers.",
            },
            "negotiation_context": {
                "rationale": "Buyer wants control investment but founders retain meaningful rollover stake.",
                "batna": "Kepler can lower headline price instead of accepting mismatched rollover rights.",
                "ownership_dynamics": "Founder wants governance protection; fund sellers prefer cash certainty.",
                "strategic_notes": "Some terms have documented fallback authority; compare each term against the policy threshold before routing.",
            },
            "clause_terms": [
                clause_term(
                    "ESCROW",
                    "escrow",
                    "12% escrow due revenue recognition diligence.",
                    "10% preferred; 12% fallback with identified revenue risk.",
                    "Committee approval above 12%.",
                    "headline value",
                    NEUTRAL_REVIEW_NOTE,
                ),
                clause_term(
                    "TAX_ESCROW",
                    "tax escrow",
                    "2% separate tax escrow.",
                    "2%-3% if exposure identified.",
                    "Escalate above 3%.",
                    "headline value",
                    "Within policy.",
                ),
                clause_term(
                    "ROLLOVER",
                    "rollover valuation",
                    "Rollover equity issued at 3.5% lower implied valuation than cash.",
                    "Same implied valuation; mismatch above 2% escalates.",
                    "Escalate mismatch above 2%.",
                    "cash consideration and rollover schedule",
                    NEUTRAL_REVIEW_NOTE,
                ),
                clause_term(
                    "CAP",
                    "indemnity cap",
                    "15% general cap.",
                    "Cap at escrow; fallback 12.5%.",
                    "Committee approval above 12.5%.",
                    "headline value",
                    NEUTRAL_REVIEW_NOTE,
                ),
                clause_term(
                    "GOVERNANCE",
                    "governance",
                    "Founder veto over annual budget and debt above $1M.",
                    "Protective provisions allowed; ordinary-course vetoes escalate.",
                    "Escalate founder veto over budget.",
                    "governance rights",
                    NEUTRAL_REVIEW_NOTE,
                ),
                clause_term(
                    "NONCOMPETE",
                    "non-compete",
                    "36 months limited to SaaS analytics.",
                    "36-month fallback with founder employment.",
                    "Escalate broader scope or above 36 months.",
                    "founder employment",
                    NEUTRAL_REVIEW_NOTE,
                ),
            ],
        },
        {
            "deal_id": "D-SOLSTICE-820",
            "codename": "Solstice Field",
            "client": "Solstice Strategic Capital",
            "client_side": "BUYER",
            "structure": "ROLLOVER_STOCK_PURCHASE",
            "status": "final issues matrix",
            "target": "Solstice Field Services, Inc.",
            "buyer": "SSC Field Buyer, Inc.",
            "seller": "Solstice Field Securityholders",
            "policy_id": "P-ROLLOVER-SPA-2026",
            "headline_value": 224000000,
            "equity_value": 224000000,
            "industry": "Energy Services",
            "signing_date": "2026-09-08",
            "closing_deadline": "2026-11-30",
            "economics": {
                "consideration_mix": {
                    "cash_at_close": 154000000,
                    "seller_note": 12000000,
                    "rollover_equity": 58000000,
                    "earnout": 0,
                },
                "working_capital": {
                    "target": 26300000,
                    "collar": 2250000,
                    "mechanic": "Seller draft uses stale May balance sheet and broad collar.",
                },
                "escrows": {
                    "general_percent": 10.0,
                    "general_amount": 22400000,
                    "tax_percent": 3.5,
                    "tax_amount": 7840000,
                },
                "indemnity_cap_percent": 14.5,
                "basket": {"type": "deductible", "percent": 0.75, "de_minimis": 50000},
                "survival_periods": {"general_reps_months": 18, "tax_reps_months": 72, "fundamental_reps_months": 72},
                "break_fee_percent": None,
            },
            "parties": {
                "buyers": ["SSC Field Buyer, Inc."],
                "sellers": [
                    seller("Solstice Founder Group", "founder seller", 42.0, 94080000),
                    seller("Prairie Energy Fund", "fund seller", 33.0, 73920000),
                    seller("Solstice Management Rollover", "management", 25.0, 56000000),
                ],
                "representatives": ["Aster Legal LLP", "Ridgewell Energy Advisors"],
                "committee_members": ["Noah Brooks", "Val Tan", "Mira Qureshi"],
                "key_employees": ["Tess Wilder, founder COO", "Anil Rao, field safety lead"],
            },
            "schedules": {
                "cap_table": {
                    "status": "ACTIVE",
                    "as_of": "2026-07-25",
                    "sellers": ["Solstice Founder Group", "Prairie Energy Fund", "Solstice Management Rollover"],
                },
                "stale_cap_table": {
                    "status": "STALE",
                    "as_of": "2026-05-31",
                    "note": "Before note payoff and rollover allocation update.",
                },
                "material_contracts": [
                    {
                        "name": "BasinOps Master Services",
                        "annual_revenue": 45400000,
                        "consent_required": True,
                        "condition_type": "closing",
                    },
                    {
                        "name": "SunWell Safety Services",
                        "annual_revenue": 19800000,
                        "consent_required": True,
                        "condition_type": "closing",
                    },
                    {
                        "name": "Fleet Telematics License",
                        "annual_cost": 2600000,
                        "consent_required": False,
                        "condition_type": "notice",
                    },
                ],
                "employment_terms": {
                    "founder_employment": "COO and safety lead retention agreements.",
                    "non_compete": "24 months in existing basins only.",
                },
                "transition_services": {
                    "required": True,
                    "status": "field dispatch TSA for 6 months",
                    "needed_services": ["dispatch", "safety reporting", "fleet telematics"],
                },
                "ip_transition": {
                    "required": True,
                    "note": "Transfer safety training materials and field scheduling software license.",
                },
                "regulatory_status": {
                    "hsr_required": False,
                    "basis": "No HSR after debt and excluded assets adjustment.",
                    "other_approvals": ["BasinOps consent"],
                },
            },
            "draft_terms": {
                "cash_rollover": "Cash $154M, note $12M, rollover $58M per active allocation schedule.",
                "note_offset": "Seller draft lets seller offset $12M note against buyer cash at closing without lender consent.",
                "nwc": "Target $26.3M but collar $2.25M and May stale balance sheet baseline.",
                "escrow_cap": "10% general escrow, 3.5% tax escrow, 14.5% general cap based on headline value.",
                "risk_overrides": "Credit committee approved tax exposure reserve up to 3%, not 3.5%; cap should use cash consideration base if above escrow.",
            },
            "client_positions": {
                "preferred": "Follow active allocation schedule, reject unilateral note offset, update NWC baseline, keep 10% general escrow, reduce tax escrow to 3%, and cap general reps at escrow.",
                "fallback": "Cap can be 12% of cash consideration with committee approval.",
                "escalation": "Note offset without lender consent, tax escrow above 3%, collar above 0.75% headline value, or cap based on headline value requires credit committee approval.",
            },
            "negotiation_context": {
                "rationale": "Buyer wants rollover continuity but cannot let seller change credit economics through note offset.",
                "batna": "Buyer can fund more cash and reduce rollover if note offset remains unresolved.",
                "ownership_dynamics": "Management rollover group accepts economics but fund seller wants note offset.",
                "strategic_notes": "Risk-allocation overrides are in credit committee memo, not the generic rollover form.",
            },
            "clause_terms": [
                clause_term(
                    "CASH_ROLLOVER",
                    "cash and rollover mix",
                    "Cash $154M, note $12M, rollover $58M.",
                    "Allocation must match signed active schedule.",
                    "Escalate allocation mismatch.",
                    "headline value",
                    NEUTRAL_REVIEW_NOTE,
                ),
                clause_term(
                    "NOTE_OFFSET",
                    "seller note offset",
                    "Seller may offset $12M note against buyer cash without lender consent.",
                    "Seller note may offset cash only with written lender consent.",
                    "Escalate unilateral note offset.",
                    "cash consideration",
                    NEUTRAL_REVIEW_NOTE,
                ),
                clause_term(
                    "NWC",
                    "working capital",
                    "$26.3M target, $2.25M collar, May stale balance sheet.",
                    "Agreed peg and current closing balance sheet; collar up to 0.75% headline value.",
                    "Escalate collar above 0.75% or stale baseline.",
                    "headline value",
                    NEUTRAL_REVIEW_NOTE,
                ),
                clause_term(
                    "ESCROW",
                    "escrow",
                    "10% general escrow and 3.5% tax escrow.",
                    "10% general; tax escrow 2%-3%.",
                    "Aggregate above 13% escalates.",
                    "headline value",
                    NEUTRAL_REVIEW_NOTE,
                ),
                clause_term(
                    "CAP",
                    "indemnity cap",
                    "14.5% cap based on headline value.",
                    "Cap equals general escrow; fallback 12% of cash consideration.",
                    "Escalate cap based on headline.",
                    "cash consideration",
                    NEUTRAL_REVIEW_NOTE,
                ),
                clause_term(
                    "BASKET",
                    "basket",
                    "0.75% deductible; $50k de minimis.",
                    "0.75%-1.0% deductible.",
                    "Escalate below 0.5% or tipping.",
                    "headline value",
                    "Within policy.",
                ),
            ],
        },
    ]


def distractor_deals() -> list[dict]:
    specs = [
        (
            "D-ALDER-044",
            "Alder Creek",
            "Northstar Capital Partners",
            "BUYER",
            "STOCK_PURCHASE",
            "Alder Creek Systems, Inc.",
            "Industrial Software",
        ),
        (
            "D-LUMINA-909",
            "Lumina Vale",
            "BrightPath Holdings",
            "SELLER",
            "ASSET_PURCHASE",
            "Lumina Controls Division",
            "Automation",
        ),
        (
            "D-QUASAR-312",
            "Quasar Harbor",
            "Meridian Seller Desk",
            "SELLER",
            "ASSET_PURCHASE",
            "Quasar Payables Assets",
            "FinTech",
        ),
        (
            "D-HARBORMIST-561",
            "Harbor Mist",
            "Northstar Capital Partners",
            "BUYER",
            "MERGER",
            "Harbor Mist Security Corp.",
            "Cybersecurity",
        ),
        (
            "D-NEBULA-675",
            "Nebula Signal",
            "Helios Health Systems",
            "BUYER",
            "MERGER",
            "Nebula Diagnostics plc",
            "Diagnostics",
        ),
        (
            "D-BRONZE-218",
            "Bronze Foundry",
            "BrassWorks Holdings",
            "SELLER",
            "ASSET_PURCHASE",
            "Bronze Fastener Unit",
            "Aerospace Components",
        ),
        (
            "D-ORCHID-385",
            "Orchid Forge",
            "Atlas Industrial Holdings",
            "SELLER",
            "CARVE_OUT",
            "Orchid Tools Business",
            "Industrial Manufacturing",
        ),
        (
            "D-KAPPA-156",
            "Kappa Stone",
            "Kepler Growth Fund",
            "BUYER",
            "STOCK_PURCHASE",
            "Kappa Metrics LLC",
            "SaaS Analytics",
        ),
    ]
    policy_by_side = {
        ("BUYER", "MERGER"): "P-PUBLIC-MERGER-COMMITTEE-2026",
        ("BUYER", "STOCK_PURCHASE"): "P-BUYER-MIDMARKET-2026",
        ("SELLER", "ASSET_PURCHASE"): "P-SELLER-APA-2026",
        ("SELLER", "CARVE_OUT"): "P-CARVEOUT-OPS-2026",
    }
    deals = []
    for deal_id, codename, client, side, structure, target, industry in specs:
        headline = RNG.randrange(90000000, 490000000, 5000000)
        escrow_percent = RNG.choice([7.5, 8.0, 10.0, 11.0, 12.5, 14.0])
        cap_percent = RNG.choice([8.0, 10.0, 12.5, 15.0, 18.0])
        month = RNG.choice(["08", "09", "10"])
        day = RNG.randint(10, 27)
        seller_name = f"{target.split(',')[0]} Seller Group"
        buyer_name = f"{codename.replace(' ', '')} Acquisition LLC"
        if side == "SELLER":
            buyer = buyer_name
            seller_party = client if "Desk" not in client else seller_name
        else:
            buyer = buyer_name
            seller_party = seller_name
        deals.append(
            {
                "deal_id": deal_id,
                "codename": codename,
                "client": client,
                "client_side": side,
                "structure": structure,
                "status": RNG.choice(["diligence", "drafting", "redline", "committee review", "signed LOI"]),
                "target": target,
                "buyer": buyer,
                "seller": seller_party,
                "policy_id": policy_by_side.get((side, structure), "P-BUYER-MIDMARKET-2026"),
                "headline_value": headline,
                "equity_value": headline,
                "industry": industry,
                "signing_date": f"2026-{month}-{day:02d}",
                "closing_deadline": f"2026-{int(month) + 2:02d}-{min(day + 2, 28):02d}",
                "economics": {
                    "consideration_mix": {
                        "cash_at_close": int(headline * RNG.choice([0.82, 0.9, 1.0])),
                        "seller_note": RNG.choice([0, int(headline * 0.05)]),
                        "rollover_equity": RNG.choice([0, int(headline * 0.1), int(headline * 0.18)]),
                        "earnout": RNG.choice([0, int(headline * 0.04)]),
                    },
                    "working_capital": {
                        "target": int(headline * RNG.uniform(0.08, 0.14)),
                        "collar": int(headline * RNG.uniform(0.002, 0.006)),
                        "mechanic": RNG.choice(
                            [
                                "Dollar-for-dollar outside collar.",
                                "Seller budget baseline.",
                                "Monthly average baseline.",
                            ]
                        ),
                    },
                    "escrows": {
                        "general_percent": escrow_percent,
                        "general_amount": int(headline * escrow_percent / 100),
                        "tax_percent": RNG.choice([0, 2.0, 2.5, 3.5]),
                        "tax_amount": None,
                    },
                    "indemnity_cap_percent": cap_percent,
                    "basket": {
                        "type": RNG.choice(["deductible", "tipping"]),
                        "percent": RNG.choice([0.5, 0.75, 1.0]),
                        "de_minimis": RNG.choice([None, 25000, 50000]),
                    },
                    "survival_periods": {
                        "general_reps_months": RNG.choice([12, 15, 18, 24]),
                        "fundamental_reps_months": 72,
                    },
                    "break_fee_percent": RNG.choice([None, 2.75, 3.0, 3.5]),
                },
                "parties": {
                    "buyers": [buyer],
                    "sellers": [
                        seller(f"{codename} Founder Holdings", "founder seller", 45.0, int(headline * 0.45)),
                        seller(f"{codename} Fund II", "fund seller", 35.0, int(headline * 0.35)),
                        seller(f"{codename} Management Pool", "management", 20.0, int(headline * 0.20)),
                    ],
                    "representatives": [
                        "Aster Legal LLP",
                        RNG.choice(["Rook Financial Advisors", "Mason Bank", "Quill Bankers"]),
                    ],
                    "committee_members": RNG.sample(
                        ["Priya Shah", "Nora Kim", "Ruth Hall", "Dale Wexler", "Marcus Lee", "Sofia Marquez"], 3
                    ),
                    "key_employees": [f"{codename} CEO", f"{codename} Finance Lead"],
                },
                "schedules": {
                    "cap_table": {
                        "status": "ACTIVE",
                        "as_of": "2026-07-15",
                        "sellers": [
                            f"{codename} Founder Holdings",
                            f"{codename} Fund II",
                            f"{codename} Management Pool",
                        ],
                    },
                    "stale_cap_table": {
                        "status": "STALE",
                        "as_of": RNG.choice(["2026-01-31", "2026-03-31", "2026-05-01"]),
                        "note": "Superseded summary retained for comparison.",
                    },
                    "material_contracts": [
                        {
                            "name": f"{codename} Enterprise Customer Agreement",
                            "annual_revenue": int(headline * 0.12),
                            "consent_required": RNG.choice([True, False]),
                            "condition_type": RNG.choice(["closing", "notice", "post-closing covenant"]),
                        },
                        {
                            "name": f"{codename} Shared Services Agreement",
                            "annual_cost": int(headline * 0.015),
                            "consent_required": False,
                            "condition_type": "TSA",
                        },
                    ],
                    "employment_terms": {
                        "retention": "Selected key employees have retention agreements.",
                        "non_compete": RNG.choice(
                            [
                                "24 months narrow scope.",
                                "36 months with founder employment.",
                                "5-year generic template language.",
                            ]
                        ),
                    },
                    "transition_services": {
                        "required": structure in ["CARVE_OUT", "ASSET_PURCHASE"],
                        "status": RNG.choice(["drafted", "missing", "short-form placeholder"]),
                    },
                    "ip_transition": {
                        "required": True,
                        "note": RNG.choice(
                            [
                                "Trademark phase-out needed.",
                                "Patent assignment review pending.",
                                "Open-source schedule incomplete.",
                            ]
                        ),
                    },
                    "regulatory_status": {
                        "hsr_required": RNG.choice([True, False]),
                        "basis": RNG.choice(
                            [
                                "Antitrust memo pending.",
                                "No filing after threshold review.",
                                "Filing expected; no substantive overlap.",
                            ]
                        ),
                        "other_approvals": [],
                    },
                },
                "draft_terms": {
                    "escrow": f"{escrow_percent}% general escrow.",
                    "cap": f"{cap_percent}% cap.",
                    "basket": "Draft basket terms vary from playbook.",
                    "consents": "Current draft includes a mix of closing conditions and post-closing covenants.",
                },
                "client_positions": {
                    "preferred": "Apply the governing client playbook and use the latest active schedules.",
                    "fallback": "Fallback authority depends on policy thresholds and documented diligence risk.",
                    "escalation": "Escalate terms outside policy thresholds.",
                },
                "negotiation_context": {
                    "rationale": "Distractor matter with similar names and common M&A terms.",
                    "batna": "Client has alternatives but prefers current bidder if risk allocation is corrected.",
                    "ownership_dynamics": "Founder and fund holders have different consideration preferences.",
                    "strategic_notes": "Some records are stale or generic templates and should not displace active instructions.",
                },
                "clause_terms": [],
            }
        )
        deals[-1]["economics"]["escrows"]["tax_amount"] = int(
            headline * deals[-1]["economics"]["escrows"]["tax_percent"] / 100
        )
        deals[-1]["clause_terms"] = generic_clause_terms(deals[-1])
    return deals


def generic_clause_terms(deal: dict) -> list[dict]:
    headline = deal["headline_value"]
    escrow = deal["economics"]["escrows"]["general_percent"]
    cap = deal["economics"]["indemnity_cap_percent"]
    if deal["structure"] == "MERGER":
        return [
            clause_term(
                "RTF",
                "reverse termination fee",
                f"{RNG.choice([4.5, 5.0, 6.0])}% of equity value.",
                "At or below 5.0%; 5.5% fallback with covenant.",
                "Board approval above 5.5%.",
                "equity value",
                RNG.choice(["Within benchmark range.", "Needs committee review."]),
            ),
            clause_term(
                "FIDUCIARY",
                "fiduciary out",
                RNG.choice(["Standard superior proposal termination.", "Termination blocked during match period."]),
                "Preserve termination right.",
                "Escalate blocked termination.",
                "board duties",
                "Check against committee policy.",
            ),
            clause_term(
                "MAE",
                "MAE",
                RNG.choice(["Full public-company carve-outs.", "Generic private-target MAE language."]),
                "Full public-company carve-outs.",
                "Escalate restricted carve-outs.",
                "deal certainty",
                "Template conflict possible.",
            ),
            clause_term(
                "BREAKFEE",
                "company break fee",
                f"{RNG.choice([2.75, 3.0, 3.5, 4.0])}% of equity value.",
                "2.5%-3.5%; fallback 3.75%.",
                "Escalate above 3.75%.",
                "equity value",
                "Benchmark record may be outside date range.",
            ),
            clause_term(
                "RW_SURVIVAL",
                "R&W survival",
                RNG.choice(["No survival.", "18 months post-closing."]),
                "No post-closing survival in public merger.",
                "Escalate survival exposure.",
                "public merger form",
                "Confirm active draft version.",
            ),
        ]
    return [
        clause_term(
            "ESCROW",
            "escrow",
            f"{escrow}% general escrow ({money(headline * escrow / 100)}).",
            "Apply client playbook threshold.",
            "Escalate above governing threshold.",
            "headline value",
            "Compare to policy.",
        ),
        clause_term(
            "CAP",
            "indemnity cap",
            f"{cap}% general cap.",
            "General cap usually tied to escrow.",
            "Escalate above policy threshold.",
            "headline value",
            "Compare to policy.",
        ),
        clause_term(
            "BASKET",
            "basket",
            f"{deal['economics']['basket']['percent']}% {deal['economics']['basket']['type']} basket.",
            "Deductible basket preferred.",
            "Escalate tipping or low basket.",
            "headline value",
            "May conflict with standard form.",
        ),
        clause_term(
            "NWC",
            "working capital",
            f"Target {money(deal['economics']['working_capital']['target'])}; collar {money(deal['economics']['working_capital']['collar'])}.",
            "Use current finance schedule.",
            "Escalate stale baseline.",
            "headline value",
            "Confirm schedule date.",
        ),
        clause_term(
            "CONSENTS",
            "material consents",
            "Mixed closing conditions and post-closing covenants.",
            "Top material consents as closing conditions.",
            "Escalate missing top consent.",
            "revenue concentration",
            "Review consent matrix.",
        ),
        clause_term(
            "NONCOMPETE",
            "non-compete",
            deal["schedules"]["employment_terms"].get("non_compete", "No draft yet."),
            "Narrow scope and duration.",
            "Escalate broad restrictions.",
            "restricted business",
            "Generic language may be stale.",
        ),
        clause_term(
            "TSA",
            "transition services",
            deal["schedules"]["transition_services"].get("status", "not required"),
            "Required for non-standalone assets.",
            "Escalate missing TSA.",
            "operating dependency",
            "Only relevant if assets are not standalone.",
        ),
        clause_term(
            "IP",
            "IP transition",
            deal["schedules"]["ip_transition"].get("note", "Review pending."),
            "Clear retained-IP and transition boundaries.",
            "Escalate open-ended use.",
            "IP schedule",
            "Review active schedule.",
        ),
    ]


def section(heading: str, text: str) -> dict:
    return {"heading": heading, "text": text}


def doc_id_for(deal_id: str, suffix: str) -> str:
    return f"DOC-{deal_id.removeprefix('D-').replace('-', '')}-{suffix}"


def build_documents(deals: list[dict], policies: list[dict]) -> list[dict]:
    documents: list[dict] = []
    for deal in deals:
        did = deal["deal_id"]
        roles = {
            "term_sheet": doc_id_for(did, "TERM-01"),
            "draft_agreement": doc_id_for(did, "DRAFT-02"),
            "client_email": doc_id_for(did, "EMAIL-03"),
            "active_cap_table": doc_id_for(did, "CAP-ACTIVE"),
            "financial_schedule": doc_id_for(did, "FIN-04"),
            "material_contracts": doc_id_for(did, "MATCON-05"),
            "disclosure_schedule": doc_id_for(did, "DISC-06"),
            "stale_cap_table": doc_id_for(did, "CAP-STALE"),
            "template_clause": doc_id_for(did, "TEMPLATE-99"),
        }
        if deal["structure"] in ["MERGER", "CARVE_OUT"] or deal["policy_id"] in [
            "P-HYBRID-INVEST-2026",
            "P-ROLLOVER-SPA-2026",
        ]:
            roles["committee_charter"] = doc_id_for(did, "COMMITTEE-07")

        deal["record_links"] = roles
        deal["active_documents"] = [
            roles["term_sheet"],
            roles["draft_agreement"],
            roles["client_email"],
            roles["active_cap_table"],
            roles["financial_schedule"],
            roles["material_contracts"],
            roles["disclosure_schedule"],
        ]
        if "committee_charter" in roles:
            deal["active_documents"].append(roles["committee_charter"])
        deal["stale_documents"] = [roles["stale_cap_table"], roles["template_clause"]]
        deal["schedules"]["cap_table"]["source_doc_id"] = roles["active_cap_table"]
        deal["schedules"]["stale_cap_table"]["source_doc_id"] = roles["stale_cap_table"]
        deal["schedules"]["material_contracts_source_doc_id"] = roles["material_contracts"]

        common_related = [did, deal["policy_id"]]
        documents.extend(
            [
                {
                    "doc_id": roles["term_sheet"],
                    "title": f"{deal['codename']} signed commercial term sheet",
                    "deal_id": did,
                    "doc_type": "term_sheet",
                    "version_status": "ACTIVE",
                    "effective_date": deal["signing_date"],
                    "sections": [
                        section(
                            "Parties",
                            f"Buyer: {deal['buyer']}. Seller: {deal['seller']}. Client side: {deal['client_side']}.",
                        ),
                        section(
                            "Value and structure",
                            f"{deal['structure']} with headline value {money(deal['headline_value'])} and equity value {money(deal['equity_value'])}.",
                        ),
                        section(
                            "Timing",
                            f"Target signing date {deal['signing_date']}; outside closing deadline {deal['closing_deadline']}.",
                        ),
                        section("Economics", json.dumps(deal["economics"], sort_keys=True)),
                    ],
                    "related_ids": common_related,
                },
                {
                    "doc_id": roles["draft_agreement"],
                    "title": f"{deal['codename']} current draft agreement",
                    "deal_id": did,
                    "doc_type": "draft_agreement",
                    "version_status": "ACTIVE",
                    "effective_date": deal["signing_date"],
                    "sections": [
                        section("Current draft terms", json.dumps(deal["draft_terms"], sort_keys=True)),
                        section("Negotiation posture", deal["client_positions"]["preferred"]),
                        section("Fallback authority", deal["client_positions"]["fallback"]),
                        section("Escalation note", deal["client_positions"]["escalation"]),
                    ],
                    "related_ids": common_related + [roles["client_email"]],
                },
                {
                    "doc_id": roles["client_email"],
                    "title": f"{deal['codename']} latest client instruction email",
                    "deal_id": did,
                    "doc_type": "email",
                    "version_status": "ACTIVE",
                    "effective_date": deal["signing_date"],
                    "sections": [
                        section("Instruction summary", deal["client_positions"]["preferred"]),
                        section("Fallbacks", deal["client_positions"]["fallback"]),
                        section("Escalations", deal["client_positions"]["escalation"]),
                        section("Strategic context", json.dumps(deal["negotiation_context"], sort_keys=True)),
                    ],
                    "related_ids": common_related + [roles["draft_agreement"]],
                },
                {
                    "doc_id": roles["active_cap_table"],
                    "title": f"{deal['codename']} active ownership and cap table schedule",
                    "deal_id": did,
                    "doc_type": "cap_table",
                    "version_status": "ACTIVE",
                    "effective_date": deal["schedules"]["cap_table"]["as_of"],
                    "sections": [
                        section(
                            "Control note",
                            "This active cap table supersedes stale cap table exports unless a later active schedule is posted.",
                        ),
                        section("Seller records", json.dumps(deal["parties"]["sellers"], sort_keys=True)),
                        section("Schedule metadata", json.dumps(deal["schedules"]["cap_table"], sort_keys=True)),
                    ],
                    "related_ids": common_related,
                },
                {
                    "doc_id": roles["financial_schedule"],
                    "title": f"{deal['codename']} financial schedule and working capital model",
                    "deal_id": did,
                    "doc_type": "financial_schedule",
                    "version_status": "ACTIVE",
                    "effective_date": deal["signing_date"],
                    "sections": [
                        section("Working capital", json.dumps(deal["economics"]["working_capital"], sort_keys=True)),
                        section(
                            "Escrows and caps",
                            json.dumps(
                                {
                                    "escrows": deal["economics"]["escrows"],
                                    "cap_percent": deal["economics"]["indemnity_cap_percent"],
                                    "basket": deal["economics"]["basket"],
                                },
                                sort_keys=True,
                            ),
                        ),
                        section(
                            "Consideration mix", json.dumps(deal["economics"]["consideration_mix"], sort_keys=True)
                        ),
                    ],
                    "related_ids": common_related,
                },
                {
                    "doc_id": roles["material_contracts"],
                    "title": f"{deal['codename']} material contracts and consent matrix",
                    "deal_id": did,
                    "doc_type": "material_contracts",
                    "version_status": "ACTIVE",
                    "effective_date": deal["signing_date"],
                    "sections": [
                        section(
                            "Material contracts", json.dumps(deal["schedules"]["material_contracts"], sort_keys=True)
                        ),
                        section(
                            "Regulatory status", json.dumps(deal["schedules"]["regulatory_status"], sort_keys=True)
                        ),
                    ],
                    "related_ids": common_related,
                },
                {
                    "doc_id": roles["disclosure_schedule"],
                    "title": f"{deal['codename']} disclosure schedules",
                    "deal_id": did,
                    "doc_type": "disclosure_schedule",
                    "version_status": "ACTIVE",
                    "effective_date": deal["signing_date"],
                    "sections": [
                        section(
                            "Employment and restrictive covenant schedule",
                            json.dumps(deal["schedules"]["employment_terms"], sort_keys=True),
                        ),
                        section(
                            "Transition services", json.dumps(deal["schedules"]["transition_services"], sort_keys=True)
                        ),
                        section("IP transition", json.dumps(deal["schedules"]["ip_transition"], sort_keys=True)),
                    ],
                    "related_ids": common_related,
                },
                {
                    "doc_id": roles["stale_cap_table"],
                    "title": f"{deal['codename']} stale cap table export",
                    "deal_id": did,
                    "doc_type": "cap_table",
                    "version_status": "STALE",
                    "effective_date": deal["schedules"]["stale_cap_table"]["as_of"],
                    "sections": [
                        section("Stale warning", deal["schedules"]["stale_cap_table"]["note"]),
                        section(
                            "Legacy summary",
                            "This export is retained for audit trail only and should not displace active schedules.",
                        ),
                    ],
                    "related_ids": common_related + [roles["active_cap_table"]],
                },
                {
                    "doc_id": roles["template_clause"],
                    "title": f"{deal['codename']} generic template provisions imported by drafting system",
                    "deal_id": did,
                    "doc_type": "template_provision",
                    "version_status": "TEMPLATE",
                    "effective_date": "2026-01-15",
                    "sections": [
                        section(
                            "Template warning",
                            "Generic template language is not a client instruction and may conflict with current policy.",
                        ),
                        section(
                            "Examples",
                            "Includes generic 10% escrow, 5-year worldwide non-compete, and private-company MAE language.",
                        ),
                    ],
                    "related_ids": [did, "P-STANDARD-FORM-2026"],
                },
            ]
        )
        if "committee_charter" in roles:
            documents.append(
                {
                    "doc_id": roles["committee_charter"],
                    "title": f"{deal['codename']} committee charter and approval log",
                    "deal_id": did,
                    "doc_type": "committee_charter",
                    "version_status": "ACTIVE",
                    "effective_date": deal["signing_date"],
                    "sections": [
                        section("Committee members", ", ".join(deal["parties"]["committee_members"])),
                        section("Escalation categories", deal["client_positions"]["escalation"]),
                        section(
                            "Meeting note",
                            "Approval log is procedural and does not override written policy thresholds.",
                        ),
                    ],
                    "related_ids": common_related,
                }
            )

    for policy in policies:
        documents.append(
            {
                "doc_id": f"DOC-{policy['policy_id'].replace('P-', '').replace('-', '')}-POLICY",
                "title": policy["title"],
                "deal_id": None,
                "doc_type": "playbook_policy",
                "version_status": "POLICY",
                "effective_date": policy["effective_date"],
                "sections": [
                    section(
                        "Policy metadata",
                        f"{policy['client']} / {policy['policy_type']} / version {policy['version']}.",
                    ),
                    section("Rules", json.dumps(policy["rules"], sort_keys=True)),
                ],
                "related_ids": [policy["policy_id"]],
            }
        )
    return documents


def build_clauses(deals: list[dict]) -> list[dict]:
    clauses: list[dict] = []
    for deal in deals:
        draft_doc = deal["record_links"]["draft_agreement"]
        stale_doc = deal["record_links"]["template_clause"]
        for index, term in enumerate(deal["clause_terms"], start=1):
            clauses.append(
                {
                    "clause_id": f"CL-{deal['deal_id'].removeprefix('D-')}-{index:03d}",
                    "deal_id": deal["deal_id"],
                    "clause_code": term["clause_code"],
                    "topic": term["topic"],
                    "draft_value": term["draft_value"],
                    "playbook_value": term["playbook_value"],
                    "policy_threshold": term["policy_threshold"],
                    "calculation_base": term["calculation_base"],
                    "risk_hint": term["risk_hint"],
                    "source_doc_id": draft_doc,
                    "version_status": term.get("version_status", "ACTIVE"),
                }
            )
        stale_topics = RNG.sample(deal["clause_terms"], min(2, len(deal["clause_terms"])))
        for offset, term in enumerate(stale_topics, start=1):
            clauses.append(
                {
                    "clause_id": f"CL-{deal['deal_id'].removeprefix('D-')}-S{offset:02d}",
                    "deal_id": deal["deal_id"],
                    "clause_code": term["clause_code"],
                    "topic": term["topic"],
                    "draft_value": "Generic template value retained in drafting system.",
                    "playbook_value": term["playbook_value"],
                    "policy_threshold": term["policy_threshold"],
                    "calculation_base": term["calculation_base"],
                    "risk_hint": "Stale or template clause with same label; compare against active draft.",
                    "source_doc_id": stale_doc,
                    "version_status": "STALE",
                }
            )
    return clauses


def build_benchmarks() -> list[dict]:
    benchmarks = [
        {
            "benchmark_id": "BM-RTF-HEALTHTECH-2026",
            "topic": "reverse termination fee",
            "industry": "Health Technology",
            "year": 2026,
            "sample_size": 28,
            "median_percent": 4.8,
            "mean_percent": 4.9,
            "count_above_threshold": 3,
            "range_low": 3.2,
            "range_high": 6.0,
            "definition": "Percent of equity value in signed public health technology mergers.",
            "notes": "Current benchmark set used for committee RTF review.",
        },
        {
            "benchmark_id": "BM-FIDUCIARY-PUBLIC-2026",
            "topic": "fiduciary out",
            "industry": "Public Company M&A",
            "year": 2026,
            "sample_size": 42,
            "median_percent": None,
            "mean_percent": None,
            "count_above_threshold": 4,
            "range_low": None,
            "range_high": None,
            "definition": "Deals where superior proposal termination right was blocked or match period exceeded four business days.",
            "notes": "Blocked termination is uncommon and triggers committee review.",
        },
        {
            "benchmark_id": "BM-MAE-HEALTHCARE-2026",
            "topic": "MAE carve-outs",
            "industry": "Healthcare",
            "year": 2026,
            "sample_size": 36,
            "median_percent": None,
            "mean_percent": None,
            "count_above_threshold": 31,
            "range_low": None,
            "range_high": None,
            "definition": "Count with standard market, industry, law, pandemic, cyber, and announcement-effect carve-outs.",
            "notes": "Restricted carve-out packages are below market.",
        },
        {
            "benchmark_id": "BM-ESCROW-MIDMARKET-2026",
            "topic": "escrow",
            "industry": "Middle Market",
            "year": 2026,
            "sample_size": 74,
            "median_percent": 10.0,
            "mean_percent": 9.7,
            "count_above_threshold": 9,
            "range_low": 5.0,
            "range_high": 15.0,
            "definition": "General indemnity escrow as percent of headline value.",
            "notes": "Tax escrows tracked separately.",
        },
        {
            "benchmark_id": "BM-TSA-CARVEOUT-2026",
            "topic": "transition services",
            "industry": "Industrial Manufacturing",
            "year": 2026,
            "sample_size": 31,
            "median_percent": None,
            "mean_percent": None,
            "count_above_threshold": 25,
            "range_low": 6,
            "range_high": 18,
            "definition": "TSA duration in months for manufacturing carve-outs with shared ERP.",
            "notes": "Median duration is 12 months.",
        },
        {
            "benchmark_id": "BM-ROLLOVER-VALUATION-2026",
            "topic": "rollover valuation",
            "industry": "SaaS Analytics",
            "year": 2026,
            "sample_size": 22,
            "median_percent": 0.0,
            "mean_percent": 0.6,
            "count_above_threshold": 2,
            "range_low": 0.0,
            "range_high": 3.0,
            "definition": "Discount between cash purchase price and rollover implied valuation.",
            "notes": "Discounts above 2% are rare and usually approved separately.",
        },
    ]
    topics = [
        "escrow",
        "survival",
        "indemnity cap",
        "basket",
        "non-compete",
        "transition services",
        "IP transition",
        "reverse termination fee",
        "company break fee",
        "MAE carve-outs",
        "employee transfer",
        "working capital",
    ]
    industries = [
        "Industrial Software",
        "Aerospace Components",
        "Health Technology",
        "Industrial Manufacturing",
        "Cybersecurity",
        "Automation",
        "FinTech",
        "Diagnostics",
        "SaaS Analytics",
        "Energy Services",
        "Consumer",
        "Logistics",
    ]
    for i in range(1, 57):
        topic = RNG.choice(topics)
        industry = RNG.choice(industries)
        year = RNG.choice([2019, 2021, 2022, 2023, 2024, 2025, 2026])
        low = round(RNG.uniform(0.25, 4.5), 2)
        high = round(low + RNG.uniform(1.0, 11.0), 2)
        median = round((low + high) / 2 + RNG.uniform(-0.4, 0.4), 2)
        benchmarks.append(
            {
                "benchmark_id": f"BM-{topic.upper().replace(' ', '-')}-{industry.upper().replace(' ', '-')}-{year}-{i:03d}",
                "topic": topic,
                "industry": industry,
                "year": year,
                "sample_size": RNG.randint(8, 96),
                "median_percent": median
                if topic not in ["transition services", "employee transfer", "IP transition", "MAE carve-outs"]
                else None,
                "mean_percent": round(median + RNG.uniform(-0.3, 0.3), 2)
                if topic not in ["transition services", "employee transfer", "IP transition", "MAE carve-outs"]
                else None,
                "count_above_threshold": RNG.randint(0, 18),
                "range_low": low,
                "range_high": high,
                "definition": f"{topic} benchmark for {industry} transactions.",
                "notes": RNG.choice(
                    [
                        "Current-year sample.",
                        "Older sample retained as distractor.",
                        "Industry outside core peer set.",
                        "Definition differs from client playbook threshold.",
                        None,
                    ]
                ),
            }
        )
    return benchmarks


def strip_builder_fields(deals: list[dict]) -> None:
    for deal in deals:
        deal.pop("clause_terms", None)


def write_json(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    policies = build_policies()
    deals = required_deals() + distractor_deals()
    documents = build_documents(deals, policies)
    clauses = build_clauses(deals)
    benchmarks = build_benchmarks()
    strip_builder_fields(deals)

    data = {
        "metadata": {
            "system": "Aster Legal Deal Desk",
            "task_group": "task_group_020",
            "seed": SEED,
            "data_version": "2026-07-07",
            "description": "Shared M&A legal operations records for browser and API use.",
        },
        "deals": deals,
        "documents": documents,
        "policies": policies,
        "clauses": clauses,
        "benchmarks": benchmarks,
    }
    counts = {
        "deals": len(deals),
        "documents": len(documents),
        "policies": len(policies),
        "clauses": len(clauses),
        "benchmarks": len(benchmarks),
    }
    manifest = {
        "system": "Aster Legal Deal Desk",
        "task_group": "task_group_020",
        "seed": SEED,
        "data_version": "2026-07-07",
        "generated_files": ["data/dealdesk.json", "data/manifest.json"],
        "counts": counts,
        "important_deal_ids": REQUIRED_DEAL_IDS,
        "important_documents_by_deal": {
            deal["deal_id"]: {
                "active_documents": deal["active_documents"],
                "stale_documents": deal["stale_documents"],
                "policy_id": deal["policy_id"],
            }
            for deal in deals
            if deal["deal_id"] in REQUIRED_DEAL_IDS
        },
        "public_pages": [
            "/",
            "/deals",
            "/deals/<deal_id>",
            "/documents/<doc_id>",
            "/policies",
            "/policies/<policy_id>",
            "/benchmarks",
            "/clauses/compare?deal_id=<deal_id>",
        ],
        "public_api_endpoints": [
            "GET /api/health",
            "GET /api/deals",
            "GET /api/deals/<deal_id>",
            "GET /api/documents/<doc_id>",
            "GET /api/policies",
            "GET /api/policies/<policy_id>",
            "GET /api/clauses?deal_id=<deal_id>",
            "GET /api/benchmarks",
            "GET /api/search?q=<query>",
        ],
        "notes": [
            "No public endpoints contain task IDs.",
            "No public endpoints expose evaluation-style or task-specific bundles.",
            "Stale cap tables, template clauses, similar party names, older benchmarks, and null non-essential fields are deliberate distractors.",
        ],
    }
    write_json(DATA_FILE, data)
    write_json(MANIFEST_FILE, manifest)
    print(
        json.dumps(
            {"seed": SEED, "counts": counts, "data_file": str(DATA_FILE), "manifest_file": str(MANIFEST_FILE)},
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
