from pydantic import BaseModel, Field
from typing import Optional, List

class UserNeeds(BaseModel):
    """
    用户需求数据模型
    """
    departure_city: str = Field(..., description="出发城市")
    arrival_city: str = Field(..., description="到达城市")
    departure_date: str = Field(..., description="出发日期，格式：YYYY-MM-DD")
    
    budget_range: Optional[List[int]] = Field(None, description="预算范围，例如 [500, 1000]")
    comfort_requirements: Optional[List[str]] = Field(None, description="舒适度要求，例如 ['商务座', '直飞']")
    special_needs: Optional[List[str]] = Field(None, description="特殊需求")
    implicit_preferences: Optional[List[str]] = Field(None, description="从对话中推断的隐性偏好") 