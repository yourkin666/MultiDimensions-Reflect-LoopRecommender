#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
推荐结果模型定义
"""

from datetime import datetime
from enum import Enum
from typing import Optional, List, Dict, Any, Union
from pydantic import BaseModel, Field, validator

from src.models.ticket_data import TicketData, FlightTicket, TrainTicket


class RecommendationReason(BaseModel):
    """推荐理由模型"""
    factor: str  # 推荐因子
    description: str  # 描述
    weight: float  # 权重
    score: float  # 得分


class RecommendationScore(BaseModel):
    """推荐评分模型"""
    # 多维度评估分数 (0-100)
    needs_match_score: float = Field(ge=0, le=100)  # 需求匹配度
    completeness_score: float = Field(ge=0, le=100)  # 选项完整性
    practicality_score: float = Field(ge=0, le=100)  # 实用性评估
    
    # 整体评分
    overall_score: float = Field(ge=0, le=100)
    
    @validator('overall_score', always=True)
    def calculate_overall_score(cls, v, values):
        """计算整体评分"""
        if v != 0:  # 如果已经设置了值，则返回
            return v
        
        # 默认权重
        weights = {
            'needs_match_score': 0.5,
            'completeness_score': 0.3,
            'practicality_score': 0.2
        }
        
        # 计算加权平均分
        total_score = 0
        for field, weight in weights.items():
            if field in values:
                total_score += values[field] * weight
                
        return round(total_score, 1)


class RecommendationOption(BaseModel):
    """推荐选项模型"""
    option_id: str
    ticket: Union[FlightTicket, TrainTicket]
    score: float = Field(ge=0, le=100)  # 该选项得分
    rank: int  # 排名
    reasons: List[RecommendationReason]  # 推荐理由
    
    # 可选的额外信息
    alternative_options: Optional[List[Dict[str, Any]]] = None  # 替代选项
    additional_info: Optional[Dict[str, Any]] = None  # 额外信息


class RecommendationStatus(str, Enum):
    """推荐状态枚举"""
    PENDING = "pending"          # 待处理
    PROCESSING = "processing"    # 处理中
    COMPLETED = "completed"      # 已完成
    FAILED = "failed"            # 失败
    REFINED = "refined"          # 已优化


class ReflectionFeedback(BaseModel):
    """反思反馈模型"""
    reflection_id: str
    iteration: int
    strengths: List[str]  # 优点
    weaknesses: List[str]  # 缺点
    improvement_suggestions: List[str]  # 改进建议
    adjusted_parameters: Optional[Dict[str, Any]] = None  # 调整的参数


class Recommendation(BaseModel):
    """推荐结果模型"""
    recommendation_id: str
    user_id: Optional[str] = None
    query_text: str  # 原始查询文本
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    
    # 推荐状态
    status: RecommendationStatus = RecommendationStatus.PENDING
    
    # 推荐选项
    options: List[RecommendationOption] = []
    
    # 评分
    scores: RecommendationScore
    
    # 反思循环
    reflection_iterations: int = 0  # 反思迭代次数
    reflection_history: List[ReflectionFeedback] = []  # 反思历史
    
    # 元数据
    processing_time_ms: Optional[int] = None  # 处理时间(毫秒)
    metadata: Optional[Dict[str, Any]] = None  # 元数据
    
    class Config:
        """配置"""
        json_encoders = {
            datetime: lambda dt: dt.isoformat()
        }
    
    def get_top_recommendation(self) -> Optional[RecommendationOption]:
        """获取得分最高的推荐"""
        if not self.options:
            return None
        
        return sorted(self.options, key=lambda x: x.score, reverse=True)[0]
    
    def add_reflection(self, feedback: ReflectionFeedback) -> None:
        """添加反思反馈"""
        self.reflection_history.append(feedback)
        self.reflection_iterations += 1
        self.updated_at = datetime.now() 