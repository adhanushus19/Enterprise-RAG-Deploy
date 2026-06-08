import pytest
from app.services.vector_store import VectorStoreService

def test_build_qdrant_filter(mock_openai):
    vs = VectorStoreService()
    
    # 1. Test None filters
    assert vs._build_qdrant_filter(None) is None
    
    # 2. Test single value filter
    f1 = vs._build_qdrant_filter({"department": "HR"})
    assert f1 is not None
    assert len(f1.must) == 1
    
    # 3. Test list value filter
    f2 = vs._build_qdrant_filter({"tags": ["policy", "insurance"]})
    assert f2 is not None
    
    # 4. Test doc_type list filter
    f3 = vs._build_qdrant_filter({"doc_type": ["pdf", "docx"]})
    assert f3 is not None

def test_get_embeddings_fallback(mock_openai):
    vs = VectorStoreService()
    vs.openai_client = None  # Force fallback
    embs = vs.get_embeddings(["hello", "world"])
    assert len(embs) == 2
    assert len(embs[0]) == 1536

def test_search_hybrid_filters(db, mock_openai):
    from app.db.models import Document, DocumentChunk
    
    doc = Document(filename="test.pdf", file_path="test.pdf", doc_type="pdf", department="Engineering", tags=["tech"])
    db.add(doc)
    db.commit()
    
    chunk = DocumentChunk(document_id=doc.id, chunk_index=1, content="Some tech content")
    db.add(chunk)
    db.commit()
    
    vs = VectorStoreService()
    
    # Test with department filter
    res = vs.search_hybrid(db, "query", filters={"department": "Engineering"})
    assert isinstance(res, list)
    
    # Test with doc_type filter
    res = vs.search_hybrid(db, "query", filters={"doc_type": "pdf"})
    assert isinstance(res, list)
    
    # Test with tags filter
    res = vs.search_hybrid(db, "query", filters={"tags": ["tech"]})
    assert isinstance(res, list)
    
    # Test with document_id filter
    res = vs.search_hybrid(db, "query", filters={"document_id": str(doc.id)})
    assert isinstance(res, list)
