"""
agents.py
The three AI agents. IMPORTANT: in this demo they are SIMULATED - they are plain
Python rules, not a real language model. The screens label them "simulated".
In a real build, each agent would call an LLM (for reading scans and explaining
reasons) but keep the same inputs, outputs and hand-offs shown here.

Every check returns:  name, status ("pass" | "flag" | "fail"), detail, source
so every recommendation can show its reasons and the policy/data it relied on.
"""
import json
from pathlib import Path

import pandas as pd

DATA = Path(__file__).parent / "data"
POLICY = json.loads((DATA / "policy.json").read_text())
RULES = {r["id"]: r for r in POLICY["rules"]}


def emi(principal, years, annual_rate=None):
    """Monthly instalment for a loan (standard EMI formula)."""
    rate = (annual_rate or POLICY["interest_rate_for_emi_calc"]) / 12
    n = years * 12
    return principal * rate * (1 + rate) ** n / ((1 + rate) ** n - 1)


def inr_short(x):
    """Short Indian format for big numbers, e.g. Rs 28 lakh, Rs 1.2 crore."""
    x = float(x)
    if x >= 1e7:
        return f"Rs {x / 1e7:.2f} crore".replace(".00", "")
    if x >= 1e5:
        return f"Rs {x / 1e5:.1f} lakh".replace(".0 ", " ")
    return inr(x)


def check(name, status, detail, source):
    return {"name": name, "status": status, "detail": detail, "source": source}


def inr(x):
    """Format a number the Indian way, e.g. Rs 12,50,000."""
    x = int(round(x))
    s = str(abs(x))
    if len(s) > 3:
        head, tail = s[:-3], s[-3:]
        parts = []
        while len(head) > 2:
            parts.insert(0, head[-2:])
            head = head[:-2]
        if head:
            parts.insert(0, head)
        s = ",".join(parts + [tail])
    return ("-" if x < 0 else "") + "Rs " + s


# ===================================================================== AGENT 1
def document_agent(app, applicant, docs):
    """Checks the simulated documents: completeness, scan quality, name match, income match."""
    checks = []
    required = POLICY["required_documents"]
    submitted = set(docs[docs.submitted].doc_type)
    missing = [d for d in required if d not in submitted]

    if missing:
        checks.append(check("Document completeness", "fail", f"Missing: {', '.join(missing)}",
                            "Document checklist (policy: required documents)"))
    else:
        checks.append(check("Document completeness", "pass", f"All {len(required)} required documents received.",
                            "Document checklist"))

    poor = docs[(docs.submitted) & (docs.scan_quality == "Poor")].doc_type.tolist()
    if poor:
        checks.append(check("Scan quality", "flag", f"Hard to read: {', '.join(poor)}. Ask for a clearer copy.",
                            "Document reader (simulated OCR)"))
    else:
        checks.append(check("Scan quality", "pass", "All scans readable.", "Document reader (simulated OCR)"))

    names = docs[docs.submitted & docs.doc_type.isin(["PAN card", "Aadhaar card"])]
    distinct = set(names.name_on_doc)
    if len(distinct) > 1:
        checks.append(check("Name match (PAN vs Aadhaar)", "flag",
                            "Names differ: " + " vs ".join(sorted(distinct)), "Document reader (simulated OCR)"))
    elif len(distinct) == 1:
        checks.append(check("Name match (PAN vs Aadhaar)", "pass", f"Both show '{distinct.pop()}'.",
                            "Document reader (simulated OCR)"))

    verified_income = float(applicant.monthly_income)
    inc = docs[(docs.doc_type == "Income proof") & docs.submitted]
    if len(inc):
        doc_income = float(inc.iloc[0].extracted_monthly_income)
        gap = abs(doc_income - applicant.monthly_income) / applicant.monthly_income
        verified_income = min(doc_income, float(applicant.monthly_income))
        if gap > RULES["P-8.1"].get("tolerance", 0.15):
            checks.append(check("Income vs declared", "flag",
                                f"Declared {inr(applicant.monthly_income)}/month but income proof shows {inr(doc_income)}/month "
                                f"({gap:.0%} gap). Lower figure used.", "Income proof vs application form; policy P-8.1"))
        else:
            checks.append(check("Income vs declared", "pass",
                                f"Income proof shows {inr(doc_income)}/month, matches declared.", "Policy P-8.1"))
    else:
        checks.append(check("Income vs declared", "fail", "No income proof received, income cannot be verified.", "Policy P-8.1"))

    bank = docs[(docs.doc_type == "Bank statements (6 months)") & docs.submitted]
    if len(bank):
        credit = float(bank.iloc[0].extracted_avg_monthly_credit)
        ratio = credit / applicant.monthly_income
        if ratio < 0.8:
            checks.append(check("Bank statement credits", "flag",
                                f"Average monthly credits {inr(credit)} are only {ratio:.0%} of declared income.", "Bank statements"))
        else:
            checks.append(check("Bank statement credits", "pass",
                                f"Average monthly credits {inr(credit)} are consistent with income.", "Bank statements"))

    status = "More information required" if missing else ("Findings flagged" if any(c["status"] != "pass" for c in checks) else "Clean")
    return {
        "agent": "Document Verification Agent",
        "tools": ["Document reader (simulated OCR)", "Document checklist"],
        "checks": checks,
        "missing": missing,
        "verified_income": verified_income,
        "status": status,
        "handoff": ("Passing the document findings and verified income to the Loan Policy Agent."),
    }


# ===================================================================== AGENT 2
def policy_agent(app, applicant, doc_result):
    """Checks the case against the bank's (fictional) written policy and cites the rule."""
    checks = []
    income = doc_result["verified_income"]
    new_emi = emi(app.loan_amount, app.tenure_years)
    foir = (applicant.existing_emi + new_emi) / income if income else 9.9
    ltv = app.loan_amount / app.property_value

    r = RULES["P-1.1"]
    maturity_age = applicant.age + app.tenure_years
    if applicant.age < r["min_age"] or applicant.age > r["max_age"]:
        checks.append(check("Age", "fail", f"Age {applicant.age} outside {r['min_age']}-{r['max_age']}.", "P-1.1"))
    elif maturity_age > r["max_age_at_maturity"]:
        checks.append(check("Age at maturity", "flag", f"Age {applicant.age} + {app.tenure_years}-year tenure = {maturity_age} (limit {r['max_age_at_maturity']}). Shorter tenure needed.", "P-1.1"))
    else:
        checks.append(check("Age", "pass", f"Age {applicant.age}, age at maturity {maturity_age}.", "P-1.1"))

    if income < RULES["P-2.1"]["min_income"]:
        checks.append(check("Minimum income", "fail", f"Verified income {inr(income)} below {inr(RULES['P-2.1']['min_income'])}.", "P-2.1"))
    else:
        checks.append(check("Minimum income", "pass", f"Verified income {inr(income)}/month.", "P-2.1"))

    r = RULES["P-4.1"]
    detail = (f"New EMI {inr(new_emi)} + existing {inr(applicant.existing_emi)} = {inr(new_emi + applicant.existing_emi)} "
              f"on income {inr(income)} -> FOIR {foir:.0%}.")
    if foir > r["max_foir"]:
        checks.append(check("FOIR", "fail", detail + f" Above the {r['max_foir']:.0%} limit.", "P-4.1"))
    elif foir > r["preferred_foir"]:
        checks.append(check("FOIR", "flag", detail + f" Within limit but above preferred {r['preferred_foir']:.0%}.", "P-4.1"))
    else:
        checks.append(check("FOIR", "pass", detail, "P-4.1"))

    caps = RULES["P-5.1"]["ltv_caps"]
    cap = next(c for limit, c in caps if limit is None or app.loan_amount <= limit)
    detail = f"Loan {inr(app.loan_amount)} on property {inr(app.property_value)} -> LTV {ltv:.0%} (cap {cap:.0%} for this loan size)."
    checks.append(check("LTV", "fail" if ltv > cap + 1e-9 else "pass", detail, "P-5.1; RBI LTV norms"))

    if app.tenure_years > RULES["P-6.1"]["max_tenure"]:
        checks.append(check("Tenure", "fail", f"{app.tenure_years} years exceeds {RULES['P-6.1']['max_tenure']}.", "P-6.1"))
    else:
        checks.append(check("Tenure", "pass", f"{app.tenure_years} years within limit.", "P-6.1"))

    if doc_result["missing"]:
        checks.append(check("Documents required by policy", "fail", "Policy cannot be fully confirmed until missing documents arrive.", "Policy: required documents"))

    status = ("Policy breach" if any(c["status"] == "fail" for c in checks)
              else "Needs review" if any(c["status"] == "flag" for c in checks) else "Policy met")
    return {
        "agent": "Loan Policy Agent",
        "tools": ["Policy library (policy.json)", "EMI calculator", "RBI LTV norms reference"],
        "checks": checks,
        "foir": foir,
        "ltv": ltv,
        "new_emi": new_emi,
        "status": status,
        "handoff": "Passing policy results to the Credit Risk Review Agent, which will add bureau and property-charge data.",
    }


# ===================================================================== AGENT 3
def risk_agent(app, applicant, doc_result, policy_result, bureau, cersai, repay):
    """Combines everything, adds external + repayment data, flags risks, recommends."""
    checks = []
    r = RULES["P-3.1"]
    score = int(bureau.credit_score)
    if score < r["min_score"]:
        checks.append(check("Credit score (mock bureau)", "fail", f"Score {score} is below {r['min_score']}. Senior review needed.", "Mock credit bureau; P-3.1"))
    elif score < r["preferred_score"]:
        checks.append(check("Credit score (mock bureau)", "flag", f"Score {score}: acceptable but below preferred {r['preferred_score']}.", "Mock credit bureau; P-3.1"))
    else:
        checks.append(check("Credit score (mock bureau)", "pass", f"Score {score}.", "Mock credit bureau; P-3.1"))

    if bureau.max_dpd_12m >= 60:
        checks.append(check("Recent delays (mock bureau)", "fail", f"Payment overdue by {int(bureau.max_dpd_12m)} days in last 12 months.", "Mock credit bureau"))
    elif bureau.max_dpd_12m > 0:
        checks.append(check("Recent delays (mock bureau)", "flag", f"Payment overdue by {int(bureau.max_dpd_12m)} days in last 12 months.", "Mock credit bureau"))
    else:
        checks.append(check("Recent delays (mock bureau)", "pass", "No overdue payments in last 12 months.", "Mock credit bureau"))

    if bureau.enquiries_6m >= 5 or bureau.card_utilisation_pct >= 80:
        checks.append(check("Credit hunger / utilisation", "flag",
                            f"{int(bureau.enquiries_6m)} credit enquiries in 6 months; card utilisation {int(bureau.card_utilisation_pct)}%.", "Mock credit bureau"))
    else:
        checks.append(check("Credit hunger / utilisation", "pass",
                            f"{int(bureau.enquiries_6m)} enquiries in 6 months; card utilisation {int(bureau.card_utilisation_pct)}%.", "Mock credit bureau"))

    if cersai.existing_charge:
        checks.append(check("Existing charge on property (mock CERSAI)", "fail", f"Property already has a charge held by: {cersai.charge_holder}.", "Mock CERSAI; P-7.1"))
    else:
        checks.append(check("Existing charge on property (mock CERSAI)", "pass", "No existing charge found.", "Mock CERSAI; P-7.1"))

    if repay.missed_emis_24m > 0 or repay.cheque_bounces_12m > 0:
        sev = "fail" if (repay.missed_emis_24m >= 4 or repay.cheque_bounces_12m >= 3) else "flag"
        checks.append(check("Repayment history (core banking)", sev,
                            f"{int(repay.missed_emis_24m)} missed EMIs in 24 months; {int(repay.cheque_bounces_12m)} cheque bounces in 12 months.", "Core banking data"))
    else:
        checks.append(check("Repayment history (core banking)", "pass", "No missed EMIs or bounced cheques.", "Core banking data"))

    all_checks = doc_result["checks"] + policy_result["checks"] + checks
    fails = [c for c in all_checks if c["status"] == "fail"]
    flags = [c for c in all_checks if c["status"] == "flag"]

    if doc_result["missing"]:
        rec = "More information required"
        why = [f"Missing documents: {', '.join(doc_result['missing'])}."]
    elif fails:
        rec = "Needs further assessment"
        why = [f"{c['name']}: {c['detail']}" for c in fails]
    elif len(flags) >= 4:
        rec = "Needs further assessment"
        why = [f"{len(flags)} flags raised, which together warrant a closer look: " + "; ".join(c["name"] for c in flags) + "."]
    else:
        rec = "Ready for review"
        why = ["All mandatory checks passed" + (f", with {len(flags)} minor flag(s) for the officer to note." if flags else ".")]

    return {
        "agent": "Credit Risk Review Agent",
        "tools": ["Mock credit bureau (CIBIL-style)", "Mock CERSAI search", "Core banking data (repayment history)"],
        "checks": checks,
        "all_fails": fails,
        "all_flags": flags,
        "recommendation": rec,
        "reasons": why,
        "handoff": "Sending the recommendation and reasons to the human credit officer. The officer makes the final decision.",
    }


# ============================================================ run all, load data
def load_tables():
    t = {
        "applicants": pd.read_csv(DATA / "applicants.csv"),
        "applications": pd.read_csv(DATA / "applications.csv"),
        "documents": pd.read_csv(DATA / "documents.csv"),
        "bureau": pd.read_csv(DATA / "bureau_mock.csv"),
        "cersai": pd.read_csv(DATA / "cersai_mock.csv"),
        "repay": pd.read_csv(DATA / "repayment_history.csv"),
    }
    t["documents"]["submitted"] = t["documents"]["submitted"].astype(bool)
    t["documents"]["scan_quality"] = t["documents"]["scan_quality"].fillna("")
    return t


def run_workflow(app_id, t):
    """Run the three agents in order for one application. Returns all three results."""
    app = t["applications"][t["applications"].application_id == app_id].iloc[0]
    applicant = t["applicants"][t["applicants"].applicant_id == app.applicant_id].iloc[0]
    docs = t["documents"][t["documents"].application_id == app_id]
    bureau = t["bureau"][t["bureau"].applicant_id == app.applicant_id].iloc[0]
    cersai = t["cersai"][t["cersai"].application_id == app_id].iloc[0]
    repay = t["repay"][t["repay"].applicant_id == app.applicant_id].iloc[0]

    d = document_agent(app, applicant, docs)
    p = policy_agent(app, applicant, d)
    r = risk_agent(app, applicant, d, p, bureau, cersai, repay)
    return {"app": app, "applicant": applicant, "docs": docs, "doc": d, "policy": p, "risk": r}
