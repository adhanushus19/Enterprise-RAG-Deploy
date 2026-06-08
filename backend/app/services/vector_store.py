import logging
import uuid
from typing import List, Dict, Any, Optional
from qdrant_client import QdrantClient
from qdrant_client.http import models as qmodels
from openai import OpenAI
from rank_bm25 import BM25Okapi
from app.config import settings
from app.db.models import DocumentChunk, Document
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

class VectorStoreService:
    """
    Manages vector storage (Qdrant), embedding generation (OpenAI),
    and hybrid retrieval orchestration (Dense + BM25 with Reciprocal Rank Fusion).
    """

    def __init__(self) -> None:
        self.qdrant_client = QdrantClient(
            host=settings.QDRANT_HOST,
            port=settings.QDRANT_PORT
        )
        self.openai_client = None
        if settings.OPENAI_API_KEY:
            self.openai_client = OpenAI(api_key=settings.OPENAI_API_KEY)
        
        self.collection_name = "knowledge_base"
        self.vector_size = 1536  # text-embedding-3-small dimension
        self._ensure_collection()

    def _ensure_collection(self) -> None:
        try:
            collections = self.qdrant_client.get_collections().collections
            collection_names = [col.name for col in collections]
            if self.collection_name not in collection_names:
                logger.info(f"Creating Qdrant collection: {self.collection_name}")
                self.qdrant_client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=qmodels.VectorParams(
                        size=self.vector_size,
                        distance=qmodels.Distance.COSINE
                    )
                )
        except Exception as e:
            logger.error("Failed to check/create Qdrant collection", exc_info=True)

    def get_embeddings(self, texts: List[str]) -> List[List[float]]:
        """
        Generates dense vector embeddings using OpenAI API.
        Falls back to dummy embeddings if API key is missing.
        """
        if not self.openai_client:
            logger.warning("OPENAI_API_KEY is not set. Generating dummy embeddings for testing.")
            # Return dummy 1536-dim vectors
            import random
            return [[random.random() for _ in range(self.vector_size)] for _ in texts]
        
        try:
            response = self.openai_client.embeddings.create(
                input=texts,
                model="text-embedding-3-small"
            )
            return [data.embedding for data in response.data]
        except Exception as e:
            logger.error("Failed to generate embeddings", exc_info=True)
            raise e

    def index_chunks(self, db_chunks: List[DocumentChunk], document: Document) -> List[str]:
        """
        Generates embeddings for chunks and uploads them to Qdrant.
        Returns the list of vector IDs generated.
        """
        if not db_chunks:
            return []

        texts = [chunk.content for chunk in db_chunks]
        embeddings = self.get_embeddings(texts)

        points = []
        vector_ids = []
        for i, chunk in enumerate(db_chunks):
            v_id = str(uuid.uuid4())
            vector_ids.append(v_id)
            
            # Prepare payload containing all searchable/filterable metadata
            payload = {
                "document_id": str(document.id),
                "chunk_index": chunk.chunk_index,
                "page_number": chunk.page_number,
                "content": chunk.content,
                "filename": document.filename,
                "author": document.author or "Unknown",
                "department": document.department or "General",
                "doc_type": document.doc_type,
                "tags": document.tags or []
            }
            
            points.append(
                qmodels.PointStruct(
                    id=v_id,
                    vector=embeddings[i],
                    payload=payload
                )
            )

        try:
            self.qdrant_client.upsert(
                collection_name=self.collection_name,
                points=points
            )
            logger.info(f"Successfully indexed {len(points)} points in Qdrant.")
        except Exception as e:
            logger.error("Failed to index points in Qdrant", exc_info=True)
            raise e

        return vector_ids

    def delete_document(self, document_id: str) -> None:
        """
        Deletes all vector points associated with a document ID.
        """
        try:
            self.qdrant_client.delete(
                collection_name=self.collection_name,
                points_selector=qmodels.FilterSelector(
                    filter=qmodels.Filter(
                        must=[
                            qmodels.FieldCondition(
                                key="document_id",
                                match=qmodels.MatchValue(value=document_id)
                            )
                        ]
                    )
                )
            )
            logger.info(f"Deleted points for document {document_id} from Qdrant.")
        except Exception as e:
            logger.error("Failed to delete points from Qdrant", exc_info=True)
            raise e

    def _build_qdrant_filter(self, filters: Optional[Dict[str, Any]]) -> Optional[qmodels.Filter]:
        if not filters:
            return None
        
        must_conditions = []
        for key, val in filters.items():
            if val:
                if key == "tags" and isinstance(val, list):
                    for tag in val:
                        must_conditions.append(
                            qmodels.FieldCondition(
                                key="tags",
                                match=qmodels.MatchValue(value=tag)
                            )
                        )
                elif isinstance(val, list):
                    must_conditions.append(
                        qmodels.FieldCondition(
                            key=key,
                            match=qmodels.MatchAny(any=val)
                        )
                    )
                else:
                    must_conditions.append(
                        qmodels.FieldCondition(
                            key=key,
                            match=qmodels.MatchValue(value=val)
                        )
                    )
        
        return qmodels.Filter(must=must_conditions) if must_conditions else None

    def search_dense(self, query: str, limit: int = 10, filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Performs semantic (dense) search in Qdrant.
        """
        query_vector = self.get_embeddings([query])[0]
        q_filter = self._build_qdrant_filter(filters)

        try:
            results = self.qdrant_client.search(
                collection_name=self.collection_name,
                query_vector=query_vector,
                query_filter=q_filter,
                limit=limit
            )
            
            hits = []
            for hit in results:
                hits.append({
                    "id": hit.id,
                    "score": hit.score,
                    "content": hit.payload["content"],
                    "document_id": hit.payload["document_id"],
                    "filename": hit.payload["filename"],
                    "page_number": hit.payload["page_number"],
                    "author": hit.payload["author"],
                    "department": hit.payload["department"],
                    "doc_type": hit.payload["doc_type"],
                    "tags": hit.payload["tags"]
                })
            return hits
        except Exception as e:
            logger.error("Dense search failed", exc_info=True)
            return []

    def search_hybrid(
        self,
        db: Session,
        query: str,
        limit: int = 10,
        filters: Optional[Dict[str, Any]] = None,
        rrf_k: int = 60
    ) -> List[Dict[str, Any]]:
        """
        Executes hybrid retrieval by performing:
        1. Dense retrieval (Qdrant semantic search)
        2. Sparse retrieval (BM25 over filtered SQL chunks)
        Combines results using Reciprocal Rank Fusion (RRF).
        """
        # 1. Fetch dense results (retrieve slightly more to allow RRF overlap)
        candidate_limit = max(limit * 3, 30)
        dense_results = self.search_dense(query, limit=candidate_limit, filters=filters)

        # 2. Fetch all matching chunks from DB to build temporary BM25 index
        db_query = db.query(DocumentChunk).join(Document)
        
        # Apply filters to SQL query
        if filters:
            if filters.get("department"):
                db_query = db_query.filter(Document.department == filters["department"])
            if filters.get("doc_type"):
                db_query = db_query.filter(Document.doc_type == filters["doc_type"])
            if filters.get("document_id"):
                doc_id_val = filters["document_id"]
                if isinstance(doc_id_val, str):
                    try:
                        doc_id_val = uuid.UUID(doc_id_val)
                    except Exception:
                        pass
                db_query = db_query.filter(DocumentChunk.document_id == doc_id_val)
            if filters.get("tags"):
                tags = filters["tags"]
                if isinstance(tags, str):
                    tags = [tags]
                for tag in tags:
                    db_query = db_query.filter(Document.tags.contains([tag]))

        matching_chunks = db_query.all()

        sparse_results = []
        if matching_chunks:
            # Tokenize documents simple word-splitting
            tokenized_corpus = [chunk.content.lower().split() for chunk in matching_chunks]
            bm25 = BM25Okapi(tokenized_corpus)
            
            tokenized_query = query.lower().split()
            scores = bm25.get_scores(tokenized_query)
            
            # Match scores back to database chunks
            chunk_scores = []
            for i, chunk in enumerate(matching_chunks):
                chunk_scores.append((chunk, scores[i]))
            
            # Sort by BM25 score descending and take top N
            chunk_scores.sort(key=lambda x: x[1], reverse=True)
            top_sparse = chunk_scores[:candidate_limit]
            
            for chunk, score in top_sparse:
                if score > 0:  # Only include matching chunks
                    sparse_results.append({
                        "id": str(chunk.id),
                        "score": score,
                        "content": chunk.content,
                        "document_id": str(chunk.document_id),
                        "filename": chunk.document.filename,
                        "page_number": chunk.page_number,
                        "author": chunk.document.author,
                        "department": chunk.document.department,
                        "doc_type": chunk.document.doc_type,
                        "tags": chunk.document.tags
                    })

        # 3. Reciprocal Rank Fusion (RRF)
        rrf_scores: Dict[str, Dict[str, Any]] = {}
        
        # Dense ranking
        for rank, hit in enumerate(dense_results):
            # Qdrant hits have random vector point IDs, we map them by content/doc_id or the original point ID if matches database chunk ID
            # Let's uniquely identify chunks by document_id + page_number + content
            chunk_key = f"{hit['document_id']}_{hit['page_number']}_{hit['content'][:50]}"
            if chunk_key not in rrf_scores:
                rrf_scores[chunk_key] = {"hit": hit, "rrf_score": 0.0}
            rrf_scores[chunk_key]["rrf_score"] += 1.0 / (rrf_k + (rank + 1))
            
        # Sparse ranking
        for rank, hit in enumerate(sparse_results):
            chunk_key = f"{hit['document_id']}_{hit['page_number']}_{hit['content'][:50]}"
            if chunk_key not in rrf_scores:
                rrf_scores[chunk_key] = {"hit": hit, "rrf_score": 0.0}
            rrf_scores[chunk_key]["rrf_score"] += 1.0 / (rrf_k + (rank + 1))

        # 4. Sort and filter
        sorted_rrf = sorted(rrf_scores.values(), key=lambda x: x["rrf_score"], reverse=True)
        
        final_hits = []
        for item in sorted_rrf[:limit]:
            hit = item["hit"]
            hit["rrf_score"] = item["rrf_score"]
            final_hits.append(hit)
            
        # If no sparse results or dense results found, return whatever we have
        if not final_hits:
            return dense_results[:limit]
            
        return final_hits
