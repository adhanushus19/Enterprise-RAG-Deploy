import logging
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from app.services.vector_store import VectorStoreService

logger = logging.getLogger(__name__)

class RetrieverAgent:
    """
    Agent responsible for calling the VectorStoreService to run hybrid retrieval.
    """

    def __init__(self):
        self.vector_store = VectorStoreService()

    def run(self, db: Session, query: str, filters: Optional[Dict[str, Any]] = None, limit: int = 15) -> List[Dict[str, Any]]:
        logger.info(f"Retriever Agent running hybrid search for: '{query}' with filters={filters}")
        try:
            results = self.vector_store.search_hybrid(db=db, query=query, limit=limit, filters=filters)
            logger.info(f"Retriever Agent retrieved {len(results)} chunks.")
            return results
        except Exception as e:
            logger.error(f"Retriever Agent failed during hybrid search: {str(e)}")
            return []
