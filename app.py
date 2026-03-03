from flask import Flask, request, jsonify, send_from_directory
from bug_bucket_classifier import classify_bug
from routing import determine_routing

app = Flask(__name__, static_folder=".")

@app.route("/")
def index():
    return send_from_directory(".", "index.html")

@app.route("/triage", methods=["POST"])
def triage():
    data = request.get_json()

    bug_text = data.get("bug_report", "")
    impact = data.get("impact", "Single caller")

    classification = classify_bug(bug_text)

    routing = determine_routing(
        primary_bucket=classification["primary_bucket"],
        severity=classification["severity"]
    )

    return jsonify({
        "primary_bucket": classification["primary_bucket"],
        "severity": classification["severity"],
        "routing_team": routing["routing_team"],
        "escalation_flag": routing["escalation_flag"],
        "routing_rationale": routing["routing_rationale"],
        "next_steps": routing["next_steps"]
    })

if __name__ == "__main__":
    app.run(debug=True, port=3000)
