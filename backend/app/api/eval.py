from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.db.database import get_db
from app.db.models import QueryLog, Message

router = APIRouter()

@router.get("/stats")
def get_eval_stats(db: Session = Depends(get_db)):
    """Get aggregated evaluation statistics and recent feedback."""
    
    # 1. RAGAS Averages
    # Since scores are stored as strings (e.g. "0.8523"), we'll query them all and avg in python for simplicity,
    # or just use cast in SQLite. For SQLite, casting string to float is easy.
    logs = db.query(
        QueryLog.faithfulness_score,
        QueryLog.answer_relevancy_score
    ).filter(QueryLog.faithfulness_score.isnot(None)).all()
    
    faithfulness_scores = [float(l.faithfulness_score) for l in logs if l.faithfulness_score]
    relevancy_scores = [float(l.answer_relevancy_score) for l in logs if l.answer_relevancy_score]
    
    avg_faithfulness = sum(faithfulness_scores) / len(faithfulness_scores) if faithfulness_scores else 0.0
    avg_relevancy = sum(relevancy_scores) / len(relevancy_scores) if relevancy_scores else 0.0
    
    # 2. Feedback Counts
    thumbs_up = db.query(func.count(Message.id)).filter(Message.feedback == "thumbs_up").scalar() or 0
    thumbs_down = db.query(func.count(Message.id)).filter(Message.feedback == "thumbs_down").scalar() or 0
    
    # 3. Recent negative feedback comments
    recent_feedback = db.query(Message.content, Message.feedback_comment, Message.created_at)\
        .filter(Message.feedback == "thumbs_down", Message.feedback_comment.isnot(None))\
        .order_by(Message.created_at.desc())\
        .limit(10)\
        .all()
        
    formatted_feedback = [
        {
            "message": f.content[:100] + "..." if len(f.content) > 100 else f.content,
            "comment": f.feedback_comment,
            "created_at": f.created_at.isoformat()
        } for f in recent_feedback
    ]
    
    return {
        "metrics": {
            "faithfulness": avg_faithfulness,
            "answer_relevancy": avg_relevancy,
            "total_evaluated": len(faithfulness_scores)
        },
        "feedback": {
            "thumbs_up": thumbs_up,
            "thumbs_down": thumbs_down,
            "recent_comments": formatted_feedback
        }
    }
