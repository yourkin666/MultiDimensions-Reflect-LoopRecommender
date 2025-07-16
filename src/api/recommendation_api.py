#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
推荐系统API接口
"""

import json
import logging
import uuid
from datetime import datetime
from typing import Dict, Any, List, Optional

from sanic import Blueprint, Sanic
from sanic.response import json as sanic_json
from sanic.request import Request
from sanic_ext import validate

from pydantic import BaseModel, Field

from src.core.reflection_engine import ReflectionEngine
from src.core.data_processor import DataProcessor
from src.core.evaluator import RecommendationEvaluator
from src.utils.llm_client import LLMClient
from src.models.user_needs import UserNeeds
from src.models.recommendation import Recommendation, RecommendationStatus


# 定义API请求和响应模型
class RecommendationRequest(BaseModel):
    """推荐请求模型"""
    conversation_text: str = Field(..., description="用户对话文本")
    user_id: Optional[str] = Field(None, description="用户ID")
    max_iterations: Optional[int] = Field(3, description="最大反思迭代次数")
    score_threshold: Optional[float] = Field(85.0, description="评分阈值")


class ReflectionRequest(BaseModel):
    """反思请求模型"""
    recommendation_id: str = Field(..., description="推荐ID")
    feedback: Optional[str] = Field(None, description="用户反馈")


# 创建蓝图
recommendation_bp = Blueprint("recommendations", url_prefix="/api/v1")

# 全局引擎实例
engine: Optional[ReflectionEngine] = None
# 内存中的推荐结果缓存 (在实际应用中应使用Redis等缓存系统)
recommendation_cache: Dict[str, Recommendation] = {}


def setup_routes(app: Sanic) -> None:
    """
    设置路由
    
    Args:
        app: Sanic应用实例
    """
    global engine
    
    # 初始化日志
    logger = logging.getLogger(__name__)
    
    # 初始化组件
    llm_client = LLMClient()
    data_processor = DataProcessor()
    evaluator = RecommendationEvaluator(llm_client)
    
    # 创建反思引擎
    engine = ReflectionEngine(
        llm_client=llm_client,
        data_processor=data_processor,
        evaluator=evaluator
    )
    
    # 注册蓝图
    app.blueprint(recommendation_bp)
    
    logger.info("API路由设置完成")


@recommendation_bp.route("/recommendations", methods=["POST"])
async def create_recommendation(request: Request) -> Dict[str, Any]:
    """
    创建推荐
    
    Args:
        request: HTTP请求
        
    Returns:
        推荐结果
    """
    try:
        # 解析请求数据
        data = request.json
        req = RecommendationRequest(**data)
        
        # 执行推荐
        recommendation = await engine.recommend(req.conversation_text)
        
        # 缓存推荐结果
        recommendation_cache[recommendation.recommendation_id] = recommendation
        
        # 返回响应
        return sanic_json({
            "status": "success",
            "recommendation_id": recommendation.recommendation_id,
            "recommendation": recommendation.dict(),
            "processing_time_ms": recommendation.processing_time_ms
        })
        
    except Exception as e:
        logging.error(f"创建推荐时出错: {str(e)}", exc_info=True)
        return sanic_json({
            "status": "error",
            "message": f"创建推荐时出错: {str(e)}"
        }, status=500)


@recommendation_bp.route("/recommendations/<recommendation_id>", methods=["GET"])
async def get_recommendation(request: Request, recommendation_id: str) -> Dict[str, Any]:
    """
    获取推荐
    
    Args:
        request: HTTP请求
        recommendation_id: 推荐ID
        
    Returns:
        推荐结果
    """
    try:
        if recommendation_id not in recommendation_cache:
            return sanic_json({
                "status": "error",
                "message": f"找不到ID为 {recommendation_id} 的推荐"
            }, status=404)
            
        recommendation = recommendation_cache[recommendation_id]
        
        return sanic_json({
            "status": "success",
            "recommendation": recommendation.dict()
        })
        
    except Exception as e:
        logging.error(f"获取推荐时出错: {str(e)}", exc_info=True)
        return sanic_json({
            "status": "error",
            "message": f"获取推荐时出错: {str(e)}"
        }, status=500)


@recommendation_bp.route("/recommendations/<recommendation_id>/reflect", methods=["POST"])
async def reflect_recommendation(request: Request, recommendation_id: str) -> Dict[str, Any]:
    """
    对推荐进行反思
    
    Args:
        request: HTTP请求
        recommendation_id: 推荐ID
        
    Returns:
        反思结果
    """
    try:
        if recommendation_id not in recommendation_cache:
            return sanic_json({
                "status": "error",
                "message": f"找不到ID为 {recommendation_id} 的推荐"
            }, status=404)
            
        # 获取当前推荐
        recommendation = recommendation_cache[recommendation_id]
        
        # 解析请求数据
        data = request.json
        req = ReflectionRequest(recommendation_id=recommendation_id, **data)
        
        # 获取用户需求 (在实际应用中应从数据库获取)
        # 这里简单从推荐结果的查询文本中重新提取
        user_needs = await engine.extract_user_needs(recommendation.query_text)
        
        if req.feedback:
            # 如果有用户反馈，更新用户需求
            # 在实际应用中，这里应该根据用户反馈调整需求
            updated_needs = await engine.llm_client.extract_needs(req.feedback)
            user_needs = updated_needs
        
        # 评估当前推荐
        scores, suggestions = await engine.evaluator.evaluate(recommendation, user_needs)
        
        # 反思并改进
        adjusted_params = await engine.reflect_and_improve(recommendation, user_needs, scores, suggestions)
        
        # 应用改进
        updated_needs = await engine.apply_improvements(recommendation, user_needs, adjusted_params)
        
        # 获取候选票务
        tickets = await engine.get_candidate_tickets(updated_needs)
        
        # 生成新的推荐
        new_recommendation = await engine.generate_recommendations(
            updated_needs, tickets, recommendation.query_text
        )
        
        # 创建反思反馈
        feedback = await engine.create_reflection_feedback(
            recommendation.reflection_iterations + 1,
            scores,
            suggestions,
            adjusted_params
        )
        
        # 更新新推荐的信息
        new_recommendation.reflection_iterations = recommendation.reflection_iterations + 1
        new_recommendation.reflection_history = recommendation.reflection_history + [feedback]
        new_recommendation.status = RecommendationStatus.REFINED
        
        # 缓存新的推荐结果
        recommendation_cache[new_recommendation.recommendation_id] = new_recommendation
        
        return sanic_json({
            "status": "success",
            "previous_recommendation_id": recommendation_id,
            "new_recommendation_id": new_recommendation.recommendation_id,
            "reflection_feedback": feedback.dict(),
            "new_recommendation": new_recommendation.dict()
        })
        
    except Exception as e:
        logging.error(f"反思推荐时出错: {str(e)}", exc_info=True)
        return sanic_json({
            "status": "error",
            "message": f"反思推荐时出错: {str(e)}"
        }, status=500)


@recommendation_bp.route("/health", methods=["GET"])
async def health_check(request: Request) -> Dict[str, Any]:
    """
    健康检查
    
    Args:
        request: HTTP请求
        
    Returns:
        健康状态
    """
    return sanic_json({
        "status": "ok",
        "timestamp": datetime.now().isoformat(),
        "service": "多维度反思循环推荐系统",
        "version": "1.0.0"
    }) 