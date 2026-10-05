"""
Unified Document Ingestion + Interactive RAG Chat Workspace.
Provides a clean, general-purpose RAG experience:
Upload documents (.pdf, .docx, .md, .txt), track indexing status,
and query your knowledge base with citation-grounded answers.
"""
from __future__ import annotations

import os
from pathlib import Path
import streamlit as st
from frontend.api_client import APIClient
from frontend.styles import render_citation_card, render_groundedness_badge


def format_bytes(size_bytes: int) -> str:
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    return f"{size_bytes / (1024 * 1024):.2f} MB"


def _safe_metric(val: any, default: str = "—") -> int | float | str:
    if val is None:
        return default
    if isinstance(val, (int, float, str)):
        return val
    if isinstance(val, (list, tuple, set, dict)):
        return len(val)
    return str(val)


def render_unified_workspace(
    client: APIClient,
    active_workspace: dict | None = None,
    workspace_id: str | None = None,
):
    if active_workspace is None:
        active_workspace = {"id": workspace_id or "default", "name": "Knowledge Base"}
    elif isinstance(active_workspace, str):
        active_workspace = {"id": active_workspace, "name": "Knowledge Base"}

    ws_id = str(active_workspace.get("id") or workspace_id or "default")
    workspace_name = active_workspace.get("name", "Knowledge Base")

    # Fetch document list for status & counts
    docs = client.list_documents(workspace_id=ws_id)
    total_docs = len(docs)
    indexed_docs = sum(1 for d in docs if d.get("status") == "indexed")
    processing_docs = sum(1 for d in docs if d.get("status") in ("pending", "processing", "queued"))
    total_chunks = sum(d.get("chunk_count", 0) for d in docs)
    has_indexed_docs = indexed_docs > 0

    # -------------------------------------------------------------
    # 1. DOCUMENT SECTION
    # -------------------------------------------------------------
    st.markdown("### 📄 Documents")
    
    with st.container():
        col_upload, col_summary = st.columns([3, 1])

        with col_upload:
            uploaded_files = st.file_uploader(
                "Upload documents (.pdf, .docx, .md, .txt)",
                accept_multiple_files=True,
                type=["pdf", "docx", "md", "txt"],
                key="unified_file_uploader",
                help="Uploaded documents are parsed, chunked, and indexed for semantic search.",
                label_visibility="collapsed",
            )

            if uploaded_files:
                if st.button("🚀 Upload & Index Documents", type="primary", use_container_width=True):
                    for uf in uploaded_files:
                        with st.spinner(f"Indexing {uf.name}..."):
                            file_bytes = uf.getvalue()
                            content_type = uf.type or "application/octet-stream"
                            res = client.ingest_document(
                                workspace_id=ws_id,
                                filename=uf.name,
                                file_bytes=file_bytes,
                                content_type=content_type,
                                visibility="workspace",
                            )
                            if res.get("success"):
                                st.success(f"✓ Indexed **{uf.name}** ({res.get('chunk_count', 0)} chunks)")
                            else:
                                st.error(f"Failed to index {uf.name}: {res.get('error')}")
                    st.rerun()

        with col_summary:
            st.markdown(
                f"""
                <div class="kpi-card" style="padding: 0.6rem 0.8rem;">
                    <div class="kpi-label">Indexed Documents</div>
                    <div class="kpi-value" style="font-size: 1.15rem;">{indexed_docs} / {total_docs} Ready</div>
                    <div style="font-size: 0.74rem; color: #94A3B8; margin-top: 0.2rem;">
                        <b>{total_chunks}</b> chunks indexed
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    # Document List
    if docs:
        st.markdown("<div style='margin-top: 0.5rem;'>", unsafe_allow_html=True)
        for doc in docs:
            doc_id = str(doc.get("id"))
            filename = doc.get("filename", "Untitled")
            status = doc.get("status", "unknown")
            size_str = format_bytes(doc.get("size_bytes", 0))
            chunks = doc.get("chunk_count", 0)
            file_type = Path(filename).suffix.upper().replace(".", "") or "TXT"
            error_msg = doc.get("error_message")

            if status == "indexed":
                status_badge = f'<span class="badge badge-green">✓ Indexed</span>'
            elif status == "failed":
                status_badge = '<span class="badge badge-red">✕ Failed</span>'
            else:
                status_badge = '<span class="badge badge-amber">⟳ Processing</span>'

            with st.container():
                c1, c2, c3, c4, c5 = st.columns([3.5, 1.2, 1.8, 1.5, 1.0])
                with c1:
                    st.markdown(f"**📄 {filename}**")
                    st.caption(f"Size: {size_str}")
                with c2:
                    st.markdown(f"<span class='badge badge-blue'>{file_type}</span>", unsafe_allow_html=True)
                with c3:
                    st.markdown(status_badge, unsafe_allow_html=True)
                    if status == "failed" and error_msg:
                        st.caption(f"Error: {error_msg}")
                with c4:
                    st.markdown(f"**{chunks}** chunks")
                with c5:
                    if status == "failed":
                        if st.button("🔄", key=f"retry_doc_{doc_id}", help=f"Retry indexing {filename}"):
                            st.rerun()
                    if st.button("🗑️", key=f"del_doc_{doc_id}", help=f"Delete {filename}"):
                        del_res = client.delete_document(ws_id, doc_id)
                        if del_res.get("success"):
                            st.success(f"Deleted {filename}")
                            st.rerun()
                        else:
                            st.error(f"Error: {del_res.get('error')}")
                st.markdown("<hr style='margin: 0.2rem 0; opacity: 0.08;'/>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)
    else:
        st.info("Upload documents to build your knowledge base.")

    st.markdown("<hr style='margin: 1.25rem 0; opacity: 0.12;'/>", unsafe_allow_html=True)

    # -------------------------------------------------------------
    # 2. CHAT SECTION (Directly below document section)
    # -------------------------------------------------------------
    col_chat_title, col_chat_ctrl = st.columns([3.5, 1])
    with col_chat_title:
        st.markdown("### 💬 Chat")
    with col_chat_ctrl:
        if st.button("➕ Clear Chat", use_container_width=True, key="clear_chat_history_btn"):
            st.session_state["messages"] = []
            st.session_state["session_id"] = None
            st.rerun()

    # Empty State Guidance for Chat
    if not has_indexed_docs:
        if processing_docs > 0:
            st.info(
                "Your documents are being indexed. Chat will become available when indexing completes."
            )
        else:
            st.info(
                "Index a document to start chatting."
            )

    # Initialize messages list
    if "messages" not in st.session_state:
        st.session_state["messages"] = []

    # Render Conversation History
    for msg in st.session_state["messages"]:
        role = msg.get("role")
        content = msg.get("content", "")
        with st.chat_message(role, avatar="🧑‍💻" if role == "user" else "⚡"):
            st.markdown(content)

            if role == "assistant":
                groundedness = msg.get("groundedness")
                citations = msg.get("citations", [])
                debug = msg.get("retrieval_debug")

                if groundedness:
                    st.markdown(render_groundedness_badge(groundedness), unsafe_allow_html=True)

                if citations:
                    with st.expander(f"📚 Sources ({len(citations)} cited)", expanded=False):
                        for idx, cit in enumerate(citations, 1):
                            st.markdown(render_citation_card(idx, cit), unsafe_allow_html=True)

                if debug:
                    with st.expander("🛠️ Retrieval Diagnostics", expanded=False):
                        c1, c2, c3, c4 = st.columns(4)
                        c1.metric("Dense Candidates", _safe_metric(debug.get("vector_candidates") or debug.get("vector_candidates_count") or debug.get("dense_candidates")))
                        c2.metric("BM25 Candidates", _safe_metric(debug.get("keyword_candidates") or debug.get("keyword_candidates_count")))
                        c3.metric("RRF Fused Pool", _safe_metric(debug.get("fused_candidates") or debug.get("fused_candidates_count")))
                        c4.metric("Final Chunks", _safe_metric(debug.get("final_chunks")))
                        timings = debug.get("timings")
                        if timings:
                            st.json(timings)

    # Chat input handling
    user_input = st.chat_input("Ask a question about your indexed documents...")

    if user_input:
        if not has_indexed_docs:
            st.warning("Please upload and index at least one document before asking questions.")
        else:
            # Add user message to state and UI
            st.session_state["messages"].append({"role": "user", "content": user_input})
            with st.chat_message("user", avatar="🧑‍💻"):
                st.markdown(user_input)

            # Assistant streaming generation
            with st.chat_message("assistant", avatar="⚡"):
                stream_placeholder = st.empty()
                full_response = ""
                citations_data = []
                groundedness_data = {}
                retrieval_debug_data = {}
                active_session_id = st.session_state.get("session_id")

                with st.spinner("Searching documents and generating answer..."):
                    stream_gen = client.chat_stream(
                        workspace_id=str(ws_id),
                        query=user_input,
                        session_id=active_session_id,
                    )

                    for event in stream_gen:
                        evt_type = event.get("event")
                        if evt_type == "session":
                            st.session_state["session_id"] = event.get("session_id")
                        elif evt_type == "delta":
                            full_response += event.get("delta", "")
                            stream_placeholder.markdown(full_response + " ▌")
                        elif evt_type == "done":
                            citations_data = event.get("citations", [])
                            groundedness_data = event.get("groundedness", {})
                            retrieval_debug_data = event.get("retrieval_debug", {})
                        elif evt_type == "error":
                            err_msg = event.get("error", "Unknown error")
                            stream_placeholder.error(f"⚠️ Error: {err_msg}")
                            full_response = f"⚠️ Error: {err_msg}"

                # Final response
                stream_placeholder.markdown(full_response)

                if groundedness_data:
                    st.markdown(render_groundedness_badge(groundedness_data), unsafe_allow_html=True)

                if citations_data:
                    with st.expander(f"📚 Sources ({len(citations_data)} cited)", expanded=True):
                        for idx, cit in enumerate(citations_data, 1):
                            st.markdown(render_citation_card(idx, cit), unsafe_allow_html=True)

                if retrieval_debug_data:
                    with st.expander("🛠️ Retrieval Diagnostics", expanded=False):
                        c1, c2, c3, c4 = st.columns(4)
                        c1.metric("Dense Candidates", _safe_metric(retrieval_debug_data.get("vector_candidates") or retrieval_debug_data.get("vector_candidates_count") or retrieval_debug_data.get("dense_candidates")))
                        c2.metric("BM25 Candidates", _safe_metric(retrieval_debug_data.get("keyword_candidates") or retrieval_debug_data.get("keyword_candidates_count")))
                        c3.metric("RRF Fused Pool", _safe_metric(retrieval_debug_data.get("fused_candidates") or retrieval_debug_data.get("fused_candidates_count")))
                        c4.metric("Final Chunks", _safe_metric(retrieval_debug_data.get("final_chunks")))
                        timings = retrieval_debug_data.get("timings")
                        if timings:
                            st.json(timings)

                # Append to session state
                st.session_state["messages"].append({
                    "role": "assistant",
                    "content": full_response,
                    "citations": citations_data,
                    "groundedness": groundedness_data,
                    "retrieval_debug": retrieval_debug_data,
                })

