"""
Unit tests for the Benchmark Evaluation Harness, Metrics, and Dataset Integrity.
"""
import json
from pathlib import Path

from app.services.evaluation.metrics import (
    citation_coverage,
    citation_precision,
    mean_reciprocal_rank,
    ndcg_at_k,
    precision_at_k,
    recall_at_k,
)
from frontend.standalone_engine import StandaloneEngine


def test_retrieval_metrics_math():
    retrieved = ["doc_a.txt", "doc_b.txt", "doc_c.txt", "doc_d.txt", "doc_e.txt"]
    relevant = {"doc_a.txt", "doc_c.txt"}

    # Precision@5: 2 hits out of 5 = 0.4
    assert precision_at_k(retrieved, relevant, k=5) == 0.4
    # Precision@1: 1 hit out of 1 = 1.0
    assert precision_at_k(retrieved, relevant, k=1) == 1.0

    # Recall@5: 2 hits out of 2 = 1.0
    assert recall_at_k(retrieved, relevant, k=5) == 1.0
    # Recall@1: 1 hit out of 2 = 0.5
    assert recall_at_k(retrieved, relevant, k=1) == 0.5

    # MRR: First hit at rank 1 = 1.0
    assert mean_reciprocal_rank(retrieved, relevant) == 1.0

    # First hit at rank 2
    assert mean_reciprocal_rank(["doc_x.txt", "doc_a.txt"], relevant) == 0.5

    # nDCG@5 with binary relevance
    assert ndcg_at_k(retrieved, relevant, k=5) > 0.8


def test_citation_metrics_math():
    citations = [
        {"filename": "doc_a.txt", "snippet": "Sample fact"},
        {"filename": "doc_b.txt", "snippet": "Sample fact 2"},
    ]
    expected = {"doc_a.txt"}

    # 1 of 2 citations is valid
    assert citation_precision(citations, expected) == 0.5
    # 1 of 1 expected doc was cited
    assert citation_coverage(citations, expected) == 1.0

    # Negative question with empty citations
    assert citation_precision([], set()) == 1.0
    assert citation_coverage([], set()) == 1.0


def test_golden_qa_dataset_integrity():
    golden_file = Path(__file__).resolve().parents[2] / "eval" / "golden_qa.json"
    assert golden_file.exists(), "eval/golden_qa.json must exist"

    cases = json.loads(golden_file.read_text(encoding="utf-8"))
    assert len(cases) >= 10, f"Expected at least 10 golden benchmark cases, got {len(cases)}"

    valid_categories = {
        "direct_fact",
        "exact_identifier",
        "paraphrase",
        "multi_chunk",
        "multi_document",
        "dense_keyword_disagreement",
        "conflicting_version",
        "negative_unanswerable",
    }

    for case in cases:
        assert "id" in case
        assert "query" in case and len(case["query"]) > 5
        assert "expected_filenames" in case
        assert "category" in case
        assert case["category"] in valid_categories, f"Invalid category {case['category']}"


def test_benchmark_end_to_end_with_corpus():
    engine = StandaloneEngine()
    ws_id = "eval_test_ws"
    engine.workspaces[ws_id] = {"id": ws_id, "name": "Benchmark Evaluation Workspace"}

    # Ingest standard benchmark corpus
    ingest_res = engine.ingest_benchmark_corpus(ws_id)
    assert ingest_res["success"] is True
    assert len(ingest_res["documents"]) == 4

    # Run benchmark evaluation
    eval_res = engine.run_eval(ws_id, k=5)
    assert eval_res["num_cases"] == 10
    assert "comparative_retrieval_metrics" in eval_res
    assert "dense_vector_only" in eval_res["comparative_retrieval_metrics"]
    assert "bm25_keyword_only" in eval_res["comparative_retrieval_metrics"]
    assert "reciprocal_rank_fusion" in eval_res["comparative_retrieval_metrics"]
    assert "rrf_cross_encoder_reranked" in eval_res["comparative_retrieval_metrics"]

    # Verify metrics are properly calculated
    assert eval_res["avg_recall_at_k"] > 0.5
    assert eval_res["avg_mrr"] > 0.5
    assert eval_res["refusal_accuracy"] == 1.0
    assert len(eval_res["cases"]) == 10
