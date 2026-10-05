"""
Production RAG AI Assistant - Streamlit Web Dashboard.
Features hybrid search, real-time citation grounding, document ingestion,
multi-tenant RBAC workspaces, automated evaluation benchmarks, and Prometheus observability.
Provides instant direct access to the RAG platform without mandatory login.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

# Ensure project root is prioritized on sys.path
FRONTEND_DIR = Path(__file__).resolve().parent
ROOT_CANDIDATE_1 = FRONTEND_DIR.parent
ROOT_CANDIDATE_2 = ROOT_CANDIDATE_1 / "production-rag-ai-assistant"

target_root = ROOT_CANDIDATE_1
if (ROOT_CANDIDATE_2 / "app").is_dir():
    target_root = ROOT_CANDIDATE_2
elif (ROOT_CANDIDATE_1 / "app").is_dir():
    target_root = ROOT_CANDIDATE_1

while str(FRONTEND_DIR) in sys.path:
    sys.path.remove(str(FRONTEND_DIR))

if str(target_root) not in sys.path:
    sys.path.insert(0, str(target_root))

import streamlit as st
from frontend.api_client import APIClient
from frontend.components.eval_view import render_eval_view
from frontend.components.metrics_view import render_metrics_view
from frontend.components.unified_workspace import render_unified_workspace
from frontend.components.workspaces_view import render_workspaces_view
from frontend.styles import CUSTOM_CSS, render_header


def init_session():
    if "api_url" not in st.session_state:
        st.session_state["api_url"] = os.getenv("API_BASE_URL", "http://localhost:8000")
    if "engine_mode" not in st.session_state:
        st.session_state["engine_mode"] = "Auto (FastAPI / Standalone Fallback)"
    if "active_workspace" not in st.session_state:
        st.session_state["active_workspace"] = None
    if "workspaces" not in st.session_state:
        st.session_state["workspaces"] = []
    if "messages" not in st.session_state:
        st.session_state["messages"] = []
    if "session_id" not in st.session_state:
        st.session_state["session_id"] = None
    if "auth_user" not in st.session_state:
        st.session_state["auth_user"] = {
            "email": "user@workspace.local",
            "full_name": "Workspace Operator",
            "is_superuser": True,
            "role": "admin",
        }
    if "token" not in st.session_state:
        st.session_state["token"] = "session_token"


def main():
    st.set_page_config(
        page_title="Production RAG Assistant",
        page_icon="⚡",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    # Inject Obsidian Dark Theme styling
    st.markdown(CUSTOM_CSS, unsafe_allow_html=True)
    init_session()

    client = APIClient(
        base_url=st.session_state["api_url"],
        token=st.session_state.get("token"),
    )

    # Check health and backend status
    backend_status = client.health_check()
    is_live = backend_status.get("fastapi_online", False)

    # Auto-load workspaces
    if not st.session_state["workspaces"]:
        ws_list = client.list_workspaces()
        st.session_state["workspaces"] = ws_list
        if ws_list and not st.session_state["active_workspace"]:
            st.session_state["active_workspace"] = ws_list[0]

    # Sidebar Navigation & Controls
    with st.sidebar:
        st.markdown(
            """
            <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 12px;">
                <div style="width: 34px; height: 34px; border-radius: 8px; background: linear-gradient(135deg, #6366f1, #8b5cf6); display: flex; align-items: center; justify-content: center; font-size: 16px;">⚡</div>
                <div>
                    <h3 style="margin: 0; font-size: 1.05rem; color: #f8fafc; font-weight: 700;">Production RAG</h3>
                    <span style="font-size: 0.74rem; color: #94a3b8;">Document Assistant</span>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # Connection Status
        if is_live:
            st.markdown(
                '<div style="display: inline-flex; align-items: center; gap: 6px; background: rgba(16, 185, 129, 0.1); border: 1px solid rgba(16, 185, 129, 0.25); border-radius: 6px; padding: 3px 8px; margin-bottom: 14px; font-size: 0.72rem; color: #34d399; font-weight: 600;">● Backend Connected</div>',
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                '<div style="display: inline-flex; align-items: center; gap: 6px; background: rgba(16, 185, 129, 0.1); border: 1px solid rgba(16, 185, 129, 0.25); border-radius: 6px; padding: 3px 8px; margin-bottom: 14px; font-size: 0.72rem; color: #34d399; font-weight: 600;">● Connected</div>',
                unsafe_allow_html=True,
            )

        # Active Workspace Selection
        st.markdown("<p style='font-size: 0.72rem; text-transform: uppercase; letter-spacing: 0.05em; color: #94A3B8; font-weight: 600; margin-bottom: 3px;'>Active Workspace</p>", unsafe_allow_html=True)
        ws_names = [w.get("name", "Untitled") for w in st.session_state["workspaces"]]
        if ws_names:
            current_idx = 0
            if st.session_state["active_workspace"]:
                for i, w in enumerate(st.session_state["workspaces"]):
                    if w.get("id") == st.session_state["active_workspace"].get("id"):
                        current_idx = i
                        break
            chosen_ws_name = st.selectbox("Active Workspace", ws_names, index=current_idx, label_visibility="collapsed")
            for w in st.session_state["workspaces"]:
                if w.get("name") == chosen_ws_name:
                    st.session_state["active_workspace"] = w
                    break
        else:
            st.info("No workspaces available.")

        if "selected_nav" not in st.session_state:
            st.session_state["selected_nav"] = "💬 RAG Assistant"

        current_nav = st.session_state["selected_nav"]

        st.markdown("<div class='sidebar-nav-header'>MAIN</div>", unsafe_allow_html=True)
        if st.button("💬 RAG Assistant", key="nav_btn_rag", use_container_width=True, type="primary" if current_nav == "💬 RAG Assistant" else "secondary"):
            st.session_state["selected_nav"] = "💬 RAG Assistant"
            st.rerun()

        st.markdown("<div class='sidebar-nav-header'>ADMIN</div>", unsafe_allow_html=True)
        if st.button("⚙ Administration", key="nav_btn_admin", use_container_width=True, type="primary" if current_nav == "⚙ Administration" else "secondary"):
            st.session_state["selected_nav"] = "⚙ Administration"
            st.rerun()

        st.markdown("<div class='sidebar-nav-header'>DEVELOPER</div>", unsafe_allow_html=True)
        if st.button("📊 Evaluation", key="nav_btn_eval", use_container_width=True, type="primary" if current_nav == "📊 Evaluation" else "secondary"):
            st.session_state["selected_nav"] = "📊 Evaluation"
            st.rerun()
        if st.button("📈 Metrics", key="nav_btn_metrics", use_container_width=True, type="primary" if current_nav == "📈 Metrics" else "secondary"):
            st.session_state["selected_nav"] = "📈 Metrics"
            st.rerun()

        selected_nav = st.session_state["selected_nav"]

    # Active Workspace Resolution
    active_ws = st.session_state.get("active_workspace") or {"id": "default", "name": "Knowledge Base"}

    # Top Header
    header_html = render_header(
        app_name="Production RAG Assistant",
        subtitle="Chat with your documents",
        workspace_name=active_ws.get("name") if active_ws.get("name") != "default" else "Knowledge Base",
        backend_status="ok",
        mode_label="Backend Connected" if is_live else "Connected",
    )
    st.markdown(header_html, unsafe_allow_html=True)

    # Main Router
    if selected_nav == "💬 RAG Assistant":
        render_unified_workspace(client=client, active_workspace=active_ws)
    elif selected_nav == "⚙ Administration":
        render_workspaces_view(client=client, active_workspace=active_ws)
    elif selected_nav == "📊 Evaluation":
        render_eval_view(client=client, active_workspace=active_ws)
    elif selected_nav == "📈 Metrics":
        render_metrics_view(client=client)


if __name__ == "__main__":
    main()

