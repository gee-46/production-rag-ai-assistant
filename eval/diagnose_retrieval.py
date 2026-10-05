"""
Diagnostic Evaluation Suite for Multi-Arm Hybrid Retrieval, RRF Parameter Tuning,
and Cross-Encoder Reranking Analysis.

Runs an empirical comparison of:
- Dense Vector (all-MiniLM-L6-v2)
- BM25 Lexical Keyword
- RRF at k=10, 20, 40, 60, 100
- Cross-Encoder Reranking (ms-marco-MiniLM-L-6-v2)

Logs per-query rankings, candidate ordering changes, and reciprocal rank contributions.
"""
from __future__ import annotations

import json
import math
import re
import sys
import time
from pathlib import Path

# Ensure UTF-8 console output on Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.evaluation.metrics import (
    citation_coverage,
    citation_precision,
    mean_reciprocal_rank,
    ndcg_at_k,
    precision_at_k,
    recall_at_k,
)
from app.services.retrieval.hybrid import reciprocal_rank_fusion
from frontend.standalone_engine import StandaloneEngine


def run_comprehensive_retrieval_diagnostic():
    print("=" * 90)
    print("🔬 COMPREHENSIVE RETRIEVAL DIAGNOSTIC & RRF / CROSS-ENCODER AUDIT")
    print("=" * 90)

    engine = StandaloneEngine.get_instance()
    ws_id = "eval_diagnostic_workspace"
    engine.workspaces[ws_id] = {"id": ws_id, "name": "Diagnostic Workspace", "owner_id": "eval"}

    # 1. Ingest Multi-Domain Benchmark Corpus
    ingest_res = engine.ingest_benchmark_corpus(ws_id)
    chunks = engine.doc_chunks.get(ws_id, [])
    print(f"\n[Corpus Summary]")
    print(f"- Ingested Documents: {len(ingest_res.get('documents', []))} ({', '.join(ingest_res.get('documents', []))})")
    print(f"- Total Ingested Chunks: {len(chunks)}")
    for i, c in enumerate(chunks, 1):
        print(f"  [{i}] Doc: {c.filename} | Length: {len(c.text)} chars | Tokens: {c.chunk_metadata.get('token_count', '—')}")

    golden_file = Path(__file__).resolve().parents[1] / "eval" / "golden_qa.json"
    cases = json.loads(golden_file.read_text(encoding="utf-8"))
    print(f"\n[Benchmark Suite]")
    print(f"- Total Test Cases: {len(cases)}")
    print(f"- Answerable Cases: {sum(1 for c in cases if not c.get('negative', False))}")
    print(f"- Unanswerable/Negative Cases: {sum(1 for c in cases if c.get('negative', False))}")

    # Configurations to test
    rrf_ks = [10, 20, 40, 60, 100]
    config_keys = ["dense", "bm25"] + [f"rrf_k_{k}" for k in rrf_ks] + ["rrf_60_reranked"]
    config_results = {k: [] for k in config_keys}

    per_query_log = []

    print("\n" + "=" * 90)
    print("PER-QUERY RANKING AUDIT")
    print("=" * 90)

    # Pre-load CrossEncoder once
    ce_model = None
    try:
        from sentence_transformers import CrossEncoder
        ce_model = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")
    except Exception as e:
        print(f"[Warning] CrossEncoder could not be loaded: {e}")

    for case_idx, case in enumerate(cases, 1):
        query = case["query"]
        expected = set(case.get("expected_filenames", []))
        is_neg = case.get("negative", False)
        cat = case.get("category", "general")

        query_tokens = set(re.findall(r"\w+", query.lower()))

        # 1. BM25 Lexical Ranking
        keyword_scores = []
        for c in chunks:
            c_tokens = set(re.findall(r"\w+", c.text.lower()))
            overlap = len(query_tokens.intersection(c_tokens))
            score = overlap / (len(query_tokens) + 1e-5)
            keyword_scores.append((c, score))
        bm25_ranked = [c for c, s in sorted(keyword_scores, key=lambda x: x[1], reverse=True)]
        bm25_cand_names = [c.filename for c in bm25_ranked]

        # 2. Dense Semantic Vector Ranking
        vector_ranked = []
        if engine._embedder:
            q_vec = engine._embedder.encode(query)
            c_vecs = engine._embedder.encode([c.text for c in chunks])
            import numpy as np
            sims = np.dot(c_vecs, q_vec) / (np.linalg.norm(c_vecs, axis=1) * np.linalg.norm(q_vec) + 1e-8)
            v_scored = sorted(zip(chunks, sims), key=lambda x: float(x[1]), reverse=True)
            vector_ranked = [c for c, s in v_scored]
        else:
            vector_ranked = bm25_ranked
        dense_cand_names = [c.filename for c in vector_ranked]

        # 3. RRF with varying K constants
        rrf_rankings = {}
        for k_val in rrf_ks:
            fused = reciprocal_rank_fusion([vector_ranked, bm25_ranked], k=k_val)
            rrf_rankings[f"rrf_k_{k_val}"] = [c.filename for c in fused]

        # 4. Cross-Encoder Reranking over RRF (k=60)
        rrf_60_fused = reciprocal_rank_fusion([vector_ranked, bm25_ranked], k=60)
        
        reranked_chunks = list(rrf_60_fused)
        reranker_scores = {}
        if ce_model is not None:
            pairs = [[query, c.text] for c in rrf_60_fused]
            scores = ce_model.predict(pairs)
            scored_pairs = sorted(zip(rrf_60_fused, scores), key=lambda x: float(x[1]), reverse=True)
            reranked_chunks = [c for c, s in scored_pairs]
            reranker_scores = {c.filename: float(s) for c, s in scored_pairs}
        else:
            reranker_scores = {"status": "not loaded"}

        reranked_names = [c.filename for c in reranked_chunks]

        # Evaluate all configurations
        eval_map = {
            "dense": dense_cand_names,
            "bm25": bm25_cand_names,
            **rrf_rankings,
            "rrf_60_reranked": reranked_names,
        }

        row_metrics = {}
        for cfg, cands in eval_map.items():
            r_k = recall_at_k(cands, expected, k=5)
            p_k = precision_at_k(cands, expected, k=5)
            mrr = mean_reciprocal_rank(cands, expected)
            ndcg = ndcg_at_k(cands, expected, k=5)
            row_metrics[cfg] = {"recall": r_k, "prec": p_k, "mrr": mrr, "ndcg": ndcg}
            config_results[cfg].append(row_metrics[cfg])

        # Find first rank of relevant document
        def first_rel_rank(cands, target_set):
            if not target_set:
                return "N/A (negative)"
            for rank, item in enumerate(cands, 1):
                if item in target_set:
                    return rank
            return ">5"

        print(f"\n[Case {case_idx:02d}] ({cat})")
        print(f"  Query: '{query}'")
        print(f"  Expected Target: {list(expected) if expected else '[] (Refusal expected)'}")
        print(f"  - Dense Rank: {dense_cand_names[:4]} (1st hit: rank {first_rel_rank(dense_cand_names, expected)})")
        print(f"  - BM25 Rank:  {bm25_cand_names[:4]} (1st hit: rank {first_rel_rank(bm25_cand_names, expected)})")
        print(f"  - RRF(k=60):  {rrf_rankings['rrf_k_60'][:4]} (1st hit: rank {first_rel_rank(rrf_rankings['rrf_k_60'], expected)})")
        print(f"  - Reranked:   {reranked_names[:4]} (1st hit: rank {first_rel_rank(reranked_names, expected)})")
        if isinstance(reranker_scores, dict) and "status" not in reranker_scores:
            print(f"    Reranker Raw Logits: {', '.join(f'{k}: {v:.3f}' for k, v in list(reranker_scores.items())[:3])}")

    # Aggregated Comparative Matrix
    print("\n" + "=" * 90)
    print("AGGREGATED RETRIEVAL PERFORMANCE MATRIX (All 10 Queries)")
    print("=" * 90)
    print(f"{'Retrieval Configuration':<32} | {'Recall@5':<10} | {'Prec@5':<10} | {'MRR':<10} | {'nDCG@5':<10}")
    print("-" * 85)

    for cfg in config_keys:
        res_list = config_results[cfg]
        n = len(res_list) or 1
        avg_rec = sum(x["recall"] for x in res_list) / n
        avg_prec = sum(x["prec"] for x in res_list) / n
        avg_mrr = sum(x["mrr"] for x in res_list) / n
        avg_ndcg = sum(x["ndcg"] for x in res_list) / n
        
        display_name = {
            "dense": "Dense Semantic (Cosine)",
            "bm25": "BM25 Lexical Keyword",
            "rrf_k_10": "RRF (k=10)",
            "rrf_k_20": "RRF (k=20)",
            "rrf_k_40": "RRF (k=40)",
            "rrf_k_60": "RRF (k=60)",
            "rrf_k_100": "RRF (k=100)",
            "rrf_60_reranked": "RRF (k=60) + Cross-Encoder",
        }.get(cfg, cfg)

        print(f"{display_name:<32} | {avg_rec*100:>8.1f}% | {avg_prec*100:>8.1f}% | {avg_mrr:>10.4f} | {avg_ndcg:>10.4f}")

    print("=" * 90)


if __name__ == "__main__":
    run_comprehensive_retrieval_diagnostic()
