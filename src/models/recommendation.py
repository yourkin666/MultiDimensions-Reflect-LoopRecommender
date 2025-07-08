from pydantic import BaseModel, Field
from typing import List, Union
from .ticket_data import FlightTicket, TrainTicket

class Recommendation(BaseModel):
    """
    单个推荐项的数据模型
    """
    ticket: Union[FlightTicket, TrainTicket]
    recommendation_reason: str = Field(..., description="推荐理由")
    satisfaction_score: float = Field(..., description="预计满意度分数 (0-100)")

class RecommendationResult(BaseModel):
    """
    最终推荐结果的数据模型
    """
    recommendations: List[Recommendation]
    reflection_summary: str = Field(..., description="反思过程总结")
    reflection_cycles: int = Field(..., description="反思循环次数") 