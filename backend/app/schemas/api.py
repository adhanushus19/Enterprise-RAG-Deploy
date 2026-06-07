from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from datetime import datetime
from uuid import UUID

class DocumentSchema(BaseModel):
    id: UUID
    filename: str
    file_path: str
    author: Optional[str]
    department: Optional[str]
    creation_date: Optional[datetime]
    tags: List[str]
    doc_type: str
    status: str
    created_at: datetime

    class Config:
        from_attributes = True

class QueryRequest(BaseModel):
    query: str = Field(description="The user's query/question")
    filters: Optional[Dict[str, Any]] = Field(default=None, description="Metadata filters (e.g. department, doc_type, tags)")
    chat_history: Optional[List[Dict[str, str]]] = Field(default=None, description="Conversational history (list of role/content dicts)")

class CitationResponse(BaseModel):
    id: int
    filename: str
    page_number: Optional[int]
    author: Optional[str]
    department: Optional[str]
    snippet: str

class QueryResponse(BaseModel):
    query: str
    answer: str
    citations: List[CitationResponse]

class SearchRequest(BaseModel):
    query: str
    filters: Optional[Dict[str, Any]] = None
    limit: Optional[int] = 10

class SearchHit(BaseModel):
    document_id: str
    filename: str
    page_number: Optional[int]
    content: str
    author: Optional[str]
    department: Optional[str]
    doc_type: str
    tags: List[str]
    score: Optional[float] = None
    rrf_score: Optional[float] = None

class CompareRequest(BaseModel):
    document_ids: List[UUID] = Field(description="List of document IDs to compare")
    comparison_prompt: Optional[str] = Field(default="Compare the documents focusing on key differences and similarities.", description="Specific prompt or focus area for comparison")

class CompareResponse(BaseModel):
    comparison: str
    compared_documents: List[Dict[str, Any]]

class EvaluationCreate(BaseModel):
    query: str
    response: str
    precision_at_k: Optional[float] = None
    recall_at_k: Optional[float] = None
    mrr: Optional[float] = None
    faithfulness: Optional[float] = None
    answer_relevancy: Optional[float] = None
    context_precision: Optional[float] = None

class EvaluationResponseSchema(BaseModel):
    id: UUID
    query: str
    response: str
    precision_at_k: Optional[float]
    recall_at_k: Optional[float]
    mrr: Optional[float]
    faithfulness: Optional[float]
    answer_relevancy: Optional[float]
    context_precision: Optional[float]
    timestamp: datetime

    class Config:
        from_attributes = True

class EvaluationMetricsSummary(BaseModel):
    total_evaluations: int
    avg_precision_at_k: Optional[float]
    avg_recall_at_k: Optional[float]
    avg_mrr: Optional[float]
    avg_faithfulness: Optional[float]
    avg_answer_relevancy: Optional[float]
    avg_context_precision: Optional[float]
