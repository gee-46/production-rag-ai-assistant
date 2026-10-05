"""
Automated RAG Evaluation & Golden Dataset Benchmark Runner Component.
Provides multi-configuration retrieval comparisons, citation precision/coverage,
per-category breakdown, and query-level diagnostic logs.
"""
from __future__ import annotations

import pandas as pd
import streamlit as st
from frontend.api_client import APIClient


def render_eval_view(
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

    st.markdown(f"### 🧪 RAG Evaluation Benchmark: **{workspace_name}**")
    st.caption(
        "Execute end-to-end multi-configuration retrieval and generation evaluation against the labeled Golden QA dataset "
        "to empirically measure Recall@K, Precision@K, MRR, nDCG@K, citation fidelity, and negative refusal accuracy."
    )

    col1, col2 = st.columns([1, 1])
    with col1:
        run_btn = st.button("▶️ Run Golden Benchmark (10 Cases)", type="primary", use_container_width=True)
    with col2:
        ingest_corpus_btn = st.button("📥 Ingest Multi-Domain Benchmark Corpus", use_container_width=True)

    if ingest_corpus_btn:
        with st.spinner("Ingesting multi-domain benchmark documents into workspace..."):
            res = client.ingest_benchmark_corpus(workspace_id=workspace_id)
            if res.get("success"):
                st.success(f"✅ Ingested {len(res.get('documents', []))} multi-domain benchmark documents ({res.get('chunks', 0)} chunks).")
            else:
                st.error(f"❌ Failed to ingest benchmark corpus: {res.get('error')}")

    if run_btn:
        with st.spinner("Executing 4-way retrieval & generation benchmark across labeled queries..."):
            eval_res = client.run_eval(workspace_id=workspace_id)
            if eval_res.get("success"):
                data = eval_res.get("data", {})
                st.session_state["last_eval_result"] = data
                st.success("✅ Evaluation benchmark completed successfully!")
            else:
                st.error(f"❌ Evaluation run failed: {eval_res.get('error')}")

    # Display results if available
    eval_data = st.session_state.get("last_eval_result")
    if eval_data:
        st.markdown("---")

        # Warnings if applicable
        warnings = eval_data.get("warnings", [])
        for w in warnings:
            st.warning(f"⚠️ {w}")

        st.markdown("#### 📊 Overall Pipeline Metrics (RRF + Reranked)")
        m1, m2, m3, m4 = st.columns(4)
        prec = eval_data.get("avg_precision_at_k", 0.0)
        rec = eval_data.get("avg_recall_at_k", 0.0)
        mrr = eval_data.get("avg_mrr", 0.0)
        ndcg = eval_data.get("avg_ndcg_at_k", 0.0)

        with m1:
            st.metric("🎯 Precision@5", f"{prec * 100:.1f}%")
        with m2:
            st.metric("🔍 Recall@5", f"{rec * 100:.1f}%")
        with m3:
            st.metric("🏆 MRR", f"{mrr:.3f}")
        with m4:
            st.metric("📈 nDCG@5", f"{ndcg:.3f}")

        m5, m6, m7, m8 = st.columns(4)
        cit_prec = eval_data.get("avg_citation_precision", 0.0)
        cit_cov = eval_data.get("avg_citation_coverage", 0.0)
        grounded = eval_data.get("groundedness_rate", 0.0)
        refusal_acc = eval_data.get("refusal_accuracy", 0.0)

        with m5:
            st.metric("📎 Citation Precision", f"{cit_prec * 100:.1f}%")
        with m6:
            st.metric("📚 Citation Coverage", f"{cit_cov * 100:.1f}%")
        with m7:
            st.metric("🛡️ Groundedness Rate", f"{grounded * 100:.1f}%")
        with m8:
            st.metric("🚫 Negative Refusal Acc.", f"{refusal_acc * 100:.1f}%")

        # Comparative Configuration Matrix
        st.markdown("#### 🔬 Comparative Retrieval Evaluation Matrix")
        comparative = eval_data.get("comparative_retrieval_metrics", {})
        if comparative:
            rows = []
            for arm, metrics in comparative.items():
                label = {
                    "dense_vector_only": "1. Dense Vector Search Only",
                    "bm25_keyword_only": "2. BM25 / Keyword Search Only",
                    "reciprocal_rank_fusion": "3. Hybrid Reciprocal Rank Fusion (RRF, k=60)",
                    "rrf_cross_encoder_reranked": "4. Hybrid RRF + Cross-Encoder Reranking",
                }.get(arm, arm)
                rows.append({
                    "Retrieval Configuration": label,
                    "Recall@5": f"{metrics.get('recall_at_k', 0.0) * 100:.1f}%",
                    "Precision@5": f"{metrics.get('precision_at_k', 0.0) * 100:.1f}%",
                    "MRR": f"{metrics.get('mrr', 0.0):.3f}",
                    "nDCG@5": f"{metrics.get('ndcg_at_k', 0.0):.3f}",
                })
            st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

        # Category Breakdown
        category_stats = eval_data.get("category_breakdown", {})
        if category_stats:
            st.markdown("#### 🏷️ Performance by Query Category")
            cat_rows = []
            for cat, cmetrics in category_stats.items():
                cat_rows.append({
                    "Query Category": cat.replace("_", " ").title(),
                    "Count": cmetrics.get("count", 0),
                    "Avg Recall@5": f"{cmetrics.get('avg_recall_at_k', 0.0) * 100:.1f}%",
                    "Avg MRR": f"{cmetrics.get('avg_mrr', 0.0):.3f}",
                    "Citation Coverage": f"{cmetrics.get('citation_coverage', 0.0) * 100:.1f}%",
                })
            st.dataframe(pd.DataFrame(cat_rows), use_container_width=True, hide_index=True)

        # Per-Query Breakdown
        cases = eval_data.get("cases", [])
        if cases:
            st.markdown("#### 📋 Labeled Query Results")
            for i, c in enumerate(cases, 1):
                query_text = c.get("query", "")
                cat = c.get("category", "")
                rec_val = c.get("final_recall", 0.0)
                status_icon = "✅" if rec_val > 0.5 or c.get("refusal_correct") else "❌"
                with st.expander(f"{status_icon} Case {i}: [{cat}] {query_text[:75]}...", expanded=False):
                    q_col1, q_col2 = st.columns(2)
                    with q_col1:
                        st.markdown(f"**Query:** {query_text}")
                        st.markdown(f"**Category:** `{cat}`")
                        st.markdown(f"**Expected Sources:** `{c.get('expected_sources', [])}`")
                        st.markdown(f"**Retrieved Sources:** `{c.get('retrieved_sources', [])}`")
                    with q_col2:
                        st.markdown(f"**Recall@5:** `{rec_val * 100:.1f}%` | **MRR:** `{c.get('final_mrr', 0.0):.3f}`")
                        st.markdown(f"**Citations:** `{c.get('citations', [])}`")
                        st.markdown(f"**Grounded:** `{'Yes' if c.get('grounded') else 'No'}`")
                        st.markdown(f"**Refusal Correct:** `{'Yes' if c.get('refusal_correct') else 'N/A'}`")
                    st.markdown(f"**Generated Answer:** {c.get('generated_answer', '')}")

        # Raw Telemetry JSON
        with st.expander("🔍 Raw Benchmark Payload & Diagnostic JSON", expanded=False):
            st.json(eval_data)
