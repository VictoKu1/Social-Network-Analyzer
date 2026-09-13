"""
Flask web application for validating social media links and analyzing personality.
"""

from flask import Flask, request, jsonify, render_template
from werkzeug.exceptions import HTTPException
from analyze import validate_social_link, analyze_personality
from llm_providers import LLMError, get_llm_settings, get_ollama_models
from security_limits import MAX_REQUEST_BYTES, SecurityError, validate_links_list
from request_security import WorkAdmission, authorize_request

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = MAX_REQUEST_BYTES
work_admission = WorkAdmission()


@app.before_request
def check_access():
    """Apply the same access boundary to pages, assets and API routes."""
    authorize_request(request)


@app.after_request
def security_headers(response):
    """Keep generated output inert and sensitive responses out of caches."""
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; script-src 'self'; style-src 'self' https://fonts.googleapis.com; "
        "font-src 'self' https://fonts.gstatic.com; img-src 'self'; object-src 'none'; "
        "base-uri 'none'; frame-ancestors 'none'; form-action 'self'"
    )
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Cache-Control"] = "no-store"
    return response


@app.errorhandler(SecurityError)
def handle_security_error(error):
    """Expose fixed messages and actionable authentication/quota status."""
    response = jsonify({"error": {"code": error.code, "message": error.message}})
    response.status_code = error.status
    if error.status == 401:
        response.headers["WWW-Authenticate"] = 'Basic realm="Social Network Analyzer", charset="UTF-8"'
    if error.status == 429:
        response.headers["Retry-After"] = "60"
    return response


@app.errorhandler(HTTPException)
def handle_http_error(error):
    """Return safe JSON for malformed or oversized HTTP requests."""
    message = "The request is too large." if error.code == 413 else "The request could not be accepted."
    return jsonify({"error": {"code": "invalid_request", "message": message}}), error.code


@app.errorhandler(LLMError)
def handle_llm_error(error):
    """Return safe, actionable provider errors with a non-success status."""
    return jsonify({"error": {"code": error.code, "message": error.message}}), error.status


@app.route("/api/llm-config")
def llm_config():
    """Expose readiness and model names, never API keys."""
    response = jsonify(get_llm_settings())
    response.headers["Cache-Control"] = "no-store"
    return response


@app.route("/api/ollama/models")
def ollama_models():
    """Discover installed models on the server's configured Ollama service."""
    with work_admission.acquire():
        response = jsonify(get_ollama_models())
    response.headers["Cache-Control"] = "no-store"
    return response


@app.route("/")
def index():
    """
    Serve the main HTML page.
    """
    return render_template("index.html")


@app.route("/validate_links", methods=["POST"])
def validate_links():
    """
    Receives JSON with a list of links, validates each link,
    and returns JSON with results + 'all_valid' status.
    """
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({"error": {"code": "invalid_request", "message": "Send a JSON object."}}), 400
    links = validate_links_list(data.get("links", []))

    validation_results = []
    all_valid = True

    for link in links:
        is_valid, platform = validate_social_link(link)
        validation_results.append(
            {"url": link, "is_valid": is_valid, "platform": platform}
        )
        if not is_valid:
            all_valid = False

    return jsonify({"results": validation_results, "all_valid": all_valid})


@app.route("/analyze", methods=["POST"])
def analyze():
    """
    Receives JSON with:
      - 'links_info': list of { url, platform }
      - 'personal_description': string
    Calls the analyze_personality function and returns the analysis text.
    """
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({"error": {"code": "invalid_request", "message": "Send a JSON object."}}), 400
    links_info = data.get("links_info", [])
    personal_description = data.get("personal_description", "")

    with work_admission.acquire():
        result = analyze_personality(
            links_info, personal_description, provider=data.get("provider"), model=data.get("model")
        )
    return jsonify({"analysis": result})


if __name__ == "__main__":
    app.run(host="127.0.0.1", debug=False)
