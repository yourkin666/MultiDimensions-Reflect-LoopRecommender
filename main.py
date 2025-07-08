import os
from sanic import Sanic, Request, json
from dotenv import load_dotenv

from src.utils.llm_client import LLMClient
from src.core.data_processor import DataProcessor
from src.core.evaluator import Evaluator
from src.core.reflection_engine import ReflectionEngine
from src.api.recommendation_api import setup_recommendation_api

# 加载 .env 文件中的环境变量
load_dotenv()

# 初始化 Sanic 应用
app = Sanic("ReflectionRecommender")

# --- 生命周期事件 ---
@app.listener('before_server_start')
async def setup_services(app: Sanic, loop):
    """
    在服务器启动前，初始化所有服务和引擎
    """
    print("Initializing services...")
    # 实例化所有核心组件
    app.ctx.llm_client = LLMClient(api_key=os.getenv("OPENAI_API_KEY"))
    app.ctx.data_processor = DataProcessor(llm_client=app.ctx.llm_client)
    app.ctx.evaluator = Evaluator(llm_client=app.ctx.llm_client)
    app.ctx.engine = ReflectionEngine(
        llm_client=app.ctx.llm_client,
        evaluator=app.ctx.evaluator
    )
    print("Services initialized.")

@app.listener('after_server_stop')
async def cleanup_services(app: Sanic, loop):
    """
    在服务器关闭后，清理资源
    """
    print("Closing services...")
    await app.ctx.llm_client.close()
    print("Services closed.")

# --- 注册 API ---
setup_recommendation_api(app)

# --- 健康检查端点 ---
@app.get("/")
async def health_check(request: Request):
    return json({"status": "ok", "message": "Welcome to the Reflection Recommender API!"})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True, auto_reload=True) 