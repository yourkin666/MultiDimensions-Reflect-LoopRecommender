import json
from typing import List, Union, Dict, Any

from src.models.user_needs import UserNeeds
from src.models.ticket_data import FlightTicket, TrainTicket
from src.models.recommendation import RecommendationResult, Recommendation
from src.core.evaluator import Evaluator, EvaluationResult
from src.utils.llm_client import LLMClient
from pydantic import ValidationError

class ReflectionEngine:
    """
    反思循环推荐引擎
    """
    def __init__(self, llm_client: LLMClient, evaluator: Evaluator, max_cycles: int = 3):
        self.llm_client = llm_client
        self.evaluator = evaluator
        self.max_cycles = max_cycles

    async def recommend(self, user_needs: UserNeeds, ticket_data: List[Union[FlightTicket, TrainTicket]]) -> RecommendationResult:
        """
        执行带反思循环的推荐过程
        """
        # 将Pydantic模型转换为字典列表，方便LLM处理
        tickets_dict = [ticket.dict() for ticket in ticket_data]
        
        reflection_summary = ""
        current_recommendations = []
        
        # 初始的改进建议为空
        improvement_suggestions = "N/A"

        for cycle in range(self.max_cycles):
            # 1. 生成推荐
            prompt = self._build_recommendation_prompt(user_needs, tickets_dict, improvement_suggestions, cycle)
            raw_recs_text = await self.llm_client.generate(prompt)
            
            try:
                # 解析LLM返回的推荐列表
                current_recommendations = json.loads(raw_recs_text)
            except json.JSONDecodeError:
                print(f"Cycle {cycle+1}: LLM返回的推荐不是有效的JSON格式。")
                # 如果返回格式错误，可以在此重试或直接进入下一轮反思
                improvement_suggestions = "The output was not valid JSON. Please provide the recommendations in a valid JSON list format."
                reflection_summary += f"Cycle {cycle+1}: Failed to generate valid recommendations.\n"
                continue

            # 2. 自我评估
            evaluation = await self.evaluator.self_evaluate(user_needs, current_recommendations)
            
            reflection_summary += f"Cycle {cycle+1}: Score={evaluation.quality_score}. Issues: {'; '.join(evaluation.issues_found)}\n"

            # 3. 判断是否满足条件
            if evaluation.is_sufficient:
                print(f"在第 {cycle + 1} 轮后达到满意结果。")
                return self._format_final_result(current_recommendations, reflection_summary, cycle + 1)
            
            # 4. 如果不满足，准备下一轮
            improvement_suggestions = evaluation.improvement_suggestions
            print(f"第 {cycle + 1} 轮反思，准备下一轮。改进建议: {improvement_suggestions}")

        print("达到最大反思次数，返回当前最佳结果。")
        return self._format_final_result(current_recommendations, reflection_summary, self.max_cycles)

    def _build_recommendation_prompt(self, user_needs: UserNeeds, tickets_dict: List[Dict[str, Any]], improvement_suggestions: str, cycle: int) -> str:
        """
        构建用于生成推荐的提示
        """
        user_needs_dict = user_needs.dict(exclude_none=True)
        
        reflection_guidance = ""
        if cycle > 0:
            reflection_guidance = f"""
            **重要提醒：**
            这已是第 {cycle + 1} 轮推荐。在上一轮中，我们发现了一些问题，请务必根据以下建议进行改进：
            ---
            {improvement_suggestions}
            ---
            """

        return f"""
        作为一名顶级的旅行规划专家，请根据用户的需求和可用的票务数据，为用户生成最合适的旅行方案。

        **用户需求:**
        ```json
        {json.dumps(user_needs_dict, indent=2, ensure_ascii=False)}
        ```

        **可用票务数据:**
        ```json
        {json.dumps(tickets_dict, indent=2, ensure_ascii=False)}
        ```
        
        {reflection_guidance}

        **任务要求:**
        1.  从可用票务数据中挑选出 **1到3个** 最符合用户需求的选项。
        2.  为每个选项提供一个 **精准、有说服力** 的推荐理由。
        3.  为每个选项估算一个 **预计满意度分数** (0-100)。
        4.  **最终结果必须以JSON列表的格式返回**，每个列表项包含 "ticket", "recommendation_reason", 和 "satisfaction_score" 三个字段。**不要返回任何额外的解释或文本**。

        **输出格式示例:**
        ```json
        [
            {{
                "ticket": {{ ...票务完整信息... }},
                "recommendation_reason": "这是最符合您时间要求的直飞航班，性价比很高。",
                "satisfaction_score": 95.0
            }},
            {{
                "ticket": {{ ...票务完整信息... }},
                "recommendation_reason": "这趟高铁虽然时间稍长，但价格非常实惠，且座位舒适。",
                "satisfaction_score": 88.0
            }}
        ]
        ```
        """
    
    def _format_final_result(self, raw_recommendations: List[Dict[str, Any]], summary: str, cycles: int) -> RecommendationResult:
        """
        将LLM的原始输出格式化为最终的Pydantic模型
        """
        valid_recs = []
        for raw_rec in raw_recommendations:
            try:
                # 嵌套的ticket也需要被正确解析
                ticket_data = raw_rec.get("ticket", {})
                if ticket_data.get("ticket_type") == "flight":
                    ticket_obj = FlightTicket(**ticket_data)
                elif ticket_data.get("ticket_type") == "train":
                    ticket_obj = TrainTicket(**ticket_data)
                else:
                    continue # 如果票务类型未知，则跳过

                valid_recs.append(Recommendation(
                    ticket=ticket_obj,
                    recommendation_reason=raw_rec.get("recommendation_reason", "N/A"),
                    satisfaction_score=raw_rec.get("satisfaction_score", 0.0)
                ))
            except ValidationError as e:
                print(f"推荐项格式验证失败: {raw_rec}, Error: {e}")
                continue
                
        return RecommendationResult(
            recommendations=valid_recs,
            reflection_summary=summary.strip(),
            reflection_cycles=cycles
        ) 