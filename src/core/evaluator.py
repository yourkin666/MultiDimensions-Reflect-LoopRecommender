import json
from typing import Tuple, Dict, Any, List
from pydantic import BaseModel, Field, ValidationError

from src.models.user_needs import UserNeeds
from src.models.recommendation import RecommendationResult
from src.utils.llm_client import LLMClient

class EvaluationResult(BaseModel):
    """
    评估结果的数据模型
    """
    quality_score: float = Field(..., description="推荐质量的综合评分 (0-100)")
    is_sufficient: bool = Field(..., description="是否足够好，无需再反思")
    issues_found: List[str] = Field(..., description="发现的主要问题列表")
    improvement_suggestions: str = Field(..., description="具体的改进建议")

class Evaluator:
    """
    使用LLM评估推荐质量的评估器
    """
    def __init__(self, llm_client: LLMClient):
        self.llm_client = llm_client

    async def self_evaluate(self, user_needs: UserNeeds, recommendations: List[Dict[str, Any]]) -> EvaluationResult:
        """
        让LLM自我评估生成的推荐
        """
        # 为了让LLM更好地理解，我们将Pydantic模型转换为字典
        user_needs_dict = user_needs.dict(exclude_none=True)
        
        prompt = f"""
        作为一名专业的、极其挑剔的旅行规划师，请严格评估以下为你生成的旅行推荐方案。

        **原始用户需求:**
        ```json
        {json.dumps(user_needs_dict, indent=2, ensure_ascii=False)}
        ```

        **当前推荐方案:**
        ```json
        {json.dumps(recommendations, indent=2, ensure_ascii=False)}
        ```

        **评估任务:**
        请从以下角度进行全面、深入的评估，并以JSON格式返回你的评估结果：
        1.  **需求匹配度**: 是否完全满足用户的显性需求（城市、日期、预算、舒适度）？
        2.  **隐性需求挖掘**: 是否洞察并满足了用户的潜在偏好？
        3.  **方案合理性**: 推荐的方案是否便捷、经济、高效？是否存在不合理的行程（如红眼航班、长时间中转）？
        4.  **选项多样性**: 是否提供了足够且有意义的选择，而不是简单罗列？
        5.  **价值与创新**: 是否有超出用户预期的惊喜或更优的替代方案？

        **输出格式:**
        请严格按照以下JSON格式返回你的评估结果，不要添加任何额外说明:
        {{
            "quality_score": <一个0-100的浮点数，代表综合质量评分>,
            "is_sufficient": <布尔值，如果评分高于85分，则为true，否则为false>,
            "issues_found": ["问题1", "问题2", ...],
            "improvement_suggestions": "具体的、可操作的改进建议，用于指导下一轮推荐。"
        }}
        """
        
        response_text = await self.llm_client.generate(prompt)
        
        try:
            response_data = json.loads(response_text)
            return EvaluationResult(**response_data)
        except (json.JSONDecodeError, ValidationError) as e:
            print(f"评估结果解析或验证失败: {e}")
            # 在评估失败时，返回一个默认的“不满意”结果，以触发反思
            return EvaluationResult(
                quality_score=30.0,
                is_sufficient=False,
                issues_found=["评估模块返回格式错误，无法解析。"],
                improvement_suggestions="请检查并修复评估模型的输出格式。"
            ) 