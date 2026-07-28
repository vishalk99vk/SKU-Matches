import os
import uuid

from flask import Flask, render_template, request, send_file, jsonify, url_for

from matcher_pipeline import run_matching

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")
OUTPUT_DIR = os.path.join(BASE_DIR, "outputs")
TEMPLATE_FILE = os.path.join(BASE_DIR, "static", "Image_Matching_Template.xlsx")

os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 50 * 1024 * 1024  # 50 MB


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/download-template")
def download_template():
    return send_file(
        TEMPLATE_FILE,
        as_attachment=True,
        download_name="Image_Matching_Template.xlsx",
    )


@app.route("/upload", methods=["POST"])
def upload():
    if "file" not in request.files:
        return jsonify({"error": "No file uploaded"}), 400

    file = request.files["file"]
    if file.filename == "":
        return jsonify({"error": "No file selected"}), 400

    job_id = uuid.uuid4().hex[:12]
    input_path = os.path.join(UPLOAD_DIR, f"{job_id}_input.xlsx")
    output_path = os.path.join(OUTPUT_DIR, f"{job_id}_matched.xlsx")
    file.save(input_path)

    try:
        summary = run_matching(input_path, output_path)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

    return jsonify({
        "job_id": job_id,
        "summary": summary,
        "download_url": url_for("download_result", job_id=job_id),
    })


@app.route("/download-result/<job_id>")
def download_result(job_id):
    output_path = os.path.join(OUTPUT_DIR, f"{job_id}_matched.xlsx")
    if not os.path.exists(output_path):
        return jsonify({"error": "Result not found"}), 404
    return send_file(output_path, as_attachment=True, download_name="Matched_Results.xlsx")


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
