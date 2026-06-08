import os
import time
import logging
import json
from uuid import UUID
from typing import List, Optional
from datetime import datetime

from fastapi import FastAPI, UploadFile, File, Form, Depends, HTTPException, Header, BackgroundTasks, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response, JSONResponse
from sqlalchemy.orm import Session
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST

from app.config import settings
from app.db.connection import engine, Base, get_db
from app.db.models import Document, DocumentChunk, EvaluationMetric
from app.schemas.api import (
    DocumentSchema, QueryRequest, QueryResponse, SearchRequest, SearchHit,
    CompareRequest, CompareResponse, EvaluationMetricsSummary, EvaluationResponseSchema,
    EvaluationCreate
)
from app.services.document_processor import DocumentProcessor
from app.services.vector_store import VectorStoreService
from app.agents.graph import rag_graph

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("enterprise_rag")

class JSONFormatter(logging.Formatter):
    def format(self, record):
        log_data = {
            "timestamp": self.formatTime(record),
            "level": record.levelname,
            "message": record.getMessage(),
            "name": record.name
        }
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
        return json.dumps(log_data)

# Apply JSON formatter for containerized structured logging
for handler in logging.getLogger().handlers:
    handler.setFormatter(JSONFormatter())

# Initialize DB Tables
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Enterprise AI Knowledge Assistant API",
    description="Production-grade Retrieval-Augmented Generation (RAG) platform",
    version="1.0.0"
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_headers=["*"],
    allow_methods=["*"],
)

# Prometheus Metrics
REQUEST_COUNT = Counter("api_requests_total", "Total API Requests", ["method", "endpoint", "status"])
REQUEST_LATENCY = Histogram("api_request_duration_seconds", "API Request Latency", ["method", "endpoint"])
INGESTION_COUNT = Counter("document_ingestion_total", "Total Documents Ingested", ["doc_type", "status"])

# Custom Rate Limiter (Token bucket dictionary per IP)
RATE_LIMIT_WINDOWS = {}
LIMIT_MAX_REQUESTS = 60
LIMIT_WINDOW_SECONDS = 60

@app.middleware("http")
async def rate_limiting_and_metrics_middleware(request, call_next):
    # Skip rate limiting on metrics and health check
    if request.url.path in ["/metrics", "/health"]:
        return await call_next(request)
        
    client_ip = request.client.host
    now = time.time()
    
    # Prune old logs
    if client_ip not in RATE_LIMIT_WINDOWS:
        RATE_LIMIT_WINDOWS[client_ip] = []
    
    RATE_LIMIT_WINDOWS[client_ip] = [t for t in RATE_LIMIT_WINDOWS[client_ip] if now - t < LIMIT_WINDOW_SECONDS]
    
    if len(RATE_LIMIT_WINDOWS[client_ip]) >= LIMIT_MAX_REQUESTS:
        return JSONResponse(
            status_code=429,
            content={"detail": "Too many requests. Rate limit exceeded."}
        )
    
    RATE_LIMIT_WINDOWS[client_ip].append(now)
    
    # Track metrics
    method = request.method
    endpoint = request.url.path
    
    start_time = time.time()
    try:
        response = await call_next(request)
        duration = time.time() - start_time
        REQUEST_COUNT.labels(method=method, endpoint=endpoint, status=response.status_code).inc()
        REQUEST_LATENCY.labels(method=method, endpoint=endpoint).observe(duration)
        return response
    except Exception as e:
        REQUEST_COUNT.labels(method=method, endpoint=endpoint, status=500).inc()
        raise e

# Security Header Dependency
def verify_api_key(x_api_key: str = Header(..., description="Secret corporate API key authentication")) -> str:
    if x_api_key != settings.API_KEY:
        raise HTTPException(status_code=401, detail="Unauthorized: Invalid API Key")
    return x_api_key

# Background Ingestion Task
def process_document_ingestion(doc_id: UUID, file_path: str, filename: str, doc_type: str, db_session_factory):
    # We open a fresh session for the background task to avoid cross-thread transaction contamination
    db = db_session_factory()
    processor = DocumentProcessor()
    vector_store = VectorStoreService()
    
    doc = db.query(Document).filter(Document.id == doc_id).first()
    if not doc:
        db.close()
        return

    try:
        # 1. Parse File
        chunks = processor.parse_file(file_path, doc_type)
        if not chunks:
            raise ValueError("No text content could be extracted from this document.")

        # 2. Extract Metadata using LLM on the first chunk
        first_chunk_text = chunks[0][0]
        metadata = processor.extract_metadata(first_chunk_text, filename, doc_type)

        doc.author = metadata["author"]
        doc.department = metadata["department"]
        doc.creation_date = metadata["creation_date"]
        doc.tags = metadata["tags"]
        
        # 3. Create database chunks
        db_chunks = []
        for content, idx in chunks:
            chunk = DocumentChunk(
                document_id=doc.id,
                chunk_index=idx,
                content=content,
                page_number=idx
            )
            db.add(chunk)
            db_chunks.append(chunk)
        
        db.commit() # Commit chunks to get IDs

        # 4. Embed and store in Qdrant
        vector_ids = vector_store.index_chunks(db_chunks, doc)
        
        # 5. Map Qdrant IDs back to PG chunks
        for i, chunk in enumerate(db_chunks):
            chunk.vector_id = vector_ids[i]
            
        doc.status = "completed"
        db.commit()
        INGESTION_COUNT.labels(doc_type=doc_type, status="completed").inc()
        logger.info(f"Ingestion completed for document: {filename} (ID: {doc.id})")
        
    except Exception as e:
        logger.error(f"Ingestion failed for document {filename}: {str(e)}", exc_info=True)
        doc.status = "failed"
        db.commit()
        INGESTION_COUNT.labels(doc_type=doc_type, status="failed").inc()
    finally:
        db.close()

# Prometheus metrics route
@app.get("/metrics", include_in_schema=False)
def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)

# Service liveness/readiness health check
from sqlalchemy import text

@app.get("/health", status_code=200)
def health_check(db: Session = Depends(get_db)):
    health_status = {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "services": {
            "database": "unhealthy",
            "qdrant": "unhealthy"
        }
    }
    
    # 1. Test Database Connectivity
    try:
        db.execute(text("SELECT 1"))
        health_status["services"]["database"] = "healthy"
    except Exception as e:
        logger.error(f"Health check failed for database: {str(e)}")
        health_status["status"] = "unhealthy"
        
    # 2. Test Qdrant Connectivity
    try:
        from app.services.vector_store import VectorStoreService
        vs = VectorStoreService()
        if vs.qdrant_client:
            vs.qdrant_client.get_collections()
            health_status["services"]["qdrant"] = "healthy"
    except Exception as e:
        logger.error(f"Health check failed for Qdrant: {str(e)}")
        health_status["status"] = "unhealthy"

    if health_status["status"] == "unhealthy":
        return JSONResponse(status_code=503, content=health_status)
        
    return health_status

# Endpoints
@app.post("/api/v1/documents/upload", response_model=DocumentSchema, dependencies=[Depends(verify_api_key)])
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    # Validate file type
    filename = file.filename
    ext = filename.split(".")[-1].lower() if "." in filename else ""
    if ext not in ["pdf", "docx", "pptx", "xlsx"]:
        raise HTTPException(status_code=400, detail="Unsupported file extension. Only PDF, DOCX, PPTX, XLSX permitted.")

    # Save physical file
    target_path = os.path.join(settings.UPLOAD_DIR, f"{time.time()}_{filename}")
    with open(target_path, "wb") as f:
        f.write(await file.read())

    # Insert Document stub
    doc = Document(
        filename=filename,
        file_path=target_path,
        doc_type=ext,
        status="processing"
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)

    # Trigger background ingestion
    # Pass SessionLocal creator to background task to manage db lifecycle safely
    from app.db.connection import SessionLocal
    background_tasks.add_task(
        process_document_ingestion,
        doc_id=doc.id,
        file_path=target_path,
        filename=filename,
        doc_type=ext,
        db_session_factory=SessionLocal
    )

    return doc

@app.delete("/api/v1/documents/{document_id}", dependencies=[Depends(verify_api_key)])
async def delete_document(document_id: UUID, db: Session = Depends(get_db)):
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    # Delete from Qdrant
    vector_store = VectorStoreService()
    try:
        vector_store.delete_document(str(doc.id))
    except Exception as e:
        logger.error(f"Failed to delete Qdrant points: {str(e)}")

    # Delete physical file
    if os.path.exists(doc.file_path):
        try:
            os.remove(doc.file_path)
        except Exception as e:
            logger.error(f"Failed to delete physical file {doc.file_path}: {str(e)}")

    # Delete from DB (Cascade delete removes chunks)
    db.delete(doc)
    db.commit()

    return {"message": "Document successfully deleted."}

@app.get("/api/v1/documents", response_model=List[DocumentSchema], dependencies=[Depends(verify_api_key)])
async def list_documents(db: Session = Depends(get_db)):
    return db.query(Document).order_by(Document.created_at.desc()).all()

@app.post("/api/v1/search", response_model=List[SearchHit], dependencies=[Depends(verify_api_key)])
async def search_documents(request: SearchRequest, db: Session = Depends(get_db)):
    vector_store = VectorStoreService()
    hits = vector_store.search_hybrid(db=db, query=request.query, limit=request.limit, filters=request.filters)
    return hits

@app.post("/api/v1/query", response_model=QueryResponse, dependencies=[Depends(verify_api_key)])
async def query_rag_pipeline(request: QueryRequest, db: Session = Depends(get_db)):
    # Prepare graph inputs
    inputs = {
        "query": request.query,
        "filters": request.filters,
        "chat_history": request.chat_history or [],
        "retrieved_chunks": [],
        "reranked_chunks": [],
        "citations": [],
        "verification_passed": True,
        "verification_feedback": "",
        "answer": "",
        "loop_count": 0
    }
    
    # Run graph passing db session in config configurable
    try:
        config = {"configurable": {"db": db}}
        output = rag_graph.invoke(inputs, config=config)
        
        return QueryResponse(
            query=request.query,
            answer=output["answer"],
            citations=output["citations"]
        )
    except Exception as e:
        logger.error(f"RAG Graph execution failed: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal RAG pipeline error during multi-agent graph execution.")

@app.post("/api/v1/compare", response_model=CompareResponse, dependencies=[Depends(verify_api_key)])
async def compare_documents(request: CompareRequest, db: Session = Depends(get_db)):
    # 1. Fetch documents metadata
    docs = db.query(Document).filter(Document.id.in_(request.document_ids)).all()
    if len(docs) < 2:
        raise HTTPException(status_code=400, detail="Comparison requires at least 2 valid documents.")

    # 2. Compile document summaries or first few paragraphs
    comparison_context = ""
    compared_info = []
    
    for i, doc in enumerate(docs):
        # Fetch first 5 chunks of the document
        chunks = db.query(DocumentChunk).filter(DocumentChunk.document_id == doc.id).order_by(DocumentChunk.chunk_index).limit(5).all()
        chunks_text = "\n".join([c.content for c in chunks])
        
        comparison_context += f"--- Document {i+1}: {doc.filename} ---\nMetadata:\n- Author: {doc.author}\n- Department: {doc.department}\n- Created: {doc.creation_date}\n\nContent Excerpts:\n{chunks_text}\n\n"
        compared_info.append({
            "id": str(doc.id),
            "filename": doc.filename,
            "author": doc.author,
            "department": doc.department
        })

    # 3. Generate side-by-side analysis from OpenAI
    try:
        client = VectorStoreService().openai_client
        if not client:
            raise ValueError("OpenAI client not configured.")
            
        system_prompt = (
            "You are an expert document examiner and policy auditor. Synthesize a comparison report "
            "analyzing similarities, contradictions, and key differences between the documents presented.\n"
            "Organize the output clearly using Markdown tables, bullet points, and headers."
        )
        
        user_prompt = f"Prompt Instructions: {request.comparison_prompt}\n\nDocuments Context:\n{comparison_context}"
        
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.0
        )
        comparison_report = response.choices[0].message.content
        
        return CompareResponse(
            comparison=comparison_report,
            compared_documents=compared_info
        )
    except Exception as e:
        logger.error(f"Compare service failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to generate document comparison: {str(e)}")

@app.get("/api/v1/evaluation", response_model=EvaluationMetricsSummary, dependencies=[Depends(verify_api_key)])
async def get_evaluation_metrics(db: Session = Depends(get_db)):
    # Calculate aggregated averages of metrics stored in PG
    metrics_list = db.query(EvaluationMetric).all()
    total = len(metrics_list)
    if total == 0:
        return EvaluationMetricsSummary(
            total_evaluations=0,
            avg_precision_at_k=0.0,
            avg_recall_at_k=0.0,
            avg_mrr=0.0,
            avg_faithfulness=0.0,
            avg_answer_relevancy=0.0,
            avg_context_precision=0.0
        )

    p_k = [m.precision_at_k for m in metrics_list if m.precision_at_k is not None]
    r_k = [m.recall_at_k for m in metrics_list if m.recall_at_k is not None]
    mrr = [m.mrr for m in metrics_list if m.mrr is not None]
    faith = [m.faithfulness for m in metrics_list if m.faithfulness is not None]
    relev = [m.answer_relevancy for m in metrics_list if m.answer_relevancy is not None]
    c_prec = [m.context_precision for m in metrics_list if m.context_precision is not None]

    return EvaluationMetricsSummary(
        total_evaluations=total,
        avg_precision_at_k=sum(p_k) / len(p_k) if p_k else None,
        avg_recall_at_k=sum(r_k) / len(r_k) if r_k else None,
        avg_mrr=sum(mrr) / len(mrr) if mrr else None,
        avg_faithfulness=sum(faith) / len(faith) if faith else None,
        avg_answer_relevancy=sum(relev) / len(relev) if relev else None,
        avg_context_precision=sum(c_prec) / len(c_prec) if c_prec else None
    )

@app.post("/api/v1/evaluation", response_model=EvaluationResponseSchema, dependencies=[Depends(verify_api_key)])
async def record_evaluation_metric(metric: EvaluationCreate, db: Session = Depends(get_db)):
    db_metric = EvaluationMetric(
        query=metric.query,
        response=metric.response,
        precision_at_k=metric.precision_at_k,
        recall_at_k=metric.recall_at_k,
        mrr=metric.mrr,
        faithfulness=metric.faithfulness,
        answer_relevancy=metric.answer_relevancy,
        context_precision=metric.context_precision
    )
    db.add(db_metric)
    db.commit()
    db.refresh(db_metric)
    return db_metric
