import pytest
from uuid import uuid4

# Test API Authentication Guardrail
def test_unauthenticated_requests(client):
    endpoints = [
        ("GET", "/api/v1/documents"),
        ("POST", "/api/v1/search"),
        ("POST", "/api/v1/query"),
        ("POST", "/api/v1/compare"),
        ("GET", "/api/v1/evaluation"),
        ("POST", "/api/v1/evaluation")
    ]
    for method, path in endpoints:
        if method == "GET":
            res = client.get(path)
        else:
            res = client.post(path, json={})
        assert res.status_code == 422 or res.status_code == 401 or res.status_code == 400

def test_list_documents(client, db):
    # Retrieve documents list with valid headers
    res = client.get("/api/v1/documents", headers={"X-API-Key": "enterprise-secret-key-123"})
    assert res.status_code == 200
    assert isinstance(res.json(), list)

def test_search_documents(client, mock_openai):
    payload = {
        "query": "test query search",
        "limit": 5
    }
    res = client.post(
        "/api/v1/search",
        json=payload,
        headers={"X-API-Key": "enterprise-secret-key-123"}
    )
    assert res.status_code == 200
    hits = res.json()
    assert isinstance(hits, list)

def test_query_rag_pipeline(client, mock_openai):
    payload = {
        "query": "Is there a travel policy in the system?",
        "filters": {"doc_type": "pdf"}
    }
    res = client.post(
        "/api/v1/query",
        json=payload,
        headers={"X-API-Key": "enterprise-secret-key-123"}
    )
    assert res.status_code == 200
    data = res.json()
    assert "query" in data
    assert "answer" in data
    assert "citations" in data

def test_compare_documents_validation(client):
    # Comparison should fail if less than 2 document IDs are provided
    payload = {
        "document_ids": [str(uuid4())]
    }
    res = client.post(
        "/api/v1/compare",
        json=payload,
        headers={"X-API-Key": "enterprise-secret-key-123"}
    )
    assert res.status_code == 400

def test_evaluation_logging_and_retrieval(client):
    # Log evaluation results
    eval_payload = {
        "query": "How do I log a security bug?",
        "response": "Follow protocol 1.",
        "precision_at_k": 1.0,
        "recall_at_k": 1.0,
        "mrr": 1.0,
        "faithfulness": 0.95,
        "answer_relevancy": 0.90,
        "context_precision": 1.0
    }
    
    res_log = client.post(
        "/api/v1/evaluation",
        json=eval_payload,
        headers={"X-API-Key": "enterprise-secret-key-123"}
    )
    assert res_log.status_code == 200
    logged_data = res_log.json()
    assert logged_data["query"] == "How do I log a security bug?"
    
    # Get evaluations summary
    res_summary = client.get(
        "/api/v1/evaluation",
        headers={"X-API-Key": "enterprise-secret-key-123"}
    )
    assert res_summary.status_code == 200
    summary = res_summary.json()
    assert summary["total_evaluations"] >= 1
    assert summary["avg_precision_at_k"] == 1.0
    assert summary["avg_faithfulness"] == 0.95
