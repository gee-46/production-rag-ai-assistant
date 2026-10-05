"""
Unit and regression tests for multi-tenant workspace isolation,
session conversation segregation, and demo mode access controls.
"""
import uuid
import pytest
from unittest.mock import MagicMock
from fastapi import Request

from app.core.config import Settings
from app.core.errors import PermissionError_
from app.api.deps import get_current_user
from frontend.standalone_engine import StandaloneEngine


def test_cross_workspace_retrieval_isolation():
    """Verify that retrieval in Workspace A strictly never leaks chunks from Workspace B."""
    engine = StandaloneEngine()
    
    ws_a = str(uuid.uuid4())
    ws_b = str(uuid.uuid4())
    ws_empty = str(uuid.uuid4())
    
    engine.workspaces[ws_a] = {"id": ws_a, "name": "Workspace A"}
    engine.workspaces[ws_b] = {"id": ws_b, "name": "Workspace B"}
    engine.workspaces[ws_empty] = {"id": ws_empty, "name": "Empty Workspace"}
    
    doc_a_text = "Project APOLLO is a deep space exploration vehicle. Primary thruster is Ion-9."
    doc_b_text = "Project ZEPHYR is a high-altitude atmospheric balloon. Sensor payload is Baro-X."
    
    engine.ingest_document(workspace_id=ws_a, filename="apollo.txt", file_bytes=doc_a_text.encode("utf-8"))
    engine.ingest_document(workspace_id=ws_b, filename="zephyr.txt", file_bytes=doc_b_text.encode("utf-8"))
    
    # Query Workspace A
    chunks_a, debug_a = engine.retrieve(workspace_id=ws_a, query="What is the thruster for APOLLO?")
    assert len(chunks_a) > 0
    assert any("apollo" in c.filename.lower() for c in chunks_a)
    assert not any("zephyr" in c.filename.lower() for c in chunks_a)
    
    # Query Workspace B
    chunks_b, debug_b = engine.retrieve(workspace_id=ws_b, query="What is the sensor payload for ZEPHYR?")
    assert len(chunks_b) > 0
    assert any("zephyr" in c.filename.lower() for c in chunks_b)
    assert not any("apollo" in c.filename.lower() for c in chunks_b)
    
    # Query Empty Workspace C - must NEVER fall back to A or B
    chunks_c, debug_c = engine.retrieve(workspace_id=ws_empty, query="What is the thruster for APOLLO?")
    assert len(chunks_c) == 0
    assert debug_c["final_chunks"] == 0


def test_cross_session_conversation_isolation():
    """Verify chat histories in different session IDs do not pollute each other."""
    engine = StandaloneEngine()
    ws_id = str(uuid.uuid4())
    
    session_1 = "sess-user-alpha-123"
    session_2 = "sess-user-beta-456"
    
    # Stream in session 1
    for _ in engine.chat_stream(workspace_id=ws_id, query="Hello from Alpha", session_id=session_1):
        pass
        
    # Stream in session 2
    for _ in engine.chat_stream(workspace_id=ws_id, query="Hello from Beta", session_id=session_2):
        pass
        
    history_1 = engine.get_conversation_history(session_1)
    history_2 = engine.get_conversation_history(session_2)
    
    assert any(m["content"] == "Hello from Alpha" for m in history_1)
    assert not any(m["content"] == "Hello from Alpha" for m in history_2)
    assert any(m["content"] == "Hello from Beta" for m in history_2)
    assert not any(m["content"] == "Hello from Beta" for m in history_1)


def test_demo_local_only_access_control():
    """Verify unauthenticated demo mode restricts non-localhost origins when demo_local_only is True."""
    settings = Settings(auth_enabled=False, demo_local_only=True)
    db = MagicMock()
    db.get.return_value = None
    db.query.return_value.filter.return_value.first.return_value = None
    
    # Localhost client request
    req_local = MagicMock(spec=Request)
    req_local.client.host = "127.0.0.1"
    
    user_local = get_current_user(request=req_local, authorization=None, db=db, settings=settings)
    assert user_local.email == "demo@company.com"
    
    # Remote / non-localhost client request
    req_remote = MagicMock(spec=Request)
    req_remote.client.host = "203.0.113.195"
    
    with pytest.raises(PermissionError_) as exc_info:
        get_current_user(request=req_remote, authorization=None, db=db, settings=settings)
    assert "restricted to localhost" in str(exc_info.value)

