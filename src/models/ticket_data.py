#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
票务数据模型定义
"""

from datetime import datetime
from enum import Enum
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class TransportType(str, Enum):
    """交通方式枚举"""
    FLIGHT = "flight"  # 飞机
    TRAIN = "train"    # 火车
    BUS = "bus"        # 汽车
    SHIP = "ship"      # 轮船


class SeatClass(str, Enum):
    """座位等级枚举"""
    # 飞机座位
    ECONOMY = "economy"        # 经济舱
    PREMIUM_ECONOMY = "premium_economy"  # 高级经济舱
    BUSINESS = "business"      # 商务舱
    FIRST = "first"            # 头等舱
    
    # 火车座位
    HARD_SEAT = "hard_seat"    # 硬座
    SOFT_SEAT = "soft_seat"    # 软座
    HARD_SLEEPER = "hard_sleeper"  # 硬卧
    SOFT_SLEEPER = "soft_sleeper"  # 软卧
    STANDING = "standing"      # 无座
    HIGH_SPEED_SECOND = "high_speed_second"  # 高铁二等座
    HIGH_SPEED_FIRST = "high_speed_first"    # 高铁一等座
    HIGH_SPEED_BUSINESS = "high_speed_business"  # 高铁商务座


class TicketData(BaseModel):
    """票务数据基础模型"""
    id: str
    transport_type: TransportType
    departure_city: str
    arrival_city: str
    departure_time: datetime
    arrival_time: datetime
    price: float
    seat_class: SeatClass
    available_seats: int
    
    # 元数据
    company: str  # 航空公司/铁路局
    transport_number: str  # 航班号/车次号
    departure_station: str  # 出发站/机场
    arrival_station: str  # 到达站/机场
    duration_minutes: int  # 行程时长(分钟)
    
    # 附加信息
    transfer_info: Optional[List[Dict[str, Any]]] = None  # 中转信息
    restrictions: Optional[Dict[str, Any]] = None  # 限制条件
    additional_fees: Optional[Dict[str, float]] = None  # 额外费用
    
    class Config:
        """配置"""
        json_encoders = {
            datetime: lambda dt: dt.isoformat()
        }
        
    @property
    def travel_duration(self) -> str:
        """计算旅行时间"""
        hours, minutes = divmod(self.duration_minutes, 60)
        return f"{hours}h {minutes}m"
    
    @property
    def is_direct(self) -> bool:
        """是否是直达"""
        return self.transfer_info is None or len(self.transfer_info) == 0


class FlightTicket(TicketData):
    """机票数据模型"""
    baggage_allowance: Optional[Dict[str, Any]] = None  # 行李限额
    meal_included: bool = False  # 是否含餐
    aircraft_type: Optional[str] = None  # 飞机型号
    
    @classmethod
    def create_from_api_data(cls, data: Dict[str, Any]) -> "FlightTicket":
        """从API数据创建实例"""
        # 实现从原始API数据到模型的转换逻辑
        pass


class TrainTicket(TicketData):
    """火车票数据模型"""
    is_high_speed: bool = False  # 是否高铁
    stops: Optional[List[Dict[str, Any]]] = None  # 停靠站信息
    
    @classmethod
    def create_from_api_data(cls, data: Dict[str, Any]) -> "TrainTicket":
        """从API数据创建实例"""
        # 实现从原始API数据到模型的转换逻辑
        pass 