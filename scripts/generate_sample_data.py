# Run from the project root: python scripts/generate_sample_data.py
# (Regenerates the CSVs in ./data -- sample data is already included, this is for reference/reproducibility.)

import pandas as pd
import numpy as np
import random
from datetime import datetime, timedelta

random.seed(42)
np.random.seed(42)

# ---------------------------------------------------------------
# 1. SOP MASTER - "Genome" baseline for Loan Underwriting process
# ---------------------------------------------------------------
sop_steps = [
    (1, "Application Intake", "Receive and log loan application from origination channel", "Loan Ops Associate", 10, "Low", "REG-KYC-01"),
    (2, "KYC & Identity Verification", "Verify applicant identity documents against KYC registry", "Compliance Analyst", 20, "High", "REG-KYC-02"),
    (3, "Credit Bureau Pull", "Pull credit report from bureau and parse score", "Underwriter", 15, "Medium", "REG-CRD-01"),
    (4, "Income & Employment Verification", "Validate income proofs, payslips, and employer records", "Underwriter", 25, "Medium", "REG-INC-03"),
    (5, "Debt-to-Income Calculation", "Compute DTI ratio using verified income and liabilities", "Underwriter", 10, "Medium", "REG-DTI-01"),
    (6, "Collateral Valuation", "Independent valuation of pledged collateral/property", "Valuation Specialist", 45, "High", "REG-COL-02"),
    (7, "Fraud Risk Screening", "Run applicant data through fraud detection engine", "Risk Analyst", 15, "High", "REG-FRD-01"),
    (8, "Automated Credit Scoring", "Run application through ML credit scoring model", "System", 5, "Medium", "REG-CRD-04"),
    (9, "Manual Underwriting Review", "Senior underwriter reviews edge-case / flagged applications", "Senior Underwriter", 30, "High", "REG-UWR-05"),
    (10, "Conditional Approval Decision", "Issue conditional approval with any stipulations", "Underwriting Manager", 15, "Medium", "REG-UWR-06"),
    (11, "Document Stipulation Collection", "Collect any outstanding stipulated documents", "Loan Ops Associate", 20, "Low", "REG-DOC-02"),
    (12, "Final Compliance Sign-off", "Compliance officer certifies regulatory adherence", "Compliance Officer", 15, "High", "REG-COM-01"),
    (13, "Final Approval & Booking", "Final approval and loan booking into core system", "Underwriting Manager", 10, "Medium", "REG-UWR-07"),
    (14, "Disbursement Instruction", "Generate disbursement instruction to treasury/payments", "Loan Ops Associate", 10, "Medium", "REG-DIS-01"),
    (15, "Post-Disbursement Audit Tagging", "Tag file for post-disbursement quality audit sampling", "QA Analyst", 5, "Low", "REG-AUD-01"),
]

rows = []
for step in sop_steps:
    rows.append({
        "sop_id": "SOP-LU-001",
        "step_no": step[0],
        "step_name": step[1],
        "description": step[2],
        "owner_role": step[3],
        "expected_duration_min": step[4],
        "risk_level": step[5],
        "compliance_ref": step[6],
        "version": "v3.2",
        "last_updated": "2026-06-15",
        "status": "Active",
    })
sop_master = pd.DataFrame(rows)
sop_master.to_csv("data/sop_master.csv", index=False)

# ---------------------------------------------------------------
# 2. PROCESS EXECUTION LOGS - real-world executions (with drift)
# ---------------------------------------------------------------
executors = ["A.Rao","K.Menon","S.Iyer","P.Nair","R.Das","T.Sharma","M.Khan","V.Reddy","N.Bose","J.Pillai"]
deviation_types = [
    "None","Step Skipped","Order Swapped","Extra Manual Step Added",
    "Duration Overrun","Documentation Missing","Approval Bypassed","Tool Substitution"
]

log_rows = []
log_id = 1
start_date = datetime(2026, 5, 1)
n_cases = 260

for case_idx in range(n_cases):
    case_id = f"LN-{2026000+case_idx}"
    case_start = start_date + timedelta(hours=np.random.randint(0, 24*95))
    # inject a drift pattern over time: later cases show more drift (simulating process decay)
    drift_prob = 0.05 + 0.35 * (case_idx / n_cases)
    cur_time = case_start
    steps_to_run = list(range(1, 16))

    # simulate structural drift: order swap or skip for some cases
    if random.random() < drift_prob * 0.4:
        # skip a low-risk step
        skip_candidates = [1, 11, 15]
        steps_to_run.remove(random.choice(skip_candidates))
    if random.random() < drift_prob * 0.25 and len(steps_to_run) > 5:
        i = random.randint(2, len(steps_to_run)-2)
        steps_to_run[i], steps_to_run[i+1] = steps_to_run[i+1], steps_to_run[i]

    for step_no in steps_to_run:
        step_row = sop_master[sop_master.step_no == step_no].iloc[0]
        expected = step_row.expected_duration_min
        deviation_flag = False
        dtype = "None"
        actual_duration = max(1, int(np.random.normal(expected, expected*0.15)))

        if random.random() < drift_prob:
            deviation_flag = True
            dtype = random.choice(deviation_types[1:])
            if dtype == "Duration Overrun":
                actual_duration = int(expected * np.random.uniform(1.6, 3.2))
            elif dtype == "Extra Manual Step Added":
                actual_duration = int(expected * np.random.uniform(1.3, 1.8))

        cur_time += timedelta(minutes=actual_duration + np.random.randint(1, 20))
        log_rows.append({
            "log_id": log_id,
            "case_id": case_id,
            "sop_id": "SOP-LU-001",
            "step_no": step_no,
            "step_name": step_row.step_name,
            "executed_by": random.choice(executors),
            "timestamp": cur_time.strftime("%Y-%m-%d %H:%M:%S"),
            "expected_duration_min": expected,
            "actual_duration_min": actual_duration,
            "deviation_flag": deviation_flag,
            "deviation_type": dtype,
            "risk_level": step_row.risk_level,
        })
        log_id += 1

process_logs = pd.DataFrame(log_rows)
process_logs.to_csv("data/process_execution_logs.csv", index=False)

# ---------------------------------------------------------------
# 3. SOP VERSIONS / GENOME GENERATIONS (mutation history)
# ---------------------------------------------------------------
mutation_rows = [
    ("GEN-001","SOP-LU-001",1,"Baseline","Initial SOP genome established from regulatory baseline",0.71,"Approved","N.Fernandes","2025-11-02"),
    ("GEN-002","SOP-LU-001",2,"Step Reorder","Moved Fraud Risk Screening before Collateral Valuation to reduce wasted valuation cost on fraud cases",0.78,"Approved","N.Fernandes","2026-01-10"),
    ("GEN-003","SOP-LU-001",3,"Step Merge","Merged Income Verification sub-checks into single automated step using document AI",0.83,"Approved","R.Kapoor","2026-03-04"),
    ("GEN-004","SOP-LU-001",4,"New Control Insertion","Inserted Automated Credit Scoring step prior to Manual Review to cut manual review load by 34%",0.87,"Approved","R.Kapoor","2026-04-22"),
    ("GEN-005","SOP-LU-001",5,"Duration Optimization","Reduced expected duration for Document Stipulation Collection based on observed cycle-time data",0.85,"Pending Review","-","2026-07-30"),
    ("GEN-006","SOP-LU-001",5,"Risk Control Strengthening","Add secondary compliance check after Collateral Valuation for high-value loans (>50L) to mitigate rising drift risk","0.90","Pending Review","-","2026-08-05"),
]
sop_versions = pd.DataFrame(mutation_rows, columns=[
    "version_id","sop_id","generation","mutation_type","mutation_description",
    "fitness_score","status","approved_by","timestamp"
])
sop_versions.to_csv("data/sop_versions.csv", index=False)

# ---------------------------------------------------------------
# 4. RISK INCIDENTS
# ---------------------------------------------------------------
risk_types = ["Compliance Breach","Fraud Indicator","SLA Breach","Data Quality Issue","Unauthorized Step Bypass","Valuation Anomaly"]
risk_rows = []
for i in range(1, 43):
    step_no = random.choice(sop_master.step_no.tolist())
    step_row = sop_master[sop_master.step_no == step_no].iloc[0]
    sev = random.choices(["Low","Medium","High","Critical"], weights=[0.35,0.32,0.23,0.10])[0]
    detected = start_date + timedelta(days=random.randint(0, 100))
    risk_rows.append({
        "incident_id": f"RSK-{1000+i}",
        "sop_id": "SOP-LU-001",
        "step_no": step_no,
        "step_name": step_row.step_name,
        "risk_type": random.choice(risk_types),
        "severity": sev,
        "detected_on": detected.strftime("%Y-%m-%d"),
        "description": f"Anomalous pattern detected at '{step_row.step_name}' during automated risk scan.",
        "resolved": random.choice([True, False, False]),
    })
risk_incidents = pd.DataFrame(risk_rows)
risk_incidents.to_csv("data/risk_incidents.csv", index=False)

# ---------------------------------------------------------------
# 5. AUDIT TRAIL (system + human actions)
# ---------------------------------------------------------------
actions = [
    "SOP_GENERATED","SOP_MUTATION_PROPOSED","SOP_MUTATION_APPROVED","SOP_MUTATION_REJECTED",
    "DRIFT_DETECTED","RISK_FLAGGED","ALERT_TRIGGERED","TRAINING_MATERIAL_GENERATED",
    "MANUAL_REVIEW_COMPLETED","EXPLANATION_VIEWED","DASHBOARD_EXPORTED"
]
users = ["N.Fernandes (Process Owner)","R.Kapoor (Compliance Lead)","AI Agent","S.Iyer (Underwriter)","System Monitor"]
audit_rows = []
for i in range(1, 121):
    ts = start_date + timedelta(hours=random.randint(0, 24*100))
    audit_rows.append({
        "audit_id": f"AUD-{5000+i}",
        "timestamp": ts.strftime("%Y-%m-%d %H:%M:%S"),
        "user": random.choice(users),
        "action": random.choice(actions),
        "entity_type": random.choice(["SOP","Step","Mutation","Risk","Alert"]),
        "entity_id": f"SOP-LU-001-{random.randint(1,15)}",
        "details": "Auto-logged for immutable compliance audit trail.",
    })
audit_trail = pd.DataFrame(audit_rows).sort_values("timestamp")
audit_trail.to_csv("data/audit_trail.csv", index=False)

print("Generated:")
for f in ["sop_master","process_execution_logs","sop_versions","risk_incidents","audit_trail"]:
    df = pd.read_csv(f"data/{f}.csv")
    print(f" - {f}.csv -> {df.shape}")
