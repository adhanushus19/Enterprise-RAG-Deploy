import logging
from typing import List, Dict, Any
from pydantic import BaseModel, Field
from openai import OpenAI
from app.config import settings

logger = logging.getLogger(__name__)

class VerificationOutput(BaseModel):
    passed: bool = Field(description="True if the provided chunks contain enough facts to answer the query. False if the query cannot be answered based on the chunks.")
    feedback: str = Field(description="If failed, explain what is missing. If passed, provide a brief summary of available facts.")

class VerificationAgent:
    """
    Agent responsible for verifying that the reranked chunks contain sufficient, factual
    information to resolve the user's query, preventing hallucinations.
    """

    def __init__(self):
        self.client = None
        if settings.OPENAI_API_KEY:
            self.client = OpenAI(api_key=settings.OPENAI_API_KEY)

    def run(self, query: str, chunks: List[Dict[str, Any]]) -> VerificationOutput:
        if not chunks:
            return VerificationOutput(passed=False, feedback="No document chunks were retrieved.")
        if not self.client:
            logger.warning("No OpenAI Client. Skipping verification (auto-pass).")
            return VerificationOutput(passed=True, feedback="Skipped verification due to missing client.")

        context_str = ""
        for idx, chunk in enumerate(chunks):
            context_str += f"[{idx}] (File: {chunk['filename']}): {chunk['content']}\n\n"

        system_prompt = (
            "You are a Context Verification Agent. Assess if the provided context chunks "
            "contain sufficient factual evidence to answer the user query.\n"
            "- If the query is an out-of-context question or requires facts not present in the documents, set passed to False.\n"
            "- If the chunks contain partial information but cannot fully answer, set passed to False and specify what is missing.\n"
            "- Only set passed to True if there is enough source material to formulate a factual answer."
        )

        user_prompt = f"Query: {query}\n\nContext Chunks:\n{context_str}"

        try:
            response = self.client.beta.chat.completions.parse(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                response_format=VerificationOutput,
                temperature=0.0
            )
            result = response.choices[0].message.parsed
            logger.info(f"Verification: passed={result.passed}, feedback='{result.feedback}'")
            return result
        except Exception as e:
            logger.error(f"Verification Agent failed: {str(e)}", exc_info=True)
            # Default fallback: pass to let Answer Agent handle it with its own system prompt
            return VerificationOutput(passed=True, feedback="Verification errored, bypassed to Answer Agent.")
