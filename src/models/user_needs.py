#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
用户需求模型定义
"""

from datetime import datetime, time
from enum import Enum
from typing import Optional, List, Dict, Any, Union
from pydantic import BaseModel, Field, validator

from src.models.ticket_data import TransportType, SeatClass


class TimePreference(str, Enum):
    """时间偏好枚举"""
    MORNING = "morning"      # 上午
    AFTERNOON = "afternoon"  # 下午
    EVENING = "evening"      # 晚上
    NIGHT = "night"          # 夜间
    ANY = "any"              # 任意时间


class PriceLevel(str, Enum):
    """价格水平枚举"""
    ECONOMY = "economy"      # 经济型
    STANDARD = "standard"    # 标准型
    PREMIUM = "premium"      # 高端型
    LUXURY = "luxury"        # 奢华型
    ANY = "any"              # 任意价格


class TravelPriority(str, Enum):
    """旅行优先级枚举"""
    PRICE = "price"          # 价格优先
    TIME = "time"            # 时间优先
    COMFORT = "comfort"      # 舒适度优先
    CONVENIENCE = "convenience"  # 便利性优先
    RELIABILITY = "reliability"  # 可靠性优先


class TimeRange(BaseModel):
    """时间范围模型"""
    start_time: Optional[Union[datetime, time]] = None
    end_time: Optional[Union[datetime, time]] = None
    flexible_hours: Optional[int] = None  # 灵活小时数
    preferred_time: Optional[TimePreference] = None


class BudgetRange(BaseModel):
    """预算范围模型"""
    min_price: Optional[float] = None
    max_price: Optional[float] = None
    target_price: Optional[float] = None
    price_level: Optional[PriceLevel] = PriceLevel.ANY


class SpecialRequirement(BaseModel):
    """特殊需求模型"""
    requirement_type: str
    description: str
    importance: int = Field(ge=1, le=10)  # 1-10的重要性评分


class UserNeeds(BaseModel):
    """用户需求模型"""
    user_id: Optional[str] = None
    
    # 基本旅行信息
    departure_city: str
    arrival_city: str
    departure_time_range: TimeRange
    return_time_range: Optional[TimeRange] = None  # 往返需求
    
    # 交通偏好
    preferred_transport_types: List[TransportType] = [TransportType.FLIGHT, TransportType.TRAIN]
    preferred_seat_classes: Optional[List[SeatClass]] = None
    
    # 经济因素
    budget: BudgetRange = BudgetRange()
    
    # 优先级和偏好
    priorities: List[TravelPriority] = [TravelPriority.PRICE]
    max_transfers: Optional[int] = None  # 最大中转次数
    max_duration_minutes: Optional[int] = None  # 最大行程时间(分钟)
    
    # 特殊需求
    special_requirements: Optional[List[SpecialRequirement]] = None
    
    # 历史偏好数据
    historical_preference: Optional[Dict[str, Any]] = None
    
    @validator('priorities')
    def check_priorities(cls, priorities):
        """验证优先级列表"""
        if not priorities:
            return [TravelPriority.PRICE]  # 默认价格优先
        return priorities
    
    class Config:
        """配置"""
        json_encoders = {
            datetime: lambda dt: dt.isoformat(),
            time: lambda t: t.isoformat()
        }
    
    @classmethod
    def extract_from_conversation(cls, conversation_text: str) -> "UserNeeds":
        """从对话文本中提取用户需求"""
        # 这里将来会接入LLM进行提取
        # 目前返回一个简单的默认值作为示例
        return cls(
            departure_city="北京",
            arrival_city="上海",
            departure_time_range=TimeRange(
                start_time=datetime.now(),
                preferred_time=TimePreference.ANY
            )
        ) 