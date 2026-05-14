# 🧠 Production-Grade RAG AI System

> Building a Retrieval-Augmented Generation (RAG) system from scratch — focusing on **system design, control, and reliability**

---

## 🚀 Overview

This project implements a **modular RAG pipeline** that enhances LLM responses using **external knowledge retrieval**.

Instead of relying purely on pretrained knowledge, the system:

- Retrieves relevant information from a document store
- Grounds responses using retrieved context
- Controls LLM output to reduce hallucination
- Exposes the pipeline through a FastAPI backend
- Supports dynamic document uploads without restarting the server
- Persists vector embeddings across server restarts

---

## 🎯 Objective

To build an **industry-relevant AI system** that demonstrates:

- End-to-end RAG architecture  
- Clear separation of retrieval vs generation  
- Controlled LLM behavior through prompt engineering  
- Local + pluggable LLM backend  
- API-based AI system deployment  
- Dynamic knowledge ingestion pipelines  
- Persistent vector database architecture  

---

## 🧠 System Architecture

```text
Documents → Chunking → Embeddings → Vector Store → Retrieval → Context → LLM → Answer
```

### Detailed Flow

```text
Raw Documents / Uploaded Files
              ↓
Chunking (overlap-based)
              ↓
Embeddings (SentenceTransformers)
              ↓
FAISS Vector Store
              ↓
Persistent Storage
              ↓
User Query
              ↓
Query Embedding
              ↓
Top-K Retrieval
              ↓
Context Builder (Prompt Engineering)
              ↓
LLM (Ollama - LLaMA 3)
              ↓
Grounded Answer
              ↓
FastAPI JSON Response
```

---

## ⚙️ Tech Stack

| Layer              | Technology           |
| ------------------ | -------------------- |
| Backend API        | FastAPI              |
| Backend Logic      | Python               |
| Embeddings         | SentenceTransformers |
| Vector Search      | FAISS                |
| LLM Backend        | Ollama (LLaMA 3)     |
| Optional LLM       | OpenAI API           |
| File Upload        | python-multipart     |
| DOCX Parsing       | python-docx          |
| Data Handling      | NumPy                |

---

## 🔥 Key Features

### ✅ Semantic Retrieval

- Converts text into dense vector embeddings
- Enables meaning-based search instead of keyword matching

---

### ✅ FAISS Vector Search

- Efficient similarity search
- Retrieves top-k relevant chunks

---

### ✅ Document Chunking

- Overlapping chunk strategy
- Preserves context across splits
- Improves retrieval accuracy

---

### ✅ Context Engineering

- Structured prompt design
- Forces model to answer only from retrieved context
- Reduces hallucination

---

### ✅ Structured Output Control

- Enforces bullet-point responses
- Removes unnecessary verbosity
- Produces concise and readable outputs

---

### ✅ Local LLM Integration

- Uses Ollama (LLaMA 3)
- No API dependency
- Fully offline inference capability

---

### ✅ FastAPI Backend Integration

- Exposes RAG pipeline through REST API
- Supports query-based interaction using `/query`
- Auto-generated Swagger documentation (`/docs`)
- Returns structured JSON responses

---

### ✅ Dynamic Document Upload (Day 8)

- Upload `.txt` and `.docx` files dynamically
- Automatically chunks uploaded content
- Generates embeddings in real-time
- Updates FAISS vector store live
- Makes uploaded knowledge immediately searchable

---

### ✅ Persistent Vector Storage (Day 9)

- Saves FAISS vector index locally
- Restores embeddings automatically on server restart
- Preserves uploaded knowledge across sessions
- Enables stateful retrieval architecture

---

## 🔍 Example Workflow

```python
Query: "What is RAG?"

→ Embed query
→ Retrieve relevant chunks
→ Build structured prompt
→ Generate grounded answer
→ Return API response
```

---

## 🌐 API Endpoints

### GET `/`

Health check endpoint.

#### Response

```json
{
  "message": "Production RAG API is running"
}
```

---

### POST `/query`

Query the RAG pipeline.

#### Request

```json
{
  "query": "What is RAG?"
}
```

#### Response

```json
{
  "query": "What is RAG?",
  "answer": "• Retrieves relevant documents\n• Uses retrieved context for grounded generation",
  "retrieved_chunks": [...]
}
```

---

### POST `/upload`

Upload `.txt` or `.docx` documents dynamically.

#### Response

```json
{
  "filename": "document.docx",
  "chunks_added": 5,
  "message": "Document uploaded successfully"
}
```

---

## 🧪 Current Capabilities

- Context-grounded answering
- Reduced hallucination
- Structured and controlled outputs
- Local LLM inference
- API-based interaction
- Dynamic document ingestion
- Persistent vector database
- Live vector store updates
- Modular and extensible architecture

---

## ⚠️ Current Limitations

- No reranking yet
- Basic chunking strategy
- No authentication layer
- No evaluation metrics
- Supports only `.txt` and `.docx` uploads currently
- No metadata-based filtering yet

---

## 🚧 Roadmap

- [ ] Semantic / recursive chunking
- [ ] Cross-encoder reranking
- [x] Persistent FAISS storage
- [ ] PDF support
- [ ] Metadata filtering
- [ ] Evaluation metrics (precision@k, latency)
- [ ] Docker deployment
- [ ] Cloud deployment

---

## 📂 Project Structure

```bash
rag-system/
│
├── app/
│   ├── main.py
│   │
│   └── services/
│       ├── embeddings.py
│       ├── loader.py
│       ├── vector_store.py
│       ├── chunker.py
│       ├── context_builder.py
│       └── llm.py
│
├── data/
│   └── raw_docs/
│
├── storage/
│   ├── faiss_index.bin
│   └── texts.pkl
│
├── test_pipeline.py
├── requirements.txt
└── README.md
```

---

## 🧠 Engineering Highlights

- Built without LangChain to understand system internals
- Explicit separation of retrieval vs generation
- Focused on LLM reliability and retrieval quality
- API-first backend architecture
- Dynamic runtime ingestion support
- Persistent vector database design
- Designed for extensibility and production transition

---

## 📌 Status

🚧 Actively under development  
📅 Daily iterative improvements and feature additions

---

## 🤝 Connect

- GitHub: https://github.com/gee-46
- LinkedIn: https://www.linkedin.com/in/gautam-n-chipkar-348b092a5/

---

## ⭐ Support

If you find this useful, consider starring the repo.
