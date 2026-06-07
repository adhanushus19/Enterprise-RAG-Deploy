import logging
from typing import List, Dict, Any
from pydantic import BaseModel, Field
from openai import OpenAI
from app.config import settings

logger = logging.getLogger(__name__)

class ChunkRelevance(BaseModel):
    index: int = Field(description="The index of the chunk in the input list (0-based)")
    relevance_score: float = Field(description="Relevance score from 0.0 (irrelevant) to 10.0 (highly relevant)")
    reason: str = Field(description="Brief explanation of the relevance rating")

class RerankerOutput(BaseModel):
    ranked_chunks: List[ChunkRelevance]

class RerankerAgent:
    """
    Agent responsible for evaluating the semantic relevance of each retrieved document chunk
    relative to the user query and sorting them by their relevance scores.
    """

    def __init__(self):
        self.client = None
        if settings.OPENAI_API_KEY:
            self.client = OpenAI(api_key=settings.OPENAI_API_KEY)

    def run(self, query: str, chunks: List[Dict[str, Any]], limit: int = 5) -> List[Dict[str, Any]]:
        if not chunks:
            return []
        if not self.client:
            logger.warning("No OpenAI Client. Skipping reranking, returning first K chunks.")
            return chunks[:limit]

        # Prepare batch content for LLM
        chunks_str = ""
        for idx, chunk in enumerate(chunks):
            chunks_str += f"--- Chunk Index {idx} ---\nSource: {chunk['filename']} | Page/Row: {chunk['page_number']}\nContent: {chunk['content']}\n\n"

        system_prompt = (
            "You are a Document Re-Ranking Agent. Evaluate the relevance of each document chunk "
            "to the user query. Assign a score between 0.0 and 10.0 to each chunk.\n"
            "- A score of 10.0 means the chunk directly and fully answers the query.\n"
            "- A score of 0.0 means the chunk is completely unrelated.\n"
            "Evaluate every single chunk listed and return them with their index."
        )

        user_prompt = f"Query: {query}\n\nList of Chunks:\n{chunks_str}"

        try:
            response = self.client.beta.chat.completions.parse(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                response_format=RerankerOutput,
                temperature=0.0
            )

            # Map scores back to original chunks
            scored_ranks = {item.index: item for item in response.choices[0].message.parsed.ranked_chunks}
            
            reranked_chunks = []
            for idx, chunk in enumerate(chunks):
                rank_info = scored_ranks.get(idx)
                if rank_info:
                    chunk["rerank_score"] = rank_info.relevance_score
                    chunk["rerank_reason"] = rank_info.reason
                else:
                    chunk["rerank_score"] = 0.0
                    chunk["rerank_reason"] = "No score returned by reranker"
                
                # Only keep chunks that are somewhat relevant
                if chunk["rerank_score"] > 2.0:
                    reranked_chunks.append(chunk)

            # Sort descending by score
            reranked_chunks.sort(key=lambda x: x["rerank_score"], reverse=True)
            
            logger.info(f"Reranked {len(chunks)} chunks -> Kept {len(reranked_chunks)} chunks above threshold. Returning top {limit}")
            return reranked_chunks[:limit]

        except Exception as e:
            logger.error(f"Reranker Agent failed: {str(e)}", exc_info=True)
            # Fallback to dense/hybrid ordering
            return chunks[:limit]
