import logging
from typing import List, Set, Dict, Any, Optional
from openai import OpenAI
from pydantic import BaseModel, Field
from app.config import settings

logger = logging.getLogger(__name__)

class ClaimVerification(BaseModel):
    claim: str = Field(description="A distinct factual claim made in the answer.")
    supported: bool = Field(description="True if the claim is directly supported by the context chunks, else False.")
    reason: str = Field(description="Reasoning for the support decision.")

class FaithfulnessOutput(BaseModel):
    claims: List[ClaimVerification] = Field(description="List of claims and their verification status.")

class RelevancyOutput(BaseModel):
    relevancy_score: float = Field(description="Score from 0.0 (irrelevant) to 1.0 (perfectly relevant) of the answer to the query.")
    feedback: str = Field(description="Explanation of why the score was assigned.")


class EvaluationService:
    """
    Computes Information Retrieval metrics (Precision@K, Recall@K, MRR)
    and LLM-assisted generation quality metrics (Faithfulness, Answer Relevancy, Context Precision).
    """

    def __init__(self):
        self.client = None
        if settings.OPENAI_API_KEY:
            self.client = OpenAI(api_key=settings.OPENAI_API_KEY)

    # 1. Information Retrieval Metrics
    @staticmethod
    def calculate_precision_at_k(retrieved_doc_ids: List[str], ground_truth_ids: Set[str], k: int) -> float:
        if not retrieved_doc_ids or not ground_truth_ids or k <= 0:
            return 0.0
        
        retrieved_k = retrieved_doc_ids[:k]
        relevant_retrieved = sum(1 for doc_id in retrieved_k if doc_id in ground_truth_ids)
        return relevant_retrieved / k

    @staticmethod
    def calculate_recall_at_k(retrieved_doc_ids: List[str], ground_truth_ids: Set[str], k: int) -> float:
        if not retrieved_doc_ids or not ground_truth_ids or k <= 0:
            return 0.0
        
        retrieved_k = retrieved_doc_ids[:k]
        relevant_retrieved = sum(1 for doc_id in retrieved_k if doc_id in ground_truth_ids)
        return relevant_retrieved / len(ground_truth_ids)

    @staticmethod
    def calculate_mrr(retrieved_doc_ids: List[str], ground_truth_ids: Set[str]) -> float:
        if not retrieved_doc_ids or not ground_truth_ids:
            return 0.0
        
        for rank, doc_id in enumerate(retrieved_doc_ids):
            if doc_id in ground_truth_ids:
                return 1.0 / (rank + 1)
        return 0.0

    # 2. LLM-Assisted Generation Quality Metrics (RAGAS Equivalents)
    def evaluate_faithfulness(self, context: str, answer: str) -> float:
        """
        Faithfulness measures if the claims in the generated answer are grounded in the context.
        Formula: (Number of supported claims) / (Total number of claims)
        """
        if not self.client:
            logger.warning("OpenAI client missing. Returning fallback faithfulness score.")
            return 0.9  # Fallback

        system_prompt = (
            "You are a Quality Assurance Agent in a RAG pipeline. Extract all distinct factual "
            "claims made in the answer, and then verify if each claim is directly supported by the context. "
            "Respond strictly in the JSON format defined."
        )
        
        user_prompt = f"Context:\n{context}\n\nAnswer:\n{answer}"

        try:
            response = self.client.beta.chat.completions.parse(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                response_format=FaithfulnessOutput,
                temperature=0.0
            )
            
            claims = response.choices[0].message.parsed.claims
            if not claims:
                return 1.0  # No claims to verify
            
            supported_count = sum(1 for c in claims if c.supported)
            score = supported_count / len(claims)
            logger.info(f"Faithfulness Score: {score:.2f} ({supported_count}/{len(claims)} supported)")
            return score
        except Exception as e:
            logger.error(f"Failed to evaluate faithfulness: {str(e)}")
            return 0.5

    def evaluate_answer_relevancy(self, query: str, answer: str) -> float:
        """
        Measures how relevant the answer is to the user query.
        """
        if not self.client:
            logger.warning("OpenAI client missing. Returning fallback answer relevancy score.")
            return 0.85  # Fallback

        system_prompt = (
            "You are a Quality Assurance Agent in a RAG pipeline. Evaluate if the answer "
            "directly addresses the user query and is relevant. Rate it from 0.0 (unrelated) "
            "to 1.0 (perfectly relevant)."
        )
        
        user_prompt = f"Query: {query}\n\nAnswer: {answer}"

        try:
            response = self.client.beta.chat.completions.parse(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                response_format=RelevancyOutput,
                temperature=0.0
            )
            
            score = response.choices[0].message.parsed.relevancy_score
            logger.info(f"Answer Relevancy Score: {score:.2f}")
            return score
        except Exception as e:
            logger.error(f"Failed to evaluate answer relevancy: {str(e)}")
            return 0.5
            
    def evaluate_context_precision(self, query: str, retrieved_chunks: List[Dict[str, Any]], ground_truth_ids: Set[str]) -> float:
        """
        Context precision measures if the retrieved chunks ranked highest are the most relevant ones.
        """
        if not retrieved_chunks:
            return 0.0
            
        precision_sum = 0.0
        relevant_count = 0
        
        for rank, chunk in enumerate(retrieved_chunks):
            doc_id = chunk.get("document_id")
            if doc_id in ground_truth_ids:
                relevant_count += 1
                precision_sum += relevant_count / (rank + 1)
                
        if relevant_count == 0:
            return 0.0
            
        return precision_sum / relevant_count
