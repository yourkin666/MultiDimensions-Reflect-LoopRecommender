import httpx
import os
from typing import Optional

class LLMClient:
    """
    与大模型 API 交互的客户端
    """
    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None, model: str = "gpt-4"):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.base_url = base_url or os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
        self.model = model
        
        if not self.api_key:
            raise ValueError("API key is required. Please provide it or set OPENAI_API_KEY environment variable.")

        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            timeout=60.0, # 设置默认超时时间
        )

    async def generate(self, prompt: str, max_tokens: int = 1024) -> str:
        """
        向大模型发送单个提示并获取响应
        """
        request_body = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": max_tokens,
            "temperature": 0.2, # 较低的温度以获得更确定的输出
        }
        
        try:
            response = await self.client.post("/chat/completions", json=request_body)
            response.raise_for_status() # 如果响应状态码不是 2xx，则抛出异常
            
            result = response.json()
            return result["choices"][0]["message"]["content"].strip()
            
        except httpx.HTTPStatusError as e:
            print(f"调用LLM API时发生HTTP错误: {e.response.status_code} - {e.response.text}")
            raise
        except (httpx.RequestError, KeyError, IndexError) as e:
            print(f"调用LLM API或解析响应时出错: {e}")
            raise

    async def close(self):
        """
        关闭 httpx 客户端
        """
        await self.client.aclose() 