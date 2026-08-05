import logging
from typing import Optional
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.db.models import QueryLog
from app.config import settings

logger = logging.getLogger(__name__)

async def run_evaluation_async(query_log_id: str):
    """
    Run RAGAS reference-free metrics in the background for a specific QueryLog.
    This requires LLM evaluation, so we use LangChain's OpenAI Chat wrapper.
    """
    db: Optional[Session] = next(get_db())
    if not db:
        logger.error("Could not obtain DB session for evaluation")
        return

    try:
        log_entry = db.query(QueryLog).filter(QueryLog.id == query_log_id).first()
        if not log_entry:
            return

        if not log_entry.response or not log_entry.retrieved_chunks:
            return

        contexts = [c.get("content", "") for c in log_entry.retrieved_chunks if c.get("content")]
        if not contexts:
            return

        from langchain_openai import ChatOpenAI
        from langchain_core.prompts import PromptTemplate
        from pydantic import BaseModel, Field

        # Initialize the evaluator LLM using Groq (OpenAI compatible endpoint)
        evaluator_llm = ChatOpenAI(
            model="llama-3.1-8b-instant",
            api_key=settings.groq_api_key,
            base_url="https://api.groq.com/openai/v1",
            temperature=0,
        )

        from langchain_core.output_parsers import JsonOutputParser

        eval_prompt = PromptTemplate.from_template(
            "You are an expert evaluator. Evaluate the given Answer based on the Question and Contexts.\n\n"
            "Question: {question}\n\n"
            "Contexts: {contexts}\n\n"
            "Answer: {answer}\n\n"
            "Provide a JSON object with exactly two keys: 'faithfulness_score' (0.0 to 1.0) and 'answer_relevancy_score' (0.0 to 1.0).\n"
            "Output valid JSON only."
        )

        chain = eval_prompt | evaluator_llm.bind(response_format={"type": "json_object"}) | JsonOutputParser()
        
        logger.info(f"Starting async LLM evaluation for {query_log_id}...")
        
        result = chain.invoke({
            "question": log_entry.query,
            "contexts": "\n\n".join(contexts),
            "answer": log_entry.response
        })

        logger.info(f"Eval results for {query_log_id}: {result}")

        # Update QueryLog in DB
        log_entry.faithfulness_score = str(round(float(result.get("faithfulness_score", 0)), 4))
        log_entry.answer_relevancy_score = str(round(float(result.get("answer_relevancy_score", 0)), 4))
        
        db.commit()
        logger.info(f"Successfully saved evaluation for {query_log_id}")

    except Exception as e:
        logger.error(f"Error during async RAGAS evaluation: {e}")
        db.rollback()
    finally:
        db.close()
