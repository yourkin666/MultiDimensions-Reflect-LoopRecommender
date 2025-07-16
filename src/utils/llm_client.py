#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
大模型客户端
"""

import os
import json
import logging
import asyncio
from typing import List, Dict, Any, Optional, Tuple
import time

import openai
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain
from langchain.llms import OpenAI

from src.models.user_needs import UserNeeds
from src.models.recommendation import Recommendation, RecommendationScore


class LLMClient:
    """大模型客户端类"""
    
    def __init__(self, api_key: Optional[str] = None, model: str = "gpt-4o", temperature: float = 0.2):
        """
        初始化大模型客户端
        
        Args:
            api_key: OpenAI API密钥，默认从环境变量获取
            model: 使用的模型名称
            temperature: 生成文本的随机性
        """
        self.logger = logging.getLogger(__name__)
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.model = model
        self.temperature = temperature
        self.client = openai.OpenAI(api_key=self.api_key)
        
        # 创建一些常用的提示模板
        self.needs_extraction_template = """
        分析以下用户对话文本，提取用户的旅行需求信息。以JSON格式输出以下字段：

        - departure_city: 出发城市
        - arrival_city: 到达城市
        - departure_time_range: 出发时间范围（包括start_time, end_time, preferred_time）
        - return_time_range: 返回时间范围（如果有）
        - preferred_transport_types: 偏好的交通方式 (flight, train)
        - preferred_seat_classes: 偏好的座位等级
        - budget: 预算范围（包括min_price, max_price）
        - priorities: 优先级（price, time, comfort, convenience, reliability）
        - max_transfers: 最大中转次数（如果提到）
        - max_duration_minutes: 最大行程时间（分钟）
        - special_requirements: 特殊需求

        用户对话：
        {conversation_text}
        
        JSON输出：
        """
        
        self.reflection_template = """
        作为一个挑剔的用户，请评估以下推荐：
        
        用户需求：
        {user_needs}
        
        推荐方案：
        {recommendations}
        
        请从以下角度进行严格评估：
        1. 这个推荐是否真正理解了我的核心需求？
        2. 有没有遗漏重要的考虑因素？
        3. 是否存在更优的替代方案？
        4. 推荐的逻辑是否合理？
        
        请给出以下格式的回复：
        
        需求匹配度评分(0-100)：
        选项完整性评分(0-100)：
        实用性评估评分(0-100)：
        
        改进建议：
        1. 
        2. 
        3. 
        
        调整参数（JSON格式）：
        """
    
    async def extract_needs(self, conversation_text: str) -> UserNeeds:
        """
        从对话文本中提取用户需求
        
        Args:
            conversation_text: 用户对话文本
            
        Returns:
            用户需求对象
        """
        self.logger.info("使用LLM提取用户需求")
        
        try:
            # 构建提示
            prompt = self.needs_extraction_template.format(conversation_text=conversation_text)
            
            # 调用API
            response = await self._call_llm_async(prompt)
            
            # 解析JSON响应
            try:
                # 查找JSON内容
                json_str = self._extract_json(response)
                needs_dict = json.loads(json_str)
                
                # 创建用户需求对象
                return UserNeeds(**needs_dict)
                
            except json.JSONDecodeError:
                self.logger.error(f"无法解析LLM响应为JSON: {response}")
                # 返回默认需求对象
                return UserNeeds.extract_from_conversation(conversation_text)
                
        except Exception as e:
            self.logger.error(f"从对话提取需求时出错: {str(e)}")
            return UserNeeds.extract_from_conversation(conversation_text)
    
    async def evaluate_needs_match(self, recommendation: Recommendation, user_needs: UserNeeds) -> float:
        """
        评估需求匹配度
        
        Args:
            recommendation: 推荐结果
            user_needs: 用户需求
            
        Returns:
            需求匹配度评分
        """
        try:
            # 构建提示
            prompt = self._build_evaluation_prompt(recommendation, user_needs, "需求匹配度")
            
            # 调用API
            response = await self._call_llm_async(prompt)
            
            # 尝试从响应中提取分数
            score = self._extract_score(response)
            return score
            
        except Exception as e:
            self.logger.error(f"评估需求匹配度时出错: {str(e)}")
            return 70.0  # 返回默认分数
    
    async def evaluate_completeness(self, recommendation: Recommendation, user_needs: UserNeeds) -> float:
        """
        评估选项完整性
        
        Args:
            recommendation: 推荐结果
            user_needs: 用户需求
            
        Returns:
            选项完整性评分
        """
        try:
            # 构建提示
            prompt = self._build_evaluation_prompt(recommendation, user_needs, "选项完整性")
            
            # 调用API
            response = await self._call_llm_async(prompt)
            
            # 尝试从响应中提取分数
            score = self._extract_score(response)
            return score
            
        except Exception as e:
            self.logger.error(f"评估选项完整性时出错: {str(e)}")
            return 70.0  # 返回默认分数
    
    async def evaluate_practicality(self, recommendation: Recommendation, user_needs: UserNeeds) -> float:
        """
        评估实用性
        
        Args:
            recommendation: 推荐结果
            user_needs: 用户需求
            
        Returns:
            实用性评分
        """
        try:
            # 构建提示
            prompt = self._build_evaluation_prompt(recommendation, user_needs, "实用性评估")
            
            # 调用API
            response = await self._call_llm_async(prompt)
            
            # 尝试从响应中提取分数
            score = self._extract_score(response)
            return score
            
        except Exception as e:
            self.logger.error(f"评估实用性时出错: {str(e)}")
            return 70.0  # 返回默认分数
    
    async def generate_improvement_suggestions(self, 
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
        try:
            # 构建提示
            prompt = f"""
            根据以下信息，给出改进推荐结果的具体建议：
            
            用户需求：
            {self._format_user_needs(user_needs)}
            
            当前推荐评分：
            - 需求匹配度: {scores.needs_match_score}/100
            - 选项完整性: {scores.completeness_score}/100
            - 实用性评估: {scores.practicality_score}/100
            - 整体评分: {scores.overall_score}/100
            
            请提供3-5条具体的改进建议，每条建议应该简洁明了且可操作。
            """
            
            # 调用API
            response = await self._call_llm_async(prompt)
            
            # 处理响应
            suggestions = self._extract_suggestions(response)
            return suggestions
            
        except Exception as e:
            self.logger.error(f"生成改进建议时出错: {str(e)}")
            return ["提高推荐方案的整体质量", "更好地匹配用户核心需求", "增加选项多样性"]
    
    async def reflect_and_adjust(self,
                               recommendation: Recommendation,
                               user_needs: UserNeeds,
                               scores: RecommendationScore,
                               improvement_suggestions: List[str]) -> Dict[str, Any]:
        """
        反思并调整参数
        
        Args:
            recommendation: 推荐结果
            user_needs: 用户需求
            scores: 评分
            improvement_suggestions: 改进建议
            
        Returns:
            调整后的参数
        """
        try:
            # 构建提示
            prompt = f"""
            基于以下信息，请调整用户需求参数以改进推荐结果：
            
            当前用户需求：
            {self._format_user_needs(user_needs)}
            
            当前推荐评分：
            - 需求匹配度: {scores.needs_match_score}/100
            - 选项完整性: {scores.completeness_score}/100
            - 实用性评估: {scores.practicality_score}/100
            - 整体评分: {scores.overall_score}/100
            
            改进建议：
            {self._format_suggestions(improvement_suggestions)}
            
            请根据改进建议和评分，以JSON格式提供调整后的用户需求参数。
            仅包含需要调整的字段，并使用点表示法表示嵌套字段。
            例如: {{"budget.max_price": 800, "priorities": ["time", "comfort"]}}
            """
            
            # 调用API
            response = await self._call_llm_async(prompt)
            
            # 解析JSON
            adjusted_params = self._extract_json_dict(response)
            return adjusted_params
            
        except Exception as e:
            self.logger.error(f"反思并调整参数时出错: {str(e)}")
            return {}  # 返回空字典表示无调整
    
    async def _call_llm_async(self, prompt: str) -> str:
        """
        异步调用大模型API
        
        Args:
            prompt: 提示文本
            
        Returns:
            模型响应
        """
        try:
            completion = await asyncio.to_thread(
                self.client.chat.completions.create,
                model=self.model,
                temperature=self.temperature,
                messages=[
                    {"role": "system", "content": "你是一个专业的旅行推荐助手，擅长分析用户需求并提供高质量的票务推荐。"},
                    {"role": "user", "content": prompt}
                ]
            )
            return completion.choices[0].message.content
            
        except Exception as e:
            self.logger.error(f"调用LLM API时出错: {str(e)}")
            raise
    
    def _format_user_needs(self, user_needs: UserNeeds) -> str:
        """格式化用户需求为文本"""
        formatted = f"出发城市: {user_needs.departure_city}\n"
        formatted += f"到达城市: {user_needs.arrival_city}\n"
        
        # 出发时间
        if user_needs.departure_time_range:
            if user_needs.departure_time_range.start_time:
                formatted += f"出发时间开始: {user_needs.departure_time_range.start_time}\n"
            if user_needs.departure_time_range.end_time:
                formatted += f"出发时间结束: {user_needs.departure_time_range.end_time}\n"
            if user_needs.departure_time_range.preferred_time:
                formatted += f"偏好时间段: {user_needs.departure_time_range.preferred_time.value}\n"
        
        # 交通方式
        formatted += f"偏好交通方式: {', '.join([t.value for t in user_needs.preferred_transport_types])}\n"
        
        # 座位等级
        if user_needs.preferred_seat_classes:
            formatted += f"偏好座位等级: {', '.join([s.value for s in user_needs.preferred_seat_classes])}\n"
        
        # 预算
        if user_needs.budget:
            if user_needs.budget.min_price:
                formatted += f"最低预算: {user_needs.budget.min_price}\n"
            if user_needs.budget.max_price:
                formatted += f"最高预算: {user_needs.budget.max_price}\n"
            if user_needs.budget.price_level:
                formatted += f"价格水平: {user_needs.budget.price_level.value}\n"
        
        # 优先级
        formatted += f"优先考虑因素: {', '.join([p.value for p in user_needs.priorities])}\n"
        
        # 其他条件
        if user_needs.max_transfers is not None:
            formatted += f"最大中转次数: {user_needs.max_transfers}\n"
        if user_needs.max_duration_minutes is not None:
            formatted += f"最大行程时间: {user_needs.max_duration_minutes} 分钟\n"
        
        return formatted
    
    def _format_recommendations(self, recommendation: Recommendation) -> str:
        """格式化推荐结果为文本"""
        if not recommendation.options:
            return "没有推荐选项"
            
        formatted = f"共 {len(recommendation.options)} 个推荐选项:\n\n"
        
        for i, option in enumerate(recommendation.options[:3]):  # 最多显示前3个
            ticket = option.ticket
            formatted += f"选项 {i+1} (评分: {option.score}/100):\n"
            formatted += f"- 交通方式: {ticket.transport_type.value}\n"
            formatted += f"- 公司: {ticket.company} {ticket.transport_number}\n"
            formatted += f"- 出发: {ticket.departure_city} ({ticket.departure_station}) {ticket.departure_time}\n"
            formatted += f"- 到达: {ticket.arrival_city} ({ticket.arrival_station}) {ticket.arrival_time}\n"
            formatted += f"- 座位: {ticket.seat_class.value}, 可用座位: {ticket.available_seats}\n"
            formatted += f"- 价格: ¥{ticket.price}\n"
            formatted += f"- 行程时长: {ticket.travel_duration}\n"
            formatted += f"- 是否直达: {'是' if ticket.is_direct else '否'}\n"
            formatted += "\n"
            
        return formatted
    
    def _format_suggestions(self, suggestions: List[str]) -> str:
        """格式化建议列表为文本"""
        return "\n".join(f"{i+1}. {suggestion}" for i, suggestion in enumerate(suggestions))
    
    def _build_evaluation_prompt(self, 
                                recommendation: Recommendation, 
                                user_needs: UserNeeds,
                                evaluation_aspect: str) -> str:
        """构建评估提示"""
        prompt = f"""
        请评估以下推荐方案的{evaluation_aspect}，评分范围0-100：
        
        用户需求：
        {self._format_user_needs(user_needs)}
        
        推荐方案：
        {self._format_recommendations(recommendation)}
        
        请仅返回一个0-100之间的评分数字，不要有其他任何内容。
        """
        return prompt
    
    def _extract_score(self, response: str) -> float:
        """从响应中提取分数"""
        try:
            # 尝试直接解析为数字
            score = float(response.strip())
            return max(0, min(100, score))
        except ValueError:
            # 如果直接解析失败，尝试从文本中提取数字
            import re
            matches = re.findall(r'\b(\d{1,3}(?:\.\d+)?)\b', response)
            if matches:
                score = float(matches[0])
                return max(0, min(100, score))
                
            # 如果仍然失败，返回默认值
            return 70.0
    
    def _extract_json(self, text: str) -> str:
        """从文本中提取JSON字符串"""
        import re
        json_pattern = r'\{[\s\S]*\}'
        matches = re.search(json_pattern, text)
        if matches:
            return matches.group(0)
        
        # 如果没有找到完整的JSON，尝试提取代码块中的内容
        code_block_pattern = r'```(?:json)?\s*([\s\S]*?)\s*```'
        matches = re.search(code_block_pattern, text)
        if matches:
            return matches.group(1)
            
        return text  # 如果都没找到，返回原始文本
    
    def _extract_json_dict(self, text: str) -> Dict[str, Any]:
        """从文本中提取JSON字典"""
        try:
            json_str = self._extract_json(text)
            return json.loads(json_str)
        except json.JSONDecodeError:
            self.logger.error(f"无法解析为JSON字典: {text}")
            return {}
    
    def _extract_suggestions(self, text: str) -> List[str]:
        """从文本中提取建议列表"""
        import re
        
        # 尝试匹配数字列表项
        suggestions = []
        pattern = r'\d+\.\s*(.*?)(?=\d+\.|$)'
        matches = re.findall(pattern, text, re.DOTALL)
        
        if matches:
            suggestions = [match.strip() for match in matches if match.strip()]
        
        # 如果没有找到数字列表，尝试匹配破折号列表
        if not suggestions:
            pattern = r'-\s*(.*?)(?=-|$)'
            matches = re.findall(pattern, text, re.DOTALL)
            suggestions = [match.strip() for match in matches if match.strip()]
        
        # 如果仍然没找到，拆分文本按行处理
        if not suggestions:
            lines = [line.strip() for line in text.split('\n') if line.strip()]
            suggestions = [line for line in lines if not line.startswith("建议") and not ":" in line][:5]
        
        return suggestions[:5]  # 最多返回5条建议 