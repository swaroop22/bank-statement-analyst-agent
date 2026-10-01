"""
Flask Web Application for Bank Statement Spending Analyst Agent.
Provides an interactive dashboard for Google Drive analysis, file drag-and-drop,
live charts, subscription breakdown, and markdown exports.
"""

import os
import tempfile
import json
from flask import Flask, render_template, request, jsonify, Response, send_file
from werkzeug.utils import secure_filename

from core.pipeline import SpendingAnalysisPipeline
from core.models import AnalysisReport

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = os.path.join(tempfile.gettempdir(), 'bank_agent_uploads')
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50 MB
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

pipeline = SpendingAnalysisPipeline()

# Budget & Concierge State
USER_SETTINGS = {
    "income_target": None,
    "pay_cadence": "Monthly",
    "savings_goal_percent": 20.0,
    "category_budgets": {},
    "canceled_subscriptions": {},  # merchant -> {monthly_amount, annual_savings, canceled_at}
    "total_annual_saved": 0.0
}

# Cache latest report
LATEST_REPORT = {
    "report": None,
    "transactions": [],
    "markdown": ""
}


def generate_budget(report_dict, user_settings=None):
    """
    Computes safe-to-spend allowance, category budget targets,
    pacing status, and recommended category spending caps.
    """
    settings = user_settings or USER_SETTINGS
    inflow = float(report_dict.get("total_inflow", 0.0))
    income = float(settings.get("income_target") or inflow)
    total_outflow = float(report_dict.get("total_outflow", 0.0))
    recurring_monthly = float(report_dict.get("total_recurring_monthly", 0.0))
    currency = report_dict.get("currency", "USD")
    sym = report_dict.get("currency_symbol", "$" if currency != "INR" else "₹")

    custom_budgets = settings.get("category_budgets", {})
    categories = report_dict.get("category_breakdowns", [])

    category_budgets = []
    total_budgeted = 0.0
    total_variable_spent = 0.0

    for cat in categories:
        c_name = cat["category"]
        c_spent = float(cat["total_spent"])

        # Determine budget limit
        if c_name in custom_budgets and custom_budgets[c_name] is not None:
            limit = float(custom_budgets[c_name])
        else:
            # Category budget recommendation
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

    # Safe-to-Spend Allowance:
    # Safe to Spend = Monthly Inflow - Fixed Recurring Bills - Variable Outflow to date
    if income > 0:
        safe_to_spend = max(0.0, income - recurring_monthly - total_variable_spent)
        allowance_total = max(0.0, income - recurring_monthly)
    else:
        allowance_total = total_budgeted
        safe_to_spend = max(0.0, total_budgeted - total_outflow)

    days_in_month = 30
    days_left = 18  # Typical projection window
    daily_safe_allowance = (safe_to_spend / days_left) if days_left > 0 else 0.0

    return {
        "income_baseline": round(income, 2),
        "fixed_bills_monthly": round(recurring_monthly, 2),
        "variable_spent": round(total_variable_spent, 2),
        "total_spent": round(total_outflow, 2),
        "total_budgeted": round(total_budgeted, 2),
        "safe_to_spend": round(safe_to_spend, 2),
        "allowance_total": round(allowance_total, 2),
        "safe_to_spend_percent": round((safe_to_spend / allowance_total * 100.0) if allowance_total > 0 else 0.0, 1),
        "daily_safe_allowance": round(daily_safe_allowance, 2),
        "days_left": days_left,
        "category_budgets": category_budgets,
        "pay_cadence": settings.get("pay_cadence", "Monthly"),
        "savings_rate_projected": round(((income - total_outflow) / income * 100.0) if income > 0 else 0.0, 1),
        "canceled_subscriptions": list(settings.get("canceled_subscriptions", {}).values()),
        "total_annual_saved": round(settings.get("total_annual_saved", 0.0), 2)
    }




@app.route('/')
def index():
    return render_template('index.html')


@app.route('/api/analyze-drive', methods=['POST'])
def analyze_drive():
    data = request.get_json() or {}
    url = data.get('url', '').strip()
    password = data.get('password', '').strip() or None
    if not url:
        return jsonify({"success": False, "error": "Google Drive URL is required."}), 400

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

        LATEST_REPORT["report"] = report
        LATEST_REPORT["transactions"] = txs
        LATEST_REPORT["markdown"] = md_text

        rep_dict = report.to_dict()
        budget_data = generate_budget(rep_dict, USER_SETTINGS)

        return jsonify({
            "success": True,
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
    if 'files' not in request.files:
        return jsonify({"success": False, "error": "No statement files uploaded."}), 400

    password = request.form.get('password', '').strip() or None
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
        LATEST_REPORT["report"] = report
        LATEST_REPORT["transactions"] = txs
        LATEST_REPORT["markdown"] = md_text

        rep_dict = report.to_dict()
        budget_data = generate_budget(rep_dict, USER_SETTINGS)

        return jsonify({
            "success": True,
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
    """Analyze the already downloaded SBI statements from Google Drive folder directly."""
    data = request.get_json() or {}
    password = data.get('password', '').strip() or None

    drive_dir = os.path.join(os.path.dirname(__file__), "downloads", "drive_folder_1RncmKINKSQozomIa_yy6jl4anWqMccVP")
    if not os.path.exists(drive_dir):
        # Check any folder inside downloads
        downloads_base = os.path.join(os.path.dirname(__file__), "downloads")
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
        LATEST_REPORT["report"] = report
        LATEST_REPORT["transactions"] = txs
        LATEST_REPORT["markdown"] = md_text

        rep_dict = report.to_dict()
        budget_data = generate_budget(rep_dict, USER_SETTINGS)

        return jsonify({
            "success": True,
            "report": rep_dict,
            "transactions": [t.to_dict() for t in txs],
            "markdown": md_text,
            "budget": budget_data
        })
    except Exception as e:
        err_msg = str(e)
        is_enc = any(k in err_msg.lower() for k in ["password", "encrypted", "decrypt"])
        return jsonify({"success": False, "error": err_msg, "is_encrypted": is_enc}), 200 if is_enc else 500



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
        budget_data = generate_budget(rep_dict, USER_SETTINGS)

        return jsonify({
            "success": True,
            "report": rep_dict,
            "transactions": [t.to_dict() for t in txs],
            "markdown": md_text,
            "budget": budget_data
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


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
