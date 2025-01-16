"""
Flask web application for validating social media links and analyzing personality.
"""
from flask import Flask, request, jsonify, render_template
from analyze import validate_social_link, analyze_personality

app = Flask(__name__)

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
    data = request.json
    links = data.get("links", [])

    validation_results = []
    all_valid = True

    for link in links:
        is_valid, platform = validate_social_link(link)
        validation_results.append({
            "url": link,
            "is_valid": is_valid,
            "platform": platform
        })
        if not is_valid:
            all_valid = False

    return jsonify({
        "results": validation_results,
        "all_valid": all_valid
    })

@app.route("/analyze", methods=["POST"])
def analyze():
    """
    Receives JSON with:
      - 'links_info': list of { url, platform }
      - 'personal_description': string
    Calls the analyze_personality function and returns the analysis text.
    """
    data = request.json
    links_info = data.get("links_info", [])
    personal_description = data.get("personal_description", "")

    result = analyze_personality(links_info, personal_description)
    return jsonify({"analysis": result})

if __name__ == "__main__":
    # Run in debug mode for development
    app.run(debug=True)
