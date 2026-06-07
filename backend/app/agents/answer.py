import logging
from typing import List, Dict, Any, Optional
from openai import OpenAI
from app.config import settings

logger = logging.getLogger(__name__)

class AnswerAgent:
    """
    Agent responsible for synthesizing the final response. It takes the retrieved, reranked,
    and verified chunks, formats them, and instructs the LLM to construct a comprehensive answer
    with exact inline citations.
    """

    def __init__(self):
        self.client = None
        if settings.OPENAI_API_KEY:
            self.client = OpenAI(api_key=settings.OPENAI_API_KEY)

    def run(self, query: str, chunks: List[Dict[str, Any]], citations: List[Dict[str, Any]], verification_failed: bool = False, verification_feedback: str = "") -> str:
        if not self.client:
            logger.warning("No OpenAI Client. Returning placeholder response.")
            return "OpenAI API client is not configured. Please set the OPENAI_API_KEY environment variable."

        if verification_failed:
            return (
                f"I cannot fully answer your question based on the ingested documents.\n\n"
                f"**System Check Feedback:** {verification_feedback}\n\n"
                "Please upload documents containing this information or adjust your search query."
            )

        context_str = ""
        for citation in citations:
            # Map index
            context_str += f"[{citation['id']}] (Source: {citation['filename']}, Page: {citation['page_number']}): {citation['snippet']}\n\n"

        system_prompt = (
            "You are an Enterprise AI Knowledge Assistant. Synthesize a clear, detailed, "
            "and professional answer to the user's query using ONLY the provided context chunks.\n"
            "- Ground every single claim in the provided context.\n"
            "- Add inline citations in the format [id] (e.g. '[1]') at the end of the sentence or clause supporting the claim.\n"
            "- Do not write a separate bibliography or citations list at the end of the response; just insert the inline tags.\n"
            "- Do not extrapolate or assume. If the context does not answer the question, state that the documents do not contain the answer."
        )

        user_prompt = f"User Query: {query}\n\nContext:\n{context_str}"

        try:
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.0
            )
            answer = response.choices[0].message.content
            logger.info("Answer Agent successfully generated answer.")
            return answer
        except Exception as e:
            logger.error(f"Answer Agent failed: {str(e)}", exc_info=True)
            return "An internal error occurred while generating the answer. Please try again."
