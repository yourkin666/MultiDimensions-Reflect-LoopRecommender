from pydantic import BaseModel, Field
from typing import Optional

class Ticket(BaseModel):
    """
    票务基础模型
    """
    ticket_type: str = Field(..., description="票务类型, 'flight' 或 'train'")
    departure_city: str = Field(..., description="出发城市")
    arrival_city: str = Field(..., description="到达城市")
    departure_time: str = Field(..., description="出发时间, 格式: YYYY-MM-DD HH:MM:SS")
    arrival_time: str = Field(..., description="到达时间, 格式: YYYY-MM-DD HH:MM:SS")
    price: float = Field(..., description="价格")
    carrier: str = Field(..., description="承运公司/列车号")
    duration: str = Field(..., description="总时长")
    availability: bool = Field(True, description="是否可预订")

class FlightTicket(Ticket):
    """
    机票数据模型
    """
    ticket_type: str = Field("flight", description="票务类型")
    seat_type: str = Field(..., description="座位等级, 例如 '经济舱', '商务舱'")
    stops: int = Field(0, description="中转次数")
    flight_number: str = Field(..., description="航班号")

class TrainTicket(Ticket):
    """
    火车票数据模型
    """
    ticket_type: str = Field("train", description="票务类型")
    seat_type: str = Field(..., description="座位类型, 例如 '二等座', '卧铺'")
    train_number: str = Field(..., description="车次") 