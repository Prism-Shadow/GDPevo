# Cedar Ridge Intake — Classification Rules

This reference contains all business rules for classifying patient registration, referral readiness, transfer intake, program enrollment, and chart activation from portal data. Apply these rules after fetching the relevant entity detail views.

---

## 1. Patient Registration Intake (train_001 pattern)

### 1.1 Insurance Status

Determined from the patient''s coverage records (\ → \):

| Field check | Result |
|---|---|
| Coverage \ = \ AND \ contains the roster''s \ | \ |
| Coverage \ = \ BUT \ does NOT contain the roster''s \ | \ (reason: \) |
| Coverage \ = \ | \ (reason: \) |
| Coverage \ = \ | \ (reason: \) |
| Coverage \ = \ | \ |
| No coverage record | \ |

### 1.2 Prescription (PBM) Status

Determined from \ → \:

| Field check | Result |
|---|---|
| PBM \ = 1 AND \ = \ AND \ matches coverage \ | \ |
| PBM \ = 0 OR \ = \ | \ (reason: \) |
| PBM \ = \ | \ (reason: \) |
| PBM \ does not match coverage \ | \ (reason: \) |
| No PBM record | \ (reason: \) |

\ mismatch: when the PBM record has a different policy number than the coverage record for the same payer.

### 1.3 Pharmacy Status

From \ → \ (ordered by \ ascending):

| Field check | Result |
|---|---|
| Top-ranked pharmacy \ = \ | \ |
| Top-ranked pharmacy \ = \ | \ (reason: \) |
| No pharmacy or all unknown | \ (reason: \) |

### 1.4 Lifestyle Risk

From \ → \. Count risk factors:

| Factor | High-Risk Signal |
|---|---|
| \ | \ |
| \ | \ |
| \ | \ or \ |
| \ | < 6.0 |

**Classification:**
- \: any one of: current smoker, heavy alcohol, no exercise (None/null), or sleep < 6 hours
- \: none of the high-risk signals but some suboptimal factors (e.g., moderate alcohol, former smoker)
- \: no risk factors; sleep >= 7, non-smoker, light/none alcohol, regular exercise

### 1.5 Overall Risk

| Condition | Result |
|---|---|
| \ = \ OR any registration blocker exists | \ |
| \ = \ AND no registration blockers | \ |
| Otherwise | \ |

### 1.6 Patient-Level Blocked Reason Codes

Add each code when the condition is true:

| Code | Condition |
|---|---|
| \ | Insurance status \ due to expired coverage |
| \ | Insurance status \ due to pending coverage |
| \ | Insurance active but service_line not in coverage |
| \ | PBM inactive, rejected, or pending |
| \ | No PBM record |
| \ | PBM policy doesn''t match coverage policy |
| \ | Top pharmacy out of network |
| \ | No pharmacy or unknown |
| \ | Patient \ is \ |
| \ | Patient \ = 0 |
| \ | Patient''s \ is \ but \ is null, OR preferred_contact is \/\ but \ is null |
| \ | \ = \ |

Note: \ applies when the patient''s stated preferred contact method lacks the corresponding data (null email for email-preferring, null phone for phone/sms-preferring). \ preferred contact is always available.

### 1.7 Registration Status

Derived from blocked reason codes:

| Status | Rule |
|---|---|
| \ | Zero blocked reason codes |
| \ | Contains \ OR \ (hard coverage blockers) — OR has multiple compound issues that make registration infeasible |
| \ | Has blockers but none are the hard coverage reject blockers above |
| \ | Has only administrative issues (\, \, \) with no clinical/lifestyle concerns |

---

## 2. Referral Readiness Audit (train_002 & train_005 pattern)

### 2.1 ICD Discrepancy Detection

For each referral, fetch \ to get the linked \ metadata, or use \.

**ICD chapter mismatch:** the ICD code''s chapter does not match the expected chapter for the referral''s \. Expected chapter mapping:

| Service Line | Expected ICD Chapter(s) |
|---|---|
| \ | M00-M99 (musculoskeletal) |
| \ | J00-J99 (respiratory) |
| \ | I00-I99 (circulatory) |
| \ | Any (no hard chapter expectation) |

If the ICD chapter is S00-T88 (injury) on an orthopedics referral, that''s a mismatch — orthopedics expects M00-M99. Similarly, I00-I99 (circulatory) on a pulmonary referral is a mismatch.

**Diagnosis description / laterality check:** When the referral''s \ or \ does not match the ICD code''s clinical meaning, flag as \. For example, an asthma ICD code (J00-J99 chapter) with \ = \.

**Laterality check:** When the ICD code has a known laterality but the referral narrative contradicts it.

### 2.2 Issue Codes

Per-referral issue codes (unordered set):

| Code | Condition |
|---|---|
| \ | ICD chapter doesn''t match service line expectation |
| \ | Referral reason or diagnosis description contradicts the ICD code |
| \ | ICD laterality contradicts narrative |
| \ | Another referral exists for the same patient with the same ICD, reason, and different referring practice |
| \ | Two different patients share the same \ |
| \ | \ = 0 |
| \ | \ = 0 |
| \ | \ = 1 AND \ is \ or \ |
| \ | \ = 1 |
| \ | Appointment exists AND there are other blockers (use this instead of \ when other issues are present) |

### 2.3 Readiness Status

| Status | Rule |
|---|---|
| \ | No issue codes |
| \ | Has \, \, or \ (resource/process blockers) |
| \ | Has \, \, \, \, or \ (clinical/judgment issues) — AND no hard blockers |
| \ | Has only \ with no other issues |

When a referral has both review-issues and blocker-issues, classify as \.

### 2.4 Priority Tier

| Tier | Assignment |
|---|---|
| \ | \ = \ AND has issues |
| \ | \ = \ AND has issues, OR urgent referrals already being handled |
| \ | \ = \ OR admin-only issues (shared_insurance_anomaly alone) |
| \ | No issues (\ = \) |

### 2.5 Duplicate Detection

Two referrals are duplicates when they share all of:
- Same - Same - Same - Different \ (or explicitly flagged as duplicate in \)

The earlier \ (lower numeric suffix) is the primary. Recommendation: \ unless there is a reason to keep both (\).

### 2.6 Shared Insurance Anomalies

When two referrals for different patients share the same \:
- Disposition: \ (different patients should have different policy IDs)
- If same patient: \ (same patient with multiple referrals sharing insurance)

---

## 3. Transfer Intake Review (train_003 pattern)

### 3.1 Required Documents Checklist

Every dialysis transfer packet must contain all of these document types:

\, \, \, \, \, \, \, \, \, \, \, \, \, \, 
### 3.2 Packet Completeness

Fetch \ → \. A document is **present** only if \ = \ AND \ = 1. Draft documents (\ = 0) count as missing.

\:
- \: all required document types are present as finalized
- \: any required document type is missing or is a draft

\: list of document type codes absent from finalized documents.

### 3.3 Stale Documents

Some document types have freshness requirements. A document is **stale** if its \ is more than \ ago (relative to today''s date or the evaluation date).

| Document Type | Freshness Limit (days) |
|---|---|
| \ | 30 |
| \ | 365 |
| \ | 365 |
| \ | 30 |
| \ | 30 |

Other document types have no explicit freshness limit (do not report them as stale).

### 3.4 Capacity Check

From \ → \. Find the capacity record whose \ matches the transfer''s \. Sum \ across all locations for that date.

| Condition | \ |
|---|---|
| Sum of \ across locations for the target date > 0 | \ |
| No capacity record for target date OR sum = 0 | \ |

\: the integer sum of open chairs for that date. Use 0 when no matching record exists.

### 3.5 Feasibility

| Condition | \ |
|---|---|
| Packet complete AND no stale docs AND capacity available | \ |
| Packet complete AND no stale docs AND capacity unavailable | \ |
| Packet incomplete or has stale docs AND capacity available | \ |
| Packet incomplete or has stale docs AND capacity unavailable | \ |

### 3.6 Final Intake Decision

| Decision | Rule |
|---|---|
| \ | Packet complete, no stale docs, capacity available |
| \ | Packet complete but capacity unavailable OR only minor admin issues |
| \ | Any missing or stale clinical documents |

### 3.7 Next Contact

**Owner:**
| Owner | Rule |
|---|---|
| \ | Decision is \ (clinical documents needed) |
| \ | Decision is \ (admin issues) |
| \ | Decision is \ but capacity borderline |
| \ | Decision is \ and everything is ready |

**Route:**
| Route | When Used |
|---|---|
| \ | Missing documents or stale clinical docs — fax back to referring facility |
| \ | Need to reach the patient directly (missing transport, insurance proof) |
| \ | Internal Cedar Ridge workflow (scheduling, capacity) |
| \ | No contact needed |

---

## 4. Program Enrollment Panel (train_004 pattern)

### 4.1 Eligibility

| Condition | \ |
|---|---|
| Candidate \ matches the program''s target (e.g., \ for DMHTN-2026A) | \ |
| Candidate \ does NOT match the program''s target | \ |

### 4.2 Reason Codes

| Code | Condition |
|---|---|
| \ | \ matches the program (always present when \ = true) |
| \ | \ does NOT match the program |
| \ | Chart \ does not contain a diabetes/hypertension diagnosis — always accompanies \ |
| \ | \ = \ (omit if other status) |
| \ | \ = \ |
| \ | \ = \ |
| \ | Chart does not exist (\ → \ is empty, or \ = 0) |
| \ | \ array is empty or missing |
| \ | \ missing vitals |
| \ | \ missing labs |
| \ | \ missing medication list |
| \ | \ → \ = 1 |
| \ | Candidate \ < 50 |
| \ | \ → \ contains \ |
| \ | \ → recent ED visit indicator present |

### 4.3 Enrollment Status

| Status | Rule |
|---|---|
| \ | \ = true AND \ = \ AND chart is active and complete |
| \ | \ = true AND (\ = \ OR chart has significant gaps) — but consent not declined |
| \ | \ = false OR \ = \ OR chart not active with declined consent |

### 4.4 Follow-Up Cadence

| Cadence | Condition |
|---|---|
| \ | High-touch enrollment (hospitalization, adherence < 50, recent ED) |
| \ | CKD diagnosis present |
| \ | Standard enrollment with no high-touch factors |
| \ | Hold status |
| \ | Reject status |

### 4.5 Missing Chart Artifacts

List artifact names that are absent from the patient''s \ → \:

| Artifact | When Missing |
|---|---|
| \ | No chart at all (\ = 0 or chart_artifacts empty) |
| \ | \ not in chart_artifacts |
| \ | \ not in chart_artifacts |
| \ | \ not in chart_artifacts |
| \ | \ not in chart_artifacts |
| \ | \ = \ |

### 4.6 Outreach Channel

Use the candidate''s \ field. When it is null or unavailable, fall back to the patient''s \. Valid channels: \, \, \, \, \.

### 4.7 Initial Monitoring Package

| Package Type | When Assigned | Components | \ |
|---|---|---|---|
| \ | \ with high-touch reasons (hospitalization, low adherence, ED) | \, \, \, \, \ | 7 |
| \ | \ with CKD or standard monitoring | \, \, \, \ (CKD: + med_reconciliation; standard: lab only) | 14 (CKD) / 30 (standard) |
| \ | \ | \, \ | \ |
| \ | \ | \ | \ |

For \, adjust components:
- CKD patients: include \ (\ = 14)
- Standard patients without CKD: omit \ (\ = 30)

---

## 5. Chart Activation (train_005 pattern)

### 5.1 Chart Action

For referrals with \ = \, check what needs to happen with the patient''s chart (\):

| Chart Action | Condition |
|---|---|
| \ | No chart exists (\ empty, \ = 0) |
| \ | Chart exists but is missing required artifacts |
| \ | Chart is complete with all required artifacts |

### 5.2 Required Chart Artifacts

The standard set of chart artifacts needed for a specialty referral chart: \, \, \, \, \, \, \.

\: the set of required artifacts not present in \. Always sort alphabetically.

---

## 6. Correspondence Queue (train_005 pattern)

### 6.1 Template Types

| Template | When Used | Typical Reason Codes |
|---|---|---|
| \ | ICD discrepancy / narrative mismatch | \, \ |
| \ | Authorization denied or pending with missing records | \, \ |
| \ | Duplicate referrals found | \ |
| \ | Referral has existing appointment AND other blockers | \ plus other reason codes |

### 6.2 Reason Codes for Correspondence

| Code | When Used |
|---|---|
| \ | ICD chapter doesn''t match service line (e.g., cardiac ICD on pulmonary referral) |
| \ | Referral reason contradicts ICD (e.g., "pain evaluation" for asthma code) |
| \ | \ = \ |
| \ | \ = 0 |
| \ | Duplicate referral group needs resolution |
| \ | \ = 1 AND other issues present |

---

## 7. Summary Calculations

### 7.1 Cohort / Batch Summaries

Use the output template definition to determine which summary fields are needed. Common patterns:

- **Counts by status**: iterate over all entities, count each status value
- **Counts by risk/urgency**: same pattern for risk levels or urgency tiers
- **Cross-tabulations**: counts by two dimensions (e.g., urgency × readiness_status)

All counts must be integers. Include zero-count categories from the template''s allowed values unless the template explicitly says to omit zeros.

### 7.2 Priority Ordering

When assigning \:
- Only include non-ready referrals
- Sort by urgency (urgent first) then by severity/blocker count
- Assign sequential ranks starting from 1
