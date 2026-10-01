"""
Flask Web Application for Bank Statement Spending Analyst Agent.
Provides an interactive dashboard for Google Drive analysis, file drag-and-drop,
live charts, subscription breakdown, and markdown exports.
"""

import os
import tempfile
import json
import re
from datetime import datetime
from collections import defaultdict
from flask import Flask, render_template, request, jsonify, Response, send_file
from werkzeug.utils import secure_filename

from core.pipeline import SpendingAnalysisPipeline
from core.models import AnalysisReport, Transaction, TransactionType

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = os.path.join(tempfile.gettempdir(), 'bank_agent_uploads')
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50 MB
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

pipeline = SpendingAnalysisPipeline()

# Multi-Profile State Management for Family Dashboards
PROFILES = {
    "mom": {
        "id": "mom",
        "name": "Mom",
        "avatar": "👩",
        "relation": "Mom (India)",
        "subtitle": "State Bank of India (12 Statements) • Dec 2022 – Jan 2024",
        "currency": "INR",
        "currency_symbol": "₹",
        "drive_folder_url": "https://drive.google.com/drive/folders/1RncmKINKSQozomIa_yy6jl4anWqMccVP?usp=drive_link",
        "pdf_password": "46756010166",
        "user_settings": {
            "income_target": None,
            "pay_cadence": "Monthly",
            "savings_goal_percent": 20.0,
            "category_budgets": {},
            "canceled_subscriptions": {},
            "total_annual_saved": 0.0
        },
        "report": None,
        "transactions": [],
        "markdown": "",
        "metadata": []
    },
    "dad": {
        "id": "dad",
        "name": "Dad",
        "avatar": "👨",
        "relation": "Dad (India)",
        "subtitle": "Kismatpur Construction & Senior Accounts • Aug 2023 – Jul 2024 (99 Payees)",
        "currency": "INR",
        "currency_symbol": "₹",
        "drive_folder_url": "",
        "pdf_password": "",
        "user_settings": {
            "income_target": None,
            "pay_cadence": "Monthly",
            "savings_goal_percent": 25.0,
            "category_budgets": {},
            "canceled_subscriptions": {},
            "total_annual_saved": 0.0
        },
        "report": None,
        "transactions": [],
        "markdown": "",
        "metadata": []
    },
    "wife": {
        "id": "wife",
        "name": "Wife",
        "avatar": "👩‍💼",
        "relation": "Wife (India)",
        "subtitle": "ICICI Salary & Operational Accounts • 2023",
        "currency": "INR",
        "currency_symbol": "₹",
        "drive_folder_url": "",
        "pdf_password": "",
        "user_settings": {
            "income_target": None,
            "pay_cadence": "Monthly",
            "savings_goal_percent": 30.0,
            "category_budgets": {},
            "canceled_subscriptions": {},
            "total_annual_saved": 0.0
        },
        "report": None,
        "transactions": [],
        "markdown": "",
        "metadata": []
    }
}

ACTIVE_PROFILE_ID = "mom"

def ensure_profile_loaded(profile_id: str):
    prof = PROFILES.get(profile_id)
    if not prof:
        return
    if prof.get("report") is not None and len(prof.get("transactions", [])) > 0:
        return

    if profile_id == "mom":
        drive_dir = os.path.join(os.path.dirname(__file__), "downloads", "drive_folder_1RncmKINKSQozomIa_yy6jl4anWqMccVP")
        if not os.path.exists(drive_dir):
            downloads_base = os.path.join(os.path.dirname(__file__), "downloads")
            if os.path.exists(downloads_base):
                subdirs = [os.path.join(downloads_base, d) for d in os.listdir(downloads_base) if os.path.isdir(os.path.join(downloads_base, d))]
                if subdirs:
                    drive_dir = subdirs[0]
        if os.path.exists(drive_dir):
            files = [
                os.path.join(drive_dir, f) for f in os.listdir(drive_dir)
                if f.lower().endswith(('.pdf', '.csv', '.xlsx', '.xls'))
            ]
            if files:
                try:
                    report, txs, md_text = pipeline.process_files(files, password=prof.get("pdf_password") or "46756010166")
                    prof["report"] = report
                    prof["transactions"] = txs
                    prof["markdown"] = md_text
                except Exception as e:
                    print(f"Error loading Mom statements: {e}")
    elif profile_id == "dad":
        dad_file = os.path.join(os.path.dirname(__file__), "samples", "dad_sbi_senior_account_2023.csv")
        if not os.path.exists(dad_file):
            try:
                from samples.generate_family_samples import generate_family_statements
                generate_family_statements(os.path.join(os.path.dirname(__file__), "samples"))
            except Exception as e:
                print(f"Error generating Dad sample: {e}")
        if os.path.exists(dad_file):
            try:
                report, txs, md_text = pipeline.process_files([dad_file])
                prof["report"] = report
                prof["transactions"] = txs
                prof["markdown"] = md_text
            except Exception as e:
                print(f"Error loading Dad sample: {e}")
    elif profile_id == "wife":
        wife_file = os.path.join(os.path.dirname(__file__), "samples", "wife_icici_salary_account_2023.csv")
        if not os.path.exists(wife_file):
            try:
                from samples.generate_family_samples import generate_family_statements
                generate_family_statements(os.path.join(os.path.dirname(__file__), "samples"))
            except Exception as e:
                print(f"Error generating Wife sample: {e}")
        if os.path.exists(wife_file):
            try:
                report, txs, md_text = pipeline.process_files([wife_file])
                prof["report"] = report
                prof["transactions"] = txs
                prof["markdown"] = md_text
            except Exception as e:
                print(f"Error loading Wife sample: {e}")

def get_active_profile():
    global ACTIVE_PROFILE_ID
    ensure_profile_loaded(ACTIVE_PROFILE_ID)
    return PROFILES.get(ACTIVE_PROFILE_ID, PROFILES["mom"])

class ActiveProfileReportProxy(dict):
    def __getitem__(self, key):
        return get_active_profile().get(key)
    def __setitem__(self, key, value):
        get_active_profile()[key] = value
    def __contains__(self, key):
        return key in get_active_profile()
    def get(self, key, default=None):
        return get_active_profile().get(key, default)

class ActiveProfileSettingsProxy(dict):
    def __getitem__(self, key):
        return get_active_profile()["user_settings"].get(key)
    def __setitem__(self, key, value):
        get_active_profile()["user_settings"][key] = value
    def __contains__(self, key):
        return key in get_active_profile()["user_settings"]
    def get(self, key, default=None):
        return get_active_profile()["user_settings"].get(key, default)
    def values(self):
        return get_active_profile()["user_settings"].values()

LATEST_REPORT = ActiveProfileReportProxy()
USER_SETTINGS = ActiveProfileSettingsProxy()



def generate_budget(report_dict, user_settings=None, transactions=None):
    """
    Computes safe-to-spend allowance / net surplus, category budget targets,
    pacing status, review queue metrics, monthly spending trend, and transparent calculation breakdown.
    """
    settings = user_settings or USER_SETTINGS
    inflow = float(report_dict.get("total_inflow", 0.0))
    income = float(settings.get("income_target") or inflow)
    total_outflow = float(report_dict.get("total_outflow", 0.0))
    recurring_monthly = float(report_dict.get("total_recurring_monthly", 0.0))
    currency = report_dict.get("currency", "USD")
    sym = report_dict.get("currency_symbol", "$" if currency != "INR" else "₹")
    statement_period = report_dict.get("statement_period", "")

    # Parse period dates to determine if multi-month historical or current cycle
    is_historical = True
    months_count = 1
    date_matches = re.findall(r'\b(20\d{2}-\d{2}-\d{2})\b', statement_period)
    if len(date_matches) >= 2:
        try:
            d1 = datetime.strptime(date_matches[0], "%Y-%m-%d")
            d2 = datetime.strptime(date_matches[1], "%Y-%m-%d")
            days_span = (d2 - d1).days
            months_count = max(1, round(days_span / 30.4))
            is_historical = (days_span > 45)
        except Exception:
            pass

    custom_budgets = settings.get("category_budgets", {})
    categories = report_dict.get("category_breakdowns", [])

    category_budgets = []
    total_budgeted = 0.0
    total_variable_spent = 0.0
    needs_review_amount = 0.0
    needs_review_count = 0

    for cat in categories:
        c_name = cat["category"]
        c_spent = float(cat["total_spent"])

        if c_name in ["Miscellaneous / Other", "Uncategorized / Needs Review"]:
            needs_review_amount += c_spent

        # Determine budget limit
        if c_name in custom_budgets and custom_budgets[c_name] is not None:
            limit = float(custom_budgets[c_name])
        else:
            if currency == "INR":
                if c_spent > 0:
                    limit = float(max(round(c_spent * 1.15, -2), round(c_spent + 200, -2)))
                else:
                    limit = 1000.0
            else:
                if c_spent > 0:
                    limit = float(max(round(c_spent * 1.15, -1), round(c_spent + 25, -1)))
                else:
                    limit = 100.0

        total_budgeted += limit
        pct_used = (c_spent / limit * 100.0) if limit > 0 else 0.0
        remaining = limit - c_spent

        is_fixed = any(k in c_name.lower() for k in ["housing", "debt", "rent"])
        if not is_fixed:
            total_variable_spent += c_spent

        status = "danger" if pct_used >= 100.0 else ("warning" if pct_used >= 75.0 else "good")

        category_budgets.append({
            "category": c_name,
            "spent": round(c_spent, 2),
            "budget": round(limit, 2),
            "percentage_used": round(pct_used, 1),
            "remaining": round(remaining, 2),
            "is_over": bool(c_spent > limit),
            "over_amount": round(max(0.0, c_spent - limit), 2),
            "status": status,
            "top_merchants": cat.get("top_merchants", [])
        })

    # Count transactions needing review if transactions list provided
    if transactions:
        needs_review_txs = [
            t for t in transactions 
            if (getattr(t, 'category', '') in ["Miscellaneous / Other", "Uncategorized / Needs Review"])
            and (getattr(t, 'type', None) == TransactionType.DEBIT or getattr(t, 'type', None) == 'DEBIT')
            and not getattr(t, 'is_internal_transfer', False)
            and not getattr(t, 'is_excluded', False)
        ]
        needs_review_count = len(needs_review_txs)
        needs_review_amount = sum(getattr(t, 'amount', 0.0) for t in needs_review_txs)

    # Safe to Spend / Net Discretionary Surplus calculation
    if is_historical:
        safe_to_spend = max(0.0, income - recurring_monthly - total_variable_spent)
        allowance_total = max(0.0, income - recurring_monthly)
        safe_label = "Net Discretionary Surplus (Historical Period)"
        period_label = f"Historical analysis: {statement_period}"
        daily_safe_allowance = None  # Suppress per-day in historical mode
    else:
        allowance_total = max(0.0, income - recurring_monthly) if income > 0 else total_budgeted
        safe_to_spend = max(0.0, income - recurring_monthly - total_variable_spent) if income > 0 else max(0.0, total_budgeted - total_outflow)
        safe_label = "Safe-to-Spend Allowance"
        period_label = f"Billing cycle: {statement_period}"
        days_left = 18
        daily_safe_allowance = round(safe_to_spend / days_left, 2) if days_left > 0 else 0.0

    # Monthly Trend (Spend over time)
    monthly_trend = []
    if transactions:
        month_buckets = defaultdict(lambda: {"outflow": 0.0, "inflow": 0.0})
        for t in transactions:
            t_date = getattr(t, 'date', '')
            if len(t_date) >= 7:
                m_key = t_date[:7]  # YYYY-MM
                t_amt = getattr(t, 'amount', 0.0)
                t_type = getattr(t, 'type', None)
                t_type_val = t_type.value if hasattr(t_type, 'value') else str(t_type)
                is_xfer = getattr(t, 'is_internal_transfer', False)
                is_excl = getattr(t, 'is_excluded', False)
                if not is_xfer and not is_excl:
                    if t_type_val == 'DEBIT':
                        month_buckets[m_key]["outflow"] += t_amt
                    elif t_type_val == 'CREDIT':
                        month_buckets[m_key]["inflow"] += t_amt

        for mk in sorted(month_buckets.keys()):
            try:
                m_obj = datetime.strptime(mk, "%Y-%m")
                m_label = m_obj.strftime("%b %Y")
            except Exception:
                m_label = mk
            out_val = round(month_buckets[mk]["outflow"], 2)
            in_val = round(month_buckets[mk]["inflow"], 2)
            monthly_trend.append({
                "key": mk,
                "label": m_label,
                "outflow": out_val,
                "inflow": in_val,
                "net": round(in_val - out_val, 2)
            })

    confirmed_spending = max(0.0, round(total_outflow - needs_review_amount, 2))
    projected_surplus = max(0.0, round(income - confirmed_spending - recurring_monthly, 2))
    net_cash_flow_val = float(report_dict.get("net_cash_flow", income - total_outflow))

    # Transparent calculation breakdown for users
    calculation_breakdown = {
        "formula": "Net Cash Flow = Total Inflows − Total Outflows (including unreviewed items)",
        "surplus_formula": "Discretionary Surplus = Total Inflows − Fixed Bills − Confirmed Living Expenses",
        "inflow_total": round(income, 2),
        "total_outflow": round(total_outflow, 2),
        "confirmed_spending": round(confirmed_spending, 2),
        "needs_review_amount": round(needs_review_amount, 2),
        "needs_review_count": needs_review_count,
        "fixed_bills": round(recurring_monthly, 2),
        "variable_spend": round(total_variable_spent, 2),
        "safe_to_spend": round(safe_to_spend, 2),
        "net_cash_flow": round(net_cash_flow_val, 2),
        "projected_surplus": round(projected_surplus, 2),
        "internal_transfers_excluded": report_dict.get("internal_transfers_excluded", 0),
        "omitted_categories": ["Internal Transfers (Scrubbed)", "Excluded Transactions"],
        "bills_zero_explanation": (
            "₹0 Fixed Bills / Subscriptions Detected: In Indian bank statements, recurring debits (like rent, utilities, insurance, "
            "or investments) are frequently transferred manually via NEFT, Cheque, or ad-hoc UPI rather than auto-debit mandates (NACH/ECS). "
            "These large transfers are currently grouped under 'Miscellaneous / Other' and 'Uncategorized / Needs Review'. "
            "Use the Review Queue below to re-classify or exclude them."
        ),
        "period_context": f"Calculated across the {months_count}-month period ({statement_period})."
    }

    return {
        "income_baseline": round(income, 2),
        "fixed_bills_monthly": round(recurring_monthly, 2),
        "variable_spent": round(total_variable_spent, 2),
        "total_spent": round(total_outflow, 2),
        "confirmed_spending": round(confirmed_spending, 2),
        "projected_surplus": round(projected_surplus, 2),
        "net_cash_flow": round(net_cash_flow_val, 2),
        "total_budgeted": round(total_budgeted, 2),
        "safe_to_spend": round(safe_to_spend, 2),
        "allowance_total": round(allowance_total, 2),
        "safe_to_spend_percent": round((safe_to_spend / allowance_total * 100.0) if allowance_total > 0 else 0.0, 1),
        "daily_safe_allowance": daily_safe_allowance,
        "is_historical": is_historical,
        "safe_label": safe_label,
        "period_label": period_label,
        "months_count": months_count,
        "needs_review_amount": round(needs_review_amount, 2),
        "needs_review_count": needs_review_count,
        "category_budgets": category_budgets,
        "monthly_trend": monthly_trend,
        "calculation_breakdown": calculation_breakdown,
        "pay_cadence": settings.get("pay_cadence", "Monthly"),
        "savings_rate_projected": round(((income - total_outflow) / income * 100.0) if income > 0 else 0.0, 1),
        "canceled_subscriptions": list(settings.get("canceled_subscriptions", {}).values()),
        "total_annual_saved": round(settings.get("total_annual_saved", 0.0), 2)
    }




@app.route('/')
def index():
    return render_template('index.html')


@app.route('/api/profiles', methods=['GET'])
def list_profiles():
    """List all family member profiles with aggregated health and review statistics."""
    for pid in PROFILES:
        ensure_profile_loaded(pid)
    
    profiles_summary = []
    for pid, p in PROFILES.items():
        rep = p.get("report")
        txs = p.get("transactions", [])
        rep_dict = rep.to_dict() if rep else {}
        b_data = generate_budget(rep_dict, p["user_settings"], txs) if rep else {}
        
        profiles_summary.append({
            "id": pid,
            "name": p["name"],
            "relation": p["relation"],
            "avatar": p["avatar"],
            "subtitle": p["subtitle"],
            "currency_symbol": p.get("currency_symbol", "₹"),
            "total_outflow": rep.total_outflow if rep else 0.0,
            "confirmed_spending": b_data.get("confirmed_spending", 0.0),
            "total_inflow": rep.total_inflow if rep else 0.0,
            "net_cash_flow": rep.net_cash_flow if rep else 0.0,
            "needs_review_count": b_data.get("needs_review_count", 0),
            "needs_review_amount": b_data.get("needs_review_amount", 0.0),
            "transaction_count": len(txs),
            "drive_folder_url": p.get("drive_folder_url", ""),
            "pdf_password": p.get("pdf_password", ""),
            "is_active": (pid == ACTIVE_PROFILE_ID)
        })

    return jsonify({
        "success": True,
        "active_profile_id": ACTIVE_PROFILE_ID,
        "profiles": profiles_summary
    })


@app.route('/api/profile/switch', methods=['POST'])
def switch_profile():
    """Switch currently active family portfolio."""
    global ACTIVE_PROFILE_ID
    data = request.get_json() or {}
    new_pid = data.get('profile_id', 'mom')
    if new_pid not in PROFILES:
        return jsonify({"success": False, "error": f"Unknown profile: {new_pid}"}), 404

    ACTIVE_PROFILE_ID = new_pid
    ensure_profile_loaded(new_pid)
    prof = PROFILES[new_pid]
    rep = prof.get("report")
    txs = prof.get("transactions", [])
    rep_dict = rep.to_dict() if rep else {}
    b_data = generate_budget(rep_dict, prof["user_settings"], txs) if rep else {}

    return jsonify({
        "success": True,
        "active_profile_id": ACTIVE_PROFILE_ID,
        "profile": {
            "id": prof["id"],
            "name": prof["name"],
            "relation": prof["relation"],
            "avatar": prof["avatar"],
            "subtitle": prof["subtitle"],
            "drive_folder_url": prof.get("drive_folder_url", ""),
            "pdf_password": prof.get("pdf_password", ""),
            "currency_symbol": prof.get("currency_symbol", "₹")
        },
        "report": rep_dict,
        "transactions": [t.to_dict() for t in txs],
        "budget": b_data,
        "markdown": prof.get("markdown", "")
    })


@app.route('/api/profile/update-credentials', methods=['POST'])
def update_profile_credentials():
    """Update drive credentials per family profile."""
    data = request.get_json() or {}
    pid = data.get('profile_id', ACTIVE_PROFILE_ID)
    if pid not in PROFILES:
        return jsonify({"success": False, "error": f"Unknown profile: {pid}"}), 404
    
    if 'drive_folder_url' in data:
        PROFILES[pid]['drive_folder_url'] = data['drive_folder_url'].strip()
    if 'pdf_password' in data:
        PROFILES[pid]['pdf_password'] = data['pdf_password'].strip()
    
    return jsonify({
        "success": True, 
        "profile": {
            "id": pid,
            "drive_folder_url": PROFILES[pid]['drive_folder_url'],
            "pdf_password": PROFILES[pid]['pdf_password']
        }
    })


@app.route('/api/dad/vendor-summary', methods=['GET'])
def get_dad_vendor_summary():
    """Return mapped monthly vendor payment data for Dad's account."""
    json_path = os.path.join(os.path.dirname(__file__), 'dad_mapped_transactions.json')
    if not os.path.exists(json_path):
        return jsonify({"success": False, "error": "Mapped vendor file not found"}), 404

    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    person_totals = data.get('person_totals', {})
    person_monthly = data.get('person_monthly', {})
    months = data.get('months', [])
    monthly_items = data.get('monthly_items', {})

    def get_trade_category(vendor):
        v = vendor.lower()
        if 'steel' in v or 'metal' in v: return 'Steel & Structural Metals'
        if 'granite' in v or 'tile' in v: return 'Granite, Marble & Tiles'
        if 'civil' in v or 'construction' in v: return 'Civil Construction Contractors'
        if 'labour' in v or 'mastri' in v or 'atm cash' in v: return 'Site Labour & Supervision'
        if 'driver' in v or 'transport' in v or 'travel' in v or 'motors' in v: return 'Vehicle, Transport & Fuel'
        if 'loan' in v or 'emi' in v: return 'Loan EMI & Financials'
        if 'plot' in v: return 'Land & Property Acquisition'
        if 'brick' in v: return 'Bricks & Masonry'
        if 'hardware' in v or 'traders' in v or 'sink' in v: return 'Hardware, Tools & Fixtures'
        if 'sand' in v or 'dust' in v: return 'Sand & Fine Aggregates'
        if 'cement' in v or 'concrete' in v: return 'Cement & Ready Mix'
        if 'door' in v or 'window' in v: return 'Doors & UPVC Windows'
        if 'plumb' in v or 'carpent' in v: return 'Plumbing & Carpentry'
        if 'electr' in v or 'wire' in v: return 'Electrical & Wiring'
        if 'paint' in v: return 'Painting & Finishing'
        if 'chidvila' in v or 'flat' in v or 'apartment' in v: return 'Property & Advance Accounts'
        if 'planner' in v or 'lawyer' in v: return 'Architect, Planning & Legal'
        if 'water' in v: return 'Water Supply'
        if 'insurance' in v: return 'Insurance'
        return 'General & Contingency'

    sorted_p = sorted(person_totals.items(), key=lambda x: x[1], reverse=True)
    grand_total = sum(person_totals.values())

    vendors_list = []
    category_totals = defaultdict(float)

    for rank, (p, tot) in enumerate(sorted_p, 1):
        cat = get_trade_category(p)
        category_totals[cat] += tot
        m_counts = len([m for m in months if person_monthly.get(p, {}).get(m, 0) > 0])
        pct = round((tot / grand_total * 100), 2) if grand_total > 0 else 0
        vendors_list.append({
            "rank": rank,
            "name": p,
            "category": cat,
            "total": tot,
            "percentage": pct,
            "active_months_count": m_counts,
            "monthly": person_monthly.get(p, {})
        })

    monthly_totals = {}
    for m in months:
        monthly_totals[m] = sum(person_monthly[p].get(m, 0.0) for p in person_monthly)

    categories_list = sorted([{"category": c, "total": t, "percentage": round((t / grand_total * 100), 2)}
                              for c, t in category_totals.items()], key=lambda x: x["total"], reverse=True)

    return jsonify({
        "success": True,
        "months": months,
        "monthly_totals": monthly_totals,
        "grand_total": grand_total,
        "total_vendors": len(vendors_list),
        "vendors": vendors_list,
        "categories": categories_list,
        "monthly_items": monthly_items
    })


@app.route('/api/dad/download-vendor-csv', methods=['GET'])
def download_dad_vendor_csv():
    """Download CSV file of Dad's monthly mapped vendor payments."""
    csv_path = os.path.join(os.path.dirname(__file__), 'dad_monthly_vendor_payments.csv')
    if not os.path.exists(csv_path):
        return "File not found", 404
    return send_file(csv_path, as_attachment=True, download_name='dad_monthly_vendor_payments.csv', mimetype='text/csv')


@app.route('/api/analyze-drive', methods=['POST'])
def analyze_drive():
    global ACTIVE_PROFILE_ID
    data = request.get_json() or {}
    url = data.get('url', '').strip()
    target_pid = data.get('profile_id', ACTIVE_PROFILE_ID)
    if target_pid in PROFILES:
        ACTIVE_PROFILE_ID = target_pid
    prof = get_active_profile()

    password = data.get('password', '').strip() or prof.get('pdf_password') or None
    if not url:
        return jsonify({"success": False, "error": "Google Drive URL is required."}), 400

    prof["drive_folder_url"] = url
    if password:
        prof["pdf_password"] = password

    try:
        report, txs, md_text, err = pipeline.process_google_drive(url, password=password)
        if err:
            is_enc = any(k in err.lower() for k in ["password", "encrypted", "decrypt"])
            return jsonify({
                "success": False, 
                "error": err, 
                "is_encrypted": is_enc,
                "restricted": "permission" in err.lower() or "restricted" in err.lower()
            }), 200

        prof["report"] = report
        prof["transactions"] = txs
        prof["markdown"] = md_text
        prof["subtitle"] = f"Google Drive ({len(txs)} Statements)"

        rep_dict = report.to_dict()
        budget_data = generate_budget(rep_dict, prof["user_settings"], txs)

        return jsonify({
            "success": True,
            "active_profile_id": target_pid,
            "profile": {
                "id": prof["id"],
                "name": prof["name"],
                "relation": prof["relation"],
                "avatar": prof["avatar"],
                "subtitle": prof["subtitle"],
                "currency_symbol": prof.get("currency_symbol", "₹")
            },
            "report": rep_dict,
            "transactions": [t.to_dict() for t in txs],
            "markdown": md_text,
            "budget": budget_data
        })
    except Exception as e:
        err_msg = str(e)
        is_enc = any(k in err_msg.lower() for k in ["password", "encrypted", "decrypt"])
        return jsonify({"success": False, "error": err_msg, "is_encrypted": is_enc}), 200 if is_enc else 500


@app.route('/api/analyze-files', methods=['POST'])
def analyze_files():
    global ACTIVE_PROFILE_ID
    if 'files' not in request.files:
        return jsonify({"success": False, "error": "No statement files uploaded."}), 400

    target_pid = request.form.get('profile_id', ACTIVE_PROFILE_ID)
    if target_pid in PROFILES:
        ACTIVE_PROFILE_ID = target_pid
    prof = get_active_profile()

    password = request.form.get('password', '').strip() or prof.get('pdf_password') or None
    uploaded_files = request.files.getlist('files')
    saved_paths = []

    for file in uploaded_files:
        if file and file.filename:
            filename = secure_filename(file.filename)
            dest = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(dest)
            saved_paths.append(dest)

    if not saved_paths:
        return jsonify({"success": False, "error": "No valid files received."}), 400

    try:
        report, txs, md_text = pipeline.process_files(saved_paths, password=password)
        prof["report"] = report
        prof["transactions"] = txs
        prof["markdown"] = md_text
        prof["subtitle"] = f"{len(saved_paths)} Uploaded Statement(s)"

        rep_dict = report.to_dict()
        budget_data = generate_budget(rep_dict, prof["user_settings"], txs)

        return jsonify({
            "success": True,
            "active_profile_id": target_pid,
            "profile": {
                "id": prof["id"],
                "name": prof["name"],
                "relation": prof["relation"],
                "avatar": prof["avatar"],
                "subtitle": prof["subtitle"],
                "currency_symbol": prof.get("currency_symbol", "₹")
            },
            "report": rep_dict,
            "transactions": [t.to_dict() for t in txs],
            "markdown": md_text,
            "budget": budget_data
        })
    except Exception as e:
        err_msg = str(e)
        is_enc = any(k in err_msg.lower() for k in ["password", "encrypted", "decrypt"])
        return jsonify({"success": False, "error": err_msg, "is_encrypted": is_enc}), 200 if is_enc else 500


@app.route('/api/analyze-downloaded', methods=['POST'])
def analyze_downloaded():
    """Analyze the statements for the active (or requested) profile."""
    global ACTIVE_PROFILE_ID
    data = request.get_json() or {}
    target_pid = data.get('profile_id', ACTIVE_PROFILE_ID)
    if target_pid in PROFILES:
        ACTIVE_PROFILE_ID = target_pid
    prof = get_active_profile()
    password = data.get('password', '').strip() or prof.get('pdf_password') or None

    if target_pid == 'mom':
        drive_dir = os.path.join(os.path.dirname(__file__), "downloads", "drive_folder_1RncmKINKSQozomIa_yy6jl4anWqMccVP")
        if not os.path.exists(drive_dir):
            downloads_base = os.path.join(os.path.dirname(__file__), "downloads")
            if os.path.exists(downloads_base):
                subdirs = [os.path.join(downloads_base, d) for d in os.listdir(downloads_base) if os.path.isdir(os.path.join(downloads_base, d))]
                if subdirs:
                    drive_dir = subdirs[0]
                else:
                    return jsonify({"success": False, "error": "No downloaded statements found locally. Please analyze via Google Drive URL."}), 404

        files = [
            os.path.join(drive_dir, f) for f in os.listdir(drive_dir)
            if f.lower().endswith(('.pdf', '.csv', '.xlsx', '.xls'))
        ]
        if not files:
            return jsonify({"success": False, "error": "No statement files found in local download directory."}), 404

        try:
            report, txs, md_text = pipeline.process_files(files, password=password)
            prof["report"] = report
            prof["transactions"] = txs
            prof["markdown"] = md_text
        except Exception as e:
            return jsonify({"success": False, "error": str(e)}), 500
    else:
        ensure_profile_loaded(target_pid)

    rep = prof.get("report")
    txs = prof.get("transactions", [])
    rep_dict = rep.to_dict() if rep else {}
    budget_data = generate_budget(rep_dict, prof["user_settings"], txs)

    return jsonify({
        "success": True,
        "active_profile_id": target_pid,
        "profile": {
            "id": prof["id"],
            "name": prof["name"],
            "relation": prof["relation"],
            "avatar": prof["avatar"],
            "subtitle": prof["subtitle"],
            "currency_symbol": prof.get("currency_symbol", "₹")
        },
        "report": rep_dict,
        "transactions": [t.to_dict() for t in txs],
        "markdown": prof.get("markdown", ""),
        "budget": budget_data
    })


@app.route('/api/sample-demo', methods=['GET', 'POST'])
def sample_demo():
    """Run analysis immediately on pre-configured sample files."""
    samples_dir = os.path.join(os.path.dirname(__file__), 'samples')
    files = [
        os.path.join(samples_dir, f) for f in os.listdir(samples_dir)
        if f.lower().endswith(('.csv', '.pdf', '.xlsx'))
    ]
    if not files:
        from samples.generate_sample_data import generate_samples
        generate_samples(samples_dir)
        files = [
            os.path.join(samples_dir, f) for f in os.listdir(samples_dir)
            if f.lower().endswith(('.csv', '.pdf', '.xlsx'))
        ]

    try:
        report, txs, md_text = pipeline.process_files(files)
        LATEST_REPORT["report"] = report
        LATEST_REPORT["transactions"] = txs
        LATEST_REPORT["markdown"] = md_text

        rep_dict = report.to_dict()
        budget_data = generate_budget(rep_dict, USER_SETTINGS, txs)

        return jsonify({
            "success": True,
            "report": rep_dict,
            "transactions": [t.to_dict() for t in txs],
            "markdown": md_text,
            "budget": budget_data
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/transaction/update', methods=['POST'])
def update_transaction():
    """Update single transaction category, transfer classification, exclusion, or note."""
    data = request.get_json() or {}
    tx_id = data.get('tx_id')
    new_category = data.get('category')
    is_transfer = data.get('is_internal_transfer')
    is_excluded = data.get('is_excluded')
    note = data.get('note')

    if not LATEST_REPORT["transactions"]:
        return jsonify({"success": False, "error": "No statement active"}), 400

    target_tx = None
    for tx in LATEST_REPORT["transactions"]:
        if tx.id == tx_id:
            target_tx = tx
            break

    if not target_tx:
        return jsonify({"success": False, "error": f"Transaction {tx_id} not found"}), 404

    if new_category is not None:
        target_tx.category = new_category
    if is_transfer is not None:
        target_tx.is_internal_transfer = bool(is_transfer)
    if is_excluded is not None:
        target_tx.is_excluded = bool(is_excluded)
    if note is not None:
        target_tx.notes = str(note)

    # Re-analyze with updated transactions
    updated_report = pipeline.analyst.analyze(
        LATEST_REPORT["transactions"],
        metadata_list=LATEST_REPORT.get("metadata")
    )
    LATEST_REPORT["report"] = updated_report
    LATEST_REPORT["markdown"] = pipeline.analyst.format_markdown_report(updated_report)

    rep_dict = updated_report.to_dict()
    budget_data = generate_budget(rep_dict, USER_SETTINGS, LATEST_REPORT["transactions"])

    return jsonify({
        "success": True,
        "report": rep_dict,
        "transactions": [t.to_dict() for t in LATEST_REPORT["transactions"]],
        "budget": budget_data
    })


@app.route('/api/transactions/batch-update', methods=['POST'])
def batch_update_transactions():
    """Batch re-classify transactions (e.g. mark multiple as transfer or exclude)."""
    data = request.get_json() or {}
    tx_ids = set(data.get('tx_ids', []))
    action = data.get('action')
    category = data.get('category')

    if not LATEST_REPORT["transactions"]:
        return jsonify({"success": False, "error": "No statement active"}), 400

    updated_count = 0
    for tx in LATEST_REPORT["transactions"]:
        if tx.id in tx_ids:
            if action == 'mark_transfer':
                tx.is_internal_transfer = True
            elif action == 'unmark_transfer':
                tx.is_internal_transfer = False
            elif action == 'exclude':
                tx.is_excluded = True
            elif action == 'unexclude':
                tx.is_excluded = False
            elif action == 'categorize' and category:
                tx.category = category
            updated_count += 1

    updated_report = pipeline.analyst.analyze(
        LATEST_REPORT["transactions"],
        metadata_list=LATEST_REPORT.get("metadata")
    )
    LATEST_REPORT["report"] = updated_report
    LATEST_REPORT["markdown"] = pipeline.analyst.format_markdown_report(updated_report)

    rep_dict = updated_report.to_dict()
    budget_data = generate_budget(rep_dict, USER_SETTINGS, LATEST_REPORT["transactions"])

    return jsonify({
        "success": True,
        "updated_count": updated_count,
        "report": rep_dict,
        "transactions": [t.to_dict() for t in LATEST_REPORT["transactions"]],
        "budget": budget_data
    })


@app.route('/api/filter-period', methods=['POST'])
def filter_period():
    """Filter dashboard by month (e.g. 2023-12) or return all."""
    data = request.get_json() or {}
    period_key = data.get('period', 'ALL')

    if not LATEST_REPORT["transactions"]:
        return jsonify({"success": False, "error": "No statements loaded"}), 400

    if period_key == 'ALL':
        selected_txs = LATEST_REPORT["transactions"]
    else:
        selected_txs = [t for t in LATEST_REPORT["transactions"] if t.date.startswith(period_key)]

    if not selected_txs:
        return jsonify({"success": False, "error": f"No transactions found for period {period_key}"}), 404

    period_report = pipeline.analyst.analyze(
        selected_txs,
        metadata_list=LATEST_REPORT.get("metadata")
    )
    rep_dict = period_report.to_dict()
    budget_data = generate_budget(rep_dict, USER_SETTINGS, selected_txs)

    return jsonify({
        "success": True,
        "report": rep_dict,
        "transactions": [t.to_dict() for t in selected_txs],
        "budget": budget_data
    })


@app.route('/api/budget-settings', methods=['GET', 'POST'])
def budget_settings():
    """Retrieve or update budget targets and pay schedule."""
    if request.method == 'POST':
        data = request.get_json() or {}
        if 'income_target' in data:
            try:
                USER_SETTINGS['income_target'] = float(data['income_target']) if data['income_target'] else None
            except (ValueError, TypeError):
                pass
        if 'pay_cadence' in data:
            USER_SETTINGS['pay_cadence'] = str(data['pay_cadence'])
        if 'savings_goal_percent' in data:
            try:
                USER_SETTINGS['savings_goal_percent'] = float(data['savings_goal_percent'])
            except (ValueError, TypeError):
                pass
        if 'category_budgets' in data and isinstance(data['category_budgets'], dict):
            for cat, limit in data['category_budgets'].items():
                try:
                    USER_SETTINGS['category_budgets'][cat] = float(limit)
                except (ValueError, TypeError):
                    pass

    # If we have an active report, return updated budget
    current_budget = None
    if LATEST_REPORT["report"]:
        current_budget = generate_budget(LATEST_REPORT["report"].to_dict(), USER_SETTINGS)

    return jsonify({
        "success": True,
        "settings": {
            "income_target": USER_SETTINGS['income_target'],
            "pay_cadence": USER_SETTINGS['pay_cadence'],
            "savings_goal_percent": USER_SETTINGS['savings_goal_percent'],
            "category_budgets": USER_SETTINGS['category_budgets'],
            "total_annual_saved": USER_SETTINGS['total_annual_saved']
        },
        "budget": current_budget
    })


@app.route('/api/concierge-cancel', methods=['POST'])
def concierge_cancel():
    """Cancel subscription via concierge simulation."""
    data = request.get_json() or {}
    merchant = data.get('merchant', '').strip()
    monthly_amount = float(data.get('monthly_amount', 0.0))
    annual_savings = round(monthly_amount * 12.0, 2)

    if not merchant:
        return jsonify({"success": False, "error": "Merchant name required"}), 400

    USER_SETTINGS["canceled_subscriptions"][merchant] = {
        "merchant": merchant,
        "monthly_amount": monthly_amount,
        "annual_savings": annual_savings,
        "status": "Cancellation Initiated"
    }

    # Recalculate total annual savings
    USER_SETTINGS["total_annual_saved"] = sum(
        item["annual_savings"] for item in USER_SETTINGS["canceled_subscriptions"].values()
    )

    current_budget = None
    if LATEST_REPORT["report"]:
        current_budget = generate_budget(LATEST_REPORT["report"].to_dict(), USER_SETTINGS)

    return jsonify({
        "success": True,
        "merchant": merchant,
        "annual_savings": annual_savings,
        "total_annual_saved": USER_SETTINGS["total_annual_saved"],
        "canceled_subscriptions": list(USER_SETTINGS["canceled_subscriptions"].values()),
        "budget": current_budget
    })


@app.route('/api/concierge-restore', methods=['POST'])
def concierge_restore():
    """Restore a previously cancelled subscription."""
    data = request.get_json() or {}
    merchant = data.get('merchant', '').strip()
    if merchant in USER_SETTINGS["canceled_subscriptions"]:
        del USER_SETTINGS["canceled_subscriptions"][merchant]

    USER_SETTINGS["total_annual_saved"] = sum(
        item["annual_savings"] for item in USER_SETTINGS["canceled_subscriptions"].values()
    )

    current_budget = None
    if LATEST_REPORT["report"]:
        current_budget = generate_budget(LATEST_REPORT["report"].to_dict(), USER_SETTINGS)

    return jsonify({
        "success": True,
        "total_annual_saved": USER_SETTINGS["total_annual_saved"],
        "canceled_subscriptions": list(USER_SETTINGS["canceled_subscriptions"].values()),
        "budget": current_budget
    })


@app.route('/api/export-markdown', methods=['GET'])
def export_markdown():
    if not LATEST_REPORT["markdown"]:
        return "No analysis report generated yet.", 400
    return Response(
        LATEST_REPORT["markdown"],
        mimetype="text/markdown",
        headers={"Content-Disposition": "attachment;filename=spending_analysis_report.md"}
    )


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5055))
    print(f"🚀 Starting Bank Statement Analyst Dashboard at http://localhost:{port}")
    app.run(host='0.0.0.0', port=port, debug=True)
