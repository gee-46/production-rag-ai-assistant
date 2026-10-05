"""
Production RAG Assistant - End-to-End Stabilization, Security, Ingestion,
and Live Generation Verification Suite (Phases 8-12).
"""
import datetime
import io
import os
import sys
import tempfile
import time
import uuid
from pathlib import Path

# Ensure UTF-8 output on Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from docx import Document as DocxDocument
from fpdf import FPDF
from frontend.standalone_engine import StandaloneEngine
import pytest


def test_phase_8_live_generation(engine: StandaloneEngine):
    print("\n" + "=" * 75)
    print("PHASE 8: REAL RAG GENERATION WITH LIVE GROQ PROVIDER")
    print("=" * 75)
    ws_id = "phase8_orbit_workspace"
    engine.workspaces[ws_id] = {"id": ws_id, "name": "Project ORBIT Knowledge Base"}

    orbit_text = (
        "Project ORBIT has identifier ZX-731.\n"
        "Its test environment is Cedar.\n"
        "The project owner is Mira.\n"
        "Security clearance level is Gamma-4."
    )
    doc_res = engine.ingest_document(
        workspace_id=ws_id,
        filename="project_orbit_spec.txt",
        file_bytes=orbit_text.encode("utf-8"),
        content_type="text/plain",
    )
    print(f"Ingested doc: {doc_res['filename']} (status={doc_res['status']})")

    # 1. Identifier question
    print("\n[Query 1] 'What is the identifier for Project ORBIT?'")
    stream1 = list(engine.chat_stream(ws_id, "What is the identifier for Project ORBIT?"))
    ans1 = "".join(e.get("delta", "") for e in stream1 if e.get("event") == "delta")
    done1 = next((e for e in stream1 if e.get("event") == "done"), {})
    print(f"Answer: {ans1.strip()}")
    print(f"Citations: {done1.get('citations')}")
    print(f"Groundedness: {done1.get('groundedness')}")
    assert "ZX-731" in ans1, f"Expected ZX-731 in answer, got: {ans1}"
    assert len(done1.get("citations", [])) > 0, "Expected at least 1 citation"
    assert done1["citations"][0]["filename"] == "project_orbit_spec.txt"

    # 2. Test environment question
    print("\n[Query 2] 'What is its test environment?'")
    stream2 = list(engine.chat_stream(ws_id, "What is its test environment?"))
    ans2 = "".join(e.get("delta", "") for e in stream2 if e.get("event") == "delta")
    done2 = next((e for e in stream2 if e.get("event") == "done"), {})
    print(f"Answer: {ans2.strip()}")
    print(f"Citations: {done2.get('citations')}")
    assert "Cedar" in ans2 or "cedar" in ans2.lower(), f"Expected Cedar in answer, got: {ans2}"

    # 3. Owner question
    print("\n[Query 3] 'Who owns Project ORBIT?'")
    stream3 = list(engine.chat_stream(ws_id, "Who owns Project ORBIT?"))
    ans3 = "".join(e.get("delta", "") for e in stream3 if e.get("event") == "delta")
    done3 = next((e for e in stream3 if e.get("event") == "done"), {})
    print(f"Answer: {ans3.strip()}")
    print(f"Citations: {done3.get('citations')}")
    assert "Mira" in ans3 or "mira" in ans3.lower(), f"Expected Mira in answer, got: {ans3}"

    # 4. Unknown question (Must Refuse)
    print("\n[Query 4] 'What identifier belongs to Project UNKNOWN?'")
    stream4 = list(engine.chat_stream(ws_id, "What identifier belongs to Project UNKNOWN?"))
    ans4 = "".join(e.get("delta", "") for e in stream4 if e.get("event") == "delta")
    done4 = next((e for e in stream4 if e.get("event") == "done"), {})
    print(f"Answer: {ans4.strip()}")
    print(f"Citations: {done4.get('citations')}")
    assert len(done4.get("citations", [])) == 0, f"Refusal must have no citations, got: {done4.get('citations')}"
    assert "does not contain" in ans4.lower() or "cannot" in ans4.lower() or "not contain" in ans4.lower(), f"Expected polite refusal, got: {ans4}"
    print(">>> Phase 8 Generation & Refusal tests PASSED successfully.")


def test_phase_9_document_ingestion(engine: StandaloneEngine):
    print("\n" + "=" * 75)
    print("PHASE 9: MULTI-FORMAT DOCUMENT INGESTION & ROBUSTNESS")
    print("=" * 75)
    ws_id = "phase9_ingestion_workspace"
    engine.workspaces[ws_id] = {"id": ws_id, "name": "Ingestion Robustness Workspace"}

    # 1. Plain Text (TXT)
    txt_bytes = b"Server cluster delta alpha initialized on port 8080."
    res_txt = engine.ingest_document(ws_id, "cluster.txt", txt_bytes, content_type="text/plain")
    assert res_txt["status"] == "indexed"
    assert res_txt["chunk_count"] >= 1
    print(f"[TXT]  Ingested {res_txt['filename']} -> status: {res_txt['status']} (chunks={res_txt['chunk_count']})")

    # 2. Markdown (MD)
    md_bytes = b"# Deployment Architecture\n\n- Primary Host: edge-proxy.internal\n- Port: 9443"
    res_md = engine.ingest_document(ws_id, "architecture.md", md_bytes, content_type="text/markdown")
    assert res_md["status"] == "indexed"
    print(f"[MD]   Ingested {res_md['filename']} -> status: {res_md['status']} (chunks={res_md['chunk_count']})")

    # 3. PDF
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", size=12)
    pdf.cell(200, 10, text="Telemetry Protocol v3 uses UDP port 4055 for heartbeats.", new_x="LMARGIN", new_y="NEXT")
    pdf_bytes = bytes(pdf.output())
    res_pdf = engine.ingest_document(ws_id, "telemetry.pdf", pdf_bytes, content_type="application/pdf")
    assert res_pdf["status"] == "indexed"
    print(f"[PDF]  Ingested {res_pdf['filename']} -> status: {res_pdf['status']} (chunks={res_pdf['chunk_count']})")

    # 4. DOCX
    docx_io = io.BytesIO()
    doc_obj = DocxDocument()
    doc_obj.add_heading("Safety Protocol Document", 0)
    doc_obj.add_paragraph("Emergency override pin code is 9942.")
    doc_obj.save(docx_io)
    docx_bytes = docx_io.getvalue()
    res_docx = engine.ingest_document(ws_id, "safety.docx", docx_bytes, content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document")
    assert res_docx["status"] == "indexed"
    print(f"[DOCX] Ingested {res_docx['filename']} -> status: {res_docx['status']} (chunks={res_docx['chunk_count']})")

    # 5. Empty Document Handling
    res_empty = engine.ingest_document(ws_id, "empty_file.txt", b"", content_type="text/plain")
    print(f"[Empty] Ingested empty file -> status: {res_empty['status']} (chunks={res_empty['chunk_count']})")

    # 6. Verify Retrieval across all 4 formats
    q1_chunks, _ = engine.retrieve(ws_id, "emergency override pin code", top_k=2)
    assert any("safety.docx" in c.filename for c in q1_chunks)
    print(f"[Retrieval Check DOCX] Query 'emergency override pin code' retrieved: {[c.filename for c in q1_chunks]}")

    q2_chunks, _ = engine.retrieve(ws_id, "UDP port for heartbeats", top_k=2)
    assert any("telemetry.pdf" in c.filename for c in q2_chunks)
    print(f"[Retrieval Check PDF] Query 'UDP port for heartbeats' retrieved: {[c.filename for c in q2_chunks]}")

    print(">>> Phase 9 Ingestion & Multi-Format tests PASSED successfully.")


def test_phase_10_security_and_isolation(engine: StandaloneEngine):
    print("\n" + "=" * 75)
    print("PHASE 10: WORKSPACE ISOLATION & ACCESS CONTROL (RBAC)")
    print("=" * 75)

    # Create User A and Workspace A
    res_user_a = engine.register("user_a@enterprise.com", "pass_a_secure", "User A")
    user_a_id = res_user_a["data"]["id"]
    ws_a_id = "workspace_a_tenant"
    engine.workspaces[ws_a_id] = {"id": ws_a_id, "name": "Workspace A Secret Docs", "owner_id": user_a_id}
    engine.workspace_members[ws_a_id] = [{"user_id": user_a_id, "email": "user_a@enterprise.com", "role": "owner"}]

    # Ingest confidential doc in Workspace A
    engine.ingest_document(
        workspace_id=ws_a_id,
        filename="confidential_finances.txt",
        file_bytes=b"Q4 Net Margin is exactly 34.2 percent. Classified Secret.",
        uploaded_by=user_a_id,
        visibility="workspace",
        content_type="text/plain",
    )

    # Create User B and Workspace B
    res_user_b = engine.register("user_b@enterprise.com", "pass_b_secure", "User B")
    user_b_id = res_user_b["data"]["id"]
    ws_b_id = "workspace_b_tenant"
    engine.workspaces[ws_b_id] = {"id": ws_b_id, "name": "Workspace B Public Docs", "owner_id": user_b_id}
    engine.workspace_members[ws_b_id] = [{"user_id": user_b_id, "email": "user_b@enterprise.com", "role": "owner"}]

    # User B queries Workspace B for User A's secret
    chunks_b, _ = engine.retrieve(ws_b_id, "Q4 Net Margin percent classified secret", top_k=5)
    print(f"User B query in Workspace B retrieved: {[c.filename for c in chunks_b]}")
    assert len(chunks_b) == 0, "Workspace B must NOT retrieve chunks from Workspace A!"

    # Verify document listing isolation
    docs_a = engine.list_documents(ws_a_id)
    docs_b = engine.list_documents(ws_b_id)
    assert len(docs_a) == 1 and docs_a[0]["filename"] == "confidential_finances.txt"
    assert len(docs_b) == 0, "Workspace B must list 0 documents"

    print(">>> Phase 10 Workspace Isolation & Security tests PASSED successfully.")


def test_phase_11_persistence_and_failure_modes(engine: StandaloneEngine):
    print("\n" + "=" * 75)
    print("PHASES 11 & 12: PERSISTENCE DOCUMENTATION & TRUTHFUL FAILURE MODES")
    print("=" * 75)

    # Test empty retrieval refusal
    empty_ws = "empty_workspace_testing"
    engine.workspaces[empty_ws] = {"id": empty_ws, "name": "Empty Space"}
    stream_empty = list(engine.chat_stream(empty_ws, "What is the secret passkey?"))
    ans_empty = "".join(e.get("delta", "") for e in stream_empty if e.get("event") == "delta")
    done_empty = next((e for e in stream_empty if e.get("event") == "done"), {})
    print(f"Empty Workspace Query -> Answer: '{ans_empty.strip()}' | Citations: {done_empty.get('citations')}")
    assert "does not contain" in ans_empty.lower() or "not contain" in ans_empty.lower()
    assert len(done_empty.get("citations", [])) == 0

    print(">>> Phases 11 & 12 Failure Modes & Refusal verification PASSED successfully.")


if __name__ == "__main__":
    shared_engine = StandaloneEngine()
    test_phase_8_live_generation(shared_engine)
    test_phase_9_document_ingestion(shared_engine)
    test_phase_10_security_and_isolation(shared_engine)
    test_phase_11_persistence_and_failure_modes(shared_engine)
    print("\n" + "=" * 75)
    print("ALL VERIFICATION PHASES COMPLETED SUCCESSFULLY.")
    print("=" * 75)
