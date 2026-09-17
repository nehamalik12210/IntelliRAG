import logging
from typing import Optional

from sqlalchemy.orm import Session

from app.db.database import get_db
from app.db.models import QueryLog
from app.config import settings

logger = logging.getLogger(__name__)


async def run_evaluation_async(query_log_id: str):
    """
    Run reference-free LLM evaluation in the background
    for a specific QueryLog.

    The evaluator uses Groq through LangChain's
    OpenAI-compatible ChatOpenAI wrapper.
    """

    db: Optional[Session] = next(get_db())

    if not db:
        logger.error(
            "Could not obtain DB session for evaluation"
        )
        return

    try:
        # ─────────────────────────────────────────────
        # Retrieve query log
        # ─────────────────────────────────────────────
        log_entry = (
            db.query(QueryLog)
            .filter(QueryLog.id == query_log_id)
            .first()
        )

        if not log_entry:
            logger.warning(
                f"QueryLog {query_log_id} not found"
            )
            return

        # No answer or retrieval context
        if (
            not log_entry.response
            or not log_entry.retrieved_chunks
        ):
            return

        contexts = [
            c.get("content", "")
            for c in log_entry.retrieved_chunks
            if c.get("content")
        ]

        if not contexts:
            return

        # ─────────────────────────────────────────────
        # Imports
        # ─────────────────────────────────────────────
        from langchain_openai import ChatOpenAI
        from langchain_core.prompts import PromptTemplate
        from langchain_core.output_parsers import JsonOutputParser
        from pydantic import BaseModel, Field

        # ─────────────────────────────────────────────
        # Evaluation output schema
        # ─────────────────────────────────────────────
        class EvaluationResult(BaseModel):
            faithfulness_score: float = Field(
                ge=0.0,
                le=1.0,
            )

            answer_relevancy_score: float = Field(
                ge=0.0,
                le=1.0,
            )

        # ─────────────────────────────────────────────
        # Check Groq API key
        # ─────────────────────────────────────────────
        if not settings.groq_api_key:
            logger.warning(
                "GROQ_API_KEY is not configured. "
                "Skipping RAG evaluation."
            )
            return

        # ─────────────────────────────────────────────
        # Evaluation LLM
        # ─────────────────────────────────────────────
        #
        # Use the configured Groq model instead of
        # hard-coding an old/deprecated model.
        #
        evaluator_llm = ChatOpenAI(
            model=settings.default_llm_model,
            api_key=settings.groq_api_key,
            base_url="https://api.groq.com/openai/v1",
            temperature=0,
        )

        # ─────────────────────────────────────────────
        # Evaluation prompt
        # ─────────────────────────────────────────────
        eval_prompt = PromptTemplate.from_template(
            """
You are an expert evaluator for a Retrieval-Augmented
Generation (RAG) system.

Evaluate the generated answer using the question and
retrieved context.

Question:
{question}

Retrieved Context:
{contexts}

Generated Answer:
{answer}

Evaluate the answer on two dimensions:

1. faithfulness_score:
   How well is the answer supported by the retrieved
   context?
   Score from 0.0 to 1.0.

2. answer_relevancy_score:
   How directly and appropriately does the answer
   address the user's question?
   Score from 0.0 to 1.0.

Return ONLY valid JSON with exactly these two keys:

{{
    "faithfulness_score": 0.0,
    "answer_relevancy_score": 0.0
}}

Do not include explanations outside the JSON.
"""
        )

        # ─────────────────────────────────────────────
        # Build evaluation chain
        # ─────────────────────────────────────────────
        chain = (
            eval_prompt
            | evaluator_llm.bind(
                response_format={
                    "type": "json_object"
                }
            )
            | JsonOutputParser()
        )

        logger.info(
            f"Starting LLM evaluation for "
            f"{query_log_id} using "
            f"{settings.default_llm_model}"
        )

        # ─────────────────────────────────────────────
        # Run evaluation
        # ─────────────────────────────────────────────
        result = chain.invoke(
            {
                "question": log_entry.query,
                "contexts": "\n\n".join(contexts),
                "answer": log_entry.response,
            }
        )

        logger.info(
            f"Evaluation result for "
            f"{query_log_id}: {result}"
        )

        # ─────────────────────────────────────────────
        # Validate scores
        # ─────────────────────────────────────────────
        faithfulness = float(
            result.get("faithfulness_score", 0)
        )

        relevancy = float(
            result.get("answer_relevancy_score", 0)
        )

        # Keep values inside expected range
        faithfulness = max(
            0.0,
            min(1.0, faithfulness)
        )

        relevancy = max(
            0.0,
            min(1.0, relevancy)
        )

        # ─────────────────────────────────────────────
        # Save evaluation results
        # ─────────────────────────────────────────────
        log_entry.faithfulness_score = str(
            round(faithfulness, 4)
        )

        log_entry.answer_relevancy_score = str(
            round(relevancy, 4)
        )

        db.commit()

        logger.info(
            f"Successfully saved evaluation "
            f"for {query_log_id}"
        )

    except Exception as e:
        logger.exception(
            f"Error during async RAGAS evaluation: {e}"
        )

        db.rollback()

    finally:
        db.close()
