# HomeLoan AI - Intelligent Loan Processing Assistant (demo)

A point-of-view demo of agentic AI for home loan processing at a mid-sized Indian bank.
ALL DATA IS FICTIONAL. Agents are simulated (rule-based). Bureau and CERSAI services are mocked.

## Run it (Anaconda Prompt / Terminal)
1. cd into this folder
2. pip install -r requirements.txt
3. python generate_data.py      (optional - data is already included; re-run to regenerate)
4. streamlit run app.py

## Files
- app.py              the website (pages, tables, buttons)
- agents.py           the three agents + EMI calculator
- generate_data.py    creates the fictional data in data/
- data/               CSV files, mock bureau/CERSAI, policy.json
- data/decisions.csv  created when an officer records a decision
