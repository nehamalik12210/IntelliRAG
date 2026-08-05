from pydantic import BaseModel
from typing import Optional

class RetrievalSettingsUpdate(BaseModel):
    hybrid_fusion_method: Optional[str] = None
    hybrid_search_weight: Optional[float] = None
    top_k_retrieval: Optional[int] = None
    top_k_rerank: Optional[int] = None
    reranker_enabled: Optional[bool] = None

class RetrievalSettingsResponse(BaseModel):
    hybrid_fusion_method: str
    hybrid_search_weight: float
    top_k_retrieval: int
    top_k_rerank: int
    reranker_enabled: bool
