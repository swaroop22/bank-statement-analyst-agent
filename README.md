# Bank Statement Spending Analyst Agent 💳

An autonomous Personal Finance & Financial Data Extraction Agent designed to access, parse, sanitize, categorize, and analyze bank and credit card statements provided via **Google Drive shared links** or **local uploads** (PDF, CSV, Excel).

---

## 🌟 Key Capabilities

1. **Multi-Format Ingestion:**
   - **Google Drive Integration:** Ingests statements directly from Google Drive folder URLs or direct file links. Detects restricted view permissions and provides clear guidance.
   - **Multi-File Local Uploads:** Supports PDF (single-line & staggered tabular formats), CSV, TSV, and Excel (`.xlsx`, `.xls`).
   - **Multi-Account Aggregation:** Combines multiple accounts (e.g., Chase Checking + Amex Credit Card + Bank of America) into a unified spending analysis.

2. **Hygiene & Zero Double-Counting Engine:**
   - **Internal Transfer Filtering:** Automatically excludes credit card payments from checking accounts, account-to-account transfers, and statement balance forward rows.
   - **De-duplication:** Hashes date, amount, and sanitized payee to eliminate overlapping statement duplicate transactions.
   - **Refund Offsetting:** Detects merchant returns and offsets them directly against their originating expense category instead of skewing income figures.

3. **Smart Budgeting & Safe-to-Spend Allowance:**
   - **Interactive Category Budget Sliders:** Category spend trackers for Groceries, Dining, Housing, Utilities, Shopping, and Transport with real-time sliders and spend-alert meters (Green < 75%, Amber 75-99%, Coral Red ≥ 100%).
   - **"Safe to Spend" / "Left to Spend" Allowance Gauge:** Calculates remaining allowance using the formula (`Income - Fixed Bills - Variable Outflows = Safe to Spend`) with daily safe burn pace.
   - **Subscription Cancel Concierge:** 1-click concierge cancellation simulation that computes projected annual savings, tracks active cancellations, and increments the savings counter.

4. **Strict 9-Category Schema + Inflows:**
   - **Housing & Utilities** (rent, electric, gas, water, internet, trash)
   - **Groceries** (supermarkets, wholesale clubs, local produce)
   - **Dining Out & Food Delivery** (restaurants, cafes, delivery services)
   - **Transportation** (fuel, transit, rideshares, tolls, auto maintenance)
   - **Healthcare & Medical** (pharmacy, clinics, vision/dental, insurance)
   - **Shopping & Discretionary** (apparel, electronics, home goods, personal care)
   - **Entertainment & Subscriptions** (streaming, gym memberships, hobbies)
   - **Debt Service** (student/auto/personal loans, excluding card payoff transfers)
   - **Miscellaneous / Other** (bank fees, ATM cash withdrawals)
   - **Uncategorized / Needs Review** (strict fallback to prevent hallucinations)
   - **Income / Inflows** (isolated in executive summary, never treated as negative spend)

5. **Security & Privacy Guardrails:**
   - **Account Redaction:** Masks account numbers to the last 4 digits (e.g., `Checking ...4812`, `SBI Savings ...0544`).
   - **PII Scrubbing:** Strips SSNs, PANs, routing numbers, and residential street addresses from all outputs.
   - **100.0% Mathematical Reconciliation:** Category breakdown percentages are strictly balanced to sum to exactly 100.0% of total reported outflow.

---

## 🚀 Quickstart

### 1. Environment Setup
The project uses a Python 3.9+ virtual environment.

```bash
cd scratch/bank-statement-analyst-agent

# Activate virtual environment
source .venv/bin/activate
```

### 2. Run Analysis via CLI

Analyze the included sample multi-account statements:
```bash
python cli.py --dir samples/
```

Analyze a specific statement file (PDF, CSV, or Excel):
```bash
python cli.py --file samples/bank_of_america_checking_oct2024.pdf
```

Analyze a Google Drive folder:
```bash
python cli.py --drive-url "https://drive.google.com/drive/folders/1RncmKINKSQozomIa_yy6jl4anWqMccVP?usp=drive_link"
```

Save reports:
```bash
python cli.py --dir samples/ --output-md spending_report.md --output-json spending_report.json
```

---

## 💻 Web Dashboard UI

Launch the dark-mode glassmorphic web dashboard:

```bash
python app.py
```
Open **[http://localhost:5055](http://localhost:5055)** in your browser.

- **Google Drive URL Input:** Paste any shared Google Drive link.
- **Drag & Drop:** Upload multiple PDF and CSV statements simultaneously.
- **One-Click Demo:** Click `⚡ Run Multi-Account Demo` to see instant end-to-end reconciliation.
- **Export:** 1-click download of the complete Markdown report.

---

## 🔒 Google Drive Folder Permissions Guide

If a Google Drive folder is restricted, the agent detects this and prompts:
1. Open the folder in **Google Drive**.
2. Click **Share** (top-right button).
3. Under **General access**, change from **Restricted** to **Anyone with the link**.
4. Set role to **Viewer**.
5. Copy the link and re-run analysis.

---

## 🧪 Running Tests

The test suite validates parsing, hygiene, categorization, 100% spend sum constraint, and PII redaction:

```bash
.venv/bin/pytest tests/
```

---

## 📁 Project Structure

```
bank-statement-analyst-agent/
├── .venv/                      # Python virtual environment
├── core/
│   ├── models.py               # Transaction, StatementMetadata, Report data structures
│   ├── drive_downloader.py     # Google Drive folder/file downloader with permission guards
│   ├── hygiene.py              # Transfer filtering, de-duplication, refund offsetter
│   ├── categorizer.py          # 9-Category rule & LLM classifier
│   ├── recurring_detector.py   # Subscriptions & recurring fixed burn analyzer
│   ├── analyst.py              # Report synthesizer, 100% sum balancer, PII redactor
│   ├── pipeline.py             # End-to-end pipeline orchestrator
│   └── parsers/
│       ├── base_parser.py      # Abstract parser interface
│       ├── csv_excel_parser.py # CSV/XLSX multi-bank column extractor
│       └── pdf_parser.py       # PDF statement reader (single & staggered layouts)
├── samples/
│   ├── chase_checking_oct2024_act4812.csv
│   ├── amex_credit_card_oct2024_act8821.csv
│   ├── bank_of_america_checking_oct2024.pdf
│   ├── generate_sample_data.py
│   └── generate_sample_pdf.py
├── templates/
│   └── index.html              # Glassmorphic web dashboard
├── tests/
│   └── test_agent.py           # Pytest test suite
├── app.py                      # Flask web application server
├── cli.py                      # Rich terminal CLI
├── requirements.txt            # Dependency specifications
└── README.md                   # System documentation
```
