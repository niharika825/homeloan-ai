"""
generate_data.py
Creates ALL the fictional data used by the demo. Run it once:  python generate_data.py

Nothing here is real. Names, incomes, scores and charges are randomly generated.
Output files go into the  data/  folder:
  applicants.csv        -> core banking: customer profile
  applications.csv      -> the loan applications
  documents.csv         -> simulated scanned documents + what was "read" from them
  bureau_mock.csv       -> MOCK credit bureau (CIBIL-style) responses
  cersai_mock.csv       -> MOCK CERSAI (existing charge on property) responses
  repayment_history.csv -> core banking: repayment behaviour
  policy.json           -> the fictional bank's home loan policy (rules the Policy Agent reads)
"""
import json
import random
from pathlib import Path

import numpy as np
import pandas as pd

random.seed(42)
np.random.seed(42)
OUT = Path(__file__).parent / "data"
OUT.mkdir(exist_ok=True)

N = 300

FIRST = ["Aarav", "Vihaan", "Aditya", "Rohan", "Karthik", "Suresh", "Imran", "Manish", "Rahul", "Arjun",
         "Ananya", "Priya", "Sneha", "Kavya", "Meera", "Divya", "Fatima", "Neha", "Pooja", "Lakshmi",
         "Harpreet", "Sanjay", "Deepak", "Ritu", "Nisha", "Vikram", "Amit", "Swati", "Ravi", "Shweta"]
LAST = ["Sharma", "Iyer", "Reddy", "Patel", "Nair", "Khan", "Singh", "Gupta", "Mehta", "Das",
        "Joshi", "Kulkarni", "Menon", "Verma", "Bose", "Chopra", "Rao", "Shetty", "Pillai", "Malhotra"]
CITIES = ["Mumbai", "Pune", "Bengaluru", "Hyderabad", "Chennai", "Delhi NCR", "Ahmedabad", "Kolkata", "Jaipur", "Kochi"]
EMPLOYERS = ["Infosys", "TCS", "Wipro", "HDFC Life", "Reliance Retail", "Tata Motors", "Apollo Hospitals",
             "State Government Dept.", "Local School Trust", "Mahindra Logistics", "Zomato", "Fortis Healthcare"]

# ---------------------------------------------------------------- applicants
rows = []
for i in range(N):
    emp = random.choices(["Salaried", "Self-employed", "Government"], weights=[0.65, 0.22, 0.13])[0]
    income = int(np.clip(np.random.lognormal(mean=11.1, sigma=0.5), 25000, 400000) // 1000 * 1000)
    existing_emi = int(income * random.choice([0, 0, 0, 0, 0.05, 0.08, 0.1, 0.15, 0.25]) // 500 * 500)
    rows.append({
        "applicant_id": f"CUST{1001 + i}",
        "name": f"{random.choice(FIRST)} {random.choice(LAST)}",
        "age": int(np.clip(np.random.normal(36, 8), 22, 62)),
        "city": random.choice(CITIES),
        "employment_type": emp,
        "employer": "Self (own business)" if emp == "Self-employed" else random.choice(EMPLOYERS),
        "monthly_income": income,
        "existing_emi": existing_emi,
        "years_with_bank": random.randint(0, 15),
        "avg_balance": int(income * random.uniform(0.3, 4) // 100 * 100),
    })
applicants = pd.DataFrame(rows)
applicants.to_csv(OUT / "applicants.csv", index=False)

# -------------------------------------------------------------- applications
apps = []
for i, a in applicants.iterrows():
    tenure = random.choice([10, 15, 20, 20, 25, 25, 30])
    multiple = random.uniform(12, 42)
    loan = int(round(a.monthly_income * multiple, -5))
    loan = max(loan, 1500000)
    ltv = random.choices([0.55, 0.6, 0.65, 0.7, 0.75, 0.8, 0.9], weights=[2, 3, 4, 4, 4, 1, 0.5])[0]
    prop_value = int(round(loan / ltv, -5))
    apps.append({
        "application_id": f"HL2025-{5001 + i}",
        "applicant_id": a.applicant_id,
        "loan_amount": loan,
        "property_value": prop_value,
        "tenure_years": tenure,
        "property_city": a.city,
        "property_type": random.choice(["Ready flat", "Under-construction flat", "Resale flat", "Independent house"]),
        # ~30% of applications have not yet been touched by the AI agents
        "ai_processed": random.random() > 0.30,
        "submitted_days_ago": random.randint(0, 12),
    })
applications = pd.DataFrame(apps)
applications.to_csv(OUT / "applications.csv", index=False)

# ----------------------------------------------------------------- documents
DOC_TYPES = ["PAN card", "Aadhaar card", "Income proof", "Bank statements (6 months)",
             "Sale agreement", "Property title deeds", "Approved building plan"]
docs = []
for _, ap in applications.iterrows():
    a = applicants[applicants.applicant_id == ap.applicant_id].iloc[0]
    missing_prob = random.random()
    n_missing = 0 if missing_prob < 0.78 else (1 if missing_prob < 0.93 else 2)
    missing = set(random.sample(DOC_TYPES, n_missing))
    income_mismatch = random.random() < 0.12
    name_mismatch = random.random() < 0.06
    for d in DOC_TYPES:
        submitted = d not in missing
        name_on_doc = a["name"]
        if d == "Aadhaar card" and name_mismatch:
            name_on_doc = a["name"].split()[0] + " " + random.choice(LAST)
        extracted_income = None
        extracted_credit = None
        if d == "Income proof":
            extracted_income = int(a.monthly_income * (random.uniform(0.6, 0.8) if income_mismatch else random.uniform(0.97, 1.03)))
        if d == "Bank statements (6 months)":
            extracted_credit = int(a.monthly_income * random.uniform(0.9, 1.1))
        docs.append({
            "application_id": ap.application_id,
            "doc_type": d,
            "submitted": submitted,
            "name_on_doc": name_on_doc if submitted else "",
            "extracted_monthly_income": extracted_income if submitted else None,
            "extracted_avg_monthly_credit": extracted_credit if submitted else None,
            "scan_quality": random.choices(["Good", "Poor"], weights=[0.985, 0.015])[0] if submitted else "",
        })
pd.DataFrame(docs).to_csv(OUT / "documents.csv", index=False)

# ------------------------------------------------- MOCK credit bureau (CIBIL-style)
bureau = []
for _, a in applicants.iterrows():
    base = np.random.normal(758, 55)
    score = int(np.clip(base, 520, 900))
    bureau.append({
        "applicant_id": a.applicant_id,
        "credit_score": score,
        "active_loans": random.choice([0, 1, 1, 2, 3]),
        "max_dpd_12m": 0 if score > 700 and random.random() < 0.9 else random.choice([0, 30, 60, 90]),
        "enquiries_6m": random.choices([0, 1, 2, 3, 5, 7], weights=[3, 4, 3, 2, 1, 0.5])[0],
        "card_utilisation_pct": random.choices([10, 20, 30, 45, 60, 80, 95], weights=[3, 4, 4, 3, 2, 0.7, 0.4])[0],
    })
pd.DataFrame(bureau).to_csv(OUT / "bureau_mock.csv", index=False)

# ------------------------------------------------------------ MOCK CERSAI search
cersai = []
for _, ap in applications.iterrows():
    has_charge = random.random() < 0.07
    cersai.append({
        "application_id": ap.application_id,
        "existing_charge": has_charge,
        "charge_holder": random.choice(["Another bank", "A housing finance company"]) if has_charge else "",
    })
pd.DataFrame(cersai).to_csv(OUT / "cersai_mock.csv", index=False)

# ------------------------------------------- core banking repayment behaviour
rep = []
for _, a in applicants.iterrows():
    rep.append({
        "applicant_id": a.applicant_id,
        "missed_emis_24m": random.choices([0, 1, 2, 4], weights=[0.8, 0.12, 0.05, 0.03])[0],
        "cheque_bounces_12m": random.choices([0, 1, 3], weights=[0.9, 0.07, 0.03])[0],
    })
pd.DataFrame(rep).to_csv(OUT / "repayment_history.csv", index=False)

# ------------------------------------------------------------------- policy
policy = {
    "policy_name": "Sample Home Loan Credit Policy v1.0 (FICTIONAL - for demo only)",
    "interest_rate_for_emi_calc": 0.0875,
    "required_documents": DOC_TYPES,
    "rules": [
        {"id": "P-1.1", "name": "Applicant age", "text": "Age must be between 21 and 60 at application, and age plus loan tenure must not exceed 70.",
         "min_age": 21, "max_age": 60, "max_age_at_maturity": 70},
        {"id": "P-2.1", "name": "Minimum income", "text": "Verified gross monthly income must be at least Rs 25,000.", "min_income": 25000},
        {"id": "P-3.1", "name": "Credit score", "text": "Credit bureau score of 750 or above is preferred. Below 700 needs senior review.",
         "preferred_score": 750, "min_score": 700},
        {"id": "P-4.1", "name": "FOIR (fixed obligations to income)", "text": "Total EMIs including the new loan should not exceed 50% of verified monthly income. 40% or below is preferred.",
         "max_foir": 0.50, "preferred_foir": 0.40},
        {"id": "P-5.1", "name": "Loan-to-value (LTV)", "text": "Maximum LTV is 90% up to Rs 30 lakh, 80% up to Rs 75 lakh and 75% above Rs 75 lakh (illustrative, aligned to RBI LTV norms).",
         "ltv_caps": [[3000000, 0.90], [7500000, 0.80], [None, 0.75]]},
        {"id": "P-6.1", "name": "Tenure", "text": "Maximum loan tenure is 30 years.", "max_tenure": 30},
        {"id": "P-7.1", "name": "Property charge check", "text": "The property must have no existing charge registered in the central collateral registry (CERSAI)."},
        {"id": "P-8.1", "name": "Income consistency", "text": "Income on the income proof should be within 15% of income declared on the application."},
    ],
}
(OUT / "policy.json").write_text(json.dumps(policy, indent=2))

print("Done. Files created in:", OUT)
for f in sorted(OUT.iterdir()):
    print(" -", f.name)
