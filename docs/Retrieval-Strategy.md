# Retrieval Strategy: Enterprise AI Knowledge Assistant

This document details the multi-stage retrieval pipeline designed to ensure maximum precision and recall.

---

## 1. Retrieval Pipeline Stages

```
[User Query] ──> [Query Rewriter Agent] ──> [Metadata Filters Applied]
                                                    │
                                                    ▼
                     ┌──────────────────────────────┴──────────────────────────────┐
                     ▼                                                             ▼
         [Dense Vector Retrieval] (Qdrant)                              [Sparse BM25 Retrieval] (PostgreSQL)
                     │                                                             │
                     └──────────────────────────────┬──────────────────────────────┘
                                                    ▼
                                    [Reciprocal Rank Fusion (RRF)]
                                                    │
                                                    ▼
                                     [LLM Reranker Agent] (Top K)
                                                    │
                                                    ▼
                                        [Verification Agent] ──(Failed)──> [Query Rewrite Loop]
                                                    │
                                                 (Passed)
                                                    │
                                                    ▼
                                         [Citation Generation]
                                                    │
                                                    ▼
                                           [Answer Generation]
```

### Stage 1: Query Rewriting
- **Mechanism:** The `QueryRewriterAgent` resolves ambiguity, expands synonyms, and strips conversational noise using `gpt-4o-mini` before the query hits the index.
- **Why:** Corporate users often write vague queries (e.g. "What did they change in it?"). The rewriter tracks the last 5 chat messages to inject names and definitions.

### Stage 2: Hybrid Retrieval (Dense + Sparse)
- **Dense:** Vector search against Qdrant (`text-embedding-3-small` embeddings) captures semantic relationships.
- **Sparse:** A python-side `BM25Okapi` index runs on the candidates matching the metadata scope to secure exact keyword matches (e.g. alphanumeric product codes, names, section numbers).

### Stage 3: Metadata Filtering
- **Mechanism:** Applied at the database layer (SQL query) and the vector index layer (Qdrant filter payload) before retrieval occurs.
- **Why:** Restricts search scopes to relevant files (e.g. only PPTX slides, or files tagged `finance`).

### Stage 4: Reranking
- **Mechanism:** The retrieved candidates are processed by the `RerankerAgent`. It scores each chunk on a `[0.0 - 10.0]` scale. Chunks scoring below `2.0` are pruned, and the remainder are sorted descending.
- **Why:** Standard vector scores reflect similarity, not answerability. Reranking ensures the most answerable text is placed at the top of the context block.

### Stage 5: Context Compression
- **Mechanism:** We restrict the final context injected into the answer generator to the top 5 reranked chunks. This limits prompt window expansion, mitigates "lost in the middle" phenomena, and saves token costs.

### Stage 6: Citation Generation & Pruning
- **Mechanism:** Each chunk in the context is mapped to a sequential citation ID `[1]`, `[2]`. The Answer Agent places these markers after statements it generates. A post-processing step in the `CitationAgent` matches these numbers to the text, stripping citations that were not referenced.

### Stage 7: Answer Generation
- **Mechanism:** Synthesized by the Answer Agent, which is strictly instructed to deny knowledge if the verified context does not contain the answer.

---

## 2. Engineering Tradeoffs & Scalability
- **RRF Const K:** The RRF constant $k$ is set to 60. Increasing $k$ decreases the impact of top-ranked items, while decreasing $k$ prioritizes top hits. A value of 60 balances dense and sparse systems.
- **In-Memory BM25:** Building the BM25 index dynamically on database records is efficient when scoped with metadata filters (< 10,000 chunks). If the database grows to millions of files, this should be offloaded to PostgreSQL's native `pg_trgm` or a separate ElasticSearch node.

---

## 3. Failure Scenarios & Future Improvements
- **Zero Hits:** If hybrid search yields zero hits, the Verification Agent fails immediately, triggering a query rewrite. If that fails, the pipeline returns a clean notification prompting the user to upload missing documents.
- **Future Improvements:** Implement parent-child chunking where small chunks (e.g., 100 tokens) are indexed for retrieval, but their parent contexts (e.g., 1000 tokens) are fed to the generation step, improving retrieval precision.
