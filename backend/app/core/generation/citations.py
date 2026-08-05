"""Citation extraction from LLM responses.

Parses source citations from generated text and formats them
for the frontend source panel.
"""

import re
import logging
from typing import Optional

logger = logging.getLogger(__name__)


def extract_citations(
    response_text: str,
    retrieved_chunks: list[dict],
) -> list[dict]:
    """Extract and format source citations from retrieved chunks.

    Rather than parsing citations from LLM text (which is fragile),
    we return the retrieved chunks as sources — the frontend shows them
    as clickable citations beneath each response.

    Args:
        response_text: The generated response text
        retrieved_chunks: Chunks that were used as context

    Returns:
        List of citation dicts for the frontend
    """
    citations = []
    seen = set()

    for chunk in retrieved_chunks:
        payload = chunk.get("payload", {})
        filename = payload.get("source_filename", "Unknown")
        page = payload.get("page_number", 0)
        chunk_id = chunk.get("id", "")
        score = chunk.get("score", 0.0)

        # Deduplicate by filename + page
        dedup_key = f"{filename}:{page}"
        if dedup_key in seen:
            continue
        seen.add(dedup_key)

        citations.append({
            "filename": filename,
            "page_number": page,
            "chunk_id": chunk_id,
            "relevance_score": round(score, 4) if isinstance(score, float) else score,
            "content_preview": (payload.get("content", "")[:200] + "...")
                if len(payload.get("content", "")) > 200
                else payload.get("content", ""),
        })

    return citations
