import logging
import re
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

class CitationAgent:
    """
    Agent responsible for generating structured citation objects and filtering them
    to include only those referenced inside the generated answer text.
    """

    def generate_citations(self, chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Builds a base list of formatted citation objects from the retrieved chunks.
        Each chunk is assigned a 1-based index corresponding to [1], [2], etc.
        """
        citations = []
        for idx, chunk in enumerate(chunks):
            citations.append({
                "id": idx + 1,
                "document_id": chunk["document_id"],
                "filename": chunk["filename"],
                "page_number": chunk["page_number"],
                "author": chunk["author"],
                "department": chunk["department"],
                "doc_type": chunk["doc_type"],
                "snippet": chunk["content"][:200] + "..." if len(chunk["content"]) > 200 else chunk["content"]
            })
        return citations

    def filter_citations(self, answer: str, citations: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Scans the answer text for inline citations like [1], [2], [3] and returns
        only the citation objects that are actually referenced in the text.
        Also re-indexes the citations in the text and list if necessary (to ensure sequential numbers).
        """
        # Find all numbers within square brackets in the answer (e.g. "[1]", "[2]")
        referenced_ids = [int(num) for num in re.findall(r'\[(\d+)\]', answer)]
        unique_referenced_ids = sorted(list(set(referenced_ids)))
        
        logger.info(f"Answer contains citations: {unique_referenced_ids}")
        
        filtered = []
        id_mapping = {}
        new_id = 1
        
        # Build mapping and filtered list of citations
        for old_id in unique_referenced_ids:
            matching_citation = next((c for c in citations if c["id"] == old_id), None)
            if matching_citation:
                # Create a copy with the new sequential ID
                citation_copy = matching_citation.copy()
                citation_copy["id"] = new_id
                filtered.append(citation_copy)
                id_mapping[old_id] = new_id
                new_id += 1

        # Replace citation numbers in the answer text to match the new sequential IDs
        def replace_match(match):
            old_num = int(match.group(1))
            new_num = id_mapping.get(old_num, old_num)
            return f"[{new_num}]"

        updated_answer = re.sub(r'\[(\d+)\]', replace_match, answer)

        return updated_answer, filtered
