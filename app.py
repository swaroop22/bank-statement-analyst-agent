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

# Cache latest report
LATEST_REPORT = {
    "report": None,
    "transactions": [],
    "markdown": ""
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

        return jsonify({
            "success": True,
            "report": report.to_dict(),
            "transactions": [t.to_dict() for t in txs],
            "markdown": md_text
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

        return jsonify({
            "success": True,
            "report": report.to_dict(),
            "transactions": [t.to_dict() for t in txs],
            "markdown": md_text
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

        return jsonify({
            "success": True,
            "report": report.to_dict(),
            "transactions": [t.to_dict() for t in txs],
            "markdown": md_text
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
        # Re-generate if missing
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

        return jsonify({
            "success": True,
            "report": report.to_dict(),
            "transactions": [t.to_dict() for t in txs],
            "markdown": md_text
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


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
