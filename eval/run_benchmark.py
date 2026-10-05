import json
import sys
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from frontend.standalone_engine import StandaloneEngine

def main():
    engine = StandaloneEngine()
    ws_id = "prod_benchmark_workspace"
    engine.workspaces[ws_id] = {"id": ws_id, "name": "Production Benchmark Workspace"}

    print("=" * 70)
    print("INGESTING MULTI-DOMAIN BENCHMARK CORPUS...")
    print("=" * 70)
    ingest_res = engine.ingest_benchmark_corpus(ws_id)
    print(f"Ingestion result: {ingest_res['documents']} ({ingest_res['chunks']} chunks indexed)\n")

    print("=" * 70)
    print("RUNNING 4-WAY COMPARATIVE RETRIEVAL & GENERATION BENCHMARK...")
    print("=" * 70)
    eval_res = engine.run_eval(ws_id, k=5)

    print("\n--- COMPARATIVE RETRIEVAL CONFIGURATION MATRIX ---")
    print(f"{'Configuration':<42} | {'Recall@5':<10} | {'Prec@5':<10} | {'MRR':<8} | {'nDCG@5':<8}")
    print("-" * 86)
    for arm, m in eval_res["comparative_retrieval_metrics"].items():
        name = {
            "dense_vector_only": "1. Dense Vector Search Only",
            "bm25_keyword_only": "2. BM25 Keyword Search Only",
            "reciprocal_rank_fusion": "3. Hybrid RRF (k=60)",
            "rrf_cross_encoder_reranked": "4. Hybrid RRF + Cross-Encoder Rerank",
        }.get(arm, arm)
        print(f"{name:<42} | {m['recall_at_k']*100:>8.1f}% | {m['precision_at_k']*100:>8.1f}% | {m['mrr']:>8.3f} | {m['ndcg_at_k']:>8.3f}")

    print("\n--- GENERATION & CITATION FIDELITY METRICS ---")
    print(f"Citation Precision:      {eval_res['avg_citation_precision']*100:.1f}%")
    print(f"Citation Coverage:       {eval_res['avg_citation_coverage']*100:.1f}%")
    print(f"Groundedness Rate:       {eval_res['groundedness_rate']*100:.1f}%")
    print(f"Negative Refusal Acc.:   {eval_res['refusal_accuracy']*100:.1f}%")
    print(f"Total Benchmark Latency: {eval_res['total_latency_ms']:.2f} ms")

    print("\n--- CATEGORY BREAKDOWN ---")
    print(f"{'Category':<30} | {'Count':<6} | {'Recall@5':<10} | {'MRR':<8} | {'Cit. Coverage':<12}")
    print("-" * 75)
    for cat, cm in eval_res["category_breakdown"].items():
        print(f"{cat:<30} | {cm['count']:<6} | {cm['avg_recall_at_k']*100:>8.1f}% | {cm['avg_mrr']:>8.3f} | {cm['citation_coverage']*100:>10.1f}%")

    print("\n--- DETAILED QUERY-BY-QUERY RESULTS ---")
    for i, c in enumerate(eval_res["cases"], 1):
        print(f"[{i}] Category: {c['category']} | Refusal Correct: {c['refusal_correct']}")
        print(f"    Query:            {c['query']}")
        print(f"    Expected Sources: {c['expected_sources']}")
        print(f"    Retrieved Top-5:  {c['retrieved_sources']}")
        print(f"    Citations:        {c['citations']}")
        print(f"    Recall@5: {c['final_recall']*100:.1f}% | Prec@5: {c['final_precision']*100:.1f}% | MRR: {c['final_mrr']:.3f} | nDCG@5: {c['final_ndcg']:.3f}")
        print(f"    Grounded: {c['grounded']}")
        print()

if __name__ == "__main__":
    main()
