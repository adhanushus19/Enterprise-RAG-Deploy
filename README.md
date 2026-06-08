# Enterprise AI Knowledge Assistant

[![Python Version](https://img.shields.b3g.io/badge/Python-3.12%20%7C%203.13-blue.svg)](https://python.org)
[![FastAPI](https://img.shields.b3g.io/badge/FastAPI-0.111-green.svg)](https://fastapi.tiangolo.com)
[![Qdrant](https://img.shields.b3g.io/badge/Qdrant-v1.9.5-red.svg)](https://qdrant.tech)
[![License: MIT](https://img.shields.b3g.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Build Status](https://github.com/adhanushus19/Enterprise-RAG-Deploy/actions/workflows/ci.yml/badge.svg)](https://github.com/adhanushus19/Enterprise-RAG-Deploy/actions)
[![Coverage](https://img.shields.b3g.io/badge/Coverage-83%25-brightgreen.svg)](https://github.com/adhanushus19/Enterprise-RAG-Deploy/actions)

The **Enterprise AI Knowledge Assistant** is a production-grade Retrieval-Augmented Generation (RAG) platform. It parses corporate documents (PDF, DOCX, PPTX, XLSX), extracts rich metadata using structured LLM classification, indexes vector representations in Qdrant, and orchestrates query retrieval using a multi-agent LangGraph workflow. It includes built-in SLA metric tracking (RAGAS) and a dynamic Streamlit frontend.

---

## 1. Problem Statement & Business Use Case

In large enterprises, critical information is siloed across diverse formats (PDF policies, Word contracts, PowerPoint presentations, Excel financial sheets). Standard search engines fail to capture semantic relationships, while basic RAG pipelines suffer from:
1. **Low Precision:** Irrelevant text chunks pollute the LLM context, degrading generation quality.
2. **Hallucinations:** Generative models make claims unsubstantiated by source documents.
3. **Auditability Gaps:** Lack of exact source citations makes validation tedious.

This platform solves these problems using:
- **Multi-Agent Verification:** Refines search terms iteratively if context is insufficient.
- **Hybrid Search (Dense + Sparse):** Integrates semantic Qdrant vectors with exact BM25 keyword matching.
- **Precise Citation Mapping:** Pinpoints references down to page, slide, sheet name, or spreadsheet row.

---

## 2. Architecture & Orchestration Flow

### Component Topology
```mermaid
graph TD
    User([User Streamlit UI]) -->|Upload Files| FastAPI[FastAPI Backend Gateway]
    FastAPI -->|Background Job| Parse[Parsers: PDF, Docx, Slides, Excel]
    Parse -->|Metadata extraction| LLM[OpenAI gpt-4o-mini]
    Parse -->|Store file & chunks| DB[(PostgreSQL)]
    Parse -->|Embed text & upsert| Qdrant[(Qdrant Vector DB)]
    
    User -->|Ask Question| FastAPI
    FastAPI -->|Start Graph| LangGraph[LangGraph State Machine]
    LangGraph -->|Rewrite Query| Rewriter[Query Rewriter Agent]
    Rewriter -->|Search Vector & SQL| Retriever[Hybrid RRF Retriever]
    Retriever -->|Assess Relevance| Reranker[LLM Reranker Agent]
    Reranker -->|Verify Sufficiency| Verifier{Verification Agent}
    
    Verifier -- Failed (Loop < 2) --> Rewriter
    Verifier -- Passed --> Citation[Citation Agent]
    Citation --> Answer[Answer Agent]
    Answer --> User
```

### LangGraph Iterative Verification
The agentic retrieval loop performs automated quality checks before generating answers:
1. **Query Rewriter**: Contextualizes user queries using chat history.
2. **Retriever**: Performs hybrid dense-sparse search scoped by metadata filters.
3. **Reranker**: Evaluates chunk answerability on a scale from 0.0 to 10.0.
4. **Verifier**: Determines if the top-ranked context is sufficient to answer the query. If insufficient, it provides feedback and routes back to the rewriter for a second search loop.
5. **Citation Agent**: Maps context snippets to inline citation markers.
6. **Answer Agent**: Synthesizes the final response or rejects the query if information is missing.

---

## 3. Tech Stack

- **Backend:** Python 3.12 / 3.13, FastAPI, SQLAlchemy
- **Vector Database:** Qdrant (semantic vector indexing)
- **Relational Database:** PostgreSQL (structured metadata & transactional logs)
- **Orchestration:** LangGraph, LangChain
- **Models:** OpenAI `gpt-4o-mini`, `text-embedding-3-small`
- **UI:** Streamlit, Plotly
- **Instrumentation:** Prometheus, Grafana
- **Security:** In-memory Rate Limiting (expandable to Redis), Path Injection Sanitation, Non-Root Container Execution
- **Testing:** Pytest, Pytest-cov

---

## 4. Installation & Quickstart

### Environment Variables
Configure the following parameters in a `.env` file at the root:
```env
OPENAI_API_KEY=your-api-key-here
DATABASE_URL=postgresql://postgres:postgrespassword@localhost:5432/knowledge_assistant
QDRANT_HOST=localhost
QDRANT_PORT=6333
API_KEY=enterprise-secret-key-123
```

### Running Locally (Virtual Environments)
1. **Infrastructure:** Launch PostgreSQL and Qdrant in Docker:
   ```bash
   docker-compose up -d db qdrant prometheus grafana
   ```
2. **Backend:**
   ```bash
   cd backend
   python -m venv .venv
   source .venv/bin/activate # Windows: .venv\Scripts\activate
   pip install -r requirements.txt
   uvicorn app.main:app --reload
   ```
3. **Frontend:**
   ```bash
   cd ../frontend
   python -m venv .venv
   source .venv/bin/activate # Windows: .venv\Scripts\activate
   pip install -r requirements.txt
   streamlit run app.py
   ```

### Running With Docker Compose
Launch the entire platform (databases, backend, frontend, Prometheus, Grafana) with a single command:
```bash
docker-compose up --build
```
Access endpoints:
- **Web UI:** `http://localhost:8501`
- **Backend API Docs:** `http://localhost:8000/docs`
- **Health Check Probe:** `http://localhost:8000/health`
- **Prometheus:** `http://localhost:9090`
- **Grafana:** `http://localhost:3000` (User: `admin` | Pass: `admin`)

---

## 5. API Usage Examples

### 1. Ingest a Document
```bash
curl -X POST "http://localhost:8000/api/v1/documents/upload" \
  -H "X-API-Key: enterprise-secret-key-123" \
  -F "file=@/path/to/travel_policy.pdf"
```

### 2. Query the RAG Pipeline
```bash
curl -X POST "http://localhost:8000/api/v1/query" \
  -H "X-API-Key: enterprise-secret-key-123" \
  -H "Content-Type: application/json" \
  -d '{"query": "What is the travel meal limit?", "filters": {"doc_type": "pdf"}}'
```

### 3. Check Service Health
```bash
curl -X GET "http://localhost:8000/health"
```

---

## 6. Target Developer Profiles
This repository demonstrates technical competency for:
- **AI/GenAI Engineer:** Building agentic loops, hybrid retrieval, and evaluating grounding metrics.
- **ML/Applied AI Engineer:** Implementing structured model outputs, metadata extraction, and rerankers.
- **DevOps/MLESs Engineer:** Non-root Docker packaging, Prometheus logging, and Kubernetes readiness probes.

---

## 7. Future Roadmap
- **Distributed Rate Limiting:** Transition from in-memory token bucket to Redis rate-limiting.
- **Local Rerankers:** Self-host HuggingFace Cross-Encoder models to remove external dependency latency.
- **Row-Level Security:** Enforce user authorization tags on Qdrant vector payloads.
