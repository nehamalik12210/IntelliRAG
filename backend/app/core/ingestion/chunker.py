"""Recursive character text chunker with metadata preservation.

Phase 1: Recursive character splitting with overlap + filename/page metadata.
Phase 2 (optional): Heading-aware chunking added as configurable option.
"""

import logging
from typing import Optional

from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.config import settings

logger = logging.getLogger(__name__)


def chunk_document(
    pages: list[dict],
    chunk_size: Optional[int] = None,
    chunk_overlap: Optional[int] = None,
) -> list[dict]:
    """Split document pages into overlapping chunks with preserved metadata.

    Each input page dict has 'content' and 'metadata'.
    Output chunks inherit the page metadata and add chunk-level info.

    Args:
        pages: List of page dicts from document loader
        chunk_size: Characters per chunk (default from config)
        chunk_overlap: Overlap between chunks (default from config)

    Returns:
        List of chunk dicts with 'content' and 'metadata'
    """
    chunk_size = chunk_size if chunk_size is not None else settings.chunk_size
    chunk_overlap = chunk_overlap if chunk_overlap is not None else settings.chunk_overlap

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        length_function=len,
        separators=["\n\n", "\n", ". ", " ", ""],
        is_separator_regex=False,
    )

    all_chunks = []
    global_index = 0

    for page in pages:
        text = page["content"]
        page_meta = page["metadata"]

        if not text.strip():
            continue

        # Split the page text into chunks
        texts = splitter.split_text(text)

        for chunk_text in texts:
            if not chunk_text.strip():
                continue

            chunk = {
                "content": chunk_text,
                "metadata": {
                    **page_meta,
                    "chunk_index": global_index,
                    "chunk_size": len(chunk_text),
                },
            }
            all_chunks.append(chunk)
            global_index += 1

    logger.info(
        f"Chunked {len(pages)} pages into {len(all_chunks)} chunks "
        f"(size={chunk_size}, overlap={chunk_overlap})"
    )
    return all_chunks
