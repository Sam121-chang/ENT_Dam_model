from __future__ import annotations

from flask import Flask, jsonify, render_template, request, send_from_directory

from config import Config
from services.analyze_service import AnalysisError, analyze_upload


app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = Config.MAX_CONTENT_LENGTH

CONFIG_ERRORS = Config.validate()


@app.get("/")
def index():
    return render_template("index.html", config_errors=CONFIG_ERRORS)


@app.get("/health")
def health():
    status = "ok" if not CONFIG_ERRORS else "degraded"
    return jsonify({"status": status, "errors": CONFIG_ERRORS})


@app.get("/temp/<path:filename>")
def temp_file(filename: str):
    return send_from_directory(Config.TEMP_DIR, filename)


@app.post("/analyze")
def analyze():
    if CONFIG_ERRORS:
        return (
            jsonify(
                {
                    "error": "Configuration error.",
                    "details": CONFIG_ERRORS,
                }
            ),
            500,
        )

    file = request.files.get("image")
    try:
        result = analyze_upload(file)
        return jsonify(result)
    except AnalysisError as exc:
        return jsonify({"error": str(exc)}), 400
    except Exception:
        return jsonify({"error": "Unexpected server error during image analysis."}), 500


if __name__ == "__main__":
    app.run(debug=False, host="127.0.0.1", port=5001)
