#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
多维度反思循环推荐系统 - 示例脚本
"""

import os
import sys
import json
import asyncio
from datetime import datetime, timedelta
from dotenv import load_dotenv

# 将项目根目录添加到模块搜索路径
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.core.reflection_engine import ReflectionEngine
from src.core.data_processor import DataProcessor
from src.core.evaluator import RecommendationEvaluator
from src.utils.llm_client import LLMClient
from src.models.user_needs import UserNeeds, TimePreference, TimeRange, BudgetRange, PriceLevel, TravelPriority
from src.models.ticket_data import TransportType, SeatClass
from src.utils.logger_config import setup_logger


# 示例对话内容
EXAMPLE_CONVERSATIONS = [
    """
    我想从北京去上海，下周五出发，预算在1000元以内，最好是高铁，二等座就行。
    我希望早上出发，最好是8点左右的车，这样中午就能到上海。
    """,
    
    """
    帮我查一下从广州到成都的机票，后天或大后天出发，经济舱，最好是直达航班，
    因为我带了很多行李，转机会比较麻烦。我希望总价在2000以内，如果没有就算了。
    另外，我喜欢晚上的航班，晚上8点之后起飞的那种。
    """,
    
    """
    我需要从杭州到北京的票，两天后出发。
    我比较看重舒适度，所以如果是高铁的话希望是一等座或商务座，
    飞机的话希望是头等舱或商务舱。预算在3000元以内。
    我时间比较灵活，但不想太早出发，最好是下午的行程。
    """
]


async def run_example(conversation_text: str) -> None:
    """运行示例"""
    print(f"\n{'=' * 80}")
    print(f"用户对话内容:")
    print(f"{'-' * 40}")
    print(conversation_text.strip())
    print(f"\n{'-' * 40}")
    
    # 初始化组件
    llm_client = LLMClient()
    data_processor = DataProcessor()
    evaluator = RecommendationEvaluator(llm_client)
    
    # 创建反思引擎
    engine = ReflectionEngine(
        llm_client=llm_client,
        data_processor=data_processor,
        evaluator=evaluator,
        max_iterations=2,  # 为了演示，设置较小的迭代次数
        score_threshold=90.0
    )
    
    print("1. 提取用户需求...")
    user_needs = await engine.extract_user_needs(conversation_text)
    print(f"出发城市: {user_needs.departure_city}")
    print(f"到达城市: {user_needs.arrival_city}")
    print(f"偏好交通方式: {[t.value for t in user_needs.preferred_transport_types]}")
    if user_needs.budget and user_needs.budget.max_price:
        print(f"最高预算: ¥{user_needs.budget.max_price}")
    print(f"优先级: {[p.value for p in user_needs.priorities]}")
    
    print("\n2. 获取候选票务...")
    tickets = await engine.get_candidate_tickets(user_needs)
    print(f"找到 {len(tickets)} 个候选票务")
    
    print("\n3. 生成初始推荐方案...")
    recommendation = await engine.generate_recommendations(
        user_needs, tickets, conversation_text
    )
    
    print("\n4. 评估初始推荐方案...")
    scores, suggestions = await engine.evaluator.evaluate(recommendation, user_needs)
    recommendation.scores = scores
    
    print(f"初始评分:")
    print(f"- 需求匹配度: {scores.needs_match_score}/100")
    print(f"- 选项完整性: {scores.completeness_score}/100")
    print(f"- 实用性评估: {scores.practicality_score}/100")
    print(f"- 整体评分: {scores.overall_score}/100")
    
    if scores.overall_score < engine.score_threshold:
        print("\n5. 初始方案未达到阈值分数，开始反思循环...")
        
        for iteration in range(engine.max_iterations):
            print(f"\n=== 反思循环 {iteration + 1} ===")
            
            # 反思并改进
            print("5.1 反思并调整参数...")
            adjusted_params = await engine.reflect_and_improve(
                recommendation, user_needs, scores, suggestions
            )
            
            print(f"调整参数: {json.dumps(adjusted_params, ensure_ascii=False)}")
            
            # 应用改进
            print("5.2 应用改进...")
            current_needs = await engine.apply_improvements(recommendation, user_needs, adjusted_params)
            
            # 获取候选票务
            print("5.3 获取更新后的候选票务...")
            new_tickets = await engine.get_candidate_tickets(current_needs)
            
            # 生成新的推荐
            print("5.4 生成新的推荐方案...")
            recommendation = await engine.generate_recommendations(
                current_needs, new_tickets, conversation_text
            )
            
            # 评估新的推荐
            print("5.5 评估新推荐方案...")
            scores, suggestions = await engine.evaluator.evaluate(recommendation, current_needs)
            recommendation.scores = scores
            
            print(f"本轮评分:")
            print(f"- 需求匹配度: {scores.needs_match_score}/100")
            print(f"- 选项完整性: {scores.completeness_score}/100")
            print(f"- 实用性评估: {scores.practicality_score}/100")
            print(f"- 整体评分: {scores.overall_score}/100")
            
            if scores.overall_score >= engine.score_threshold:
                print(f"\n推荐质量已达到阈值({scores.overall_score} >= {engine.score_threshold})，停止循环")
                break
                
            if iteration == engine.max_iterations - 1:
                print("\n达到最大循环次数，返回当前最佳方案")
    else:
        print("\n5. 初始方案已达到阈值分数，无需反思循环")
    
    print("\n6. 最终推荐方案:")
    print(f"{'-' * 40}")
    for i, option in enumerate(recommendation.options[:3]):  # 只显示前3个
        ticket = option.ticket
        print(f"选项 {i+1} (评分: {option.score:.1f}):")
        print(f"- 交通方式: {ticket.transport_type.value}")
        print(f"- 公司: {ticket.company} {ticket.transport_number}")
        print(f"- 出发: {ticket.departure_city} ({ticket.departure_station}) - {ticket.departure_time.strftime('%Y-%m-%d %H:%M')}")
        print(f"- 到达: {ticket.arrival_city} ({ticket.arrival_station}) - {ticket.arrival_time.strftime('%Y-%m-%d %H:%M')}")
        print(f"- 座位: {ticket.seat_class.value}, 可用座位: {ticket.available_seats}")
        print(f"- 价格: ¥{ticket.price:.2f}")
        print(f"- 行程时长: {ticket.travel_duration}")
        print(f"- 是否直达: {'是' if ticket.is_direct else '否'}")
        
        # 显示推荐理由
        print("- 推荐理由:")
        for reason in option.reasons[:3]:  # 只显示前3个理由
            print(f"  · {reason.description}: {reason.score:.1f}/100")
            
        print(f"{'-' * 40}")
    
    print("\n推荐过程耗时: {:.2f}秒".format(recommendation.processing_time_ms / 1000 if recommendation.processing_time_ms else 0))
    print(f"{'=' * 80}\n")


async def main() -> None:
    """主函数"""
    # 设置日志
    setup_logger(log_level="INFO")
    
    # 加载环境变量
    load_dotenv()
    
    # 运行示例
    for i, conversation in enumerate(EXAMPLE_CONVERSATIONS):
        print(f"\n示例 {i+1}/{len(EXAMPLE_CONVERSATIONS)}")
        await run_example(conversation)


if __name__ == "__main__":
    asyncio.run(main()) 