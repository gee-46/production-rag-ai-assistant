# Production RAG AI Assistant: Architecture & System Overview

## 1. System Architecture Overview
The Production RAG AI Assistant is an enterprise-grade Retrieval-Augmented Generation platform built on a modern, decoupled service architecture. The core stack comprises:
- **FastAPI**: High-performance asynchronous HTTP API serving authentication, workspace management, document ingestion endpoints, and conversational RAG interfaces.
- **PostgreSQL with pgvector**: Primary relational data store and vector database utilizing the `vector` extension for efficient cosine distance indexing (`vector_cosine_ops`) via IVFFlat indices and GIN indexing for full-text search.
- **Background Ingestion Worker**: A dedicated asynchronous processing daemon using PostgreSQL-backed job queuing with `FOR UPDATE SKIP LOCKED` concurrency control to ensure scalable, non-blocking document ingestion.
- **Observability Layer**: Prometheus metrics endpoint (`/metrics`) exposing request rates, retrieval/generation latency histograms, and ingestion counters alongside structured JSON logging with distributed request correlation IDs (`x-request-id`).

## 2. Authentication and Workspace Role-Based Access Control (RBAC)
Security is implemented using industry standard cryptographic primitives:
- **JWT Authentication**: Stateless authentication using JSON Web Tokens signed with HS256 and secure password hashing via `bcrypt`.
- **Multi-Tenant Workspaces**: Users organize documents and conversations inside isolated workspaces.
- **Workspace Roles**: Four granular roles are supported: `owner`, `admin`, `member`, and `viewer`.
  - `owner`: Full control over workspace settings and member administration.
  - `admin`: Can invite members, manage document visibility, and delete workspace resources.
  - `member`: Can upload documents and initiate chat sessions.
  - `viewer`: Read-only access to query documents and view public conversation history.
- **Document-Level Access Control**: Documents are tagged as either `workspace` (accessible to all workspace members) or `private` (restricted strictly to the uploader and workspace admins).

## 3. Document Extraction and Token-Aware Chunking Pipeline
Uploaded documents are processed through an automated multi-stage pipeline:
- **Multi-Format Extraction**: Supports plain text (`.txt`), Markdown (`.md`), Microsoft Word (`.docx`), and Adobe PDF (`.pdf`) documents with PyMuPDF/pypdf and Tesseract OCR fallback for scanned pages.
- **Token-Aware Chunking**: Documents are parsed by paragraph structure and tokenized using `tiktoken` (cl100k_base). Chunks are created with a target size of 300 tokens and 50 tokens of boundary overlap to preserve semantic continuity across splits. Each chunk stores exact character start/end offsets (`char_start`, `char_end`) for precise attribution.

## 4. Embeddings and Vector Representation
- **Sentence Transformers**: Dense representations are generated locally using the `all-MiniLM-L6-v2` transformer model.
- **Embedding Dimension**: Produces dense 384-dimensional floating-point vectors normalized for cosine similarity calculations.
- **Storage**: Vectors are indexed in PostgreSQL using `pgvector` with IVFFlat cosine distance indexing.

## 5. Hybrid Retrieval and Reciprocal Rank Fusion (RRF)
To eliminate semantic blind spots, the system uses hybrid multi-arm retrieval:
- **Dense Vector Search**: Scans 384-dimensional embeddings in pgvector using cosine distance (`<=>`) to identify semantically related context candidates.
- **Lexical Keyword Search**: Queries PostgreSQL generated `tsvector` columns (`content_tsv`) with `ts_rank_cd` and `plainto_tsquery('english', query)` to capture exact terms, acronyms, and alphanumeric identifiers.
- **Reciprocal Rank Fusion (RRF)**: Combines candidate lists from vector search and keyword search using the formula `score = sum(1 / (k + rank))` with constant `k = 60`. This normalizes disparate score distributions without heuristic weight tuning.
- **Cross-Encoder Reranking**: Candidate passages from RRF are rescored with a cross-encoder model (`cross-encoder/ms-marco-MiniLM-L-6-v2`) that evaluates query-passage pairs jointly to optimize precision for the top-k results.

## 6. Generation, Citations, and Groundedness Guardrails
- **Groq LLM Inference**: High-throughput language generation powered by Groq's LPU inference engine running `llama-3.1-8b-instant`.
- **Structured Context Prompting**: Retrieved passages are injected into the prompt as numbered context blocks `[1]`, `[2]`, etc.
- **Deterministic Citation Extraction**: The model is instructed to cite source indices in brackets. The citation engine parses actual `[n]` citations and maps them directly to the corresponding source document metadata and text snippets.
- **Groundedness Evaluation**: The system performs real-time lexical overlap verification across every answer sentence against cited source chunks. If an answer introduces unsupported claims, it is flagged as ungrounded and recorded in Prometheus metrics (`rag_ungrounded_answers_total`). When context is insufficient, the system issues an explicit refusal to prevent hallucination.
