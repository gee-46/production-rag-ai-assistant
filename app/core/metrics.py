from prometheus_client import Counter, Histogram

HTTP_REQUESTS_TOTAL = Counter(
    "http_requests_total", "Total HTTP requests", ["method", "path", "status_code"]
)
HTTP_REQUEST_DURATION_SECONDS = Histogram(
    "http_request_duration_seconds", "HTTP request latency", ["method", "path"]
)

RAG_RETRIEVAL_DURATION_SECONDS = Histogram(
    "rag_retrieval_duration_seconds", "Time spent in hybrid retrieval + reranking"
)
RAG_GENERATION_DURATION_SECONDS = Histogram(
    "rag_generation_duration_seconds", "Time spent waiting on the LLM provider"
)
RAG_UNGROUNDED_ANSWERS_TOTAL = Counter(
    "rag_ungrounded_answers_total", "Answers flagged as containing unsupported claims"
)
INGESTION_JOBS_TOTAL = Counter(
    "ingestion_jobs_total", "Ingestion jobs processed by outcome", ["outcome"]
)
