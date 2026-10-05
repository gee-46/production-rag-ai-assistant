"""
Unit tests for the Python Frontend API client, helpers, and metric parsers.
"""
from frontend.api_client import APIClient
from frontend.components.metrics_view import parse_prometheus_metrics
from frontend.styles import render_citation_card, render_groundedness_badge


def test_api_client_token_headers():
    client = APIClient(base_url="http://localhost:8000")
    assert client._headers() == {}

    client.set_token("test_jwt_token_123")
    headers = client._headers({"Content-Type": "application/json"})
    assert headers["Authorization"] == "Bearer test_jwt_token_123"
    assert headers["Content-Type"] == "application/json"


def test_parse_prometheus_metrics():
    raw_prom = """
# HELP http_requests_total Total HTTP requests
# TYPE http_requests_total counter
http_requests_total{method="POST",path="/auth/login",status_code="200"} 12.0
http_requests_total{method="GET",path="/health",status_code="200"} 45.0
rag_retrieval_duration_seconds_count 8.0
"""
    parsed = parse_prometheus_metrics(raw_prom)
    assert "http_requests_total" in parsed
    assert len(parsed["http_requests_total"]) == 2
    assert parsed["http_requests_total"][0]["labels"]["method"] == "POST"
    assert parsed["http_requests_total"][0]["value"] == 12.0
    assert parsed["http_requests_total"][1]["labels"]["path"] == "/health"
    assert parsed["rag_retrieval_duration_seconds_count"][0]["value"] == 8.0


def test_render_groundedness_badge_supported():
    grounded_data = {"supported": True, "method": "token_overlap", "unsupported_sentences": []}
    html = render_groundedness_badge(grounded_data)
    assert "100% Citation Grounded" in html
    assert "grounded-supported" in html


def test_render_groundedness_badge_unsupported():
    grounded_data = {"supported": False, "method": "token_overlap", "unsupported_sentences": ["Fake claim."]}
    html = render_groundedness_badge(grounded_data)
    assert "Potential Hallucination Detected" in html
    assert "Fake claim." in html


def test_render_header():
    from frontend.styles import render_header
    html = render_header(app_name="Production RAG Assistant", workspace_name="Test KB", mode_label="Local Engine")
    assert "Production RAG Assistant" in html
    assert "Test KB" in html
    assert "Local Engine" in html


def test_standalone_engine_flow():
    from frontend.standalone_engine import StandaloneEngine
    engine = StandaloneEngine.get_instance()
    workspaces = engine.list_workspaces()
    assert len(workspaces) >= 1
    ws_id = workspaces[0]["id"]

    # Ingest document into the workspace
    engine.ingest_document(
        workspace_id=ws_id,
        filename="test_guide.txt",
        file_bytes=b"This system uses a hybrid retrieval strategy combining dense vector embeddings and BM25 lexical keyword search with reciprocal rank fusion.",
        uploaded_by="test@domain.com",
    )

    # Hybrid retrieval over ingested document
    chunks, debug = engine.retrieve(ws_id, "What retrieval strategy does this system use?", top_k=3)
    assert len(chunks) >= 1
    assert "dense_candidates" in debug or "vector_candidates" in debug
    assert "keyword_candidates" in debug

    # Stream query
    events = list(engine.chat_stream(ws_id, "What retrieval strategy does this system use?"))
    assert any(e.get("event") == "delta" for e in events)
    done_evt = next(e for e in events if e.get("event") == "done")
    assert "citations" in done_evt
    assert "groundedness" in done_evt

