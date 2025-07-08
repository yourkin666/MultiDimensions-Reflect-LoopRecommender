from sanic import Blueprint, Sanic, Request, json
from sanic.response import text
from pydantic import BaseModel, Field

from src.core.reflection_engine import ReflectionEngine
from src.core.data_processor import DataProcessor

# 使用 Pydantic 定义请求体的数据结构，以获得自动验证
class RecommendRequest(BaseModel):
    conversation_history: str = Field(..., description="用户的完整对话历史")
    available_tickets: list = Field(..., description="从爬虫获取的可用票务数据列表")

# 创建一个蓝图来组织路由
recommendation_bp = Blueprint('recommendation', url_prefix='/api')

@recommendation_bp.post("/recommend")
async def handle_recommendation(request: Request):
    """
    处理推荐请求的核心端点
    """
    # Sanic-Pydantic 插件会自动验证请求体
    # 如果我们手动使用，需要在这里调用
    try:
        req_data = RecommendRequest(**request.json)
    except Exception as e:
        return json({"error": "Invalid request body", "details": str(e)}, status=400)

    # 从app的上下文中获取共享的引擎实例
    engine: ReflectionEngine = request.app.ctx.engine
    data_processor: DataProcessor = request.app.ctx.data_processor

    try:
        # 1. 从对话中提取结构化的用户需求
        user_needs = await data_processor.extract_user_needs(req_data.conversation_history)

        # 2. 结构化票务数据
        ticket_data = data_processor.structure_ticket_data(req_data.available_tickets)

        # 3. 执行反思推荐
        result = await engine.recommend(user_needs, ticket_data)
        
        # 返回Pydantic模型，Sanic可以自动将其序列化为JSON
        return json(result.dict())

    except ValueError as e:
        return json({"error": str(e)}, status=400)
    except Exception as e:
        # 捕获其他潜在的异常
        print(f"An unexpected error occurred: {e}")
        return json({"error": "An internal server error occurred."}, status=500)

def setup_recommendation_api(app: Sanic):
    """
    将蓝图注册到Sanic应用
    """
    app.blueprint(recommendation_bp) 