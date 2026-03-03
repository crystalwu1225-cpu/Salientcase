from flask import Flask, jsonify, render_template_string, request, send_from_directory

from bug_bucket_classifier import classify_bug
from routing import determine_routing

app = Flask(__name__, static_folder=".")

TEMPLATE = """
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Voice Agent Bug Intake Form</title>
  <style>
    body { font-family: Arial, sans-serif; max-width: 720px; margin: 2rem auto; padding: 0 1rem; }
    label { display: block; font-weight: 600; margin-top: 0.75rem; }
    input, textarea, select { width: 100%; padding: 0.5rem; margin-top: 0.25rem; box-sizing: border-box; }
    button { margin-top: 1rem; padding: 0.6rem 1rem; }
    .box { border: 1px solid #ddd; padding: 1rem; margin-top: 1rem; border-radius: 8px; }
  </style>
</head>
<body>
  <h1>Voice Agent Bug Intake Form</h1>

  <form method="post" action="/">
    <label for="bug_report">1. Bug Report *</label>
    <textarea id="bug_report" name="bug_report" required>{{ form_data.bug_report }}</textarea>

    <label for="customer">2. Customer *</label>
    <input id="customer" name="customer" type="text" required value="{{ form_data.customer }}" />

    <label for="caller_id">3. Caller ID</label>
    <input id="caller_id" name="caller_id" type="text" value="{{ form_data.caller_id }}" />

    <label for="start_datetime">4. Start date / time</label>
    <input id="start_datetime" name="start_datetime" type="datetime-local" value="{{ form_data.start_datetime }}" />

    <label for="impact_scope">5. Impact / Scope *</label>
    <select id="impact_scope" name="impact_scope" required>
      <option value="" {% if not form_data.impact_scope %}selected{% endif %} disabled>Select impact</option>
      <option value="single" {% if form_data.impact_scope == 'single' %}selected{% endif %}>single</option>
      <option value="many" {% if form_data.impact_scope == 'many' %}selected{% endif %}>many</option>
      <option value="outage" {% if form_data.impact_scope == 'outage' %}selected{% endif %}>outage</option>
    </select>

    <label for="reported_by">6. Reported by - email or slack *</label>
    <input id="reported_by" name="reported_by" type="text" required value="{{ form_data.reported_by }}" />

    <button type="submit">Submit Intake</button>
  </form>

  {% if triage_result %}
  <div class="box">
    <strong>Automatic Triage Result</strong>
    <ul>
      <li>Primary bucket: {{ triage_result.primary_bucket }}</li>
      <li>Severity: {{ triage_result.severity }}</li>
      <li>Routing team: {{ triage_result.routing_team }}</li>
      <li>Escalation flag: {{ triage_result.escalation_flag }}</li>
      <li>Routing rationale: {{ triage_result.routing_rationale }}</li>
      <li>Next steps: {{ triage_result.next_steps }}</li>
    </ul>
  </div>
  {% endif %}
</body>
</html>
"""


FIELDS = (
    "bug_report",
    "customer",
    "caller_id",
    "start_datetime",
    "impact_scope",
    "reported_by",
)


def triage_from_bug_report(bug_report):
    result = classify_bug(bug_report)
    routing = determine_routing(
        primary_bucket=result["primary_bucket"],
        severity=result["severity"],
    )
    return {
        "primary_bucket": result["primary_bucket"],
        "severity": result["severity"],
        "routing_team": routing["routing_team"],
        "escalation_flag": routing["escalation_flag"],
        "routing_rationale": routing["routing_rationale"],
        "next_steps": routing["next_steps"],
    }


@app.route("/", methods=["GET", "POST"])
def index():
    form_data = {name: request.form.get(name, "") for name in FIELDS}
    triage_result = (
        triage_from_bug_report(form_data["bug_report"]) if request.method == "POST" else None
    )
    return render_template_string(TEMPLATE, form_data=form_data, triage_result=triage_result)


@app.route("/legacy")
def legacy_index():
    return send_from_directory(".", "index.html")


@app.route("/triage", methods=["POST"])
def triage():
    data = request.get_json() or {}
    return jsonify(triage_from_bug_report(data.get("bug_report", "")))


if __name__ == "__main__":
    app.run(debug=True, port=3000)
