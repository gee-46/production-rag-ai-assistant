# 60–90 Second Demo Script: Production RAG AI Assistant

This script is structured for a high-impact, engineering-focused LinkedIn video demo showcasing a production-grade RAG platform rather than a toy "chat with PDF" script.

---

## Demo Setup (Pre-recording)
1. Ensure the stack is running:
   ```bash
   docker compose -f docker/docker-compose.yml up -d
   ```
2. Open your browser to the Streamlit UI (`http://localhost:8501`) or FastAPI Swagger UI (`http://localhost:8000/docs`)
3. Have a terminal open in the bottom corner showing real-time worker logs:
   ```bash
   docker compose -f docker/docker-compose.yml logs -f worker
   ```
4. Keep the metrics endpoint tab ready: `http://localhost:8000/metrics`


---

## 🎬 60–90 Second Video Script Breakdown

### 0:00 – 0:15 | Intro & API-First Architecture
- **Screen**: FastAPI Swagger UI (`http://localhost:8000/docs`)
- **Action**: Quickly scroll across the tagged endpoints: `/auth`, `/workspaces`, `/documents`, `/chat`, `/eval`, `/metrics`.
- **Narration / Voiceover**:
  > *"Most RAG tutorials stop at a basic Jupyter notebook with in-memory embeddings. Today I'm demonstrating a full-stack, enterprise-ready RAG backend running on FastAPI, PostgreSQL, pgvector, and Groq with asynchronous background ingestion and hybrid retrieval."*

---

### 0:15 – 0:30 | Auth, RBAC & Async Ingestion
- **Screen**: Swagger UI → Terminal with worker logs side-by-side
- **Action**:
  1. Execute `POST /auth/register` (e.g. `engineer@demo.com`) & `POST /auth/login` to obtain JWT.
  2. Click **Authorize** at the top of Swagger and paste the token.
  3. Execute `POST /workspaces` (`{"name": "Engineering Knowledge Base"}`).
  4. Execute `POST /workspaces/{id}/documents` with `data/demo_architecture.md`.
- **Narration / Voiceover**:
  > *"Every request is authenticated via JWT with workspace-level RBAC. When a document is uploaded, the HTTP endpoint returns a `202 Accepted` in milliseconds. It delegates chunking and embedding to an asynchronous worker using PostgreSQL `FOR UPDATE SKIP LOCKED` for lock-free concurrency."*
- **Visual Highlight**: Point to worker log in terminal showing: `job_claimed` → `chunking_succeeded` → `ingestion_succeeded (5 chunks)`.

---

### 0:30 – 0:55 | Hybrid Retrieval, RRF & Citation-Grounded Chat
- **Screen**: Swagger UI `POST /workspaces/{id}/chat`
- **Action 1**: Query: `"What retrieval strategy does this system use and why?"`
  - Show JSON response:
    - `answer`: Clear, concise explanation citing `[1]`.
    - `citations`: Extracted source chunks mapped back to `demo_architecture.md`.
    - `retrieval_debug`: Highlighting `vector_candidates: 20`, `keyword_candidates: 20`, `fused_candidates`, `final_chunks: 5`.
- **Narration / Voiceover**:
  > *"Under the hood, we don't just do simple vector search. We run a dual-arm hybrid search combining dense cosine similarity in pgvector and full-text search over tsvector. We fuse rankings using Reciprocal Rank Fusion (RRF) and pass candidates through a Cross-Encoder reranker. The LLM then generates a citation-grounded response with exact chunk attribution."*

---

### 0:55 – 1:15 | Hallucination Guardrails & Negative Query Handling
- **Screen**: Swagger UI `POST /workspaces/{id}/chat`
- **Action 2**: Query an out-of-context question: `"What was the company's Q3 revenue in 2025?"`
  - Show JSON response:
    - `answer`: *"The provided context does not contain information about the company's revenue in 2025."*
    - `groundedness.supported`: `true` (valid refusal detected).
- **Narration / Voiceover**:
  > *"For out-of-context queries, the model explicitly declines to speculate. Our built-in groundedness evaluation layer verifies token overlap across context spans and flags ungrounded claims in real time."*

---

### 1:15 – 1:30 | Observability & Testing (Closing)
- **Screen**: Switch to browser tab `http://localhost:8000/metrics` → Run test suite in terminal (`pytest tests/unit -v`).
- **Action**: Show Prometheus metrics:
  - `rag_retrieval_duration_seconds`
  - `rag_generation_duration_seconds`
  - `http_requests_total`
- **Narration / Voiceover**:
  > *"The platform is observable out-of-the-box with Prometheus metrics for retrieval latency and generation histograms, containerized with Docker Compose, and backed by a comprehensive automated test suite."*

---

## Summary of Exact API Calls for Quick Copy-Paste

### 1. Register User
- **Endpoint**: `POST /auth/register`
- **Body**:
  ```json
  {
    "email": "lead.engineer@company.com",
    "password": "SecurePassword123!",
    "full_name": "Lead Engineer"
  }
  ```

### 2. Login
- **Endpoint**: `POST /auth/login`
- **Body**:
  ```json
  {
    "email": "lead.engineer@company.com",
    "password": "SecurePassword123!"
  }
  ```

### 3. Create Workspace
- **Endpoint**: `POST /workspaces`
- **Header**: `Authorization: Bearer <TOKEN>`
- **Body**:
  ```json
  {
    "name": "Production Architecture Workspace"
  }
  ```

### 4. Upload Document
- **Endpoint**: `POST /workspaces/{workspace_id}/documents`
- **Header**: `Authorization: Bearer <TOKEN>`
- **Form Data**: `file` = select `data/demo_architecture.md`

### 5. Chat Query 1 (Retrieval & Grounding)
- **Endpoint**: `POST /workspaces/{workspace_id}/chat`
- **Header**: `Authorization: Bearer <TOKEN>`
- **Body**:
  ```json
  {
    "query": "What retrieval strategy does this system use?"
  }
  ```

### 6. Chat Query 2 (Negative / Guardrail Validation)
- **Endpoint**: `POST /workspaces/{workspace_id}/chat`
- **Header**: `Authorization: Bearer <TOKEN>`
- **Body**:
  ```json
  {
    "query": "What was the revenue of this company in 2025?"
  }
  ```
