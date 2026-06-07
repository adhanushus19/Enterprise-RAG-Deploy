# Evaluation Framework: Enterprise AI Knowledge Assistant

This document details the evaluation framework implemented to measure the accuracy, factuality, and retrieval efficiency of the RAG platform.

---

## 1. Metrics Definitions

We evaluate the pipeline using two separate sets of criteria: **Information Retrieval (IR) metrics** (how well we find documents) and **LLM Generation metrics** (how well the assistant writes responses).

### A. Information Retrieval Metrics

#### 1. Precision@K
Measures the proportion of retrieved chunks in the top $K$ that are relevant to the query:
$$\text{Precision@K} = \frac{\text{Relevant Chunks} \cap \text{Top K Chunks}}{K}$$
- **Target SLA:** > 0.80 for $K=3$.

#### 2. Recall@K
Measures the proportion of all relevant chunks that are retrieved in the top $K$:
$$\text{Recall@K} = \frac{\text{Relevant Chunks} \cap \text{Top K Chunks}}{\text{Total Relevant Chunks}}$$
- **Target SLA:** > 0.85 for $K=5$.

#### 3. Mean Reciprocal Rank (MRR)
Measures where the first relevant chunk is located in the search results:
$$\text{MRR} = \frac{1}{\text{Rank of first relevant chunk}}$$
If no relevant chunk is found, the Reciprocal Rank is 0.

---

### B. LLM Generation Quality Metrics (RAGAS Equivalents)

#### 1. Faithfulness (Groundedness)
- **Concept:** Measures if the generated answer is strictly based on the retrieved context (no hallucinations).
- **Calculation:** The system extracts all factual claims made in the answer, verifies each claim against the context using an LLM evaluator, and computes:
$$\text{Faithfulness} = \frac{\text{Number of supported claims}}{\text{Total number of claims}}$$
- **Target SLA:** > 0.90 (Zero tolerance for document hallucination).

#### 2. Answer Relevancy
- **Concept:** Measures if the generated answer directly addresses the user's question.
- **Calculation:** Evaluated on a `[0.0 - 1.0]` scale by an LLM prompt that grades the relevance of the answer to the initial query.
- **Target SLA:** > 0.85.

#### 3. Context Precision
- **Concept:** Measures if the retrieved chunks that are most relevant to the query are ranked higher in the context block.
- **Target SLA:** > 0.80.

---

## 2. Metrics Collection & Dashboard

- **Database Storage:** The `evaluation_metrics` table in PostgreSQL records every test query, generated answer, and calculated scores.
- **Streamlit Dashboard:** The `/pages/3_Evaluation.py` page fetches aggregate statistics from the database, displaying Plotly comparison charts against target SLA bars.
- **Interactive Evaluator:** Developers can run ad-hoc evaluations in the Streamlit UI to check current latency, token usages, and quality scores.

---

## 3. Engineering Tradeoffs & Scalability
* **Mock Metrics in CI:** Offline tests use mocked LLM responses to evaluate parser/database routing without calling external APIs.
* **LLM Call Overhead:** Running Faithfulness and Relevancy evaluations during live inference adds around 1.5 seconds of latency. Consequently, we recommend running detailed LLM evaluations as a **background task** (async logging) or via batch execution scripts (`scripts/evaluate_pipeline.py`) during staging deployments.

---

## 4. Failure Scenarios & Future Improvements
- **Rate Limits:** The evaluation script implements delay steps between calls to prevent hitting OpenAI RPM (Requests Per Minute) limits.
- **Future Improvements:** Integrate automated continuous regression testing, where the CI/CD pipeline triggers the evaluation script, blocking merges if average faithfulness drops below 0.85.
