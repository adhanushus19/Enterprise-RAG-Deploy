# API Documentation: Enterprise AI Knowledge Assistant

This document details the REST API endpoints provided by the FastAPI backend service.

---

## 1. Global Headers & Authentication

All API endpoints (except `/metrics` and `/health`) require the following header for authentication:

```http
X-API-Key: enterprise-secret-key-123
```

If the header is missing, the server returns `401 Unauthorized`.

---

## 2. API Endpoints Reference

### 1. Ingest / Upload Document
- **Endpoint:** `/api/v1/documents/upload`
- **Method:** `POST`
- **Content-Type:** `multipart/form-data`
- **Request Parameters:**
  - `file`: Binary file upload (permitted: `.pdf`, `.docx`, `.pptx`, `.xlsx`)
- **Response Model (200 OK):**
  ```json
  {
    "id": "7ca64731-0df8-43e5-8f64-9b5cf44e1e3e",
    "filename": "q2_financials.xlsx",
    "file_path": "uploads/171779929_q2_financials.xlsx",
    "author": null,
    "department": null,
    "creation_date": null,
    "tags": [],
    "doc_type": "xlsx",
    "status": "processing",
    "created_at": "2026-06-07T22:31:00Z"
  }
  ```
- **Error Codes:**
  - `400 Bad Request`: Unsupported file type.
  - `401 Unauthorized`: Missing or invalid API key.

---

### 2. List Documents
- **Endpoint:** `/api/v1/documents`
- **Method:** `GET`
- **Response Model (200 OK):**
  ```json
  [
    {
      "id": "7ca64731-0df8-43e5-8f64-9b5cf44e1e3e",
      "filename": "q2_financials.xlsx",
      "file_path": "uploads/171779929_q2_financials.xlsx",
      "author": "Finance Dept",
      "department": "Finance",
      "creation_date": "2026-05-15T00:00:00Z",
      "tags": ["xlsx", "quarterly", "financials"],
      "doc_type": "xlsx",
      "status": "completed",
      "created_at": "2026-06-07T22:31:00Z"
    }
  ]
  ```

---

### 3. Delete Document
- **Endpoint:** `/api/v1/documents/{document_id}`
- **Method:** `DELETE`
- **Response Model (200 OK):**
  ```json
  {
    "message": "Document successfully deleted."
  }
  ```
- **Error Codes:**
  - `404 Not Found`: Document ID does not exist.

---

### 4. Search Chunks (Hybrid Search)
- **Endpoint:** `/api/v1/search`
- **Method:** `POST`
- **Request Body (JSON):**
  ```json
  {
    "query": "daily travel allowance limit",
    "limit": 3,
    "filters": {
      "department": "HR"
    }
  }
  ```
- **Response Model (200 OK):**
  ```json
  [
    {
      "document_id": "8da85721-a3f2-411a-9864-1a3bcf4402a4",
      "filename": "travel_policy.pdf",
      "page_number": 3,
      "content": "Employees are permitted a maximum of $75 per day for meals during business travel.",
      "author": "HR Division",
      "department": "HR",
      "doc_type": "pdf",
      "tags": ["policy", "travel", "expenses"],
      "score": 0.892,
      "rrf_score": 0.033
    }
  ]
  ```

---

### 5. Multi-Agent RAG Query
- **Endpoint:** `/api/v1/query`
- **Method:** `POST`
- **Request Body (JSON):**
  ```json
  {
    "query": "What is the travel meal limit?",
    "filters": {
      "doc_type": "pdf"
    },
    "chat_history": [
      {"role": "user", "content": "Hello"},
      {"role": "assistant", "content": "Hello, how can I assist you today?"}
    ]
  }
  ```
- **Response Model (200 OK):**
  ```json
  {
    "query": "What is the travel meal limit?",
    "answer": "The daily meal expense limit during business travel is $75 [1].",
    "citations": [
      {
        "id": 1,
        "filename": "travel_policy.pdf",
        "page_number": 3,
        "author": "HR Division",
        "department": "HR",
        "snippet": "Employees are permitted a maximum of $75 per day for meals during business travel."
      }
    ]
  }
  ```

---

### 6. Compare Documents
- **Endpoint:** `/api/v1/compare`
- **Method:** `POST`
- **Request Body (JSON):**
  ```json
  {
    "document_ids": [
      "8da85721-a3f2-411a-9864-1a3bcf4402a4",
      "9ab23456-11f2-51a2-99a4-1a2bcf4401ba"
    ],
    "comparison_prompt": "Summarize policy overlaps and contradictions."
  }
  ```
- **Response Model (200 OK):**
  ```json
  {
    "comparison": "# Policy Audit Report\n\n| Feature | travel_policy.pdf | draft_revision_2026.pdf |\n| --- | --- | --- |\n| Daily Meal Limit | $75 | $90 (Contradiction/Update) |",
    "compared_documents": [
      {
        "id": "8da85721-a3f2-411a-9864-1a3bcf4402a4",
        "filename": "travel_policy.pdf",
        "author": "HR Division",
        "department": "HR"
      },
      {
        "id": "9ab23456-11f2-51a2-99a4-1a2bcf4401ba",
        "filename": "draft_revision_2026.pdf",
        "author": "Operations Division",
        "department": "General"
      }
    ]
  }
  ```

---

### 7. Evaluation Summary Metrics
- **Endpoint:** `/api/v1/evaluation`
- **Method:** `GET`
- **Response Model (200 OK):**
  ```json
  {
    "total_evaluations": 12,
    "avg_precision_at_k": 0.88,
    "avg_recall_at_k": 0.91,
    "avg_mrr": 0.95,
    "avg_faithfulness": 0.94,
    "avg_answer_relevancy": 0.89,
    "avg_context_precision": 0.87
  }
  ```

---

### 8. Liveness & Readiness Health Check
- **Endpoint:** `/health`
- **Method:** `GET`
- **Authentication:** None (public/internal probe friendly)
- **Response Model (200 OK - Healthy):**
  ```json
  {
    "status": "healthy",
    "timestamp": "2026-06-07T19:25:00.000000",
    "services": {
      "database": "healthy",
      "qdrant": "healthy"
    }
  }
  ```
- **Response Model (503 Service Unavailable - Unhealthy):**
  ```json
  {
    "status": "unhealthy",
    "timestamp": "2026-06-07T19:25:00.000000",
    "services": {
      "database": "healthy",
      "qdrant": "unhealthy"
    }
  }
  ```
