"""
Document Ingestion & Management Component.
Handles file uploads, visibility permissions, live ingestion status tracking,
and document deletion.
"""
from __future__ import annotations

import os
from pathlib import Path
import streamlit as st
from frontend.api_client import APIClient


def format_bytes(size_bytes: int) -> str:
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    return f"{size_bytes / (1024 * 1024):.2f} MB"


def render_documents_view(
    client: APIClient,
    active_workspace: dict | None = None,
    workspace_id: str | None = None,
):
    if active_workspace is None:
        active_workspace = {"id": workspace_id or "default", "name": "Workspace"}
    elif isinstance(active_workspace, str):
        active_workspace = {"id": active_workspace, "name": "Workspace"}

    workspace_id = str(active_workspace.get("id") or workspace_id or "default")
    workspace_name = active_workspace.get("name", "Workspace")

    st.markdown(f"### 📁 Document Knowledge Base: **{workspace_name}**")
    st.caption("Upload documents to be parsed, chunked, embedded with pgvector, and indexed into hybrid search.")

    col_upload, col_stats = st.columns([2, 1])

    with col_upload:
        with st.expander("📤 Upload New Document", expanded=True):
            uploaded_file = st.file_uploader(
                "Choose file (.pdf, .docx, .md, .txt)",
                type=["pdf", "docx", "md", "txt"],
                help="Files are asynchronously chunked and embedded by worker processes using PostgreSQL lock-free queues.",
            )
            col_vis, col_btn = st.columns([1, 1])
            with col_vis:
                visibility = st.selectbox(
                    "Visibility / RBAC",
                    options=["workspace", "private"],
                    format_func=lambda x: "🌐 Workspace-wide" if x == "workspace" else "🔒 Private to me",
                )
            with col_btn:
                st.write("")
                st.write("")
                upload_pressed = st.button("🚀 Upload & Ingest", type="primary", use_container_width=True)

            if upload_pressed:
                if uploaded_file is None:
                    st.warning("Please select a file to upload.")
                else:
                    file_bytes = uploaded_file.read()
                    content_type = uploaded_file.type or "application/octet-stream"
                    with st.spinner("Uploading to storage and queueing background worker job..."):
                        res = client.upload_document(
                            workspace_id=workspace_id,
                            filename=uploaded_file.name,
                            file_bytes=file_bytes,
                            content_type=content_type,
                            visibility=visibility,
                        )
                        if res.get("success"):
                            st.success(f"✅ File '{uploaded_file.name}' accepted! Ingestion job queued.")
                            st.rerun()
                        else:
                            st.error(f"❌ Upload failed: {res.get('error')}")

            # Demo asset quick upload helper
            demo_doc_path = Path(__file__).resolve().parents[2] / "data" / "demo_architecture.md"
            if demo_doc_path.exists():
                st.markdown("---")
                if st.button("📄 Load Demo Asset (`demo_architecture.md`)", use_container_width=True):
                    with open(demo_doc_path, "rb") as f:
                        demo_bytes = f.read()
                    with st.spinner("Ingesting demo architecture document..."):
                        res = client.upload_document(
                            workspace_id=workspace_id,
                            filename="demo_architecture.md",
                            file_bytes=demo_bytes,
                            content_type="text/markdown",
                            visibility="workspace",
                        )
                        if res.get("success"):
                            st.success("✅ Demo document uploaded!")
                            st.rerun()
                        else:
                            st.error(f"Upload failed: {res.get('error')}")

    with col_stats:
        docs = client.list_documents(workspace_id=workspace_id)
        total_docs = len(docs)
        indexed_docs = sum(1 for d in docs if d.get("status") == "indexed")
        total_chunks = sum(d.get("chunk_count", 0) for d in docs)

        st.markdown(
            f"""
            <div class="kpi-card">
                <div class="kpi-label">Knowledge Base Status</div>
                <div class="kpi-value">{indexed_docs} / {total_docs} Ready</div>
                <div style="font-size: 0.8rem; color: #94A3B8; margin-top: 0.4rem;">
                    <b>{total_chunks}</b> total vector chunks embedded in pgvector.
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.write("")
        if st.button("🔄 Refresh Documents List", use_container_width=True):
            st.rerun()

    # Document Table / List
    st.markdown("#### 📑 Indexed Documents")
    if not docs:
        st.info("No documents uploaded yet in this workspace. Upload a file above or load the demo asset to get started!")
    else:
        for doc in docs:
            doc_id = str(doc.get("id"))
            filename = doc.get("filename", "Untitled")
            status = doc.get("status", "unknown")
            size_str = format_bytes(doc.get("size_bytes", 0))
            chunks = doc.get("chunk_count", 0)
            vis = doc.get("visibility", "workspace")
            err = doc.get("error_message")
            created_at = str(doc.get("created_at", ""))[:19].replace("T", " ")

            # Status Badge
            if status == "indexed":
                status_html = '<span class="badge badge-green">● Indexed</span>'
            elif status in ("pending", "chunking", "embedding"):
                status_html = f'<span class="badge badge-amber">⏳ {status.title()}</span>'
            else:
                status_html = f'<span class="badge badge-red">❌ {status.title()}</span>'

            vis_icon = "🌐" if vis == "workspace" else "🔒"

            with st.container():
                d_col1, d_col2, d_col3, d_col4, d_col5 = st.columns([3, 1.5, 1, 1.5, 0.8])
                with d_col1:
                    st.markdown(f"**{vis_icon} {filename}**")
                    st.caption(f"ID: `{doc_id[:8]}...` • Size: {size_str} • Uploaded: {created_at}")
                with d_col2:
                    st.markdown(status_html, unsafe_allow_html=True)
                    if err:
                        st.caption(f"Error: {err}")
                with d_col3:
                    st.markdown(f"**{chunks}** chunks")
                with d_col4:
                    st.caption(f"Vis: {vis.title()}")
                with d_col5:
                    if st.button("🗑️", key=f"del_{doc_id}", help="Delete Document"):
                        with st.spinner("Deleting document..."):
                            del_res = client.delete_document(workspace_id, doc_id)
                            if del_res.get("success"):
                                st.success(f"Deleted {filename}")
                                st.rerun()
                            else:
                                st.error(f"Could not delete: {del_res.get('error')}")
                st.markdown("<hr style='margin: 0.4rem 0; opacity: 0.15;'/>", unsafe_allow_html=True)
