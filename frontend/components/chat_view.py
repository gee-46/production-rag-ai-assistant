"""
Interactive RAG Chat component with Streaming, Groundedness Verification,
Citation Explorer, and Hybrid Retrieval Diagnostics.
"""
from __future__ import annotations

import streamlit as st
from frontend.api_client import APIClient
from frontend.styles import render_citation_card, render_groundedness_badge


def _safe_metric(val: any, default: str = "—") -> int | float | str:
    if val is None:
        return default
    if isinstance(val, (int, float, str)):
        return val
    if isinstance(val, (list, tuple, set, dict)):
        return len(val)
    return str(val)


def render_chat_view(
    client: APIClient,
    active_workspace: dict | None = None,
    workspace_id: str | None = None,
):
    if active_workspace is None:
        active_workspace = {"id": workspace_id or "default", "name": "Workspace"}
    elif isinstance(active_workspace, str):
        active_workspace = {"id": active_workspace, "name": "Workspace"}

    workspace_id = active_workspace.get("id") or workspace_id or "default"
    workspace_name = active_workspace.get("name", "Workspace")

    # Header / Session Controls
    col_title, col_actions = st.columns([3, 1])
    with col_title:
        st.markdown(f"### 💬 RAG Chat: **{workspace_name}**")
        st.caption("Ask questions grounded exclusively in your indexed documents with dual-arm hybrid retrieval & hallucination guardrails.")
    with col_actions:
        if st.button("➕ New Conversation", use_container_width=True):
            st.session_state["messages"] = []
            st.session_state["session_id"] = None
            st.rerun()

    # Initialize message list
    if "messages" not in st.session_state:
        st.session_state["messages"] = []

    # Display Conversation History
    for msg in st.session_state["messages"]:
        role = msg.get("role")
        content = msg.get("content", "")
        with st.chat_message(role, avatar="🧑‍💻" if role == "user" else "⚡"):
            st.markdown(content)

            # If assistant message has citations or groundedness info, render rich inspector
            if role == "assistant":
                groundedness = msg.get("groundedness")
                citations = msg.get("citations", [])
                debug = msg.get("retrieval_debug")

                if groundedness:
                    st.markdown(render_groundedness_badge(groundedness), unsafe_allow_html=True)

                if citations:
                    with st.expander(f"📚 Sources & Citations ({len(citations)} chunks retrieved)", expanded=False):
                        for idx, cit in enumerate(citations, 1):
                            st.markdown(render_citation_card(idx, cit), unsafe_allow_html=True)

                if debug:
                    with st.expander("🛠️ Retrieval Diagnostics & Pipeline Telemetry", expanded=False):
                        c1, c2, c3, c4 = st.columns(4)
                        c1.metric("Dense Vector Top-K", _safe_metric(debug.get("vector_candidates") or debug.get("vector_candidates_count") or debug.get("dense_candidates")))
                        c2.metric("Keyword BM25 Top-K", _safe_metric(debug.get("keyword_candidates") or debug.get("keyword_candidates_count")))
                        c3.metric("RRF Fused Candidates", _safe_metric(debug.get("fused_candidates") or debug.get("fused_candidates_count")))
                        c4.metric("Final Reranked Chunks", _safe_metric(debug.get("final_chunks")))

                        timing = debug.get("timings", {})
                        if timing:
                            st.json(timing)

    # Input handling (from chat input or quick prompt)
    user_input = st.chat_input("Ask a question about your workspace documents...")
    if quick_prompt:
        user_input = quick_prompt

    if user_input:
        # Add user message to state and UI
        st.session_state["messages"].append({"role": "user", "content": user_input})
        with st.chat_message("user", avatar="🧑‍💻"):
            st.markdown(user_input)

        # Assistant generation with streaming
        with st.chat_message("assistant", avatar="⚡"):
            stream_placeholder = st.empty()
            full_response = ""
            citations_data = []
            groundedness_data = {}
            retrieval_debug_data = {}
            active_session_id = st.session_state.get("session_id")

            with st.spinner("Retrieving hybrid chunks and reranking..."):
                stream_gen = client.chat_stream(
                    workspace_id=str(workspace_id),
                    query=user_input,
                    session_id=active_session_id,
                )

                for event in stream_gen:
                    evt_type = event.get("event")
                    if evt_type == "session":
                        new_session = event.get("session_id")
                        st.session_state["session_id"] = new_session
                    elif evt_type == "delta":
                        delta = event.get("delta", "")
                        full_response += delta
                        stream_placeholder.markdown(full_response + " ▌")
                    elif evt_type == "done":
                        citations_data = event.get("citations", [])
                        groundedness_data = event.get("groundedness", {})
                        retrieval_debug_data = event.get("retrieval_debug", {})
                    elif evt_type == "error":
                        err_msg = event.get("error", "Unknown error")
                        stream_placeholder.error(f"⚠️ Retrieval or generation error: {err_msg}")
                        full_response = f"⚠️ Error: {err_msg}"

            # Finalize assistant message
            stream_placeholder.markdown(full_response)

            if groundedness_data:
                st.markdown(render_groundedness_badge(groundedness_data), unsafe_allow_html=True)

            if citations_data:
                with st.expander(f"📚 Sources & Citations ({len(citations_data)} chunks retrieved)", expanded=True):
                    for idx, cit in enumerate(citations_data, 1):
                        st.markdown(render_citation_card(idx, cit), unsafe_allow_html=True)

            if retrieval_debug_data:
                with st.expander("🛠️ Retrieval Diagnostics & Pipeline Telemetry", expanded=False):
                    c1, c2, c3, c4 = st.columns(4)
                    c1.metric("Dense Vector Top-K", _safe_metric(retrieval_debug_data.get("vector_candidates") or retrieval_debug_data.get("vector_candidates_count") or retrieval_debug_data.get("dense_candidates")))
                    c2.metric("Keyword BM25 Top-K", _safe_metric(retrieval_debug_data.get("keyword_candidates") or retrieval_debug_data.get("keyword_candidates_count")))
                    c3.metric("RRF Fused Candidates", _safe_metric(retrieval_debug_data.get("fused_candidates") or retrieval_debug_data.get("fused_candidates_count")))
                    c4.metric("Final Reranked Chunks", _safe_metric(retrieval_debug_data.get("final_chunks")))
                    timing = retrieval_debug_data.get("timings", {})
                    if timing:
                        st.json(timing)

            # Save assistant message to state
            st.session_state["messages"].append({
                "role": "assistant",
                "content": full_response,
                "citations": citations_data,
                "groundedness": groundedness_data,
                "retrieval_debug": retrieval_debug_data,
            })
