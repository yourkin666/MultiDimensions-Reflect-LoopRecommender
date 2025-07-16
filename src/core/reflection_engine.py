#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
反思循环推荐引擎
"""

import asyncio
import logging
import time
import uuid
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple

from src.models.user_needs import UserNeeds
from src.models.ticket_data import TicketData, FlightTicket, TrainTicket
from src.models.recommendation import (
    Recommendation, RecommendationOption, RecommendationReason,
    RecommendationScore, RecommendationStatus, ReflectionFeedback
)
from src.core.data_processor import DataProcessor
from src.core.evaluator import RecommendationEvaluator
from src.utils.llm_client import LLMClient


class ReflectionEngine:
    """反思循环推荐引擎"""
    
    def __init__(self, 
                 llm_client: LLMClient,
                 data_processor: DataProcessor,
                 evaluator: RecommendationEvaluator,
                 max_iterations: int = 3,
                 score_threshold: float = 85.0):
        """
        初始化反思引擎
        
        Args:
            llm_client: 大模型客户端
            data_processor: 数据处理器
            evaluator: 推荐评估器
            max_iterations: 最大迭代次数
            score_threshold: 评分阈值，高于该阈值则停止迭代
        """
        self.llm_client = llm_client
        self.data_processor = data_processor
        self.evaluator = evaluator
        self.max_iterations = max_iterations
        self.score_threshold = score_threshold
        self.logger = logging.getLogger(__name__)
    
    async def extract_user_needs(self, conversation_text: str) -> UserNeeds:
        """
        从对话文本中提取用户需求
        
        Args:
            conversation_text: 对话文本
            
        Returns:
            用户需求对象
        """
        self.logger.info("从对话中提取用户需求")
        # 使用LLM提取用户需求
        extracted_needs = await self.llm_client.extract_needs(conversation_text)
        return extracted_needs
    
    async def get_candidate_tickets(self, user_needs: UserNeeds) -> List[TicketData]:
        """
        获取候选票务数据
        
        Args:
            user_needs: 用户需求
            
        Returns:
            候选票务数据列表
        """
        self.logger.info("根据用户需求获取候选票务数据")
        tickets = await self.data_processor.fetch_matching_tickets(user_needs)
        self.logger.debug(f"找到 {len(tickets)} 个候选票")
        return tickets
    
    async def generate_recommendations(self, 
                                      user_needs: UserNeeds, 
                                      tickets: List[TicketData],
                                      query_text: str) -> Recommendation:
        """
        生成初始推荐方案
        
        Args:
            user_needs: 用户需求
            tickets: 候选票务数据
            query_text: 原始查询文本
            
        Returns:
            推荐结果
        """
        self.logger.info("生成初始推荐方案")
        start_time = time.time()
        
        # 创建推荐对象
        recommendation = Recommendation(
            recommendation_id=str(uuid.uuid4()),
            user_id=user_needs.user_id,
            query_text=query_text,
            status=RecommendationStatus.PROCESSING,
            scores=RecommendationScore(
                needs_match_score=0,
                completeness_score=0,
                practicality_score=0,
                overall_score=0
            )
        )
        
        # 对候选票务进行排序和筛选
        ranked_tickets = await self.data_processor.rank_tickets(tickets, user_needs)
        
        # 为每个票务创建推荐选项
        options = []
        for idx, (ticket, score, reasons) in enumerate(ranked_tickets[:10]):  # 最多取前10个
            recommendation_reasons = [
                RecommendationReason(
                    factor=factor,
                    description=description,
                    weight=weight,
                    score=factor_score
                )
                for factor, description, weight, factor_score in reasons
            ]
            
            option = RecommendationOption(
                option_id=str(uuid.uuid4()),
                ticket=ticket,
                score=score,
                rank=idx + 1,
                reasons=recommendation_reasons
            )
            options.append(option)
        
        recommendation.options = options
        
        # 计算处理时间
        end_time = time.time()
        recommendation.processing_time_ms = int((end_time - start_time) * 1000)
        
        return recommendation
    
    async def evaluate_recommendation(self, 
                                     recommendation: Recommendation, 
                                     user_needs: UserNeeds) -> Tuple[RecommendationScore, List[str]]:
        """
        评估推荐质量
        
        Args:
            recommendation: 推荐结果
            user_needs: 用户需求
            
        Returns:
            评分和改进建议
        """
        self.logger.info("评估推荐质量")
        return await self.evaluator.evaluate(recommendation, user_needs)
    
    async def reflect_and_improve(self, 
                                 recommendation: Recommendation,
                                 user_needs: UserNeeds,
                                 scores: RecommendationScore,
                                 improvement_suggestions: List[str]) -> Dict[str, Any]:
        """
        反思并改进
        
        Args:
            recommendation: 推荐结果
            user_needs: 用户需求
            scores: 评分
            improvement_suggestions: 改进建议
            
        Returns:
            调整后的参数
        """
        self.logger.info("反思并改进推荐方案")
        # 使用LLM分析改进方向并调整参数
        adjusted_params = await self.llm_client.reflect_and_adjust(
            recommendation, user_needs, scores, improvement_suggestions
        )
        return adjusted_params
    
    async def apply_improvements(self,
                               recommendation: Recommendation,
                               user_needs: UserNeeds,
                               adjusted_params: Dict[str, Any]) -> UserNeeds:
        """
        应用改进
        
        Args:
            recommendation: 推荐结果
            user_needs: 用户需求
            adjusted_params: 调整后的参数
            
        Returns:
            调整后的用户需求
        """
        self.logger.info("应用改进调整参数")
        # 创建用户需求的副本
        adjusted_needs = user_needs.copy(deep=True)
        
        # 应用参数调整
        for key, value in adjusted_params.items():
            # 使用嵌套字典的路径更新字段
            parts = key.split('.')
            target = adjusted_needs
            
            # 遍历路径直到最后一个部分
            for part in parts[:-1]:
                if hasattr(target, part):
                    target = getattr(target, part)
                else:
                    break
                    
            # 设置最终字段的值
            last_part = parts[-1]
            if hasattr(target, last_part):
                setattr(target, last_part, value)
        
        return adjusted_needs
    
    async def create_reflection_feedback(self,
                                       iteration: int,
                                       scores: RecommendationScore,
                                       improvement_suggestions: List[str],
                                       adjusted_params: Dict[str, Any]) -> ReflectionFeedback:
        """
        创建反思反馈
        
        Args:
            iteration: 迭代次数
            scores: 评分
            improvement_suggestions: 改进建议
            adjusted_params: 调整后的参数
            
        Returns:
            反思反馈
        """
        # 自动提取优缺点
        strengths, weaknesses = await self._extract_strengths_weaknesses(scores, improvement_suggestions)
        
        return ReflectionFeedback(
            reflection_id=str(uuid.uuid4()),
            iteration=iteration,
            strengths=strengths,
            weaknesses=weaknesses,
            improvement_suggestions=improvement_suggestions,
            adjusted_parameters=adjusted_params
        )
    
    async def _extract_strengths_weaknesses(self,
                                         scores: RecommendationScore,
                                         improvement_suggestions: List[str]) -> Tuple[List[str], List[str]]:
        """
        提取优缺点
        
        Args:
            scores: 评分
            improvement_suggestions: 改进建议
            
        Returns:
            优点和缺点列表
        """
        # 根据评分确定优势维度
        strengths = []
        if scores.needs_match_score >= 85:
            strengths.append("推荐方案很好地匹配了用户的核心需求")
        if scores.completeness_score >= 85:
            strengths.append("提供了全面且多样化的选择")
        if scores.practicality_score >= 85:
            strengths.append("推荐具有很高的实用性和便利性")
            
        # 从改进建议中提取缺点
        # 这里使用简单规则，实际应用中可以使用LLM分析
        weaknesses = []
        for suggestion in improvement_suggestions:
            if suggestion.startswith("改进") or "应该" in suggestion or "需要" in suggestion:
                # 简单转换为缺点表述
                weakness = suggestion.replace("改进", "").replace("应该", "缺乏").replace("需要", "缺乏")
                weaknesses.append(weakness)
        
        return strengths, weaknesses
    
    async def recommend(self, conversation_text: str) -> Recommendation:
        """
        执行完整的推荐流程
        
        Args:
            conversation_text: 对话文本
            
        Returns:
            最终推荐结果
        """
        self.logger.info("开始执行推荐流程")
        start_time = time.time()
        
        try:
            # 1. 提取用户需求
            user_needs = await self.extract_user_needs(conversation_text)
            
            # 2. 获取候选票务数据
            candidate_tickets = await self.get_candidate_tickets(user_needs)
            
            if not candidate_tickets:
                self.logger.warning("没有找到匹配的票务数据")
                # 创建空推荐结果
                return Recommendation(
                    recommendation_id=str(uuid.uuid4()),
                    user_id=user_needs.user_id,
                    query_text=conversation_text,
                    status=RecommendationStatus.FAILED,
                    scores=RecommendationScore(
                        needs_match_score=0,
                        completeness_score=0,
                        practicality_score=0,
                        overall_score=0
                    )
                )
            
            # 3. 生成初始推荐
            recommendation = await self.generate_recommendations(user_needs, candidate_tickets, conversation_text)
            
            # 4. 反思循环
            current_needs = user_needs
            
            for iteration in range(self.max_iterations):
                self.logger.info(f"开始第 {iteration+1} 次反思循环")
                
                # 4.1 评估推荐质量
                scores, improvement_suggestions = await self.evaluate_recommendation(recommendation, current_needs)
                recommendation.scores = scores
                
                # 4.2 检查是否达到质量阈值
                if scores.overall_score >= self.score_threshold:
                    self.logger.info(f"推荐质量已达到阈值({scores.overall_score} >= {self.score_threshold})，停止循环")
                    recommendation.status = RecommendationStatus.COMPLETED
                    break
                
                # 4.3 反思并改进
                adjusted_params = await self.reflect_and_improve(
                    recommendation, current_needs, scores, improvement_suggestions
                )
                
                # 4.4 应用改进
                current_needs = await self.apply_improvements(recommendation, current_needs, adjusted_params)
                
                # 4.5 创建反思反馈
                feedback = await self.create_reflection_feedback(
                    iteration + 1, scores, improvement_suggestions, adjusted_params
                )
                recommendation.add_reflection(feedback)
                
                # 4.6 使用调整后的需求重新生成推荐
                candidate_tickets = await self.get_candidate_tickets(current_needs)
                recommendation = await self.generate_recommendations(current_needs, candidate_tickets, conversation_text)
                
                # 设置状态为已优化
                recommendation.status = RecommendationStatus.REFINED
            
            # 5. 如果达到最大循环次数但仍未达到阈值
            if recommendation.status != RecommendationStatus.COMPLETED:
                self.logger.info("达到最大循环次数，返回当前最佳方案")
                recommendation.status = RecommendationStatus.COMPLETED
            
            # 计算总处理时间
            end_time = time.time()
            recommendation.processing_time_ms = int((end_time - start_time) * 1000)
            
            return recommendation
            
        except Exception as e:
            self.logger.error(f"推荐过程中发生错误: {str(e)}", exc_info=True)
            # 返回错误状态的推荐结果
            return Recommendation(
                recommendation_id=str(uuid.uuid4()),
                user_id=user_needs.user_id if 'user_needs' in locals() else None,
                query_text=conversation_text,
                status=RecommendationStatus.FAILED,
                scores=RecommendationScore(
                    needs_match_score=0,
                    completeness_score=0,
                    practicality_score=0,
                    overall_score=0
                ),
                metadata={"error": str(e)}
            ) 