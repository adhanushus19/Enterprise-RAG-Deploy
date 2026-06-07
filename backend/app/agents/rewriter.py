import logging
from pydantic import BaseModel, Field
from openai import OpenAI
from app.config import settings

logger = logging.getLogger(__name__)

class RewriterOutput(BaseModel):
    rewritten_query: str = Field(description="The expanded, search-optimized search query.")
    reason: str = Field(description="Reasoning behind the rewrite.")

class QueryRewriterAgent:
    """
    Agent responsible for analyzing the user's input query and rewriting it to optimize
    for retrieval (adding synonyms, resolving pronouns, and expanding context).
    """

    def __init__(self):
        self.client = None
        if settings.OPENAI_API_KEY:
            self.client = OpenAI(api_key=settings.OPENAI_API_KEY)

    def run(self, query: str, chat_history: list = None) -> str:
        if not self.client:
            logger.warning("No OpenAI Client initialized. Returning original query.")
            return query

        history_str = ""
        if chat_history:
            history_str = "\n".join([f"{msg['role']}: {msg['content']}" for msg in chat_history])

        system_prompt = (
            "You are a Query Expansion Agent in a corporate RAG pipeline. "
            "Your task is to rewrite the user's query to optimize it for vector search and keyword retrieval.\n"
            "- Resolve pronouns (e.g., 'their policy' -> 'company travel policy').\n"
            "- Add relevant domain terms or synonyms.\n"
            "- Remove conversational fillers ('please tell me', 'what is the value of').\n"
            "Respond strictly in the schema format."
        )

        user_prompt = f"User Chat History:\n{history_str}\n\nCurrent Query: {query}"

        try:
            response = self.client.beta.chat.completions.parse(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                response_format=RewriterOutput,
                temperature=0.0
            )
            rewritten = response.choices[0].message.parsed.rewritten_query
            logger.info(f"Original Query: '{query}' -> Rewritten: '{rewritten}'")
            return rewritten
        except Exception as e:
            logger.error(f"Query Rewriter Agent failed: {str(e)}")
            return query
