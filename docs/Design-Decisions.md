# Design Decisions: Enterprise AI Knowledge Assistant

This document outlines the core engineering decisions made during the design and implementation of the RAG platform.

---

## 1. Document Chunking Strategy

### Business Problem
Naive token-based text splitting breaks sentences, splitting numbers, context keys, or spreadsheet cell mappings across vector boundaries, leading to corrupted context and invalid answers.

### Design Rationale
We implemented **Format-Aware Page/Row Chunking**:
- **PDF/PPTX:** Segment content by page or slide number to maintain page-level spatial reference (essential for visual citation mapping).
- **DOCX:** Group paragraphs in clusters of 4 to approximate pages while maintaining contextual flow.
- **XLSX:** Group rows in batches of 10, formatting them as key-value pairs (e.g. `ColName=Value`), retaining sheet and row references.

### Engineering Tradeoffs
* *Tradeoff:* Page-based chunking can result in chunks of variable sizes (some pages have few words, others are dense), which slightly increases variance in embedding quality, but it dramatically improves citation accuracy and user trust compared to arbitrary 512-token chunks.

---

## 2. Hybrid Retrieval Merge Strategy (RRF vs. Score Weighting)

### Business Problem
Combining dense semantic scores (usually Cosine similarity bounded between `[0, 1]`) and sparse keyword scores (BM25 scores which are unbound `[0, infinity]`) is mathematically challenging. Simple weighted summation requires continuous threshold calibration and breaks down as document sizes change.

### Design Rationale
We selected **Reciprocal Rank Fusion (RRF)**:
$$\text{RRF\_Score}(d) = \sum_{m \in M} \frac{1}{k + r_m(d)}$$
RRF combines rankings from independent systems without needing to normalize their raw scores. It only cares about the relative order (rank) of the candidates in dense and sparse results.

### Engineering Tradeoffs
* *Tradeoff:* RRF discards the absolute confidence distance (e.g., a hit scoring 0.99 cosine is treated similarly to 0.91 if both are ranked #1 in their respective lists). However, RRF is highly robust, requires zero calibration, and consistently beats score-weighting in enterprise benchmarks.

---

## 3. LangGraph Multi-Agent Orchestration

### Business Problem
Linear RAG chains cannot recover if the retrieval step fetches irrelevant documents. The LLM either hallucinates or outputs a generic "I don't know" response.

### Design Rationale
We chose **LangGraph State Machine Orchestration** to support feedback loops:
- The **Verification Agent** checks the relevance of retrieved facts.
- If it fails, the state machine routes the flow back to the **Query Rewriter Agent**, appending the verifier's feedback to rewrite the query and perform a secondary retrieval before generating a response.

### Engineering Tradeoffs
* *Tradeoff:* Secondary loops double the latency and LLM token cost for complex/ambiguous queries. To limit costs, we capped the loops to a maximum of 2, reverting to a graceful denial-of-service response if verification fails twice.

---

## 4. Failure Scenarios & Scalability
- **Database Scalability:** PostgreSQL metadata tables use index indexes on `department` and `tags` columns, which prevents full-table sequential scans when handling queries.
- **Rate-Limiting:** Implemented custom IP-based token bucket rate-limiting middleware to shield backend LLM resources from denial-of-service attacks.
- **Future Improvements:** Integrate a local semantic cache (e.g., Redis or GPTCache) to intercept identical queries before passing them to the LangGraph executor, reducing LLM costs by up to 30%.
