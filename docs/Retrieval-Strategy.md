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

### Stage 1: Query Expansion & Rewriting
The `QueryRewriterAgent` contextually expands the user query using current and historical chat logs via `gpt-4o-mini`. If a prior verification step fails, it integrates feedback (e.g., "Missing details about Q2") to generate refined terms.

### Stage 2: Dense Semantic Search (Qdrant)
- **Embedding Model:** `text-embedding-3-small` (1536 dimensions).
- **Distance Metric:** Cosine similarity.
- **Goal:** Capture conceptual similarities, synonyms, and multi-lingual equivalents.

### Stage 3: Sparse Keyword Search (BM25)
- **Algorithm:** `BM25Okapi` running on python-side tokenized text.
- **Tokenization:** Query and document contents are lowercased and split into word tokens.
- **Goal:** Retrieve exact names, dates, serial keys, and specific jargon that dense vector models might dilate or rank low.

### Stage 4: Metadata Filtering
Applied dynamically prior to search:
- **Qdrant:** Binds filter conditions (`MatchValue` for strings, `MatchAny` for list elements, tags) directly in the vector search body.
- **SQL:** Performs SQL joins on target files, filtering metadata values (e.g., `department = 'HR'`).

### Stage 5: Reciprocal Rank Fusion (RRF)
RRF combines rank lists from dense and sparse queries to create a unified priority score. The RRF score of a document chunk $d$ is:

$$RRF(d) = \sum_{m \in M} \frac{1}{k + r_m(d)}$$

Where:
- $M$ is the set of search engines (dense & sparse).
- $r_m(d)$ is the rank position of document $d$ in engine $m$ (1-indexed).
- $k$ is a constant hyperparameter (default: **60**), which acts as a stabilizer to prevent low ranks from excessively penalizing matches.

### Stage 6: LLM Reranking
- Chunks are evaluated using a strict relevance prompt. The LLM rates each chunk's utility to answer the query on a `[0.0 - 10.0]` scale.
- Chunks scoring `< 2.0` are discarded.
- Only the top 5 highest-ranked chunks are kept.

### Stage 7: Citation & Generation
Each chunk receives a citation identifier. The `CitationAgent` matches inline references post-synthesis, pruning unused citation markers from the final text payload.

---

## 2. Engineering Tradeoffs & Scale

- **Dynamic BM25 vs. Native TSVector:** Building the BM25 index on the fly is lightweight for isolated scopes. For massive corporate vaults (>100,000 files), this should be shifted to PostgreSQL native full-text indexing or an external Elasticsearch instance.
- **RRF Const:** $k=60$ is the industry standard. Increasing $k$ decreases the impact of top-ranked items, while decreasing $k$ prioritizes top hits.
