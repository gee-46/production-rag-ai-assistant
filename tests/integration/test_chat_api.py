import io

from app.core.config import get_settings
from app.db.session import SessionLocal
from app.services.embeddings.factory import get_embedding_provider
from app.services.ingestion.pipeline import run_ingestion


def _ingest(document_id):
    db = SessionLocal()
    try:
        run_ingestion(db, document_id=document_id, embedder=get_embedding_provider(), settings=get_settings())
    finally:
        db.close()


def test_chat_retrieves_from_ingested_document_and_persists_session(client, registered_user, workspace):
    upload = client.post(
        f"/workspaces/{workspace['id']}/documents",
        headers=registered_user["headers"],
        files={
            "file": (
                "kb.txt",
                io.BytesIO(b"Reciprocal Rank Fusion combines multiple ranked lists into one ranking."),
                "text/plain",
            )
        },
    )
    _ingest(upload.json()["document"]["id"])

    resp = client.post(
        f"/workspaces/{workspace['id']}/chat",
        headers=registered_user["headers"],
        json={"query": "What does Reciprocal Rank Fusion do?"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["retrieval_debug"]["vector_candidates"] >= 1
    assert "session_id" in body
    assert "groundedness" in body

    # Follow-up in the same session should reuse it, not create a new one.
    follow_up = client.post(
        f"/workspaces/{workspace['id']}/chat",
        headers=registered_user["headers"],
        json={"query": "Can you say more?", "session_id": body["session_id"]},
    )
    assert follow_up.json()["session_id"] == body["session_id"]


def test_chat_with_no_documents_returns_empty_retrieval(client, registered_user, workspace):
    resp = client.post(
        f"/workspaces/{workspace['id']}/chat",
        headers=registered_user["headers"],
        json={"query": "Anything at all?"},
    )
    assert resp.status_code == 200
    assert resp.json()["retrieval_debug"]["final_chunks"] == 0


def test_chat_requires_workspace_membership(client, registered_user, workspace):
    client.post("/auth/register", json={"email": "outsider2@example.com", "password": "password123"})
    outsider_token = client.post(
        "/auth/login", json={"email": "outsider2@example.com", "password": "password123"}
    ).json()["access_token"]
    resp = client.post(
        f"/workspaces/{workspace['id']}/chat",
        headers={"Authorization": f"Bearer {outsider_token}"},
        json={"query": "hello"},
    )
    assert resp.status_code == 403
