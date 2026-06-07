# Enterprise AI Knowledge Assistant

[![Python Version](https://img.shields.b3g.io/badge/Python-3.12-blue.svg)](https://python.org)
[![FastAPI](https://img.shields.b3g.io/badge/FastAPI-0.111-green.svg)](https://fastapi.tiangolo.com)
[![Qdrant](https://img.shields.b3g.io/badge/Qdrant-v1.9.5-red.svg)](https://qdrant.tech)
[![License: MIT](https://img.shields.b3g.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Build Status](https://img.shields.b3g.io/badge/Build-Passing-brightgreen.svg)]()
[![Coverage](https://img.shields.b3g.io/badge/Coverage-%3E80%25-success.svg)]()

The **Enterprise AI Knowledge Assistant** is a production-grade Retrieval-Augmented Generation (RAG) platform. It parses corporate documents (PDF, DOCX, PPTX, XLSX), extracts rich metadata using structured LLM classification, indexes vector representations in Qdrant, and orchestrates query retrieval using a multi-agent LangGraph workflow. It includes built-in SLA metric tracking (RAGAS) and a dynamic Streamlit frontend.

---

## 1. Problem Statement
Within large-scale enterprises, critical knowledge is scattered across different unstructured and structured formats (policies, presentations, quarterly financial sheets). Naive RAG systems suffer from three primary flaws:
1. **Low Precision:** Irrelevant text chunks clutter LLM prompt contexts, degrading generation quality.
2. **Hallucinations:** Generative models make claims not present in source files.
3. **Weak Auditability:** Users cannot verify which specific document, slide, page, or spreadsheet row supported a claim.

This platform resolves these problems by using a structured multi-agent verification system, custom RRF hybrid search, and precise page/row level citation extraction.

---

## 2. Architecture Diagram

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

---

## 3. Tech Stack
- **Backend:** Python 3.12, FastAPI, SQLAlchemy
- **Vector Database:** Qdrant
- **Relational Database:** PostgreSQL
- **Orchestration:** LangGraph, LangChain
- **Models:** OpenAI GPT-4o-Mini, OpenAI text-embedding-3-small
- **UI:** Streamlit, Plotly
- **Instrumentation:** Prometheus, Grafana
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
   python -m venv venv
   source venv/bin/activate # Windows: .\venv\Scripts\activate
   pip install -r requirements.txt
   uvicorn app.main:app --reload
   ```
3. **Frontend:**
   ```bash
   cd ../frontend
   python -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   streamlit run app.py
   ```

### Running With Docker Compose
Launch the entire platform (databases, backend, frontend, Prometheus, Grafana) with a single command:
```bash
docker-compose up --build
```
Access points:
- **Web UI:** `http://localhost:8501`
- **Backend API Docs:** `http://localhost:8000/docs`
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

---

## 6. Screenshots Section
*(Run locally or build Docker containers to view the user interface. Visual previews are logged in user documentation.)*
1. **Interactive Assistant Chat:** Modern conversational thread showing highlighted inline citations.
2. **Document Library manager:** File uploader table showing ingestion pipeline states (`processing`, `completed`).
3. **Comparison Matrix:** Markdown layout detailing policy variations and update logs side-by-side.
4. **SLA Dashboard:** Plotly gauge charts detailing average Faithfulness and Precision scores.

---

## 7. CI/CD Pipeline
Continuous Integration is managed via **GitHub Actions** (`.github/workflows/ci.yml`).
On every push and pull request, the CI environment:
- Sets up Python 3.12.
- Installs PostgreSQL and system dependencies.
- Runs the test suite with code coverage.
- Blocks execution if test coverage falls below **80%**.

---

## 8. Future Enhancements
- **Redis Cache Integration:** Cache common semantic queries to reduce API latency.
- **Local Reranker Models:** Replace OpenAI calls in the reranker agent with a locally running HuggingFace Cross-Encoder.
- **Audit Logs:** Track user identities, feedback rating, and system utilization patterns.
