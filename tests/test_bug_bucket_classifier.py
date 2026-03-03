from bug_bucket_classifier import classify_bug_buckets


def test_infrastructure_detection_http_code():
    result = classify_bug_buckets("Customers see HTTP 503 and endpoints failing")
    assert result.primary == "Infrastructure"
    assert result.secondary is None


def test_infrastructure_detection_server_error_code_context():
    result = classify_bug_buckets("Backend error 502 when fetching call recording")
    assert result.primary == "Infrastructure"


def test_numeric_500_without_http_context_does_not_match_infrastructure():
    result = classify_bug_buckets("Customer says payment logged twice for $500")
    assert result.primary == "Post-call process"
    assert "Infrastructure" not in result.applicable


def test_stt_detection():
    result = classify_bug_buckets("Transcript does not match what was said and has missing sections")
    assert result.primary == "STT"


def test_tts_detection():
    result = classify_bug_buckets("The voice sounds unnatural and speech cuts off mid-sentence")
    assert result.primary == "TTS"


def test_llm_detection():
    result = classify_bug_buckets("The agent repeats the same question and ignores provided information")
    assert result.primary == "LLM"


def test_post_call_process_detection():
    result = classify_bug_buckets("Summary not generated and CRM not updated")
    assert result.primary == "Post-call process"


def test_primary_secondary_ordering_by_priority():
    result = classify_bug_buckets(
        "Agent repeats the same question and transcript does not match what was said"
    )
    assert result.primary == "LLM"
    assert result.secondary == "STT"


def test_infrastructure_overrides_others_when_multiple_present():
    result = classify_bug_buckets(
        "HTTP 500 error while the agent repeats the same question and call notes missing"
    )
    assert result.primary == "Infrastructure"
    assert result.secondary == "LLM"


def test_no_match():
    result = classify_bug_buckets("Customer is asking for a new feature")
    assert result.primary is None
    assert result.secondary is None
    assert result.applicable == ()
