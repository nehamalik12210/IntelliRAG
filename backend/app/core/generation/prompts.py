"""Prompt templates for RAG generation with citation instructions."""

RAG_SYSTEM_PROMPT = """You are IntelliRAG, a helpful AI assistant that answers questions based on the provided context from the user's knowledge base.

## Rules
1. Answer ONLY based on the provided context. If the context doesn't contain enough information, say "I don't have enough information in the provided documents to answer this question."
2. Be accurate and concise. Do not make up information.
3. Always cite your sources using the format [Source: filename, Page X] at the end of relevant statements.
4. If multiple sources support an answer, cite all of them.
5. Use markdown formatting for better readability (headers, lists, code blocks where appropriate).
6. If the user asks a follow-up question, use the conversation history for context but still ground your answer in the provided documents.
7. CRITICAL: NEVER output or reprint the raw `### Source X: ...` context blocks in your response. Synthesize the answer using your own words and only use the short citation format mentioned in Rule 3.
8. Make logical inferences when the user uses personal pronouns (e.g., "my", "I"). If they ask "what is my name" and the document is a resume or CV, assume the user is the person named in the document."""

RAG_USER_PROMPT_TEMPLATE = """## Context from Knowledge Base
{context}

## User Question
{question}

Please answer the question based on the context above. Remember to cite your sources."""

NO_CONTEXT_RESPONSE = """I couldn't find any relevant information in your knowledge base to answer this question. 

You can try:
- Rephrasing your question
- Uploading more relevant documents to your knowledge base
- Checking if the correct knowledge base is selected"""


def build_rag_messages(
    question: str,
    context_chunks: list[dict],
    conversation_history: list[dict] = None,
) -> list[dict]:
    """Build the message list for RAG generation.

    Args:
        question: The user's question
        context_chunks: Retrieved chunks with 'content' and 'payload'
        conversation_history: Prior messages in the conversation

    Returns:
        List of message dicts ready for the LLM
    """
    messages = [{"role": "system", "content": RAG_SYSTEM_PROMPT}]

    # Add conversation history (last 10 messages for context window management)
    if conversation_history:
        for msg in conversation_history[-10:]:
            if msg["role"] in ("user", "assistant"):
                messages.append({"role": msg["role"], "content": msg["content"]})

    # Build context string from retrieved chunks
    if not context_chunks:
        messages.append({"role": "user", "content": question})
        return messages

    context_parts = []
    for i, chunk in enumerate(context_chunks, 1):
        payload = chunk.get("payload", {})
        filename = payload.get("source_filename", "Unknown")
        page = payload.get("page_number", "?")
        content = payload.get("content", chunk.get("content", ""))
        context_parts.append(
            f"### Source {i}: {filename} (Page {page})\n{content}"
        )

    context_str = "\n\n---\n\n".join(context_parts)

    user_msg = RAG_USER_PROMPT_TEMPLATE.format(
        context=context_str,
        question=question,
    )
    messages.append({"role": "user", "content": user_msg})

    return messages
