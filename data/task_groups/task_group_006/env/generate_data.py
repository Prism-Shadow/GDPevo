#!/usr/bin/env python3
"""Generate deterministic ProcureOps shared environment data."""

from __future__ import annotations

import json
import random
from datetime import date, timedelta
from pathlib import Path


SEED = 6006
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
DATA_FILE = DATA_DIR / "procureops_data.json"
MANIFEST_FILE = DATA_DIR / "manifest.json"


def money(value: float) -> float:
    return round(value + 1e-9, 2)


def iso(base: date, days: int) -> str:
    return (base + timedelta(days=days)).isoformat()


def line_total(lines: list[dict], freight: float = 0.0, tax_rate: float = 0.0725) -> tuple[float, float, float]:
    subtotal = money(sum(line.get("quantity", line.get("quantity_billed", 0)) * line["unit_price"] for line in lines))
    tax = money(subtotal * tax_rate)
    total = money(subtotal + tax + freight)
    return subtotal, tax, total


def build_static_records() -> dict:
    programs = [
        {
            "program_id": "PRG-AX17",
            "name": "Axis refresh line 17",
            "owner": "Elena Marsh",
            "cost_center": "CC-410",
            "region": "North America",
            "priority": "high",
            "budget_cap": 285000.00,
            "committed_amount": 216430.40,
            "status": "active",
        },
        {
            "program_id": "PRG-NOVA-31",
            "name": "Nova field retrofit 31",
            "owner": "Ravi Menon",
            "cost_center": "CC-455",
            "region": "EMEA",
            "priority": "critical",
            "budget_cap": 420000.00,
            "committed_amount": 358204.15,
            "status": "active",
        },
        {
            "program_id": "PRG-ORBIT-09",
            "name": "Orbit supplier transition",
            "owner": "Dana Cho",
            "cost_center": "CC-390",
            "region": "North America",
            "priority": "medium",
            "budget_cap": 175000.00,
            "committed_amount": 119880.00,
            "status": "active",
        },
        {
            "program_id": "PRG-CEDAR-22",
            "name": "Cedar maintenance reserve",
            "owner": "Amira Patel",
            "cost_center": "CC-312",
            "region": "APAC",
            "priority": "medium",
            "budget_cap": 126000.00,
            "committed_amount": 87531.22,
            "status": "active",
        },
    ]

    suppliers = [
        {
            "supplier_id": "SUP-LUMA",
            "name": "LumaPro Industrial",
            "region": "US",
            "risk_rating": "watch",
            "payment_terms": "NET30",
            "status": "active",
        },
        {
            "supplier_id": "SUP-VANTIX",
            "name": "Vantix Controls",
            "region": "US",
            "risk_rating": "low",
            "payment_terms": "NET45",
            "status": "active",
        },
        {
            "supplier_id": "SUP-HEXEL",
            "name": "Hexel Motion",
            "region": "DE",
            "risk_rating": "medium",
            "payment_terms": "NET30",
            "status": "active",
        },
        {
            "supplier_id": "SUP-ORION",
            "name": "Orion Packworks",
            "region": "US",
            "risk_rating": "low",
            "payment_terms": "NET30",
            "status": "active",
        },
        {
            "supplier_id": "SUP-KAITO",
            "name": "Kaito Micro",
            "region": "JP",
            "risk_rating": "watch",
            "payment_terms": "NET60",
            "status": "active",
        },
        {
            "supplier_id": "SUP-MERIT",
            "name": "Merit Fasteners",
            "region": "MX",
            "risk_rating": "low",
            "payment_terms": "NET30",
            "status": "active",
        },
        {
            "supplier_id": "SUP-BLUESTEM",
            "name": "Bluestem Logistics",
            "region": "US",
            "risk_rating": "medium",
            "payment_terms": "NET15",
            "status": "active",
        },
        {
            "supplier_id": "SUP-NORD",
            "name": "Nord Valve Group",
            "region": "SE",
            "risk_rating": "high",
            "payment_terms": "NET45",
            "status": "quality_hold",
        },
    ]

    items = [
        {
            "sku": "LMP-228",
            "description": "LumaPro sealed lamp module",
            "category": "electrical",
            "uom": "EA",
            "standard_cost": 82.75,
            "preferred_supplier_id": "SUP-LUMA",
            "active": True,
        },
        {
            "sku": "DRV-AX17",
            "description": "Axis drive controller",
            "category": "controls",
            "uom": "EA",
            "standard_cost": 310.40,
            "preferred_supplier_id": "SUP-VANTIX",
            "active": True,
        },
        {
            "sku": "GSK-BLUE",
            "description": "Blue gasket service kit",
            "category": "seals",
            "uom": "KIT",
            "standard_cost": 18.20,
            "preferred_supplier_id": "SUP-MERIT",
            "active": True,
        },
        {
            "sku": "SEN-NOVA",
            "description": "Nova calibrated pressure sensor",
            "category": "controls",
            "uom": "EA",
            "standard_cost": 145.10,
            "preferred_supplier_id": "SUP-HEXEL",
            "active": True,
        },
        {
            "sku": "CBL-GOLD",
            "description": "Gold-rated harness cable",
            "category": "electrical",
            "uom": "EA",
            "standard_cost": 47.80,
            "preferred_supplier_id": "SUP-KAITO",
            "active": True,
        },
        {
            "sku": "VAL-ND70",
            "description": "ND70 proportional valve",
            "category": "hydraulics",
            "uom": "EA",
            "standard_cost": 228.65,
            "preferred_supplier_id": "SUP-NORD",
            "active": True,
        },
    ]

    contracts = [
        {
            "contract_id": "CR-LMP-228",
            "supplier_id": "SUP-LUMA",
            "program_id": "PRG-AX17",
            "sku": "LMP-228",
            "effective_date": "2025-11-01",
            "expiry_date": "2026-12-31",
            "ceiling_amount": 185000.00,
            "price_type": "fixed",
            "unit_price": 84.50,
            "status": "active",
            "buyer": "Nora Fields",
        },
        {
            "contract_id": "CR-NOVA-311",
            "supplier_id": "SUP-HEXEL",
            "program_id": "PRG-NOVA-31",
            "sku": "SEN-NOVA",
            "effective_date": "2026-01-01",
            "expiry_date": "2026-09-30",
            "ceiling_amount": 240000.00,
            "price_type": "indexed",
            "unit_price": 149.75,
            "status": "active",
            "buyer": "Ivy Santos",
        },
    ]

    purchase_requisitions = [
        {
            "requisition_id": "REQ-AX17-141",
            "program_id": "PRG-AX17",
            "requester": "Elena Marsh",
            "sku": "LMP-228",
            "quantity": 240,
            "need_by": "2026-06-18",
            "status": "converted",
            "priority": "high",
        },
        {
            "requisition_id": "REQ-NOVA-302",
            "program_id": "PRG-NOVA-31",
            "requester": "Ravi Menon",
            "sku": "SEN-NOVA",
            "quantity": 180,
            "need_by": "2026-06-22",
            "status": "converted",
            "priority": "critical",
        },
        {
            "requisition_id": "REQ-AX17-166",
            "program_id": "PRG-AX17",
            "requester": "Elena Marsh",
            "sku": "DRV-AX17",
            "quantity": 75,
            "need_by": "2026-06-20",
            "status": "approved",
            "priority": "high",
        },
    ]

    purchase_orders = [
        {
            "po_id": "PO-AX17-4481",
            "requisition_id": "REQ-AX17-141",
            "program_id": "PRG-AX17",
            "supplier_id": "SUP-LUMA",
            "contract_id": "CR-LMP-228",
            "order_date": "2026-05-16",
            "due_date": "2026-06-14",
            "currency": "USD",
            "status": "partial_receipt",
            "lines": [
                {
                    "line_id": 1,
                    "sku": "LMP-228",
                    "description": "LumaPro sealed lamp module",
                    "quantity": 240,
                    "unit_price": 84.50,
                }
            ],
            "buyer": "Nora Fields",
            "ship_to": "WH-BLUE",
        },
        {
            "po_id": "PO-NOVA-3107",
            "requisition_id": "REQ-NOVA-302",
            "program_id": "PRG-NOVA-31",
            "supplier_id": "SUP-HEXEL",
            "contract_id": "CR-NOVA-311",
            "order_date": "2026-05-18",
            "due_date": "2026-06-20",
            "currency": "USD",
            "status": "received",
            "lines": [
                {
                    "line_id": 1,
                    "sku": "SEN-NOVA",
                    "description": "Nova calibrated pressure sensor",
                    "quantity": 180,
                    "unit_price": 149.75,
                }
            ],
            "buyer": "Ivy Santos",
            "ship_to": "WH-GOLD",
        },
        {
            "po_id": "PO-AX17-4519",
            "requisition_id": "REQ-AX17-166",
            "program_id": "PRG-AX17",
            "supplier_id": "SUP-VANTIX",
            "contract_id": None,
            "order_date": "2026-05-28",
            "due_date": "2026-06-25",
            "currency": "USD",
            "status": "open",
            "lines": [
                {
                    "line_id": 1,
                    "sku": "DRV-AX17",
                    "description": "Axis drive controller",
                    "quantity": 75,
                    "unit_price": 318.00,
                }
            ],
            "buyer": "Nora Fields",
            "ship_to": "WH-BLUE",
        },
    ]

    receipts = [
        {
            "receipt_id": "RCV-BLUE-14",
            "po_id": "PO-AX17-4481",
            "supplier_id": "SUP-LUMA",
            "warehouse_id": "WH-BLUE",
            "receipt_date": "2026-05-30",
            "packing_slip": "PK-LUMA-5831",
            "status": "accepted",
            "lines": [
                {
                    "po_line_id": 1,
                    "sku": "LMP-228",
                    "quantity_received": 216,
                    "quantity_rejected": 0,
                    "inspection_status": "passed",
                }
            ],
            "receiver": "M. Webb",
        },
        {
            "receipt_id": "RCV-GOLD-27",
            "po_id": "PO-NOVA-3107",
            "supplier_id": "SUP-HEXEL",
            "warehouse_id": "WH-GOLD",
            "receipt_date": "2026-05-31",
            "packing_slip": "PK-HEX-9924",
            "status": "accepted_with_note",
            "lines": [
                {
                    "po_line_id": 1,
                    "sku": "SEN-NOVA",
                    "quantity_received": 180,
                    "quantity_rejected": 0,
                    "inspection_status": "passed",
                }
            ],
            "receiver": "T. Alvarez",
        },
    ]

    ap_invoices = [
        {
            "invoice_id": "AP-LUMA-7714",
            "supplier_id": "SUP-LUMA",
            "po_id": "PO-AX17-4481",
            "receipt_id": "RCV-BLUE-14",
            "invoice_date": "2026-06-01",
            "currency": "USD",
            "lines": [{"po_line_id": 1, "sku": "LMP-228", "quantity_billed": 240, "unit_price": 84.50}],
            "freight": 320.00,
            "status": "on_hold",
            "hold_code": "QTY_VARIANCE",
        },
        {
            "invoice_id": "AP-HEXEL-3309",
            "supplier_id": "SUP-HEXEL",
            "po_id": "PO-NOVA-3107",
            "receipt_id": "RCV-GOLD-27",
            "invoice_date": "2026-06-01",
            "currency": "USD",
            "lines": [{"po_line_id": 1, "sku": "SEN-NOVA", "quantity_billed": 180, "unit_price": 149.75}],
            "freight": 0.00,
            "status": "approved",
            "hold_code": None,
        },
        {
            "invoice_id": "AP-VANTIX-2188",
            "supplier_id": "SUP-VANTIX",
            "po_id": "PO-AX17-4519",
            "receipt_id": None,
            "invoice_date": "2026-06-01",
            "currency": "USD",
            "lines": [{"po_line_id": 1, "sku": "DRV-AX17", "quantity_billed": 75, "unit_price": 318.00}],
            "freight": 185.00,
            "status": "pending_receipt",
            "hold_code": "NO_RECEIPT",
        },
    ]

    for po in purchase_orders:
        subtotal, tax, total = line_total(po["lines"])
        po["subtotal"] = subtotal
        po["tax"] = tax
        po["total"] = total

    for inv in ap_invoices:
        subtotal, tax, total = line_total(inv["lines"], inv["freight"])
        inv["subtotal"] = subtotal
        inv["tax"] = tax
        inv["total"] = total

    return {
        "programs": programs,
        "suppliers": suppliers,
        "items": items,
        "contracts": contracts,
        "purchase_requisitions": purchase_requisitions,
        "purchase_orders": purchase_orders,
        "receipts": receipts,
        "ap_invoices": ap_invoices,
    }


def extend_with_noise(data: dict, rng: random.Random) -> None:
    base_date = date(2026, 1, 5)
    cost_centers = ["CC-312", "CC-390", "CC-410", "CC-455", "CC-520"]
    categories = ["electrical", "controls", "hydraulics", "packaging", "seals", "fasteners"]
    supplier_ids = [s["supplier_id"] for s in data["suppliers"]]
    program_ids = [p["program_id"] for p in data["programs"]]

    for idx in range(4, 10):
        data["programs"].append(
            {
                "program_id": f"PRG-{['DELTA', 'ION', 'MAPLE', 'QUARTZ', 'RIVER', 'SOL'][idx - 4]}-{idx + 10}",
                "name": f"Procurement wave {idx}",
                "owner": rng.choice(["Jon Kim", "Priya Shah", "Marcus Lee", "Hana Ortiz"]),
                "cost_center": rng.choice(cost_centers),
                "region": rng.choice(["North America", "EMEA", "APAC"]),
                "priority": rng.choice(["low", "medium", "high"]),
                "budget_cap": money(rng.uniform(80000, 260000)),
                "committed_amount": money(rng.uniform(25000, 180000)),
                "status": rng.choice(["active", "active", "planning", "closing"]),
            }
        )
    program_ids = [p["program_id"] for p in data["programs"]]

    for idx in range(9, 15):
        data["suppliers"].append(
            {
                "supplier_id": f"SUP-{idx:03d}",
                "name": rng.choice(["Aster Supply", "Beacon Components", "Clearpath Metals", "Dynamo Works"])
                + f" {idx}",
                "region": rng.choice(["US", "CA", "DE", "JP", "MX"]),
                "risk_rating": rng.choice(["low", "low", "medium", "watch"]),
                "payment_terms": rng.choice(["NET15", "NET30", "NET45", "NET60"]),
                "status": rng.choice(["active", "active", "active", "review"]),
            }
        )
    supplier_ids = [s["supplier_id"] for s in data["suppliers"]]

    for idx in range(7, 33):
        supplier_id = rng.choice(supplier_ids)
        sku = f"{rng.choice(['BRG', 'CBL', 'MOD', 'KIT', 'PLT', 'SNS'])}-{idx:03d}"
        data["items"].append(
            {
                "sku": sku,
                "description": f"{rng.choice(['standard', 'sealed', 'calibrated', 'reinforced'])} {rng.choice(categories)} component {idx}",
                "category": rng.choice(categories),
                "uom": rng.choice(["EA", "BOX", "KIT", "M"]),
                "standard_cost": money(rng.uniform(6.5, 385.0)),
                "preferred_supplier_id": supplier_id,
                "active": rng.random() > 0.08,
            }
        )

    skus = [i["sku"] for i in data["items"]]
    for idx in range(3, 18):
        supplier_id = rng.choice(supplier_ids)
        sku = rng.choice(skus)
        data["contracts"].append(
            {
                "contract_id": f"CR-{idx:04d}",
                "supplier_id": supplier_id,
                "program_id": rng.choice(program_ids),
                "sku": sku,
                "effective_date": iso(base_date, rng.randint(-60, 90)),
                "expiry_date": iso(base_date, rng.randint(180, 520)),
                "ceiling_amount": money(rng.uniform(45000, 220000)),
                "price_type": rng.choice(["fixed", "indexed", "not_to_exceed"]),
                "unit_price": money(rng.uniform(8.0, 360.0)),
                "status": rng.choice(["active", "active", "draft", "expired"]),
                "buyer": rng.choice(["Nora Fields", "Ivy Santos", "Quinn Zhao", "Maya Ellis"]),
            }
        )

    contract_by_sku = {}
    for contract in data["contracts"]:
        if contract["status"] == "active":
            contract_by_sku.setdefault(contract["sku"], []).append(contract)

    for idx in range(4, 38):
        sku = rng.choice(skus)
        program_id = rng.choice(program_ids)
        req_id = f"REQ-{idx:04d}"
        data["purchase_requisitions"].append(
            {
                "requisition_id": req_id,
                "program_id": program_id,
                "requester": rng.choice(["Elena Marsh", "Ravi Menon", "Dana Cho", "Amira Patel", "Jon Kim"]),
                "sku": sku,
                "quantity": rng.randint(12, 260),
                "need_by": iso(base_date, rng.randint(75, 210)),
                "status": rng.choice(["approved", "converted", "converted", "draft", "cancelled"]),
                "priority": rng.choice(["low", "medium", "high", "critical"]),
            }
        )

    for idx in range(4, 58):
        req = rng.choice(data["purchase_requisitions"])
        sku = req["sku"]
        supplier_id = next(
            (i["preferred_supplier_id"] for i in data["items"] if i["sku"] == sku), rng.choice(supplier_ids)
        )
        contract = rng.choice(contract_by_sku.get(sku, [None]))
        unit_price = (
            contract["unit_price"]
            if contract
            else money(
                next((i["standard_cost"] for i in data["items"] if i["sku"] == sku), 20.0) * rng.uniform(0.94, 1.12)
            )
        )
        quantity = max(1, int(req["quantity"] * rng.uniform(0.45, 1.25)))
        po = {
            "po_id": f"PO-{idx:05d}",
            "requisition_id": req["requisition_id"],
            "program_id": req["program_id"],
            "supplier_id": supplier_id,
            "contract_id": contract["contract_id"] if contract else None,
            "order_date": iso(base_date, rng.randint(0, 130)),
            "due_date": iso(base_date, rng.randint(70, 220)),
            "currency": "USD",
            "status": rng.choice(["open", "confirmed", "partial_receipt", "received", "cancelled", "closed"]),
            "lines": [
                {
                    "line_id": 1,
                    "sku": sku,
                    "description": f"ProcureOps item {sku}",
                    "quantity": quantity,
                    "unit_price": unit_price,
                }
            ],
            "buyer": rng.choice(["Nora Fields", "Ivy Santos", "Quinn Zhao", "Maya Ellis"]),
            "ship_to": rng.choice(["WH-BLUE", "WH-GOLD", "WH-SILVER"]),
        }
        subtotal, tax, total = line_total(po["lines"])
        po.update({"subtotal": subtotal, "tax": tax, "total": total})
        data["purchase_orders"].append(po)

    receipt_sources = [
        po for po in data["purchase_orders"] if po["status"] in {"partial_receipt", "received", "closed"}
    ]
    for idx, po in enumerate(receipt_sources[:42], start=1):
        ordered = po["lines"][0]["quantity"]
        received = ordered if po["status"] != "partial_receipt" else max(1, int(ordered * rng.uniform(0.45, 0.92)))
        rejected = 0 if rng.random() > 0.16 else rng.randint(1, max(1, int(received * 0.08)))
        data["receipts"].append(
            {
                "receipt_id": f"RCV-{idx:05d}",
                "po_id": po["po_id"],
                "supplier_id": po["supplier_id"],
                "warehouse_id": po["ship_to"],
                "receipt_date": iso(base_date, rng.randint(95, 180)),
                "packing_slip": f"PK-{rng.randint(10000, 99999)}",
                "status": rng.choice(["accepted", "accepted", "accepted_with_note", "inspection_hold"]),
                "lines": [
                    {
                        "po_line_id": 1,
                        "sku": po["lines"][0]["sku"],
                        "quantity_received": received,
                        "quantity_rejected": rejected,
                        "inspection_status": "passed" if rejected == 0 else "variance",
                    }
                ],
                "receiver": rng.choice(["M. Webb", "T. Alvarez", "S. Nguyen", "K. Price"]),
            }
        )

    receipt_by_po = {r["po_id"]: r for r in data["receipts"]}
    invoice_sources = [po for po in data["purchase_orders"] if po["status"] != "cancelled"]
    for idx, po in enumerate(invoice_sources[:48], start=1):
        line = po["lines"][0]
        qty_factor = rng.choice([1.0, 1.0, 1.0, 0.9, 1.05])
        price_factor = rng.choice([1.0, 1.0, 1.0, 0.98, 1.03])
        inv_line = {
            "po_line_id": 1,
            "sku": line["sku"],
            "quantity_billed": max(1, int(line["quantity"] * qty_factor)),
            "unit_price": money(line["unit_price"] * price_factor),
        }
        status = rng.choice(["approved", "approved", "entered", "on_hold", "paid"])
        receipt = receipt_by_po.get(po["po_id"])
        if not receipt and status in {"approved", "paid"} and rng.random() < 0.35:
            status = "pending_receipt"
        inv = {
            "invoice_id": f"AP-{idx:05d}",
            "supplier_id": po["supplier_id"],
            "po_id": po["po_id"],
            "receipt_id": receipt["receipt_id"] if receipt and rng.random() > 0.12 else None,
            "invoice_date": iso(base_date, rng.randint(110, 185)),
            "currency": "USD",
            "lines": [inv_line],
            "freight": money(rng.choice([0, 0, 75, 125, 260, 410])),
            "status": status,
            "hold_code": None,
        }
        if status in {"on_hold", "pending_receipt"}:
            inv["hold_code"] = rng.choice(["NO_RECEIPT", "QTY_VARIANCE", "PRICE_VARIANCE", "SUPPLIER_REVIEW"])
        subtotal, tax, total = line_total(inv["lines"], inv["freight"])
        inv.update({"subtotal": subtotal, "tax": tax, "total": total})
        data["ap_invoices"].append(inv)

    data["payments"] = []
    for idx, inv in enumerate([i for i in data["ap_invoices"] if i["status"] in {"approved", "paid"}][:28], start=1):
        data["payments"].append(
            {
                "payment_id": f"PAY-{idx:05d}",
                "invoice_id": inv["invoice_id"],
                "supplier_id": inv["supplier_id"],
                "scheduled_date": iso(base_date, rng.randint(150, 230)),
                "amount": inv["total"],
                "currency": inv["currency"],
                "status": "released" if inv["status"] == "paid" else rng.choice(["scheduled", "scheduled", "blocked"]),
            }
        )

    data["approval_events"] = []
    for idx, req in enumerate(data["purchase_requisitions"][:36], start=1):
        data["approval_events"].append(
            {
                "event_id": f"APR-{idx:05d}",
                "object_type": "requisition",
                "object_id": req["requisition_id"],
                "event_date": iso(base_date, rng.randint(60, 150)),
                "actor": rng.choice(["Finance Ops", "Procurement Lead", "Program Owner", "Compliance Desk"]),
                "action": rng.choice(["submitted", "approved", "approved", "returned", "escalated"]),
                "note_code": rng.choice(["BUDGET_OK", "MISSING_QUOTE", "EXPEDITE", "NORMAL_REVIEW", "CAPEX_CHECK"]),
            }
        )

    data["budget_snapshots"] = []
    for program in data["programs"]:
        data["budget_snapshots"].append(
            {
                "snapshot_id": f"BUD-{program['program_id']}",
                "program_id": program["program_id"],
                "snapshot_date": "2026-06-01",
                "budget_cap": program["budget_cap"],
                "committed_amount": program["committed_amount"],
                "pending_invoice_amount": money(
                    sum(
                        inv["total"]
                        for inv in data["ap_invoices"]
                        if any(
                            po["po_id"] == inv["po_id"] and po["program_id"] == program["program_id"]
                            for po in data["purchase_orders"]
                        )
                    )
                ),
                "currency": "USD",
            }
        )

    data["vendor_risk_events"] = []
    for idx in range(1, 36):
        supplier_id = rng.choice(supplier_ids)
        data["vendor_risk_events"].append(
            {
                "event_id": f"VRE-{idx:05d}",
                "supplier_id": supplier_id,
                "event_date": iso(base_date, rng.randint(40, 180)),
                "event_type": rng.choice(
                    ["late_delivery", "invoice_variance", "quality_hold", "bank_change", "duplicate_invoice_review"]
                ),
                "severity": rng.choice(["low", "medium", "medium", "high"]),
                "status": rng.choice(["open", "closed", "monitoring"]),
                "related_object_id": rng.choice(data["purchase_orders"])["po_id"],
            }
        )


def write_outputs(data: dict) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    data = dict(sorted(data.items()))
    DATA_FILE.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    manifest = {
        "environment": "ProcureOps",
        "seed": SEED,
        "generated_at": "2026-06-01T00:00:00Z",
        "data_file": "procureops_data.json",
        "record_counts": {name: len(records) for name, records in data.items()},
        "anchor_ids": ["PRG-AX17", "PRG-NOVA-31", "CR-LMP-228", "RCV-BLUE-14", "RCV-GOLD-27"],
        "notes": "Operational source data only; no task ids or answer keys are present.",
    }
    MANIFEST_FILE.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> None:
    rng = random.Random(SEED)
    data = build_static_records()
    extend_with_noise(data, rng)
    write_outputs(data)
    print(f"Wrote {DATA_FILE}")
    print(f"Wrote {MANIFEST_FILE}")


if __name__ == "__main__":
    main()
