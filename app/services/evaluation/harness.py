"""
Comprehensive RAG Evaluation Harness & Multi-Configuration Benchmark Runner.
Evaluates retrieval across Dense, BM25, RRF, and RRF+Reranker configurations,
computing Recall@K, Precision@K, MRR, nDCG@K, citation fidelity, and groundedness.
"""
from __future__ import annotations

import json
import time
import uuid
from pathlib import Path
from typing import Any, Optional

from sqlalchemy.orm import Session

from app.services.evaluation.metrics import (
    citation_coverage,
    citation_precision,
    mean_reciprocal_rank,
    ndcg_at_k,
    precision_at_k,
    recall_at_k,
)
from app.services.rag.hallucination import check_groundedness
from app.services.rag.orchestrator import RagOrchestrator


def load_golden_set(path: Path | None = None) -> list[dict]:
    if path is None or not path.exists():
        path = Path(__file__).resolve().parents[2] / "eval" / "golden_qa.json"
        if not path.exists():
            path = Path(__file__).resolve().parents[3] / "eval" / "golden_qa.json"
    return json.loads(path.read_text(encoding="utf-8"))


def run_comprehensive_benchmark(
    db: Session,
    *,
    golden_set: list[dict],
    workspace_id: uuid.UUID,
    user_id: uuid.UUID,
    orchestrator: RagOrchestrator,
    k: int = 5,
) -> dict:
    """
    Executes a multi-configuration benchmark measuring:
    1. Dense Vector Search Only
    2. BM25 Lexical Search Only
    3. Hybrid Reciprocal Rank Fusion (RRF, k=60)
    4. Hybrid RRF + Cross-Encoder Reranking
    """
    results_by_config = {
        "dense_only": [],
        "keyword_only": [],
        "rrf_hybrid": [],
        "rrf_reranked": [],
    }

    per_query_details = []
    start_time = time.time()

    for case in golden_set:
        query = case["query"]
        expected_docs = set(case.get("expected_filenames", []))
        is_negative = case.get("negative", False)
        category = case.get("category", "general")
        ref_answer = case.get("reference_answer", "")

        t0 = time.time()
        # 1. Retrieve with full diagnostics
        chunks, debug = orchestrator.retrieve(
            db,
            query=query,
            workspace_id=workspace_id,
            user_id=user_id,
            is_admin=True,
            vector_top_k=20,
            keyword_top_k=20,
            rerank_top_k=k,
            rrf_k=60,
        )
        retrieval_ms = (time.time() - t0) * 1000

        # Extract ranked candidate lists from debug info if available
        dense_candidates = debug.get("dense_candidates", [c.filename for c in chunks])
        keyword_candidates = debug.get("keyword_candidates", [c.filename for c in chunks])
        fused_candidates = debug.get("fused_candidates", [c.filename for c in chunks])
        final_candidates = [c.filename for c in chunks]

        # Score retrieval across configurations
        def score_list(candidate_list: list[str]) -> dict:
            return {
                "precision_at_k": precision_at_k(candidate_list, expected_docs, k),
                "recall_at_k": recall_at_k(candidate_list, expected_docs, k),
                "mrr": mean_reciprocal_rank(candidate_list, expected_docs),
                "ndcg_at_k": ndcg_at_k(candidate_list, expected_docs, k),
            }

        dense_scores = score_list(dense_candidates)
        keyword_scores = score_list(keyword_candidates)
        rrf_scores = score_list(fused_candidates)
        final_scores = score_list(final_candidates)

        results_by_config["dense_only"].append(dense_scores)
        results_by_config["keyword_only"].append(keyword_scores)
        results_by_config["rrf_hybrid"].append(rrf_scores)
        results_by_config["rrf_reranked"].append(final_scores)

        # 2. Generation & Answer Evaluation
        t_gen0 = time.time()
        answer_text = orchestrator.llm.generate(
            "Answer using only the provided context. Cite sources using [1], [2]. If the context is missing the answer, decline politely.",
            f"Context: {[c.text for c in chunks]}\nQuestion: {query}",
        )
        gen_ms = (time.time() - t_gen0) * 1000

        groundedness = check_groundedness(answer_text, chunks)

        # Extract citations
        import re
        from app.services.rag.citation import build_citations
        citations = build_citations(answer_text, chunks)

        cit_prec = citation_precision(citations, expected_docs)
        cit_cov = citation_coverage(citations, expected_docs)

        # Check negative refusal
        refused = (
            "does not contain" in answer_text.lower()
            or "not mentioned" in answer_text.lower()
            or "cannot answer" in answer_text.lower()
        )
        correct_negative_handling = is_negative == refused

        per_query_details.append(
            {
                "id": case.get("id", str(uuid.uuid4())[:8]),
                "category": category,
                "query": query,
                "expected_sources": list(expected_docs),
                "retrieved_sources": final_candidates,
                "reference_answer": ref_answer,
                "generated_answer": answer_text,
                "precision_at_k": final_scores["precision_at_k"],
                "recall_at_k": final_scores["recall_at_k"],
                "mrr": final_scores["mrr"],
                "ndcg_at_k": final_scores["ndcg_at_k"],
                "citation_precision": cit_prec,
                "citation_coverage": cit_cov,
                "grounded": groundedness["supported"],
                "groundedness_method": groundedness.get("method", "lexical_overlap"),
                "is_negative": is_negative,
                "refused_correctly": correct_negative_handling,
                "latency_ms": {"retrieval": round(retrieval_ms, 2), "generation": round(gen_ms, 2)},
            }
        )

    total_time = time.time() - start_time
    n = len(per_query_details) or 1

    # Aggregate configuration summary metrics
    def summarize(scores_list: list[dict]) -> dict:
        m = len(scores_list) or 1
        return {
            "precision_at_k": sum(s["precision_at_k"] for s in scores_list) / m,
            "recall_at_k": sum(s["recall_at_k"] for s in scores_list) / m,
            "mrr": sum(s["mrr"] for s in scores_list) / m,
            "ndcg_at_k": sum(s["ndcg_at_k"] for s in scores_list) / m,
        }

    config_summary = {cfg: summarize(scores) for cfg, scores in results_by_config.items()}

    return {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%SZ", time.gmtime()),
        "dataset_size": len(golden_set),
        "total_duration_seconds": round(total_time, 2),
        "configurations": config_summary,
        "overall_metrics": {
            "avg_precision_at_k": config_summary["rrf_reranked"]["precision_at_k"],
            "avg_recall_at_k": config_summary["rrf_reranked"]["recall_at_k"],
            "avg_mrr": config_summary["rrf_reranked"]["mrr"],
            "avg_ndcg_at_k": config_summary["rrf_reranked"]["ndcg_at_k"],
            "avg_citation_precision": sum(q["citation_precision"] for q in per_query_details) / n,
            "avg_citation_coverage": sum(q["citation_coverage"] for q in per_query_details) / n,
            "groundedness_rate": sum(1 for q in per_query_details if q["grounded"]) / n,
            "negative_refusal_accuracy": sum(1 for q in per_query_details if q["is_negative"] and q["refused_correctly"])
            / max(1, sum(1 for q in per_query_details if q["is_negative"])),
        },
        "query_results": per_query_details,
    }


def run_retrieval_eval(
    db: Session,
    *,
    golden_set: list[dict],
    workspace_id: uuid.UUID,
    user_id: uuid.UUID,
    orchestrator: RagOrchestrator,
    k: int = 5,
) -> dict:
    """Backward-compatible wrapper for retrieval evaluation."""
    return run_comprehensive_benchmark(
        db,
        golden_set=golden_set,
        workspace_id=workspace_id,
        user_id=user_id,
        orchestrator=orchestrator,
        k=k,
    )
