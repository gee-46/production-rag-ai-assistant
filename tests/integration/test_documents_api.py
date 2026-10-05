import io

from app.core.config import get_settings
from app.db.session import SessionLocal
from app.services.embeddings.factory import get_embedding_provider
from app.services.ingestion.pipeline import run_ingestion


def _run_ingestion_sync(document_id):
    """Run the ingestion pipeline inline instead of via the async worker, so
    integration tests don't need a separate worker process running."""
    db = SessionLocal()
    try:
        run_ingestion(db, document_id=document_id, embedder=get_embedding_provider(), settings=get_settings())
    finally:
        db.close()


def test_upload_rejects_disallowed_extension(client, registered_user, workspace):
    resp = client.post(
        f"/workspaces/{workspace['id']}/documents",
        headers=registered_user["headers"],
        files={"file": ("virus.exe", io.BytesIO(b"data"), "application/octet-stream")},
    )
    assert resp.status_code == 422


def test_upload_and_background_ingestion_makes_document_ready(client, registered_user, workspace):
    resp = client.post(
        f"/workspaces/{workspace['id']}/documents",
        headers=registered_user["headers"],
        files={"file": ("notes.txt", io.BytesIO(b"RAG combines retrieval with generation for grounded answers."), "text/plain")},
    )
    assert resp.status_code == 202
    document_id = resp.json()["document"]["id"]
    assert resp.json()["document"]["status"] == "pending"

    _run_ingestion_sync(document_id)

    resp = client.get(f"/workspaces/{workspace['id']}/documents/{document_id}", headers=registered_user["headers"])
    assert resp.json()["status"] == "ready"
    assert resp.json()["chunk_count"] >= 1


def test_duplicate_upload_is_deduped(client, registered_user, workspace):
    content = b"Identical content for dedup test."
    first = client.post(
        f"/workspaces/{workspace['id']}/documents",
        headers=registered_user["headers"],
        files={"file": ("a.txt", io.BytesIO(content), "text/plain")},
    )
    second = client.post(
        f"/workspaces/{workspace['id']}/documents",
        headers=registered_user["headers"],
        files={"file": ("b.txt", io.BytesIO(content), "text/plain")},
    )
    assert first.json()["document"]["id"] == second.json()["document"]["id"]
    assert "already exists" in second.json()["message"]


def test_private_document_is_hidden_from_other_members(client, registered_user, workspace):
    # Invite a second member.
    client.post("/auth/register", json={"email": "member2@example.com", "password": "password123"})
    member2_token = client.post(
        "/auth/login", json={"email": "member2@example.com", "password": "password123"}
    ).json()["access_token"]
    client.post(
        f"/workspaces/{workspace['id']}/members",
        json={"email": "member2@example.com", "role": "member"},
        headers=registered_user["headers"],
    )

    upload = client.post(
        f"/workspaces/{workspace['id']}/documents",
        headers=registered_user["headers"],
        params={"visibility": "private"},
        files={"file": ("secret.txt", io.BytesIO(b"private content"), "text/plain")},
    )
    document_id = upload.json()["document"]["id"]

    # Owner can see it.
    resp = client.get(f"/workspaces/{workspace['id']}/documents/{document_id}", headers=registered_user["headers"])
    assert resp.status_code == 200

    # Fellow member (non-admin) cannot.
    resp = client.get(
        f"/workspaces/{workspace['id']}/documents/{document_id}",
        headers={"Authorization": f"Bearer {member2_token}"},
    )
    assert resp.status_code == 403

    # And it's excluded from their document listing entirely.
    resp = client.get(
        f"/workspaces/{workspace['id']}/documents", headers={"Authorization": f"Bearer {member2_token}"}
    )
    assert all(d["id"] != document_id for d in resp.json())
