#!/usr/bin/env python3
import json
import random
import sqlite3
from datetime import date, datetime, timedelta
from pathlib import Path


SEED = 140014
BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "payer_ops.db"
MANIFEST_PATH = BASE_DIR / "data_manifest.json"


def iso(value):
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    return value


def pick(rng, values):
    return values[rng.randrange(len(values))]


def add_days(value, days):
    return value + timedelta(days=days)


def create_schema(conn):
    conn.executescript(
        """
        DROP TABLE IF EXISTS plans;
        DROP TABLE IF EXISTS members;
        DROP TABLE IF EXISTS providers;
        DROP TABLE IF EXISTS facilities;
        DROP TABLE IF EXISTS service_codes;
        DROP TABLE IF EXISTS state_sla_rules;
        DROP TABLE IF EXISTS criteria_sources;
        DROP TABLE IF EXISTS authorization_requests;
        DROP TABLE IF EXISTS auth_lines;
        DROP TABLE IF EXISTS existing_authorizations;
        DROP TABLE IF EXISTS evidence_documents;
        DROP TABLE IF EXISTS clinical_facts;
        DROP TABLE IF EXISTS coverage_criteria;
        DROP TABLE IF EXISTS case_review_events;
        DROP TABLE IF EXISTS p2p_sessions;
        DROP TABLE IF EXISTS medication_cases;
        DROP TABLE IF EXISTS medication_trials;
        DROP TABLE IF EXISTS drug_policy_requirements;
        DROP TABLE IF EXISTS assistance_programs;
        DROP TABLE IF EXISTS household_financials;
        DROP TABLE IF EXISTS appeals;
        DROP TABLE IF EXISTS rate_schedules;
        DROP TABLE IF EXISTS encounters;
        DROP TABLE IF EXISTS clinic_costs;
        DROP TABLE IF EXISTS clinic_budgets;
        DROP TABLE IF EXISTS claim_corrections;

        CREATE TABLE plans(
            plan_id TEXT PRIMARY KEY,
            plan_name TEXT,
            plan_type TEXT,
            plan_tier TEXT,
            network_type TEXT,
            state TEXT,
            routine_sla_days INTEGER,
            urgent_sla_hours INTEGER,
            stat_sla_hours INTEGER,
            formulary_type TEXT,
            gold_card_allowed INTEGER
        );
        CREATE TABLE members(
            member_id TEXT PRIMARY KEY,
            member_name TEXT,
            dob TEXT,
            plan_id TEXT,
            residence_state TEXT,
            coverage_start TEXT,
            coverage_end TEXT,
            retro_reinstated_date TEXT,
            cob_primary_status TEXT
        );
        CREATE TABLE providers(
            npi TEXT PRIMARY KEY,
            provider_name TEXT,
            specialty TEXT,
            state TEXT,
            network_status TEXT,
            approval_rate_12m REAL,
            completed_pa_12m INTEGER,
            quarterly_volume INTEGER,
            sanctions_active INTEGER,
            credentials_active INTEGER,
            gold_card_active INTEGER
        );
        CREATE TABLE facilities(
            facility_id TEXT PRIMARY KEY,
            facility_name TEXT,
            state TEXT,
            in_service_area INTEGER
        );
        CREATE TABLE service_codes(
            code TEXT PRIMARY KEY,
            description TEXT,
            service_category TEXT,
            pa_required INTEGER,
            covered INTEGER,
            notification_only INTEGER,
            gold_card_exclusion INTEGER,
            delegated_program TEXT,
            external_vendor TEXT,
            specialty_program TEXT,
            mandatory_md_review INTEGER,
            estimated_allowed_amount REAL
        );
        CREATE TABLE state_sla_rules(
            state TEXT,
            plan_type_filter TEXT,
            routine_days INTEGER,
            urgent_hours INTEGER,
            stat_hours INTEGER,
            day_type TEXT,
            notes TEXT
        );
        CREATE TABLE criteria_sources(
            source_id TEXT PRIMARY KEY,
            source_name TEXT,
            precedence_rank INTEGER,
            plan_type_filter TEXT,
            service_category_filter TEXT,
            effective_date TEXT
        );
        CREATE TABLE authorization_requests(
            case_id TEXT PRIMARY KEY,
            member_id TEXT,
            request_date TEXT,
            receipt_timestamp TEXT,
            submission_channel TEXT,
            urgency_attested TEXT,
            place_of_service TEXT,
            service_start TEXT,
            service_end TEXT,
            requesting_npi TEXT,
            servicing_npi TEXT,
            facility_id TEXT,
            primary_icd10 TEXT,
            clinical_indication TEXT,
            status TEXT,
            current_stage TEXT,
            rendered_before_submission INTEGER,
            oon_exception INTEGER,
            cob_primary_processed INTEGER,
            requested_total_units INTEGER,
            estimated_total_allowed REAL,
            target_bucket TEXT
        );
        CREATE TABLE auth_lines(
            case_id TEXT,
            line_no INTEGER,
            cpt_code TEXT,
            modifier TEXT,
            units INTEGER,
            service_category TEXT
        );
        CREATE TABLE existing_authorizations(
            existing_auth_id TEXT PRIMARY KEY,
            member_id TEXT,
            cpt_code TEXT,
            service_start TEXT,
            service_end TEXT,
            status TEXT,
            decision_date TEXT,
            original_case_id TEXT
        );
        CREATE TABLE evidence_documents(
            doc_id TEXT PRIMARY KEY,
            case_id TEXT,
            doc_type TEXT,
            doc_date TEXT,
            source_system TEXT,
            source_rank INTEGER,
            is_current INTEGER,
            title TEXT,
            summary TEXT
        );
        CREATE TABLE clinical_facts(
            case_id TEXT,
            criterion_key TEXT,
            fact_value TEXT,
            fact_date TEXT,
            source_doc_id TEXT,
            source_rank INTEGER,
            confidence_flag TEXT
        );
        CREATE TABLE coverage_criteria(
            service_category TEXT,
            criterion_key TEXT,
            criterion_label TEXT,
            required_value TEXT,
            criteria_source_id TEXT,
            plan_type_filter TEXT,
            is_required_for_approval INTEGER
        );
        CREATE TABLE case_review_events(
            event_id TEXT PRIMARY KEY,
            case_id TEXT,
            event_timestamp TEXT,
            stage TEXT,
            reviewer_role TEXT,
            event_type TEXT,
            outcome TEXT,
            notes TEXT
        );
        CREATE TABLE p2p_sessions(
            p2p_id TEXT PRIMARY KEY,
            case_id TEXT,
            scheduled_at TEXT,
            completed_at TEXT,
            requesting_provider_joined INTEGER,
            new_information INTEGER,
            outcome TEXT,
            duration_minutes INTEGER
        );
        CREATE TABLE medication_cases(
            med_case_id TEXT PRIMARY KEY,
            member_id TEXT,
            drug_name TEXT,
            diagnosis_code TEXT,
            requested_dose TEXT,
            request_date TEXT,
            payer_formulary_status TEXT,
            prescriber_npi TEXT,
            target_bucket TEXT
        );
        CREATE TABLE medication_trials(
            trial_id TEXT PRIMARY KEY,
            med_case_id TEXT,
            medication_name TEXT,
            drug_class TEXT,
            start_date TEXT,
            end_date TEXT,
            outcome TEXT,
            adverse_effect TEXT,
            documented INTEGER
        );
        CREATE TABLE drug_policy_requirements(
            drug_name TEXT,
            plan_type_filter TEXT,
            requirement_key TEXT,
            requirement_label TEXT,
            required_value TEXT,
            source_rank INTEGER
        );
        CREATE TABLE assistance_programs(
            program_id TEXT PRIMARY KEY,
            drug_name TEXT,
            max_income_fpl INTEGER,
            requires_commercial_insurance INTEGER,
            excludes_government_plan INTEGER,
            requires_denial INTEGER,
            form_name TEXT
        );
        CREATE TABLE household_financials(
            member_id TEXT PRIMARY KEY,
            household_size INTEGER,
            annual_income REAL,
            insurance_type TEXT,
            has_denial_letter INTEGER,
            assistance_consent_on_file INTEGER
        );
        CREATE TABLE appeals(
            appeal_id TEXT PRIMARY KEY,
            case_or_med_case_id TEXT,
            appeal_subject_type TEXT,
            adverse_notice_date TEXT,
            appeal_received_date TEXT,
            expedited_attestation INTEGER,
            new_evidence_received INTEGER,
            authorized_representative_on_file INTEGER,
            original_decision_type TEXT,
            plan_type TEXT,
            target_bucket TEXT
        );
        CREATE TABLE rate_schedules(
            rate_id TEXT PRIMARY KEY,
            payer TEXT,
            plan_type TEXT,
            service_category TEXT,
            cpt_code TEXT,
            state TEXT,
            effective_start TEXT,
            effective_end TEXT,
            benchmark_rate REAL,
            benchmark_source TEXT
        );
        CREATE TABLE encounters(
            encounter_id TEXT PRIMARY KEY,
            clinic_id TEXT,
            service_date TEXT,
            payer TEXT,
            plan_type TEXT,
            member_id TEXT,
            cpt_code TEXT,
            service_category TEXT,
            units INTEGER,
            billed_amount REAL,
            paid_amount REAL,
            denial_code TEXT,
            authorization_case_id TEXT
        );
        CREATE TABLE clinic_costs(
            cost_id TEXT PRIMARY KEY,
            clinic_id TEXT,
            fiscal_year INTEGER,
            service_category TEXT,
            direct_cost_per_unit REAL,
            allocated_overhead_per_unit REAL
        );
        CREATE TABLE clinic_budgets(
            budget_id TEXT PRIMARY KEY,
            clinic_id TEXT,
            fiscal_year INTEGER,
            payer TEXT,
            service_category TEXT,
            expected_units INTEGER,
            expected_net_revenue REAL,
            expected_margin_pct REAL
        );
        CREATE TABLE claim_corrections(
            correction_id TEXT PRIMARY KEY,
            encounter_id TEXT,
            correction_type TEXT,
            expected_recovery_amount REAL,
            correction_deadline TEXT,
            status TEXT
        );
        """
    )


def insert_static_data(conn):
    plans = [
        ("PLN001", "Ticonderoga Select Gold", "Commercial", "Gold", "HMO", "CA", 5, 72, 24, "closed", 1),
        ("PLN002", "Ticonderoga Choice Silver", "Commercial", "Silver", "PPO", "NY", 3, 72, 24, "open", 1),
        (
            "PLN003",
            "Ticonderoga Medicare Advantage Plus",
            "Medicare Advantage",
            "Plus",
            "HMO",
            "FL",
            7,
            72,
            24,
            "closed",
            0,
        ),
        (
            "PLN004",
            "Ticonderoga Medicare Advantage Value",
            "Medicare Advantage",
            "Value",
            "PPO",
            "PA",
            7,
            72,
            24,
            "closed",
            0,
        ),
        (
            "PLN005",
            "Ticonderoga Medicaid Managed Care",
            "Medicaid",
            "Standard",
            "HMO",
            "TX",
            4,
            48,
            12,
            "state preferred",
            0,
        ),
        ("PLN006", "Ticonderoga Exchange Bronze", "Exchange", "Bronze", "EPO", "IL", 5, 72, 24, "closed", 1),
        ("PLN007", "Ticonderoga Employer Premier", "Commercial", "Premier", "PPO", "CA", 5, 72, 24, "open", 1),
        ("PLN008", "Ticonderoga Dual Eligible Care", "Dual Eligible", "Standard", "HMO", "NY", 3, 48, 12, "closed", 0),
    ]
    conn.executemany("INSERT INTO plans VALUES (?,?,?,?,?,?,?,?,?,?,?)", plans)

    facilities = [
        ("FAC001", "Riverside Community Clinic", "CA", 1),
        ("FAC002", "North Harbor Imaging Center", "NY", 1),
        ("FAC003", "Lakeside Rehabilitation Institute", "IL", 1),
        ("FAC004", "Gulf Coast Specialty Hospital", "FL", 1),
        ("FAC005", "Hill Country Ambulatory Center", "TX", 1),
        ("FAC006", "Summit Out-of-Area Hospital", "AZ", 0),
    ]
    conn.executemany("INSERT INTO facilities VALUES (?,?,?,?)", facilities)

    services = [
        ("97110", "Therapeutic exercise", "Physical Therapy", 1, 1, 0, 0, "none", "none", "rehab", 0, 92.00),
        ("97530", "Therapeutic activities", "Physical Therapy", 1, 1, 0, 0, "none", "none", "rehab", 0, 104.00),
        (
            "70553",
            "MRI brain with contrast",
            "Advanced Imaging",
            1,
            1,
            0,
            0,
            "radiology vendor",
            "MedImage Review",
            "radiology",
            1,
            890.00,
        ),
        (
            "78431",
            "PET myocardial perfusion imaging",
            "Cardiology Imaging",
            1,
            1,
            0,
            1,
            "radiology vendor",
            "MedImage Review",
            "cardiology",
            1,
            2350.00,
        ),
        (
            "29881",
            "Knee arthroscopy meniscectomy",
            "Orthopedic Surgery",
            1,
            1,
            0,
            1,
            "none",
            "none",
            "surgery",
            1,
            6400.00,
        ),
        (
            "64483",
            "Transforaminal epidural injection",
            "Pain Management",
            1,
            1,
            0,
            0,
            "none",
            "none",
            "pain",
            1,
            1260.00,
        ),
        (
            "E0601",
            "Continuous airway pressure device",
            "Durable Medical Equipment",
            1,
            1,
            0,
            0,
            "DME vendor",
            "CareEquip Review",
            "sleep",
            0,
            780.00,
        ),
        ("J3301", "Triamcinolone injection", "Office Drug", 0, 1, 1, 0, "none", "none", "medical drug", 0, 38.00),
        (
            "S9999",
            "Experimental cellular therapy",
            "Experimental Therapy",
            1,
            0,
            0,
            1,
            "none",
            "none",
            "experimental",
            1,
            18500.00,
        ),
        (
            "G0299",
            "Home health skilled nursing",
            "Home Health",
            1,
            1,
            0,
            0,
            "home health vendor",
            "HomeCare Review",
            "home health",
            0,
            210.00,
        ),
        (
            "99214",
            "Established patient office visit",
            "Evaluation Management",
            0,
            1,
            1,
            0,
            "none",
            "none",
            "office visit",
            0,
            155.00,
        ),
        ("97140", "Manual therapy techniques", "Physical Therapy", 1, 1, 0, 0, "none", "none", "rehab", 0, 88.00),
    ]
    conn.executemany("INSERT INTO service_codes VALUES (?,?,?,?,?,?,?,?,?,?,?,?)", services)

    sla_rules = [
        ("CA", "Commercial", 5, 72, 24, "calendar", "California commercial default"),
        ("CA", "Exchange", 5, 72, 24, "calendar", "California exchange default"),
        ("NY", "Commercial", 3, 72, 24, "business", "New York routine cases use business days"),
        ("NY", "Dual Eligible", 3, 48, 12, "business", "Dual eligible expedited handling"),
        ("FL", "Medicare Advantage", 7, 72, 24, "calendar", "Medicare Advantage plan rule"),
        ("PA", "Medicare Advantage", 7, 72, 24, "calendar", "Pennsylvania Medicare Advantage rule"),
        ("TX", "Medicaid", 4, 48, 12, "calendar", "Texas Medicaid managed care rule"),
        ("IL", "Exchange", 5, 72, 24, "calendar", "Illinois exchange rule"),
        ("AZ", "Commercial", 2, 48, 12, "calendar", "Facility state conflict for out-of-area services"),
    ]
    conn.executemany("INSERT INTO state_sla_rules VALUES (?,?,?,?,?,?,?)", sla_rules)

    sources = [
        ("SRC001", "CMS NCD or LCD", 1, "Medicare Advantage", "ALL", "2025-01-01"),
        ("SRC002", "State Medicaid UM Manual", 1, "Medicaid", "ALL", "2025-01-01"),
        ("SRC003", "Ticonderoga Medical Policy", 2, "ALL", "ALL", "2025-01-01"),
        ("SRC004", "InterQual Criteria", 3, "ALL", "ALL", "2025-01-01"),
        ("SRC005", "MCG Care Guidelines", 4, "ALL", "ALL", "2025-01-01"),
    ]
    conn.executemany("INSERT INTO criteria_sources VALUES (?,?,?,?,?,?)", sources)

    criteria = []
    criteria_specs = {
        "Physical Therapy": [
            ("functional_limitation", "Documented functional limitation", "met"),
            ("plan_of_care", "Signed plan of care", "met"),
            ("measurable_progress", "Measurable progress or restorative potential", "met"),
        ],
        "Advanced Imaging": [
            ("conservative_treatment", "Recent conservative treatment trial", "met"),
            ("red_flag_symptoms", "Red flag or neurologic symptoms", "met"),
            ("prior_imaging_reviewed", "Prior imaging reviewed", "met"),
        ],
        "Cardiology Imaging": [
            ("known_cad_or_high_risk", "Known coronary disease or high risk symptoms", "met"),
            ("stress_test_inconclusive", "Prior stress test inconclusive", "met"),
            ("management_change_expected", "Result expected to change management", "met"),
        ],
        "Orthopedic Surgery": [
            ("failed_conservative_care", "Failed conservative care", "met"),
            ("imaging_confirms_pathology", "Imaging confirms pathology", "met"),
            ("mechanical_symptoms", "Mechanical symptoms documented", "met"),
        ],
        "Pain Management": [
            ("radicular_pain", "Radicular pain pattern", "met"),
            ("failed_conservative_care", "Failed conservative care", "met"),
            ("imaging_correlates", "Imaging correlates with symptoms", "met"),
        ],
        "Durable Medical Equipment": [
            ("diagnosis_confirmed", "Diagnosis confirmed by testing", "met"),
            ("face_to_face_documented", "Face-to-face evaluation documented", "met"),
            ("equipment_trial_needed", "Equipment medically necessary", "met"),
        ],
        "Home Health": [
            ("homebound_status", "Homebound status documented", "met"),
            ("skilled_need", "Intermittent skilled need documented", "met"),
            ("physician_plan", "Physician ordered plan of care", "met"),
        ],
        "Experimental Therapy": [
            ("not_experimental", "Service is not investigational or experimental", "met"),
            ("standard_options_failed", "Standard covered options attempted", "met"),
        ],
    }
    for category, rows in criteria_specs.items():
        for key, label, required in rows:
            criteria.append((category, key, label, required, "SRC003", "ALL", 1))
            criteria.append((category, key, label, required, "SRC004", "ALL", 1))
        if category in ("Advanced Imaging", "Cardiology Imaging", "Orthopedic Surgery"):
            criteria.append(
                (
                    category,
                    "cms_specific_indication",
                    "CMS indication satisfied when applicable",
                    "met",
                    "SRC001",
                    "Medicare Advantage",
                    1,
                )
            )
    conn.executemany("INSERT INTO coverage_criteria VALUES (?,?,?,?,?,?,?)", criteria)

    drug_requirements = [
        ("Remicade", "ALL", "diagnosis", "Covered inflammatory diagnosis", "met", 1),
        ("Remicade", "ALL", "step_therapy", "Trial of preferred biosimilar or exception", "met", 1),
        ("Remicade", "ALL", "tb_screen", "Tuberculosis screening documented", "met", 2),
        ("Dupixent", "ALL", "diagnosis", "Covered dermatitis or asthma diagnosis", "met", 1),
        ("Dupixent", "ALL", "topical_failure", "Failure of topical therapy", "met", 1),
        ("Eliquis", "ALL", "diagnosis", "Covered anticoagulation indication", "met", 1),
        ("Ozempic", "ALL", "diagnosis", "Type 2 diabetes diagnosis", "met", 1),
        ("Ozempic", "ALL", "step_therapy", "Metformin trial or contraindication", "met", 1),
        ("Humira", "ALL", "diagnosis", "Covered autoimmune diagnosis", "met", 1),
        ("Humira", "ALL", "step_therapy", "Preferred biosimilar trial or exception", "met", 1),
    ]
    conn.executemany("INSERT INTO drug_policy_requirements VALUES (?,?,?,?,?,?)", drug_requirements)

    assistance = [
        ("AP001", "Remicade", 500, 1, 1, 1, "Remicade Access Enrollment"),
        ("AP002", "Dupixent", 400, 1, 1, 1, "Dupixent MyWay Enrollment"),
        ("AP003", "Eliquis", 300, 1, 1, 1, "Anticoagulant Support Form"),
        ("AP004", "Ozempic", 400, 1, 1, 1, "Diabetes Savings Support Form"),
        ("AP005", "Humira", 500, 1, 1, 1, "Immunology Complete Enrollment"),
    ]
    conn.executemany("INSERT INTO assistance_programs VALUES (?,?,?,?,?,?,?)", assistance)

    return plans, facilities, services, criteria_specs


def generate_people(conn, rng, plans):
    first_names = [
        "Avery",
        "Jordan",
        "Taylor",
        "Morgan",
        "Riley",
        "Casey",
        "Quinn",
        "Reese",
        "Parker",
        "Jamie",
        "Drew",
        "Alex",
        "Cameron",
        "Rowan",
        "Blake",
        "Harper",
        "Emerson",
        "Hayden",
        "Skyler",
        "Kendall",
        "Robin",
        "Logan",
        "Sydney",
        "Bailey",
    ]
    last_names = [
        "Bennett",
        "Carter",
        "Diaz",
        "Evans",
        "Foster",
        "Garcia",
        "Hayes",
        "Irving",
        "Johnson",
        "Kim",
        "Lopez",
        "Miller",
        "Nguyen",
        "Owens",
        "Patel",
        "Quinn",
        "Roberts",
        "Sanchez",
        "Turner",
        "Underwood",
        "Valdez",
        "Walker",
        "Young",
        "Zimmer",
    ]
    plan_by_id = {row[0]: row for row in plans}
    members = []
    for idx in range(60):
        plan = plans[idx % len(plans)] if idx < 24 else pick(rng, plans)
        start = date(2023, 1, 1) + timedelta(days=rng.randint(0, 500))
        if idx in {7, 19, 31, 44}:
            end = date(2025, 1, 31) + timedelta(days=rng.randint(0, 90))
        elif idx in {12, 38}:
            end = date(2025, 5, 15)
        else:
            end = date(2026, 12, 31)
        retro = "2025-06-01" if idx in {12, 38} else None
        member = (
            f"MBR{idx + 1:04d}",
            f"{first_names[idx % len(first_names)]} {last_names[(idx * 3) % len(last_names)]}",
            iso(date(1950, 1, 1) + timedelta(days=rng.randint(6000, 25000))),
            plan[0],
            plan[5] if rng.random() < 0.75 else pick(rng, ["CA", "NY", "FL", "TX", "IL", "PA"]),
            iso(start),
            iso(end),
            retro,
            pick(rng, ["processed", "not_applicable", "pending", "primary_other_payer"]),
        )
        members.append(member)
    conn.executemany("INSERT INTO members VALUES (?,?,?,?,?,?,?,?,?)", members)

    specialties = [
        "Orthopedics",
        "Cardiology",
        "Physical Medicine",
        "Neurology",
        "Pain Medicine",
        "Primary Care",
        "Pulmonology",
        "Rheumatology",
        "Dermatology",
        "Endocrinology",
    ]
    providers = []
    for idx in range(64):
        approval_rate = round(rng.uniform(0.55, 0.96), 3)
        completed = rng.randint(12, 180)
        volume = rng.randint(5, 70)
        sanctions = 1 if idx in {9, 37} else 0
        credentials = 0 if idx in {14, 42} else 1
        network = "in_network" if rng.random() < 0.78 else pick(rng, ["out_of_network", "delegated_only"])
        gold = (
            1
            if approval_rate >= 0.86
            and completed >= 50
            and volume >= 12
            and network == "in_network"
            and not sanctions
            and credentials
            else 0
        )
        providers.append(
            (
                f"{1450000000 + idx}",
                f"{first_names[(idx + 5) % len(first_names)]} {last_names[(idx * 5) % len(last_names)]}, MD",
                specialties[idx % len(specialties)],
                pick(rng, ["CA", "NY", "FL", "TX", "IL", "PA", "AZ"]),
                network,
                approval_rate,
                completed,
                volume,
                sanctions,
                credentials,
                gold,
            )
        )
    conn.executemany("INSERT INTO providers VALUES (?,?,?,?,?,?,?,?,?,?,?)", providers)

    financials = []
    for idx, member in enumerate(members):
        plan_type = plan_by_id[member[3]][2]
        household_size = rng.randint(1, 5)
        income = float(rng.randint(28000, 145000))
        insurance_type = (
            "government" if plan_type in ("Medicare Advantage", "Medicaid", "Dual Eligible") else "commercial"
        )
        financials.append((member[0], household_size, income, insurance_type, rng.randint(0, 1), rng.randint(0, 1)))
    conn.executemany("INSERT INTO household_financials VALUES (?,?,?,?,?,?)", financials)

    return members, providers


def generate_authorizations(conn, rng, members, providers, facilities, services, criteria_specs):
    service_by_code = {row[0]: row for row in services}
    criteria_by_category = criteria_specs
    auth_targets = {
        "train_intake_batch": range(0, 6),
        "train_clinical_batch": range(6, 12),
        "test_intake_batch": range(12, 18),
        "test_p2p_batch": range(18, 24),
    }
    bucket_by_index = {}
    for bucket, indexes in auth_targets.items():
        for idx in indexes:
            bucket_by_index[idx] = bucket

    cases = []
    lines = []
    existing = []
    docs = []
    facts = []
    events = []
    p2ps = []
    appeals = []
    service_choices = [row for row in services if row[3] == 1]
    start_date = date(2025, 2, 1)

    for idx in range(156):
        case_id = f"AUTH{idx + 1:05d}"
        member = members[idx % len(members)] if idx < 40 else pick(rng, members)
        service = service_choices[idx % len(service_choices)] if idx < 36 else pick(rng, service_choices)
        if idx in {4, 16, 28, 52, 84}:
            service = service_by_code["S9999"]
        requesting = providers[(idx * 3) % len(providers)]
        servicing = providers[(idx * 5 + 7) % len(providers)]
        facility = facilities[idx % len(facilities)] if idx < 30 else pick(rng, facilities)
        req_date = start_date + timedelta(days=idx % 170)
        receipt_time = datetime.combine(req_date, datetime.min.time()) + timedelta(
            hours=8 + (idx % 9), minutes=(idx * 7) % 60
        )
        service_start = req_date + timedelta(days=rng.randint(1, 21))
        service_end = service_start + timedelta(days=rng.randint(0, 28))
        urgency = pick(rng, ["routine", "urgent", "stat"])
        if idx % 11:
            urgency = "routine"
        rendered = 1 if idx in {3, 15, 40, 61, 103} else 0
        oon_exception = 1 if idx in {5, 22, 77, 111} else rng.randint(0, 1) if servicing[4] != "in_network" else 0
        cob_processed = 0 if idx in {2, 14, 55, 90} else 1
        total_units = rng.randint(1, 16)
        status = pick(rng, ["open", "pending clinical review", "approved", "denied", "withdrawn"])
        if idx < 30:
            status = pick(rng, ["open", "pending clinical review", "pending intake", "denied"])
        stage = pick(rng, ["intake", "nurse_review", "md_review", "p2p_pending", "appeal_window", "closed"])
        if "intake" in (bucket_by_index.get(idx) or ""):
            stage = "intake"
        elif bucket_by_index.get(idx) == "test_p2p_batch":
            stage = pick(rng, ["md_review", "p2p_pending"])
        elif bucket_by_index.get(idx) == "train_clinical_batch":
            stage = pick(rng, ["nurse_review", "md_review"])
        case_row = (
            case_id,
            member[0],
            iso(req_date),
            receipt_time.isoformat(timespec="minutes"),
            pick(rng, ["portal", "fax", "edi", "phone"]),
            urgency,
            pick(rng, ["office", "outpatient hospital", "ambulatory surgical center", "home"]),
            iso(service_start),
            iso(service_end),
            requesting[0],
            servicing[0],
            facility[0],
            pick(rng, ["M25.561", "M54.16", "I25.10", "R07.9", "G47.33", "L20.9", "M06.9"]),
            pick(
                rng,
                [
                    "Persistent symptoms despite conservative care",
                    "Specialist requests review after inconclusive response",
                    "Documentation includes conflicting source notes",
                    "Prior service history is incomplete",
                    "Request includes a close-call clinical indication",
                ],
            ),
            status,
            stage,
            rendered,
            oon_exception,
            cob_processed,
            total_units,
            round(total_units * service[11], 2),
            bucket_by_index.get(
                idx, pick(rng, ["routine_ops_queue", "seasonal_volume_review", "provider_outreach_sample", None])
            ),
        )
        cases.append(case_row)

        line_count = 2 if idx % 9 == 0 else 1
        for line_no in range(1, line_count + 1):
            line_service = service
            if line_no == 2:
                line_service = pick(rng, service_choices)
            lines.append(
                (
                    case_id,
                    line_no,
                    line_service[0],
                    pick(rng, ["", "GP", "LT", "RT", "KX"]),
                    rng.randint(1, 8),
                    line_service[2],
                )
            )

        if idx % 5 == 0 or idx in {1, 13, 21, 35}:
            existing.append(
                (
                    f"EXA{idx + 1:05d}",
                    member[0],
                    service[0],
                    iso(service_start - timedelta(days=rng.randint(3, 18))),
                    iso(service_end + timedelta(days=rng.randint(1, 20))),
                    pick(rng, ["open", "approved", "denied", "expired"]),
                    iso(req_date - timedelta(days=rng.randint(2, 35))),
                    case_id if idx % 10 == 0 else None,
                )
            )

        doc_count = 2 + (idx % 3 == 0)
        for doc_no in range(doc_count):
            current = 1 if doc_no == 0 else 0
            doc_date = req_date - timedelta(days=(doc_no * 90) + rng.randint(0, 18))
            doc_id = f"DOC{idx + 1:05d}_{doc_no + 1}"
            docs.append(
                (
                    doc_id,
                    case_id,
                    pick(
                        rng,
                        [
                            "clinical note",
                            "imaging report",
                            "therapy plan",
                            "lab result",
                            "letter of medical necessity",
                        ],
                    ),
                    iso(doc_date),
                    pick(rng, ["provider_portal", "fax_index", "ehr_feed", "vendor_extract"]),
                    doc_no + 1,
                    current,
                    f"{service[2]} supporting document {doc_no + 1}",
                    pick(
                        rng,
                        [
                            "Current findings are partly documented",
                            "Older note conflicts with current severity",
                            "Objective measurements are present",
                            "Source rank requires reconciliation",
                        ],
                    ),
                )
            )

        category = service[2]
        applicable_criteria = criteria_by_category.get(
            category, [("medical_necessity", "Medical necessity documented", "met")]
        )
        for cidx, (key, _label, _required) in enumerate(applicable_criteria):
            if idx % 17 == 0 and cidx == 0:
                value = "not_met"
            elif idx % 13 == 0 and cidx == 1:
                value = "unclear"
            elif service[0] == "S9999" and key == "not_experimental":
                value = "not_met"
            else:
                value = pick(rng, ["met", "met", "met", "unclear"])
            source_rank = 1 if (idx + cidx) % 4 == 0 else 2 + (cidx % 3)
            facts.append(
                (
                    case_id,
                    key,
                    value,
                    iso(req_date - timedelta(days=rng.randint(0, 20))),
                    f"DOC{idx + 1:05d}_1",
                    source_rank,
                    pick(rng, ["clear", "conflicting", "stale", "partial"]),
                )
            )
            if idx % 19 == 0 and cidx == 0:
                facts.append(
                    (
                        case_id,
                        key,
                        "met" if value != "met" else "unclear",
                        iso(req_date - timedelta(days=120)),
                        f"DOC{idx + 1:05d}_2",
                        source_rank + 2,
                        "stale",
                    )
                )

        events.append(
            (
                f"EVT{idx + 1:05d}_1",
                case_id,
                receipt_time.isoformat(timespec="minutes"),
                "intake",
                "intake_coordinator",
                "received",
                "queued",
                "Case received for verification",
            )
        )
        if idx % 2 == 0:
            events.append(
                (
                    f"EVT{idx + 1:05d}_2",
                    case_id,
                    (receipt_time + timedelta(hours=6)).isoformat(timespec="minutes"),
                    "clinical_review",
                    pick(rng, ["nurse", "medical_director"]),
                    "clinical_screen",
                    pick(rng, ["approve", "escalate_to_md", "request_more_info", "adverse_pending"]),
                    "Review note references evidence hierarchy",
                )
            )
        if idx in set(range(18, 24)) or idx % 23 == 0:
            completed = receipt_time + timedelta(days=2, hours=2)
            p2ps.append(
                (
                    f"P2P{idx + 1:05d}",
                    case_id,
                    (receipt_time + timedelta(days=1)).isoformat(timespec="minutes"),
                    completed.isoformat(timespec="minutes") if idx % 4 != 0 else None,
                    0 if idx % 7 == 0 else 1,
                    1 if idx % 3 == 0 else 0,
                    pick(rng, ["upheld", "overturned", "additional_info_requested", "no_show"]),
                    rng.randint(8, 25),
                )
            )
        if idx % 12 == 0:
            appeals.append(
                (
                    f"APL_AUTH{idx + 1:05d}",
                    case_id,
                    "authorization",
                    iso(req_date + timedelta(days=2)),
                    iso(req_date + timedelta(days=10)),
                    1 if urgency != "routine" else 0,
                    rng.randint(0, 1),
                    rng.randint(0, 1),
                    pick(rng, ["medical necessity denial", "administrative denial", "benefit exclusion"]),
                    pick(rng, ["Commercial", "Medicare Advantage", "Medicaid", "Exchange"]),
                    pick(rng, ["routine_appeals_review", "seasonal_volume_review"]),
                )
            )

    conn.executemany("INSERT INTO authorization_requests VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", cases)
    conn.executemany("INSERT INTO auth_lines VALUES (?,?,?,?,?,?)", lines)
    conn.executemany("INSERT INTO existing_authorizations VALUES (?,?,?,?,?,?,?,?)", existing)
    conn.executemany("INSERT INTO evidence_documents VALUES (?,?,?,?,?,?,?,?,?)", docs)
    conn.executemany("INSERT INTO clinical_facts VALUES (?,?,?,?,?,?,?)", facts)
    conn.executemany("INSERT INTO case_review_events VALUES (?,?,?,?,?,?,?,?)", events)
    conn.executemany("INSERT INTO p2p_sessions VALUES (?,?,?,?,?,?,?,?)", p2ps)
    conn.executemany("INSERT INTO appeals VALUES (?,?,?,?,?,?,?,?,?,?,?)", appeals)

    target_cases = {bucket: [f"AUTH{i + 1:05d}" for i in indexes] for bucket, indexes in auth_targets.items()}
    return cases, target_cases


def generate_medications(conn, rng, members, providers):
    drugs = ["Remicade", "Dupixent", "Eliquis", "Ozempic", "Humira"]
    diagnoses = {
        "Remicade": ["K50.90", "M06.9"],
        "Dupixent": ["L20.9", "J45.50"],
        "Eliquis": ["I48.91", "I82.409"],
        "Ozempic": ["E11.9", "E66.9"],
        "Humira": ["M06.9", "L40.50"],
    }
    target_map = {
        "train_drug_batch": range(0, 4),
        "test_drug_batch": range(4, 8),
    }
    bucket_by_index = {}
    for bucket, indexes in target_map.items():
        for idx in indexes:
            bucket_by_index[idx] = bucket

    med_cases = []
    trials = []
    appeals = []
    for idx in range(40):
        drug = drugs[idx % len(drugs)] if idx < 12 else pick(rng, drugs)
        request_date = date(2025, 4, 1) + timedelta(days=idx * 5)
        med_case_id = f"MED{idx + 1:05d}"
        med_cases.append(
            (
                med_case_id,
                members[(idx * 2) % len(members)][0],
                drug,
                pick(rng, diagnoses[drug]),
                pick(rng, ["standard starting dose", "dose escalation", "maintenance dose", "weight-based dose"]),
                iso(request_date),
                pick(rng, ["preferred", "non_preferred", "step_required", "excluded_pending_exception"]),
                providers[(idx * 4 + 3) % len(providers)][0],
                bucket_by_index.get(idx, pick(rng, ["pharmacy_ops_queue", "specialty_drug_review", None])),
            )
        )
        for trial_no in range(1, 1 + rng.randint(1, 3)):
            documented = 0 if idx % 9 == 0 and trial_no == 1 else 1
            trials.append(
                (
                    f"TRIAL{idx + 1:05d}_{trial_no}",
                    med_case_id,
                    pick(
                        rng,
                        [
                            "metformin",
                            "adalimumab biosimilar",
                            "topical steroid",
                            "warfarin",
                            "methotrexate",
                            "inhaled corticosteroid",
                        ],
                    ),
                    pick(rng, ["preferred agent", "conventional therapy", "biosimilar", "supportive therapy"]),
                    iso(request_date - timedelta(days=120 + trial_no * 40)),
                    iso(request_date - timedelta(days=30 + trial_no * 10)),
                    pick(rng, ["failed", "partial response", "contraindicated", "not tolerated", "successful"]),
                    pick(rng, ["none", "rash", "nausea", "bleeding risk", "lab abnormality"]),
                    documented,
                )
            )
        if idx % 3 == 0 or idx < 8:
            appeals.append(
                (
                    f"APL_MED{idx + 1:05d}",
                    med_case_id,
                    "medication",
                    iso(request_date + timedelta(days=2)),
                    iso(request_date + timedelta(days=9)),
                    rng.randint(0, 1),
                    rng.randint(0, 1),
                    rng.randint(0, 1),
                    pick(rng, ["formulary denial", "step therapy denial", "medical necessity denial"]),
                    pick(rng, ["Commercial", "Medicare Advantage", "Medicaid", "Exchange"]),
                    bucket_by_index.get(idx, pick(rng, ["pharmacy_appeals_review", "routine_appeals_review"])),
                )
            )

    conn.executemany("INSERT INTO medication_cases VALUES (?,?,?,?,?,?,?,?,?)", med_cases)
    conn.executemany("INSERT INTO medication_trials VALUES (?,?,?,?,?,?,?,?,?)", trials)
    conn.executemany("INSERT INTO appeals VALUES (?,?,?,?,?,?,?,?,?,?,?)", appeals)
    target_meds = {bucket: [f"MED{i + 1:05d}" for i in indexes] for bucket, indexes in target_map.items()}
    return med_cases, target_meds


def generate_reimbursement(conn, rng, members, services, auth_cases):
    clinics = [
        ("CLN001", "Riverside Community Clinic", "CA"),
        ("CLN002", "North Harbor Health", "NY"),
        ("CLN003", "Lakeside Rehab Center", "IL"),
        ("CLN004", "Gulf Coast Specialty Group", "FL"),
    ]
    payers = [
        ("Ticonderoga Health", "Commercial"),
        ("Ticonderoga Health", "Medicare Advantage"),
        ("Ticonderoga Health", "Medicaid"),
        ("Ticonderoga Health", "Exchange"),
        ("Ticonderoga Health", "Dual Eligible"),
    ]
    categories = sorted({row[2] for row in services if row[4] == 1})
    service_by_category = {}
    for service in services:
        service_by_category.setdefault(service[2], []).append(service)

    rates = []
    rate_idx = 1
    for payer, plan_type in payers:
        for category in categories:
            for service in service_by_category[category][:2]:
                for state in ["CA", "NY", "FL", "TX", "IL", "PA"]:
                    base = service[11] * rng.uniform(0.62, 1.18)
                    rates.append(
                        (
                            f"RATE{rate_idx:05d}",
                            payer,
                            plan_type,
                            category,
                            service[0],
                            state,
                            "2024-01-01",
                            "2024-12-31",
                            round(base * 0.93, 2),
                            "legacy contract",
                        )
                    )
                    rate_idx += 1
                    rates.append(
                        (
                            f"RATE{rate_idx:05d}",
                            payer,
                            plan_type,
                            category,
                            service[0],
                            state,
                            "2025-01-01",
                            "2025-12-31",
                            round(base, 2),
                            "current contract",
                        )
                    )
                    rate_idx += 1
                    if rng.random() < 0.25:
                        rates.append(
                            (
                                f"RATE{rate_idx:05d}",
                                payer,
                                plan_type,
                                category,
                                service[0],
                                state,
                                "2026-01-01",
                                "2026-12-31",
                                round(base * 1.05, 2),
                                "future draft",
                            )
                        )
                        rate_idx += 1
    conn.executemany("INSERT INTO rate_schedules VALUES (?,?,?,?,?,?,?,?,?,?)", rates)

    costs = []
    cost_idx = 1
    for clinic_id, _name, _state in clinics:
        for fiscal_year in [2024, 2025]:
            for category in categories:
                costs.append(
                    (
                        f"COST{cost_idx:05d}",
                        clinic_id,
                        fiscal_year,
                        category,
                        round(rng.uniform(35, 480), 2),
                        round(rng.uniform(18, 210), 2),
                    )
                )
                cost_idx += 1
    conn.executemany("INSERT INTO clinic_costs VALUES (?,?,?,?,?,?)", costs)

    budgets = []
    budget_idx = 1
    for clinic_id, _name, _state in clinics:
        for payer, _plan_type in payers:
            for category in categories:
                expected_units = rng.randint(80, 550)
                expected_revenue = expected_units * rng.uniform(75, 580)
                budgets.append(
                    (
                        f"BUD{budget_idx:05d}",
                        clinic_id,
                        2025,
                        payer,
                        category,
                        expected_units,
                        round(expected_revenue, 2),
                        round(rng.uniform(0.08, 0.34), 3),
                    )
                )
                budget_idx += 1
    conn.executemany("INSERT INTO clinic_budgets VALUES (?,?,?,?,?,?,?,?)", budgets)

    encounters = []
    corrections = []
    active_auth_ids = [row[0] for row in auth_cases if row[14] in ("approved", "open", "pending clinical review")]
    service_lookup = {row[0]: row for row in services}
    payable_services = [row for row in services if row[4] == 1]
    for idx in range(1200):
        service = pick(rng, payable_services)
        clinic = clinics[idx % len(clinics)] if idx < 80 else pick(rng, clinics)
        payer, plan_type = pick(rng, payers)
        units = rng.randint(1, 8)
        service_date = date(2025, 1, 1) + timedelta(days=rng.randint(0, 364))
        allowed = service[11] * rng.uniform(0.55, 1.1)
        denial = None
        if idx % 17 == 0:
            denial = pick(rng, ["CO-197", "CO-16", "PR-204", "CO-50"])
            paid = 0.0 if denial in ("CO-197", "PR-204") else allowed * units * rng.uniform(0.2, 0.5)
        else:
            paid = allowed * units * rng.uniform(0.82, 1.03)
        auth_case = pick(rng, active_auth_ids) if service[3] == 1 and rng.random() < 0.55 else None
        encounter_id = f"ENC{idx + 1:06d}"
        encounters.append(
            (
                encounter_id,
                clinic[0],
                iso(service_date),
                payer,
                plan_type,
                pick(rng, members)[0],
                service[0],
                service[2],
                units,
                round(service[11] * units * rng.uniform(1.25, 2.4), 2),
                round(paid, 2),
                denial,
                auth_case,
            )
        )
        if denial or idx % 29 == 0:
            corrections.append(
                (
                    f"CORR{idx + 1:06d}",
                    encounter_id,
                    pick(
                        rng,
                        [
                            "authorization addendum",
                            "modifier correction",
                            "timely filing packet",
                            "medical record attachment",
                            "rate variance appeal",
                        ],
                    ),
                    round(service_lookup[service[0]][11] * units * rng.uniform(0.25, 0.95), 2),
                    iso(service_date + timedelta(days=rng.randint(30, 120))),
                    pick(rng, ["open", "pending documents", "submitted", "closed unrecovered"]),
                )
            )
    conn.executemany("INSERT INTO encounters VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)", encounters)
    conn.executemany("INSERT INTO claim_corrections VALUES (?,?,?,?,?,?)", corrections)

    return {
        "train_reimbursement_batch": ["CLN001", "CLN002", "2025Q1", "2025Q2"],
        "test_reimbursement_batch": ["CLN003", "CLN004", "2025Q3", "2025Q4"],
        "train_profitability_batch": ["CLN001", "CLN003", "Commercial", "Medicaid"],
        "test_profitability_batch": ["CLN002", "CLN004", "Medicare Advantage", "Exchange"],
    }


def build_manifest(conn, target_cases, target_meds, reimbursement_targets):
    tables = [
        row[0]
        for row in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
        )
    ]
    counts = {}
    for table in tables:
        counts[table] = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
    manifest = {
        "environment": "task_group_014",
        "scenario": "SCN_014_healthcare_payer_authorization_appeals",
        "primary_seed": SEED,
        "additional_seeds": [SEED + 17, SEED + 29],
        "database": "payer_ops.db",
        "tables": tables,
        "counts": counts,
        "target_business_object_identifiers": {
            "authorization_case_ids_by_bucket": target_cases,
            "medication_case_ids_by_bucket": target_meds,
            "reimbursement_and_profitability_focus": reimbursement_targets,
        },
        "notes": [
            "Target bucket labels are neutral worklist labels and are mixed with distractor rows.",
            "Manifest is construction-visible and is not intended for solver prompts.",
            "No final task answers are stored in this manifest.",
        ],
    }
    MANIFEST_PATH.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return manifest


def main():
    rng = random.Random(SEED)
    if DB_PATH.exists():
        DB_PATH.unlink()
    conn = sqlite3.connect(DB_PATH)
    try:
        create_schema(conn)
        plans, facilities, services, criteria_specs = insert_static_data(conn)
        members, providers = generate_people(conn, rng, plans)
        auth_cases, target_cases = generate_authorizations(
            conn, rng, members, providers, facilities, services, criteria_specs
        )
        _med_cases, target_meds = generate_medications(conn, rng, members, providers)
        reimbursement_targets = generate_reimbursement(conn, rng, members, services, auth_cases)
        conn.commit()
        manifest = build_manifest(conn, target_cases, target_meds, reimbursement_targets)
    finally:
        conn.close()
    print(f"Generated {DB_PATH}")
    print(json.dumps(manifest["counts"], indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
