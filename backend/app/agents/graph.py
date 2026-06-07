import logging
from typing import TypedDict, List, Dict, Any, Optional
from langgraph.graph import StateGraph, START, END

from app.agents.rewriter import QueryRewriterAgent
from app.agents.retriever import RetrieverAgent
from app.agents.reranker import RerankerAgent
from app.agents.verification import VerificationAgent
from app.agents.citation import CitationAgent
from app.agents.answer import AnswerAgent

logger = logging.getLogger(__name__)

class AgentState(TypedDict):
    query: str
    rewritten_query: str
    filters: Optional[Dict[str, Any]]
    chat_history: Optional[List[Dict[str, str]]]
    retrieved_chunks: List[Dict[str, Any]]
    reranked_chunks: List[Dict[str, Any]]
    citations: List[Dict[str, Any]]
    verification_passed: bool
    verification_feedback: str
    answer: str
    loop_count: int


# Initialize agents
rewriter_agent = QueryRewriterAgent()
retriever_agent = RetrieverAgent()
reranker_agent = RerankerAgent()
verification_agent = VerificationAgent()
citation_agent = CitationAgent()
answer_agent = AnswerAgent()


# Node functions
def rewrite_query_node(state: AgentState) -> Dict[str, Any]:
    query = state["query"]
    chat_history = state.get("chat_history", [])
    loop_count = state.get("loop_count", 0)
    
    # If this is a retry, append the feedback to the query to guide rewriter
    feedback = state.get("verification_feedback", "")
    if feedback and loop_count > 0:
        rewrite_prompt = f"{query} (Note: Previous search failed. Feedback: {feedback})"
    else:
        rewrite_prompt = query
        
    rewritten = rewriter_agent.run(rewrite_prompt, chat_history)
    return {
        "rewritten_query": rewritten,
        "loop_count": loop_count + 1
    }

from langchain_core.runnables import RunnableConfig

def retrieve_node(state: AgentState, config: RunnableConfig) -> Dict[str, Any]:
    rewritten_query = state["rewritten_query"]
    filters = state.get("filters", {})
    
    # Retrieve DB session from config
    db = config["configurable"].get("db")
    if not db:
        logger.error("Database session missing in config['configurable']['db']")
        return {"retrieved_chunks": []}
        
    chunks = retriever_agent.run(db=db, query=rewritten_query, filters=filters, limit=15)
    return {"retrieved_chunks": chunks}

def rerank_node(state: AgentState) -> Dict[str, Any]:
    query = state["query"]
    retrieved_chunks = state["retrieved_chunks"]
    
    ranked = reranker_agent.run(query=query, chunks=retrieved_chunks, limit=5)
    return {"reranked_chunks": ranked}

def verify_node(state: AgentState) -> Dict[str, Any]:
    query = state["query"]
    reranked_chunks = state["reranked_chunks"]
    
    result = verification_agent.run(query=query, chunks=reranked_chunks)
    return {
        "verification_passed": result.passed,
        "verification_feedback": result.feedback
    }

def generate_citations_node(state: AgentState) -> Dict[str, Any]:
    reranked_chunks = state["reranked_chunks"]
    
    citations = citation_agent.generate_citations(reranked_chunks)
    return {"citations": citations}

def generate_answer_node(state: AgentState) -> Dict[str, Any]:
    query = state["query"]
    reranked_chunks = state["reranked_chunks"]
    citations = state["citations"]
    verification_passed = state["verification_passed"]
    verification_feedback = state["verification_feedback"]
    
    # Synthesize answer
    raw_answer = answer_agent.run(
        query=query,
        chunks=reranked_chunks,
        citations=citations,
        verification_failed=not verification_passed,
        verification_feedback=verification_feedback
    )
    
    # Filter citations to only include those actually in response
    if verification_passed:
        final_answer, final_citations = citation_agent.filter_citations(raw_answer, citations)
    else:
        final_answer = raw_answer
        final_citations = []
        
    return {
        "answer": final_answer,
        "citations": final_citations
    }


# Routing logic
def route_after_verification(state: AgentState) -> str:
    passed = state["verification_passed"]
    loop_count = state["loop_count"]
    
    if passed:
        return "generate_citations"
    
    # Retry once if verification failed
    if loop_count < 2:
        logger.info(f"Verification failed (loop_count={loop_count}). Routing back to rewrite_query.")
        return "rewrite_query"
        
    logger.info("Verification failed twice. Moving directly to generate_answer to output rejection response.")
    return "generate_answer"


# Build the workflow Graph
workflow = StateGraph(AgentState)

# Add Nodes
workflow.add_node("rewrite_query", rewrite_query_node)
workflow.add_node("retrieve", retrieve_node)
workflow.add_node("rerank", rerank_node)
workflow.add_node("verify", verify_node)
workflow.add_node("generate_citations", generate_citations_node)
workflow.add_node("generate_answer", generate_answer_node)

# Set up edges
workflow.set_entry_point("rewrite_query")
workflow.add_edge("rewrite_query", "retrieve")
workflow.add_edge("retrieve", "rerank")
workflow.add_edge("rerank", "verify")

# Conditional edges after verification
workflow.add_conditional_edges(
    "verify",
    route_after_verification,
    {
        "rewrite_query": "rewrite_query",
        "generate_citations": "generate_citations",
        "generate_answer": "generate_answer"
    }
)

workflow.add_edge("generate_citations", "generate_answer")
workflow.add_edge("generate_answer", END)

# Compile graph
rag_graph = workflow.compile()
