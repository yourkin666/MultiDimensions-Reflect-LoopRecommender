#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
推荐评估器
"""

import logging
from typing import List, Dict, Any, Tuple, Optional
import asyncio

from src.models.user_needs import UserNeeds
from src.models.recommendation import Recommendation, RecommendationScore
from src.utils.llm_client import LLMClient


class RecommendationEvaluator:
    """推荐评估器"""
    
    def __init__(self, llm_client: Optional[LLMClient] = None):
        """
        初始化评估器
        
        Args:
            llm_client: 大模型客户端，用于生成反思评估
        """
        self.logger = logging.getLogger(__name__)
        self.llm_client = llm_client
        
    async def evaluate(self, recommendation: Recommendation, user_needs: UserNeeds) -> Tuple[RecommendationScore, List[str]]:
        """
        评估推荐质量
        
        Args:
            recommendation: 推荐结果
            user_needs: 用户需求
            
        Returns:
            评分和改进建议
        """
        self.logger.info("开始评估推荐质量")
        
        # 如果没有推荐选项，返回零分
        if not recommendation.options:
            return RecommendationScore(
                needs_match_score=0,
                completeness_score=0,
                practicality_score=0,
                overall_score=0
            ), ["没有找到匹配的推荐选项"]
        
        # 获取三个维度的评分
        needs_match_score = await self._evaluate_needs_match(recommendation, user_needs)
        completeness_score = await self._evaluate_completeness(recommendation, user_needs)
        practicality_score = await self._evaluate_practicality(recommendation, user_needs)
        
        # 创建评分对象
        scores = RecommendationScore(
            needs_match_score=needs_match_score,
            completeness_score=completeness_score,
            practicality_score=practicality_score
        )
        
        # 获取改进建议
        improvement_suggestions = await self._generate_improvement_suggestions(recommendation, user_needs, scores)
        
        self.logger.info(f"评估完成: 需求匹配={scores.needs_match_score}, 完整性={scores.completeness_score}, 实用性={scores.practicality_score}, 总分={scores.overall_score}")
        return scores, improvement_suggestions
    
    async def _evaluate_needs_match(self, recommendation: Recommendation, user_needs: UserNeeds) -> float:
        """
        评估需求匹配度
        
        Args:
            recommendation: 推荐结果
            user_needs: 用户需求
            
        Returns:
            需求匹配度评分
        """
        # 如果有LLM客户端，使用LLM评估
        if self.llm_client:
            return await self.llm_client.evaluate_needs_match(recommendation, user_needs)
        
        # 否则使用规则进行评估
        # 这是简化实现，实际系统可能需要更复杂的评估逻辑
        
        score = 80.0  # 基础分
        
        # 检查前3个推荐选项
        top_options = recommendation.options[:min(3, len(recommendation.options))]
        
        # 检查交通方式偏好
        transport_match = any(option.ticket.transport_type in user_needs.preferred_transport_types for option in top_options)
        score += 5 if transport_match else -10
        
        # 检查座位等级偏好
        if user_needs.preferred_seat_classes:
            seat_match = any(option.ticket.seat_class in user_needs.preferred_seat_classes for option in top_options)
            score += 5 if seat_match else -5
        
        # 检查预算符合度
        if user_needs.budget.max_price:
            price_match = all(option.ticket.price <= user_needs.budget.max_price for option in top_options)
            score += 10 if price_match else -15
        
        # 检查时间符合度
        if user_needs.departure_time_range.start_time and user_needs.departure_time_range.end_time:
            time_match = any(
                user_needs.departure_time_range.start_time <= option.ticket.departure_time <= user_needs.departure_time_range.end_time
                for option in top_options
            )
            score += 10 if time_match else -15
            
        # 确保分数在0-100范围内
        return max(0, min(100, score))
    
    async def _evaluate_completeness(self, recommendation: Recommendation, user_needs: UserNeeds) -> float:
        """
        评估选项完整性
        
        Args:
            recommendation: 推荐结果
            user_needs: 用户需求
            
        Returns:
            选项完整性评分
        """
        # 如果有LLM客户端，使用LLM评估
        if self.llm_client:
            return await self.llm_client.evaluate_completeness(recommendation, user_needs)
        
        # 否则使用规则进行评估
        score = 75.0  # 基础分
        
        # 评估选项数量
        option_count = len(recommendation.options)
        if option_count >= 5:
            score += 10
        elif option_count >= 3:
            score += 5
        elif option_count == 1:
            score -= 10
        elif option_count == 0:
            return 0  # 没有选项，直接返回0分
            
        # 评估选项多样性
        transport_types = {option.ticket.transport_type for option in recommendation.options}
        score += min(10, len(transport_types) * 5)  # 每种交通方式加5分，最多加10分
        
        # 评估价格范围
        if option_count > 1:
            prices = [option.ticket.price for option in recommendation.options]
            price_range = max(prices) - min(prices)
            avg_price = sum(prices) / len(prices)
            # 如果价格范围适中（不会过宽也不会过窄）
            if price_range > 0 and price_range <= avg_price * 0.5:
                score += 5
                
        # 评估时间选择
        departure_hours = {option.ticket.departure_time.hour for option in recommendation.options}
        if len(departure_hours) >= 3:  # 提供多个时间段的选择
            score += 5
            
        # 确保分数在0-100范围内
        return max(0, min(100, score))
    
    async def _evaluate_practicality(self, recommendation: Recommendation, user_needs: UserNeeds) -> float:
        """
        评估实用性
        
        Args:
            recommendation: 推荐结果
            user_needs: 用户需求
            
        Returns:
            实用性评分
        """
        # 如果有LLM客户端，使用LLM评估
        if self.llm_client:
            return await self.llm_client.evaluate_practicality(recommendation, user_needs)
        
        # 否则使用规则进行评估
        score = 70.0  # 基础分
        
        # 评估可预订性（座位可用性）
        available_options = sum(1 for option in recommendation.options if option.ticket.available_seats > 0)
        if available_options == 0:
            score -= 50  # 没有可预订选项严重扣分
        else:
            availability_ratio = available_options / len(recommendation.options)
            score += availability_ratio * 10  # 可预订比例越高，加分越多
            
        # 评估中转便利性
        direct_options = sum(1 for option in recommendation.options if option.ticket.is_direct)
        if direct_options > 0:
            score += 10  # 有直达选项加分
            
        # 评估时间合理性
        reasonable_duration_count = 0
        for option in recommendation.options:
            if user_needs.max_duration_minutes:
                if option.ticket.duration_minutes <= user_needs.max_duration_minutes:
                    reasonable_duration_count += 1
            else:
                # 如果没有指定最大时长，根据交通方式判断合理性
                if option.ticket.transport_type == "flight" and option.ticket.duration_minutes <= 240:
                    reasonable_duration_count += 1
                elif option.ticket.transport_type == "train" and option.ticket.duration_minutes <= 480:
                    reasonable_duration_count += 1
                    
        if reasonable_duration_count > 0:
            score += min(15, reasonable_duration_count * 5)  # 每个合理时长的选项加5分，最多加15分
            
        # 确保分数在0-100范围内
        return max(0, min(100, score))
    
    async def _generate_improvement_suggestions(self, 
                                             recommendation: Recommendation, 
                                             user_needs: UserNeeds,
                                             scores: RecommendationScore) -> List[str]:
        """
        生成改进建议
        
        Args:
            recommendation: 推荐结果
            user_needs: 用户需求
            scores: 评分
            
        Returns:
            改进建议列表
        """
        # 如果有LLM客户端，使用LLM生成建议
        if self.llm_client:
            return await self.llm_client.generate_improvement_suggestions(recommendation, user_needs, scores)
        
        # 否则使用规则生成建议
        suggestions = []
        
        # 根据各维度得分生成建议
        # 需求匹配度
        if scores.needs_match_score < 60:
            suggestions.append("重点关注用户的核心需求，特别是交通方式和价格预算")
            
        if scores.needs_match_score < 80:
            if user_needs.budget.max_price:
                high_price_count = sum(1 for option in recommendation.options if option.ticket.price > user_needs.budget.max_price)
                if high_price_count > 0:
                    suggestions.append(f"提供更多符合用户预算(最高{user_needs.budget.max_price})的选项")
            
            # 检查时间偏好
            if user_needs.departure_time_range.preferred_time:
                suggestions.append(f"更好地匹配用户的{user_needs.departure_time_range.preferred_time.value}时间偏好")
                
        # 选项完整性
        if scores.completeness_score < 70:
            if len(recommendation.options) < 3:
                suggestions.append("增加更多样化的推荐选项，至少提供3个不同的选择")
            
            transport_types = {option.ticket.transport_type for option in recommendation.options}
            if len(transport_types) < len(user_needs.preferred_transport_types):
                suggestions.append("尝试覆盖用户偏好的所有交通方式")
                
        # 实用性
        if scores.practicality_score < 80:
            available_options = sum(1 for option in recommendation.options if option.ticket.available_seats > 0)
            if available_options < len(recommendation.options) / 2:
                suggestions.append("提供更多可立即预订的选项")
                
            direct_options = sum(1 for option in recommendation.options if option.ticket.is_direct)
            if direct_options == 0 and len(recommendation.options) > 0:
                suggestions.append("尝试提供一些直达选项，减少中转次数")
                
        # 如果所有分数都不错但总分不高
        if (scores.needs_match_score >= 80 and 
            scores.completeness_score >= 80 and 
            scores.practicality_score >= 80 and 
            scores.overall_score < 90):
            suggestions.append("整体推荐质量良好，可以尝试提供一些特色服务或独特优势来进一步提升")
            
        # 如果没有生成任何建议，添加一个默认建议
        if not suggestions:
            if scores.overall_score >= 90:
                suggestions.append("当前推荐已经非常优秀，可以适当增加一些个性化的细节")
            else:
                suggestions.append("全面提升推荐方案的质量，确保更好地满足用户需求")
        
        return suggestions 