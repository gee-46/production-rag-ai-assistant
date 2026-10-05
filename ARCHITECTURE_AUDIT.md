# Architecture Audit — Original Prototype

Audit performed before any rewrite work began, per the project brief. The original repository was
393 lines across 8 files (`app/main.py` + 7 service modules), a learning-project-stage
implementation of chunk -> embed -> FAISS -> LLM.

## The most important finding

`app/main.py` contained a genuine `SyntaxError` (a stray `t}` token at line 206, the end of the
`/upload` handler), confirmed with `ast.parse`. **The application as committed did not run.**
`app/test_ollama.py` was also syntactically incomplete (unterminated call, unused result) and was
not a test in any real sense.

## A. What was already good

- Correct high-level pipeline shape: chunk -> embed -> index -> retrieve -> rerank -> prompt ->
  generate.
- Two-stage retrieval (FAISS bi-encoder + `cross-encoder/ms-marco-MiniLM-L-6-v2` reranker) — the
  right architecture, just not composed correctly.
- Persisting the FAISS index + texts to disk instead of rebuilding on every boot.
- A prompt that explicitly constrained the model to context-only answers — a real, if blunt,
  anti-hallucination technique.

## B. What was preserved

The pipeline stage *decomposition* (chunking / embeddings / retrieval / reranking / generation as
separate modules) was kept; nearly every implementation behind those module boundaries was rewritten.

## C. What was refactored

- **Global mutable state at import time.** `main.py` loaded documents, embedded them, and built the
  vector store as module-level code run before the app was ready to serve — no boot with zero
  documents, no testability, no health checks.
- **Blocking calls inside async handlers.** `/query` and `/upload` were `async def` but called
  synchronous, CPU-bound `model.encode()`/`reranker.predict()` directly, blocking the event loop for
  every concurrent request.
- **Naive chunking.** Split on the literal string `". "` (breaks on abbreviations, decimals, lists),
  measured size in raw characters, and declared an `overlap` parameter that was never used in the
  function body.
- **Fragile vector store.** `self.texts` was a parallel Python list kept in lockstep with FAISS index
  positions by convention only — no IDs, no metadata, no delete/update, silent corruption risk if
  ever out of sync.
- **Unsafe upload handling.** Wrote to a shared, hardcoded `temp.docx` path in the process's working
  directory using the client-supplied filename directly — a race condition under concurrent uploads.
- **No error handling anywhere** — any exception became an opaque 500.
- **`print()` as the only observability** — no levels, no correlation, nothing queryable.
- **Everything hardcoded** — model names, chunk size, `top_k`, scattered as literals across files.

## D. What was removed

- `test_ollama.py` and `test_pipeline.py` — manual scratch scripts with no assertions, not part of
  any real test suite (and the former did not even run).
- A dead duplicate `return False` in the old `vector_store.load()`.

## E. What was missing for production (now built)

Auth, multi-user/workspaces, document-level ACL, hybrid (BM25/full-text + vector) retrieval, query
citation, streaming, conversation memory, hallucination/groundedness detection, an evaluation
harness, a background job queue for ingestion, PDF/OCR support, structured logging, Prometheus
metrics, CI, and an automated test suite. See the main [README](./README.md) for what now exists and
what's confirmed working, and its Roadmap section for what's intentionally still open.

## F–J: Bottlenecks, security, retrieval quality, scalability, UX

- **Bottlenecks:** synchronous model calls in the request path; single in-process FAISS index with
  no sharding story; whole-corpus embedding at startup.
- **Security:** no auth on any endpoint; unsanitized upload filename/path; no upload size or type
  enforcement beyond a weak extension check; no rate limiting; no CORS policy.
- **Retrieval quality:** punctuation-based chunking; no token-aware sizing; no working overlap; no
  metadata filtering; no hybrid lexical+semantic search; no citation grounding to source spans.
- **Scalability:** single process, single in-memory index, no multi-tenant isolation.
- **UX:** none — a bare, and at the time broken, JSON API.
