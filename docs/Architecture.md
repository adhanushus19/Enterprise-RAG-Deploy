# System Architecture: Enterprise AI Knowledge Assistant

This document details the architectural blueprint of the **Enterprise AI Knowledge Assistant**, a production-grade multi-agent RAG platform.

## 1. Business Problem
Enterprises struggle with information silos across fragmented document formats (PDFs, Word files, presentations, and spreadsheets). Standard keyword searches fail to capture semantic intent, while naive RAG systems suffer from hallucinations, lack of source citations, and irrelevant context aggregation, leading to distrust in AI-assisted decisions.

## 2. Design Rationale
Our architecture adopts a decoupled, event-driven service topology combining:
1. **FastAPI Services** for synchronous document APIs, conversational generation, and metadata lookups.
2. **PostgreSQL** as the single source of truth for file inventory, parsing states, structured metadata, and SLA quality logs.
3. **Qdrant** as a high-performance, filterable vector search engine.
4. **LangGraph State Machine** for query expansion, iterative verification loops, and citation formatting.

```mermaid
graph TD
    User([User / Web UI]) -->|1. File Upload| API[FastAPI Gateway]
    API -->|2. Save File / DB Record| DB[(PostgreSQL)]
    API -->|3. Trigger Ingestion| Workers[Async Worker]
    Workers -->|4. Parse Content| Parser[Document Parsers]
    Workers -->|5. LLM Metadata extraction| LLM[OpenAI API]
    Workers -->|6. Save Chunks| DB
    Workers -->|7. Embed & Upsert| VectorDB[(Qdrant Vector DB)]
    
    User -->|8. Run Query| API
    API -->|9. Invoke Graph| Graph[LangGraph Workflow]
    Graph -->|10. Query Rewrite| LLM
    Graph -->|11. Dense Vector Search| VectorDB
    Graph -->|12. Sparse BM25 Search| DB
    Graph -->|13. Verification & Generation| LLM
    Graph -->|14. Filter Citations| Citations[Citation Agent]
    Citations -->|15. Log metrics| DB
    Citations -->|16. Stream Response| User
```

## 3. Multi-Agent Sequence Flow
The graph runs an iterative loop to ensure factuality before generation:

```mermaid
sequenceDiagram
    autonumber
    participant Client as API Router
    participant Graph as LangGraph StateMachine
    participant Rewriter as Query Rewriter
    participant Retriever as Hybrid Retriever
    participant Reranker as LLM Reranker
    participant Verifier as Verification Agent
    participant Citations as Citation Agent
    participant Generator as Answer Agent

    Client->>Graph: invoke(query, filters)
    Graph->>Rewriter: rewrite_query(query)
    Rewriter-->>Graph: rewritten_query
    Graph->>Retriever: retrieve(rewritten_query)
    Retriever-->>Graph: dense_hits + sparse_hits
    Graph->>Reranker: rerank(hits)
    Reranker-->>Graph: top_k_chunks
    Graph->>Verifier: verify(query, top_k_chunks)
    alt Verification Failed (loop < 2)
        Verifier-->>Graph: passed=False, feedback="Missing X"
        Graph->>Rewriter: rewrite_query(query + feedback)
        Note over Graph, Retriever: Search is repeated with refined terms
    else Verification Passed or Max Loops Exceeded
        Verifier-->>Graph: passed=True/False
    end
    Graph->>Citations: generate_citations(top_k_chunks)
    Citations-->>Graph: citations_list
    Graph->>Generator: synthesize_answer(context, citations)
    Generator-->>Graph: final_answer
    Graph-->>Client: answer + filtered_citations
```

## 4. Engineering Tradeoffs
* **LangGraph vs. Sequential Chains:** LangGraph allows backward loops (e.g., repeating search after query rewriting if verification fails). This increases latency for failed searches but guarantees high precision.
* **SQLite/Postgres Dual Setup:** We use SQLAlchemy with PostgreSQL for production and in-memory SQLite for rapid, isolated unit testing, bypassing environment setup bottlenecks during local development.

## 5. Scalability Considerations
* **Horizontal Scaling:** FastAPI and Streamlit are stateless and can be scaled horizontally using Kubernetes HPA.
* **Vector Indexing:** Qdrant collections use partition keys matching `department` to restrict search spaces to specific shards, avoiding full-index scans.

## 6. Failure Scenarios
* **Qdrant Timeout:** If Qdrant is unreachable, the system falls back fully to Postgres-based sparse keyword searches (BM25) to maintain platform availability.
* **LLM Rate Limits:** LangGraph nodes implement exponential backoff retry mechanisms to handle HTTP 429 exceptions gracefully.

## 7. Future Improvements
* **Async Task Queue:** Transition from FastAPI BackgroundTasks to Celery/RabbitMQ to manage high-volume concurrent PDF parsing pipelines.
* **Self-hosted Embeddings:** Deploy `bge-small-en-v1.5` on Triton Inference Server to eliminate dependency on OpenAI embedding network requests.
