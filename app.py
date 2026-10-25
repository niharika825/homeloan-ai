"""
app.py  -  HomeLoan AI: Intelligent Loan Processing Assistant
Run with:  streamlit run app.py

This file is the website. It only handles what you SEE (pages, tables, buttons).
The thinking lives in agents.py, and the data lives in the data/ folder.
All data is fictional. The AI agents are simulated (rule-based) and labelled as such.
"""
import time
from datetime import datetime
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

import agents
from agents import inr, inr_short

st.set_page_config(page_title="HomeLoan AI", page_icon="🏠", layout="wide")

DECISIONS_FILE = Path(__file__).parent / "data" / "decisions.csv"
ICON = {"pass": "✅", "flag": "⚠️", "fail": "❌"}
STAGE_ORDER = ["Awaiting AI review", "Missing documents", "Ready for officer review", "Decided by officer"]

# ---------------------------------------------------------------- small styling
st.markdown(
    """
    <style>
    .block-container {padding-top: 1.6rem;}
    .banner {background:#FFF4E5;border-left:5px solid #F59E0B;padding:.7rem 1rem;border-radius:6px;margin:.4rem 0 1rem 0;}
    .sim {background:#EEF2FF;border-left:5px solid #6366F1;padding:.5rem .9rem;border-radius:6px;font-size:.9rem;}
    .agentbox {border:1px solid #E5E7EB;border-radius:10px;padding:.9rem 1rem;margin-bottom:.6rem;background:#FAFAFA;}
    .handoff {color:#4B5563;font-style:italic;margin:.2rem 0 1rem 0;}
    .pill {display:inline-block;padding:.15rem .6rem;border-radius:999px;font-size:.85rem;font-weight:600;}
    .green {background:#DCFCE7;color:#166534;} .amber {background:#FEF3C7;color:#92400E;}
    .red {background:#FEE2E2;color:#991B1B;} .blue {background:#DBEAFE;color:#1E40AF;}
    </style>
    """,
    unsafe_allow_html=True,
)


# --------------------------------------------------------------------- data
@st.cache_data
def get_tables():
    return agents.load_tables()


@st.cache_data
def get_all_results():
    """Run the agents for every application once, to build the dashboard."""
    t = get_tables()
    out = {}
    for app_id in t["applications"].application_id:
        out[app_id] = agents.run_workflow(app_id, t)
    return out


def load_decisions():
    if DECISIONS_FILE.exists():
        return pd.read_csv(DECISIONS_FILE)
    return pd.DataFrame(columns=["application_id", "decision", "notes", "officer", "time"])


def stage_of(app_row, res, decided_ids):
    if app_row.application_id in decided_ids:
        return "Decided by officer"
    if not app_row.ai_processed and app_row.application_id not in st.session_state.setdefault("ran", set()):
        return "Awaiting AI review"
    if res["doc"]["missing"]:
        return "Missing documents"
    return "Ready for officer review"


def build_dashboard_table():
    t = get_tables()
    results = get_all_results()
    decisions = load_decisions()
    decided = set(decisions.application_id)
    rows = []
    for _, a in t["applications"].iterrows():
        res = results[a.application_id]
        stage = stage_of(a, res, decided)
        rec = res["risk"]["recommendation"] if stage in ("Missing documents", "Ready for officer review", "Decided by officer") else "-"
        rows.append({
            "Application": a.application_id,
            "Applicant": res["applicant"]["name"],
            "City": a.property_city,
            "Loan amount": a.loan_amount,
            "Employment": res["applicant"]["employment_type"],
            "Days since submitted": a.submitted_days_ago,
            "Status": stage,
            "AI recommendation": rec,
        })
    return pd.DataFrame(rows)


def go(page, app_id=None):
    st.session_state.page = page
    if app_id:
        st.session_state.sel_app = app_id


def pill(text, color):
    return f'<span class="pill {color}">{text}</span>'


def rec_pill(rec):
    return pill(rec, {"Ready for review": "green", "More information required": "amber", "Needs further assessment": "red"}.get(rec, "blue"))


def render_checks(checks):
    for c in checks:
        st.markdown(f"{ICON[c['status']]} **{c['name']}**  \n{c['detail']}  \n<span style='color:#6B7280;font-size:.85rem'>Based on: {c['source']}</span>",
                    unsafe_allow_html=True)



ARCH_HTML = """
<style>
.ar{display:flex;gap:10px;align-items:stretch;margin:0}
.lay{border-radius:12px;padding:10px 12px;flex:1}
.lay h4{margin:0 0 8px 0;font-size:.82rem;letter-spacing:.04em;text-transform:uppercase;color:#374151}
.cd{background:#fff;border:1px solid #D1D5DB;border-radius:8px;padding:8px 10px;font-size:.85rem;flex:1;text-align:center}
.cds{display:flex;gap:8px}
.dn{text-align:center;color:#6B7280;font-size:1.2rem;line-height:1.1;margin:2px 0}
.tag{display:inline-block;font-size:.7rem;background:#EEF2FF;color:#3730A3;border-radius:999px;padding:1px 8px;margin-top:4px}
.mock{background:#FEF3C7;color:#92400E}
</style>
<div class="ar">
 <div style="flex:5">
  <div class="lay" style="background:#FEF9C3"><h4>1 · Data sources</h4><div class="cds">
    <div class="cd"><b>Applicant documents</b><br>KYC, salary slips, statements, ITR, property papers<br><span class="tag">unstructured</span></div>
    <div class="cd"><b>RBI circulars &amp; credit policy</b><br><span class="tag">unstructured</span></div>
    <div class="cd"><b>Core banking data</b><br>profile, loans, repayments<br><span class="tag">structured</span></div>
    <div class="cd"><b>External APIs</b><br>CIBIL · CERSAI · PAN/Aadhaar<br><span class="tag mock">mocked in demo</span></div></div></div>
  <div class="dn">▼</div>
  <div class="lay" style="background:#FFEDD5"><h4>2 · Ingestion</h4><div class="cds">
    <div class="cd"><b>Document &amp; policy ingestion</b><br>read text, extract fields</div>
    <div class="cd"><b>Data loading</b><br>batch loads and API pulls</div></div></div>
  <div class="dn">▼</div>
  <div class="lay" style="background:#DBEAFE"><h4>3 · Lakehouse (BigQuery planned; CSV files in demo)</h4><div class="cds">
    <div class="cd"><b>Raw</b><br>as received</div><div class="cd"><b>Cleaned</b><br>standardised</div>
    <div class="cd"><b>Curated</b><br>one view per application</div><div class="cd"><b>Policy library</b><br>approved rules</div>
    <div class="cd"><b>Enterprise knowledge</b><br>features · document embeddings</div></div></div>
  <div class="dn">▼</div>
  <div class="lay" style="background:#E0E7FF"><h4>4 · AI agents (simulated in demo)</h4>
    <div class="cds" style="margin-bottom:8px"><div class="cd"><b>Orchestrator (runner)</b><br>runs the agents in order, passes context</div>
    <div class="cd"><b>Session &amp; memory</b><br>case state, events, saved artifacts</div></div><div class="cds">
    <div class="cd"><b>Document Verification</b></div><div style="align-self:center">➜</div>
    <div class="cd"><b>Loan Policy</b></div><div style="align-self:center">➜</div>
    <div class="cd"><b>Credit Risk Review</b></div></div>
    <div class="dn">▲▼</div>
    <div class="cds"><div class="cd" style="background:#F3E8FF"><b>5 · Tool box &amp; integrations</b> — database lookup · policy search · document reader · EMI calculator · bureau and CERSAI connectors (API or MCP; stubs in demo)</div></div></div>
  <div class="dn">▼</div>
  <div class="lay" style="background:#DCFCE7"><h4>6 · Bank employee dashboard</h4><div class="cds">
    <div class="cd">Dashboard</div><div class="cd">Application review</div><div class="cd"><b>Credit officer decision</b></div>
    <div class="cd">Front end + back end service</div></div></div>
 </div>
 <div class="lay" style="background:#FEE2E2;flex:1.3"><h4>7 · Governance &amp; control</h4>
   <div class="cd" style="margin-bottom:8px"><b>Human-in-the-loop tool</b><br>pauses the agents; officer decides, resumes or overrides</div>
   <div class="cd" style="margin-bottom:8px"><b>Feedback &amp; decision storage</b><br>officer corrections kept to improve agents</div>
   <div class="cd" style="margin-bottom:8px"><b>Explainability</b><br>reasons and sources shown</div>
   <div class="cd" style="margin-bottom:8px"><b>Audit log</b><br>who decided what, when</div>
   <div class="cd" style="margin-bottom:8px"><b>Data protection</b><br>synthetic data only in demo; masking and access control in production</div>
   <div class="cd"><b>Policy ownership</b><br>credit policy team approves rule changes</div></div>
</div>
"""

# ----------------------------------------------------------------- sidebar
PAGES = ["Dashboard", "Application Review", "Approach", "Architecture", "About & FAQ", "Contact"]
if "page" not in st.session_state:
    st.session_state.page = "Dashboard"

with st.sidebar:
    st.markdown("## 🏠 HomeLoan AI")
    st.caption("Intelligent Loan Processing Assistant")
    st.radio("Navigate", PAGES, key="page")
    st.divider()
    st.markdown('<div class="sim"><b>Demo notice</b><br>All data is fictional. Agents are simulated, and bureau and CERSAI services are mocked. No real bank systems are connected.</div>',
                unsafe_allow_html=True)

page = st.session_state.page


# ===================================================================== DASHBOARD
def page_dashboard():
    st.title("Home Loan Dashboard")
    st.caption("Credit operations view: fictional applications at a mid-sized Indian bank.")
    df = build_dashboard_table()
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total applications", len(df))
    c2.metric("Awaiting AI review", int((df.Status == "Awaiting AI review").sum()))
    c3.metric("Missing documents", int((df.Status == "Missing documents").sum()))
    c4.metric("Ready for officer review", int((df.Status == "Ready for officer review").sum()))

    left, right = st.columns([1, 2])
    with left:
        counts = df.Status.value_counts().reindex(STAGE_ORDER).dropna().reset_index()
        counts.columns = ["Status", "Applications"]
        fig = px.bar(counts, x="Applications", y="Status", orientation="h", color="Status",
                     color_discrete_sequence=["#9CA3AF", "#F59E0B", "#10B981", "#3B82F6"])
        fig.update_layout(showlegend=False, height=260, margin=dict(l=0, r=0, t=10, b=0), yaxis=dict(autorange="reversed", title=""))
        st.plotly_chart(fig, width="stretch")
    with right:
        st.markdown("**Open an application**")
        f1, f2 = st.columns(2)
        status_filter = f1.multiselect("Filter by status", STAGE_ORDER, default=[])
        text = f2.text_input("Search by name or application ID")
        view = df.copy()
        if status_filter:
            view = view[view.Status.isin(status_filter)]
        if text:
            view = view[view.Applicant.str.contains(text, case=False) | view.Application.str.contains(text, case=False)]
        pick = st.selectbox("Choose application", view.Application.tolist() or ["-"],
                            format_func=lambda x: x if x == "-" else f"{x}  -  {view[view.Application == x].Applicant.iloc[0]}")
        st.button("Open in Application Review →", on_click=go, args=("Application Review", pick), type="primary", disabled=(pick == "-"))

    show = view.copy()
    show["Loan amount"] = show["Loan amount"].apply(inr)
    st.dataframe(show, width="stretch", hide_index=True, height=380)


# ============================================================ APPLICATION REVIEW
def page_review():
    t = get_tables()
    st.title("Application Review")
    ids = t["applications"].application_id.tolist()
    if "sel_app" not in st.session_state:
        st.session_state.sel_app = ids[0]
    app_id = st.selectbox("Application", ids, key="sel_app")
    res = agents.run_workflow(app_id, t)  # same result every time: rules are deterministic
    app, ap = res["app"], res["applicant"]
    ran = st.session_state.setdefault("ran", set())
    decisions = load_decisions()

    # ---- A. application details
    st.subheader(f"{ap['name']}  ·  {app_id}")
    c = st.columns(5)
    c[0].metric("Loan requested", inr_short(app.loan_amount))
    c[1].metric("Tenure", f"{app.tenure_years} years")
    c[2].metric("Monthly income (declared)", inr(ap.monthly_income))
    c[3].metric("Existing monthly EMIs", inr(ap.existing_emi))
    c[4].metric("Property value", inr_short(app.property_value))
    st.caption(f"{ap.employment_type} · {ap.employer} · Age {ap.age} · {ap.city} · {app.property_type} in {app.property_city} · "
               f"Customer for {ap.years_with_bank} year(s) · Submitted {app.submitted_days_ago} day(s) ago")

    with st.expander("Document checklist (as received)", expanded=not (app_id in ran or app.ai_processed)):
        d = res["docs"][["doc_type", "submitted", "scan_quality"]].copy()
        d["Received"] = d.submitted.map({True: "✅ Received", False: "❌ Missing"})
        d = d.rename(columns={"doc_type": "Document", "scan_quality": "Scan quality"})[["Document", "Received", "Scan quality"]]
        st.dataframe(d, hide_index=True, width="stretch")

    # ---- B. agent workflow
    st.divider()
    st.subheader("AI workflow")
    st.markdown('<div class="sim">The three agents below are <b>simulated</b> (rule-based) for this demo. Each one shows what it checked, which tools and data it used, and what it hands to the next step.</div>',
                unsafe_allow_html=True)

    already = app_id in ran or app.ai_processed
    if not already:
        st.info("This application is waiting for AI review. Press the button to run the three agents.")
    label = "Re-run AI workflow" if already else "▶ Run AI workflow"
    if st.button(label, type="primary"):
        bar = st.progress(0, text="Starting…")
        for i, name in enumerate(["Document Verification Agent", "Loan Policy Agent", "Credit Risk Review Agent"]):
            bar.progress(int((i / 3) * 100), text=f"{name} is working…")
            time.sleep(0.7)
        bar.progress(100, text="All agents finished.")
        time.sleep(0.3)
        ran.add(app_id)
        st.rerun()
    if not already:
        return

    steps = st.columns(3)
    for col, (title, r) in zip(steps, [("1 · Document Verification", res["doc"]), ("2 · Loan Policy", res["policy"]), ("3 · Credit Risk Review", res["risk"])]):
        n_flag = sum(1 for x in r["checks"] if x["status"] != "pass")
        col.markdown(f"**{title}**  \n{len(r['checks'])} checks · {n_flag} need attention")

    for key, num in [("doc", 1), ("policy", 2), ("risk", 3)]:
        r = res[key]
        with st.container(border=True):
            st.markdown(f"#### Agent {num}: {r['agent']}")
            st.caption("Tools and data used: " + " · ".join(r["tools"]))
            render_checks(r["checks"])
            st.markdown(f'<div class="handoff">➜ {r["handoff"]}</div>', unsafe_allow_html=True)

    # ---- C. credit officer review
    st.divider()
    st.subheader("Credit officer review")
    st.markdown('<div class="banner"><b>AI recommendations are not final credit decisions.</b> The authorised credit officer is responsible for the decision.</div>',
                unsafe_allow_html=True)
    risk = res["risk"]
    st.markdown(f"**AI recommendation:** {rec_pill(risk['recommendation'])}", unsafe_allow_html=True)
    st.markdown("**Reasons**")
    for w in risk["reasons"]:
        st.markdown(f"- {w}")

    k1, k2, k3 = st.columns(3)
    with k1:
        st.markdown("**Missing documents**")
        st.write(", ".join(res["doc"]["missing"]) or "None")
    with k2:
        st.markdown("**Policy checks**")
        pc = res["policy"]["checks"]
        st.write(f"{sum(c['status']=='pass' for c in pc)} met · {sum(c['status']=='flag' for c in pc)} to review · {sum(c['status']=='fail' for c in pc)} breached")
    with k3:
        st.markdown("**Risk flags**")
        if risk["all_fails"] or risk["all_flags"]:
            for c in risk["all_fails"] + risk["all_flags"]:
                st.write(f"{ICON[c['status']]} {c['name']}")
        else:
            st.write("None")

    prior = decisions[decisions.application_id == app_id]
    if len(prior):
        last = prior.iloc[-1]
        st.success(f"Decision recorded (demo): **{last.decision}** by {last.officer} at {last.time}. Notes: {last.notes if isinstance(last.notes, str) else '-'}")

    with st.form(f"decision_{app_id}"):
        st.markdown("**Record your decision (demo)**")
        decision = st.radio("Decision", ["Approve", "Reject", "Request more information"], horizontal=True)
        notes = st.text_area("Officer notes (optional)", placeholder="e.g. Verified with customer, income letter requested.")
        officer = st.text_input("Officer name", value="Demo Credit Officer")
        if st.form_submit_button("Record decision", type="primary"):
            new = pd.DataFrame([{"application_id": app_id, "decision": decision, "notes": notes, "officer": officer,
                                 "time": datetime.now().strftime("%d %b %Y %H:%M")}])
            pd.concat([decisions, new]).to_csv(DECISIONS_FILE, index=False)
            st.rerun()


# ===================================================================== APPROACH
def page_approach():
    st.title("Our Approach")
    st.markdown("**From scattered documents to a faster, fairer home loan decision, in two steps.**")

    st.header("Act 1 · The data foundation")
    st.markdown("A home loan decision draws on three very different kinds of information. Today they sit in separate places, so people re-key and re-check them by hand. "
                "We first bring them together in **one governed data layer (a lakehouse)**.")
    a, b, c = st.columns(3)
    with a:
        st.markdown("##### 📄 Documents & policies  \n*Unstructured*")
        st.write("RBI circulars, the bank's credit policy, and applicant documents: KYC, salary slips, bank statements, ITRs, property papers.")
        st.caption("Challenge: policies change often; documents arrive as scans.")
    with b:
        st.markdown("##### 🏦 Core banking data  \n*Structured*")
        st.write("Customer profile, accounts, existing loans, repayment history.")
        st.caption("Challenge: data sits in silos.")
    with c:
        st.markdown("##### 🔌 External checks  \n*APIs*")
        st.write("Credit bureau, CERSAI (charges on property), PAN and Aadhaar verification, GST, account aggregators.")
        st.caption("Challenge: different formats, speed and cost per call.")
    st.graphviz_chart("""
    digraph G { rankdir=LR; node [shape=box, style="rounded,filled", fontname="Helvetica", fontsize=11, color="#CBD5E1"];
      src [label="Three kinds of source\\n(documents · core banking · external APIs)", fillcolor="#FEF3C7"];
      raw [label="Raw zone\\nlanded as received", fillcolor="#E5E7EB"];
      clean [label="Cleaned zone\\ntext read from scans,\\nfields standardised", fillcolor="#DBEAFE"];
      curated [label="Curated zone\\none view per application,\\nready for the agents", fillcolor="#DCFCE7"];
      src -> raw -> clean -> curated; }
    """)
    st.info("**Business benefit:** one trusted view of each application, with every number traceable to its source.")

    st.header("Act 2 · The agentic solution on top")
    st.markdown("Three focused agents work in sequence on the curated data. Each does one job, shows its reasoning, and hands over to the next. "
                "**A human credit officer makes the final decision.**")
    st.graphviz_chart("""
    digraph G { rankdir=LR; node [shape=box, style="rounded,filled", fontname="Helvetica", fontsize=11, color="#CBD5E1"];
      app [label="New application", fillcolor="#E5E7EB"];
      a1 [label="1 Document Verification\\nAgent\\nreads documents, flags gaps", fillcolor="#DBEAFE"];
      a2 [label="2 Loan Policy Agent\\nchecks the bank's policy,\\ncites each rule", fillcolor="#DBEAFE"];
      a3 [label="3 Credit Risk Review Agent\\nadds bureau + property checks,\\nflags risks, recommends", fillcolor="#DBEAFE"];
      h [label="Credit Officer\\nreviews and DECIDES", fillcolor="#DCFCE7", penwidth=2];
      app -> a1 -> a2 -> a3 -> h; }
    """)
    t = pd.DataFrame({
        "Agent": ["Document Verification", "Loan Policy", "Credit Risk Review"],
        "What it does": ["Checks all documents are present and readable; compares names and income across documents",
                         "Applies age, income, FOIR, LTV and tenure rules from the written policy",
                         "Adds credit-bureau and property-charge checks; combines everything into a recommendation"],
        "Data and tools used": ["Applicant documents, checklist", "Policy library, EMI calculator, RBI LTV norms", "Mock bureau, mock CERSAI, repayment history"],
        "Hands off to": ["Loan Policy Agent", "Credit Risk Review Agent", "Human credit officer"],
    })
    st.dataframe(t, hide_index=True, width="stretch")
    st.markdown("**What the bank gains** *(directional benefits to validate with the bank, not measured results)*")
    st.markdown("- **Faster:** missing documents and obvious gaps are caught on day one, not day five.\n"
                "- **More consistent:** every file is checked against the same written policy.\n"
                "- **Explainable:** every recommendation lists its reasons and the rule or data behind them.\n"
                "- **Controlled:** officers keep the final say, and every decision is logged.")


# =================================================================== ARCHITECTURE
def page_architecture():
    st.title("Architecture")
    st.caption("Business layers and the technology that implements them. The demo runs locally on CSV files; BigQuery is the planned data layer.")
    st.markdown(ARCH_HTML, unsafe_allow_html=True)

    st.subheader("What each layer does, and how it is built")
    st.table(pd.DataFrame({
        "Layer": ["Data sources", "Ingestion", "Lakehouse", "Agents", "Tools and APIs", "Bank employee UI", "Governance"],
        "Business role": ["Where the facts about the applicant, the property and the rules come from",
                          "Turns scans, PDFs and feeds into usable data",
                          "One governed place for all three kinds of data",
                          "Do the repetitive checking and draft a reasoned recommendation",
                          "Give agents calculations and external checks",
                          "Where officers see findings and decide",
                          "Keeps people in control and the process auditable"],
        "In this demo": ["Fictional CSV files and a sample policy file", "Python script (generate_data.py)", "CSV files in /data",
                         "Rule-based Python functions (simulated)", "EMI calculator; stubbed bureau and CERSAI responses",
                         "Streamlit web app", "Officer decision form saved to a log file"],
        "Planned production technology": ["Source systems, document stores", "Cloud Storage + Document AI, scheduled loads", "BigQuery (raw, cleaned, curated datasets)",
                                          "LLM-based agents (e.g. Claude) with tool calling", "Real bureau, CERSAI and KYC APIs behind an API gateway",
                                          "Web app on Cloud Run", "Role-based access, audit logs, PII masking, model monitoring"],
    }).set_index("Layer"))

    st.subheader("How this maps to the reference architecture")
    st.table(pd.DataFrame({
        "Reference component": ["Client's enterprise data + ETL", "Data platform (BigQuery, GCS)", "Agent's enterprise knowledge (features, embeddings)",
                                "Agent (LLM, workflow, sequential)", "Runner, session, memory, artifacts", "Tool box (retrieval, APIs, actions)",
                                "Tool integrations (function, MCP, OpenAPI)", "Front end, back end, app", "HIL tool, HIL decision storage", "Feedback storage, confidence scoring, RLHF"],
        "In our solution": ["Source layer and ingestion", "Lakehouse: raw, cleaned, curated", "Policy library, curated features, document search",
                            "Three agents run in sequence", "Orchestrator with case state and saved findings", "Database lookup, policy search, EMI calculator, bureau and CERSAI checks",
                            "Mock services in demo; API or MCP connectors in production", "Streamlit app in demo", "Credit officer decision step; decision log",
                            "Officer corrections stored; learning loop planned"],
        "Status": ["Demo: CSV files", "Planned: BigQuery", "Demo: policy file; embeddings planned", "Demo: simulated rules", "Demo: held in the page session",
                   "Demo: Python functions and stubs", "Planned", "Demo", "Demo: decision form saved to a file", "Planned, not built"],
    }).set_index("Reference component"))

    st.subheader("Human-in-the-loop points")
    st.markdown("1. **Exceptions** the agents cannot resolve (poor scans, mismatches) go to an operations user.\n"
                "2. **The final credit decision** is always made by an authorised credit officer.\n"
                "3. **Policy changes** are owned and approved by the credit policy team; agents only read the approved version.")
    st.warning("Not implemented in this demo: real bureau, CERSAI, PAN or Aadhaar connections; BigQuery; a real language model; production security.")


# ============================================================== ABOUT, FAQ, CONTACT
def page_about():
    st.title("About & FAQ")
    st.markdown("**HomeLoan AI** is a point-of-view demo showing how agentic AI could help a bank process home loan applications faster and more consistently, "
                "with credit officers always in control.")
    st.markdown("It was built as a presales demonstration. It uses **fictional data only**.")
    st.subheader("Frequently asked questions")
    faqs = [
        ("Does the AI approve or reject loans?", "No. The agents prepare the file and recommend. An authorised credit officer makes the final decision."),
        ("Is any real customer data used?", "No. All applicants, documents, scores and property checks are fictional and randomly generated."),
        ("Are real bureau or government systems connected?", "No. Credit bureau and CERSAI responses are mocked. A real build would connect to the bank's approved providers."),
        ("Are the agents using a real language model?", "In this demo they are simulated with rules and clearly labelled. A production version would use a language model for reading documents and writing explanations, with the same checks and hand-offs."),
        ("How do I know why a recommendation was made?", "Every check shows its result, the data used and the policy rule it relied on."),
        ("What about changes in RBI rules or the bank's policy?", "Policies live in a policy library the Loan Policy Agent reads. Updating the library updates the checks."),
        ("Which loan product is covered?", "Individual home loans for property purchase."),
        ("Where would the data live in production?", "In a lakehouse such as BigQuery, with raw, cleaned and curated layers."),
    ]
    for q, a in faqs:
        with st.expander(q):
            st.write(a)


def page_contact():
    st.title("Contact Us")
    st.write("Interested in seeing how this could work on your bank's data? Leave a note below.")
    with st.form("contact"):
        st.text_input("Name")
        st.text_input("Work email")
        st.text_input("Bank / organisation")
        st.text_area("What would you like to explore?")
        if st.form_submit_button("Send"):
            st.success("Thank you. This is a demo form: nothing was sent or stored.")
    st.caption("Presales contact: [add your name and email here before the interview]")


{"Dashboard": page_dashboard, "Application Review": page_review, "Approach": page_approach,
 "Architecture": page_architecture, "About & FAQ": page_about, "Contact": page_contact}[page]()
