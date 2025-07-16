#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
数据处理器
"""

import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Tuple, Optional
import asyncio
import numpy as np

from src.models.user_needs import UserNeeds, TimePreference
from src.models.ticket_data import TicketData, FlightTicket, TrainTicket, TransportType, SeatClass


class DataProcessor:
    """数据处理器"""
    
    def __init__(self, data_source_config: Dict[str, Any] = None):
        """
        初始化数据处理器
        
        Args:
            data_source_config: 数据源配置
        """
        self.logger = logging.getLogger(__name__)
        self.data_source_config = data_source_config or {}
        
    async def fetch_matching_tickets(self, user_needs: UserNeeds) -> List[TicketData]:
        """
        获取匹配用户需求的票务数据
        
        Args:
            user_needs: 用户需求
            
        Returns:
            匹配的票务数据列表
        """
        self.logger.info(f"获取从 {user_needs.departure_city} 到 {user_needs.arrival_city} 的票务数据")
        
        # 在实际应用中，这里会从数据库或外部API获取真实数据
        # 本实现提供模拟数据用于演示
        
        tickets = []
        
        # 生成一些测试数据
        # 这里简单模拟多种交通方式和时间段的票务
        for transport_type in user_needs.preferred_transport_types:
            tickets.extend(await self._generate_mock_tickets(user_needs, transport_type))
            
        self.logger.info(f"获取到 {len(tickets)} 个匹配的票务数据")
        return tickets
    
    async def _generate_mock_tickets(self, user_needs: UserNeeds, transport_type: TransportType) -> List[TicketData]:
        """
        生成模拟票务数据
        
        Args:
            user_needs: 用户需求
            transport_type: 交通方式
            
        Returns:
            模拟票务数据列表
        """
        # 确定基础出发时间
        base_time = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        if user_needs.departure_time_range.start_time:
            if isinstance(user_needs.departure_time_range.start_time, datetime):
                base_time = user_needs.departure_time_range.start_time
                
        tickets = []
        
        # 为不同时段生成票务
        time_slots = self._get_time_slots_from_preference(user_needs.departure_time_range.preferred_time)
        
        for i in range(10):  # 每个时间段生成多个票务选项
            for hours, minutes in time_slots:
                departure_time = base_time + timedelta(days=i//3, hours=hours, minutes=minutes)
                
                # 根据交通方式生成不同的持续时间
                if transport_type == TransportType.FLIGHT:
                    duration_minutes = np.random.randint(60, 240)  # 1-4小时
                    seat_classes = [SeatClass.ECONOMY, SeatClass.PREMIUM_ECONOMY, SeatClass.BUSINESS, SeatClass.FIRST]
                    companies = ["国航", "东航", "南航", "海航", "厦航"]
                    price_base = 500
                    price_range = (300, 3000)
                elif transport_type == TransportType.TRAIN:
                    duration_minutes = np.random.randint(120, 480)  # 2-8小时
                    seat_classes = [SeatClass.HARD_SEAT, SeatClass.SOFT_SEAT, SeatClass.HARD_SLEEPER, 
                                   SeatClass.SOFT_SLEEPER, SeatClass.HIGH_SPEED_SECOND, SeatClass.HIGH_SPEED_FIRST]
                    companies = ["中国铁路", "高铁", "动车", "普速铁路"]
                    price_base = 200
                    price_range = (100, 1000)
                else:
                    continue
                    
                arrival_time = departure_time + timedelta(minutes=duration_minutes)
                
                # 为每个座位等级生成票务
                for seat_class in seat_classes:
                    price_multiplier = self._get_price_multiplier(seat_class)
                    price = min(max(price_base * price_multiplier + np.random.randint(-50, 100), price_range[0]), price_range[1])
                    
                    # 模拟一些票务可能已售罄
                    available_seats = np.random.randint(0, 100)
                    if available_seats < 5:  # 少量票务
                        available_seats = np.random.randint(0, 5)
                    
                    company = np.random.choice(companies)
                    transport_number = f"{company[:2]}{np.random.randint(1000, 9999)}"
                    
                    ticket_id = f"{transport_type.value}-{transport_number}-{departure_time.strftime('%Y%m%d%H%M')}"
                    
                    # 创建票务对象
                    if transport_type == TransportType.FLIGHT:
                        ticket = FlightTicket(
                            id=ticket_id,
                            transport_type=transport_type,
                            departure_city=user_needs.departure_city,
                            arrival_city=user_needs.arrival_city,
                            departure_time=departure_time,
                            arrival_time=arrival_time,
                            price=float(price),
                            seat_class=seat_class,
                            available_seats=int(available_seats),
                            company=company,
                            transport_number=transport_number,
                            departure_station=f"{user_needs.departure_city}机场",
                            arrival_station=f"{user_needs.arrival_city}机场",
                            duration_minutes=duration_minutes,
                            baggage_allowance={"checked": "20kg", "carry_on": "10kg"},
                            meal_included=seat_class in [SeatClass.BUSINESS, SeatClass.FIRST],
                            aircraft_type=np.random.choice(["波音737", "空客A320", "波音777", "空客A330"])
                        )
                    else:  # 火车票
                        is_high_speed = seat_class in [SeatClass.HIGH_SPEED_FIRST, SeatClass.HIGH_SPEED_SECOND, 
                                                       SeatClass.HIGH_SPEED_BUSINESS]
                        ticket = TrainTicket(
                            id=ticket_id,
                            transport_type=transport_type,
                            departure_city=user_needs.departure_city,
                            arrival_city=user_needs.arrival_city,
                            departure_time=departure_time,
                            arrival_time=arrival_time,
                            price=float(price),
                            seat_class=seat_class,
                            available_seats=int(available_seats),
                            company=company,
                            transport_number=transport_number,
                            departure_station=f"{user_needs.departure_city}站",
                            arrival_station=f"{user_needs.arrival_city}站",
                            duration_minutes=duration_minutes,
                            is_high_speed=is_high_speed,
                            stops=[{"station": f"中转站{i}", "arrival": departure_time + timedelta(minutes=duration_minutes*i/3), 
                                    "departure": departure_time + timedelta(minutes=duration_minutes*i/3 + 5)} 
                                  for i in range(1, np.random.randint(0, 4))]
                        )
                    
                    tickets.append(ticket)
        
        return tickets
    
    def _get_time_slots_from_preference(self, preference: Optional[TimePreference]) -> List[Tuple[int, int]]:
        """
        根据时间偏好获取时间段
        
        Args:
            preference: 时间偏好
            
        Returns:
            小时和分钟的组合列表
        """
        if preference == TimePreference.MORNING:
            return [(6, 0), (8, 30), (10, 0)]
        elif preference == TimePreference.AFTERNOON:
            return [(12, 0), (14, 0), (16, 0)]
        elif preference == TimePreference.EVENING:
            return [(17, 0), (18, 30), (20, 0)]
        elif preference == TimePreference.NIGHT:
            return [(21, 0), (22, 30), (23, 59)]
        else:  # TimePreference.ANY 或 None
            return [(8, 0), (12, 0), (16, 0), (20, 0)]
    
    def _get_price_multiplier(self, seat_class: SeatClass) -> float:
        """
        获取座位等级对应的价格倍数
        
        Args:
            seat_class: 座位等级
            
        Returns:
            价格倍数
        """
        multipliers = {
            # 飞机座位
            SeatClass.ECONOMY: 1.0,
            SeatClass.PREMIUM_ECONOMY: 1.5,
            SeatClass.BUSINESS: 3.0,
            SeatClass.FIRST: 5.0,
            
            # 火车座位
            SeatClass.HARD_SEAT: 1.0,
            SeatClass.SOFT_SEAT: 1.3,
            SeatClass.HARD_SLEEPER: 1.8,
            SeatClass.SOFT_SLEEPER: 2.5,
            SeatClass.STANDING: 0.8,
            SeatClass.HIGH_SPEED_SECOND: 2.0,
            SeatClass.HIGH_SPEED_FIRST: 2.8,
            SeatClass.HIGH_SPEED_BUSINESS: 3.5
        }
        
        return multipliers.get(seat_class, 1.0)
    
    async def rank_tickets(self, tickets: List[TicketData], user_needs: UserNeeds) -> List[Tuple[TicketData, float, List[Tuple[str, str, float, float]]]]:
        """
        根据用户需求对票务进行评分和排序
        
        Args:
            tickets: 票务数据列表
            user_needs: 用户需求
            
        Returns:
            排序后的票务、得分和评分因素列表
        """
        self.logger.info(f"对 {len(tickets)} 个票务进行排序")
        
        # 存储票务、评分和评分因素
        scored_tickets = []
        
        for ticket in tickets:
            # 评分因素列表 (因素名, 描述, 权重, 得分)
            reasons = []
            
            # 1. 交通方式匹配度
            transport_type_score = 100 if ticket.transport_type in user_needs.preferred_transport_types else 50
            reasons.append(("transport_type", "交通方式偏好匹配度", 0.15, transport_type_score))
            
            # 2. 座位等级匹配度
            seat_class_score = 100
            if user_needs.preferred_seat_classes:
                seat_class_score = 100 if ticket.seat_class in user_needs.preferred_seat_classes else 60
            reasons.append(("seat_class", "座位等级匹配度", 0.1, seat_class_score))
            
            # 3. 价格评分
            price_score = 100  # 默认满分
            if user_needs.budget.max_price:
                if ticket.price > user_needs.budget.max_price:
                    price_score = max(0, 100 - (ticket.price - user_needs.budget.max_price) / user_needs.budget.max_price * 100)
            if user_needs.budget.min_price:
                if ticket.price < user_needs.budget.min_price:
                    price_score = max(0, 100 - (user_needs.budget.min_price - ticket.price) / user_needs.budget.min_price * 50)
            reasons.append(("price", "价格符合度", 0.2, price_score))
            
            # 4. 出发时间评分
            time_score = 100  # 默认满分
            if user_needs.departure_time_range.start_time and user_needs.departure_time_range.end_time:
                if isinstance(user_needs.departure_time_range.start_time, datetime) and isinstance(user_needs.departure_time_range.end_time, datetime):
                    if ticket.departure_time < user_needs.departure_time_range.start_time:
                        time_diff = (user_needs.departure_time_range.start_time - ticket.departure_time).total_seconds() / 3600
                        time_score = max(0, 100 - time_diff * 5)  # 每小时扣5分
                    elif ticket.departure_time > user_needs.departure_time_range.end_time:
                        time_diff = (ticket.departure_time - user_needs.departure_time_range.end_time).total_seconds() / 3600
                        time_score = max(0, 100 - time_diff * 5)  # 每小时扣5分
            reasons.append(("departure_time", "出发时间符合度", 0.25, time_score))
            
            # 5. 持续时间评分
            duration_score = 100  # 默认满分
            if user_needs.max_duration_minutes:
                if ticket.duration_minutes > user_needs.max_duration_minutes:
                    duration_score = max(0, 100 - (ticket.duration_minutes - user_needs.max_duration_minutes) / 60 * 10)  # 每超过1小时扣10分
            reasons.append(("duration", "行程时间合理性", 0.15, duration_score))
            
            # 6. 可用座位数评分
            availability_score = min(100, ticket.available_seats * 10) if ticket.available_seats > 0 else 0
            reasons.append(("availability", "座位可用性", 0.15, availability_score))
            
            # 计算总分
            total_score = 0
            for _, _, weight, score in reasons:
                total_score += weight * score
                
            scored_tickets.append((ticket, total_score, reasons))
            
        # 按总分排序
        scored_tickets.sort(key=lambda x: x[1], reverse=True)
        
        return scored_tickets 