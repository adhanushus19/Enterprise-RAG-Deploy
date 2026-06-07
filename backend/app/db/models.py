import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, ForeignKey, Integer, Float, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.db.connection import Base

class Document(Base):
    __tablename__ = "documents"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    filename = Column(String, nullable=False)
    file_path = Column(String, nullable=False)
    author = Column(String, nullable=True)
    department = Column(String, nullable=True)
    creation_date = Column(DateTime, nullable=True)
    tags = Column(JSON, nullable=True, default=list)
    doc_type = Column(String, nullable=False) # 'pdf', 'docx', 'pptx', 'xlsx'
    status = Column(String, nullable=False, default="processing") # 'processing', 'completed', 'failed'
    created_at = Column(DateTime, default=datetime.utcnow)

    chunks = relationship("DocumentChunk", back_populates="document", cascade="all, delete-orphan")

class DocumentChunk(Base):
    __tablename__ = "document_chunks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id = Column(UUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    chunk_index = Column(Integer, nullable=False)
    content = Column(String, nullable=False)
    vector_id = Column(String, nullable=True) # Matches the UUID key in Qdrant points
    page_number = Column(Integer, nullable=True) # Page/Slide/Row index for citations

    document = relationship("Document", back_populates="chunks")

class EvaluationMetric(Base):
    __tablename__ = "evaluation_metrics"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    query = Column(String, nullable=False)
    response = Column(String, nullable=False)
    precision_at_k = Column(Float, nullable=True)
    recall_at_k = Column(Float, nullable=True)
    mrr = Column(Float, nullable=True)
    faithfulness = Column(Float, nullable=True)
    answer_relevancy = Column(Float, nullable=True)
    context_precision = Column(Float, nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
