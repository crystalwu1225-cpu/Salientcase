from routing import determine_routing


def test_team_mapping_stt_and_questions_range():
    out = determine_routing(primary_bucket="STT", severity="Sev3")
    assert out["routing_team"] == "Voice AI"
    assert out["escalation_flag"] is False
    assert out["routing_rationale"] == "Routed to Voice AI due to speech recognition mismatch."
    assert 2 <= len(out["next_steps"]) <= 5


def test_escalation_by_severity_includes_exec_visibility():
    out = determine_routing(primary_bucket="LLM", severity="Sev1")
    assert out["routing_team"] == "Conversation AI"
    assert out["escalation_flag"] is True
    assert "Exec visibility recommended" in out["next_steps"]
    assert 2 <= len(out["next_steps"]) <= 5


def test_escalation_by_compliance_risk():
    out = determine_routing(
        primary_bucket="Infrastructure",
        severity="Sev3",
        compliance_risk=True,
    )
    assert out["routing_team"] == "Platform / Infra"
    assert out["escalation_flag"] is True


def test_payment_flow_blocked():
    out = determine_routing(
        primary_bucket="Post-call",
        severity="Sev3",
        payment_flow_blocked=True,
    )
    assert out["routing_team"] == "Integrations / Data"
    assert out["escalation_flag"] is True


def test_special_case_llm_threatens_customer_escalates():
    out = determine_routing(
        primary_bucket="LLM",
        severity="Sev3",
        llm_threatens_customer=True,
    )
    assert out["routing_team"] == "Conversation AI"
    assert out["escalation_flag"] is True


def test_special_case_infrastructure_outage_escalates():
    out = determine_routing(
        primary_bucket="Infrastructure",
        severity="Sev3",
        infrastructure_outage=True,
    )
    assert out["routing_team"] == "Platform / Infra"
    assert out["escalation_flag"] is True


def test_special_case_stt_incorrect_escalation_stays_voice_ai():
    out = determine_routing(
        primary_bucket="STT",
        severity="Sev3",
        stt_incorrect_escalation=True,
    )
    assert out["routing_team"] == "Voice AI"
