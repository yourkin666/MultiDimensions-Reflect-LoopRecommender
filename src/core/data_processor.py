import json
from typing import Dict, Any, List, Union
from pydantic import ValidationError

from src.models.user_needs import UserNeeds
from src.models.ticket_data import FlightTicket, TrainTicket
from src.utils.llm_client import LLMClient # 假设llm_client已实现

class DataProcessor:
    def __init__(self, llm_client: LLMClient):
        self.llm_client = llm_client

    async def extract_user_needs(self, conversation_history: str) -> UserNeeds:
        """
        从对话中提取用户需求, 并用Pydantic模型验证
        """
        prompt = f"""
        从以下对话中提取用户的出行需求，并以JSON格式返回:
        对话内容:
        ---
        {conversation_history}
        ---
        请严格按照以下JSON格式返回，不要添加任何额外说明:
        {{
            "departure_city": "出发城市",
            "arrival_city": "到达城市",
            "departure_date": "YYYY-MM-DD格式的出发日期",
            "budget_range": [最低预算, 最高预算],
            "comfort_requirements": ["舒适度要求1", "舒适度要求2"],
            "special_needs": ["特殊需求1"],
            "implicit_preferences": ["隐性偏好1"]
        }}
        如果某项信息不存在，请使用null。
        """
        
        response_text = await self.llm_client.generate(prompt)
        
        try:
            # 尝试解析LLM返回的JSON
            response_data = json.loads(response_text)
            # 使用Pydantic模型进行验证和转换
            return UserNeeds(**response_data)
        except (json.JSONDecodeError, ValidationError) as e:
            # 如果解析或验证失败，可以进行错误处理或重试
            print(f"用户需求提取失败: {e}")
            # 这里可以加入更复杂的错误处理逻辑，例如，要求LLM修复其输出
            raise ValueError("无法从对话中提取有效的用户需求。") from e

    def structure_ticket_data(self, raw_data: List[Dict[str, Any]]) -> List[Union[FlightTicket, TrainTicket]]:
        """
        将原始票务数据结构化
        """
        # 此处应包含复杂的逻辑来处理不同来源、格式混乱的爬虫数据
        # 为简化示例，我们假设raw_data已经是相对干净的
        structured_tickets = []
        for item in raw_data:
            try:
                if item.get("ticket_type") == "flight":
                    structured_tickets.append(FlightTicket(**item))
                elif item.get("ticket_type") == "train":
                    structured_tickets.append(TrainTicket(**item))
            except ValidationError as e:
                print(f"票务数据验证失败: {item}, 错误: {e}")
                # 忽略格式错误的数据
                continue
        return structured_tickets 