"""
DeepSeek API 客户端
封装 DeepSeek 的 Embedding 和 Chat 能力
"""
from openai import OpenAI
from typing import List, Dict
from config import (
    DEEPSEEK_API_KEY,
    DEEPSEEK_BASE_URL,
    LLM_MODEL,
    LLM_TEMPERATURE,
    LLM_MAX_TOKENS
)

class DeepSeekClient:
    """DeepSeek API 客户端封装"""

    def __init__(self):
        """初始化 DeepSeek 客户端"""
        self.client = OpenAI(
            api_key=DEEPSEEK_API_KEY,
            base_url=DEEPSEEK_BASE_URL
        )

    def get_embeddings(self, texts: List[str]) -> List[List[float]]:
        """
        获取文本的向量表示（Embedding）

        注意：DeepSeek 目前可能没有专门的 Embedding API
        如果有，直接使用；如果没有，暂时使用 OpenAI 的或本地模型
        """
        # DeepSeek 目前主要提供 Chat API，Embedding 功能可能尚未完善
        # 这里使用兼容 OpenAI 接口的方式调用
        try:
            response = self.client.embeddings.create(
                model=EMBEDDING_MODEL,  # 可能需要使用其他模型
                input=texts
            )
            return [item.embedding for item in response.data]
        except Exception as e:
            # 如果 DeepSeek 不支持 Embedding，抛出错误并提示解决方案
            raise RuntimeError(
                f"获取 Embedding 失败: {e}\n"
                "DeepSeek 可能暂不支持 Embedding API。\n"
                "解决方案：\n"
                "1. 使用 OpenAI 的 Embedding API（推荐，效果好）\n"
                "2. 使用本地 Embedding 模型（如 sentence-transformers）\n"
                "3. 等待 DeepSeek 更新 Embedding 支持"
            )

    def chat(
        self,
        messages: List[Dict[str, str]],
        temperature: float = None,
        max_tokens: int = None
    ) -> str:
        """
        调用 DeepSeek Chat API 生成回答

        Args:
            messages: 对话历史，格式为 [{"role": "user/system/assistant", "content": "..."}]
            temperature: 随机性（0-1，越低越确定）
            max_tokens: 最大生成 token 数

        Returns:
            AI 生成的回答文本
        """
        response = self.client.chat.completions.create(
            model=LLM_MODEL,
            messages=messages,
            temperature=temperature or LLM_TEMPERATURE,
            max_tokens=max_tokens or LLM_MAX_TOKENS,
            stream=False
        )

        return response.choices[0].message.content

    def chat_stream(
        self,
        messages: List[Dict[str, str]],
        temperature: float = None,
        max_tokens: int = None
    ):
        """
        流式调用 DeepSeek Chat API（实时返回生成内容）
        用于前端展示打字机效果
        """
        stream = self.client.chat.completions.create(
            model=LLM_MODEL,
            messages=messages,
            temperature=temperature or LLM_TEMPERATURE,
            max_tokens=max_tokens or LLM_MAX_TOKENS,
            stream=True
        )

        for chunk in stream:
            if chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content


class EmbeddingClient:
    """
    Embedding 客户端
    支持多种 Embedding 方案：OpenAI、智谱 AI、本地模型
    """

    def __init__(self, provider: str = None):
        """
        初始化 Embedding 客户端

        Args:
            provider: "openai"、"zhipu" 或 "local"，默认从环境变量读取
        """
        from config import EMBEDDING_PROVIDER, EMBEDDING_MODELS

        self.provider = provider or EMBEDDING_PROVIDER
        self.model_name = EMBEDDING_MODELS.get(self.provider, EMBEDDING_MODELS["openai"])

        if self.provider == "openai":
            self._init_openai()
        elif self.provider == "zhipu":
            self._init_zhipu()
        elif self.provider == "local":
            self._init_local()
        else:
            raise ValueError(f"不支持的 Embedding provider: {self.provider}")

    def _init_openai(self):
        """初始化 OpenAI Embedding"""
        import os
        openai_key = os.getenv("OPENAI_API_KEY", "")
        if not openai_key:
            raise ValueError(
                "使用 OpenAI Embedding 需要提供 OPENAI_API_KEY 环境变量\n"
                "获取地址: https://platform.openai.com/"
            )
        self.client = OpenAI(api_key=openai_key)

    def _init_zhipu(self):
        """初始化智谱 AI Embedding"""
        import os
        zhipu_key = os.getenv("ZHIPU_API_KEY", "")
        if not zhipu_key:
            raise ValueError(
                "使用智谱 AI Embedding 需要提供 ZHIPU_API_KEY 环境变量\n"
                "获取地址: https://open.bigmodel.cn/"
            )
        self.api_key = zhipu_key
        self.base_url = "https://open.bigmodel.cn/api/paas/v4"

    def _init_local(self):
        """初始化本地 Embedding 模型"""
        try:
            from sentence_transformers import SentenceTransformer
            print(f"正在加载本地 Embedding 模型: {self.model_name}")
            print("首次加载可能需要下载模型（约 100MB），请耐心等待...")
            self.model = SentenceTransformer(self.model_name)
            print("模型加载完成！")
        except ImportError:
            raise ImportError(
                "使用本地 Embedding 需要安装: pip install sentence-transformers\n"
                "或选择其他 Embedding 方案（修改 EMBEDDING_PROVIDER 环境变量）"
            )

    def get_embeddings(self, texts: List[str]) -> List[List[float]]:
        """获取文本的向量表示"""
        if self.provider == "openai":
            response = self.client.embeddings.create(
                model=self.model_name,
                input=texts
            )
            return [item.embedding for item in response.data]

        elif self.provider == "zhipu":
            # 智谱 AI Embedding API
            import requests
            response = requests.post(
                f"{self.base_url}/embeddings",
                headers={"Authorization": f"Bearer {self.api_key}"},
                json={
                    "model": self.model_name,
                    "input": texts
                },
                timeout=60
            )
            response.raise_for_status()
            result = response.json()
            return [item["embedding"] for item in result["data"]]

        elif self.provider == "local":
            embeddings = self.model.encode(texts)
            return embeddings.tolist()

        else:
            raise ValueError(f"未知的 provider: {self.provider}")


# 便捷函数
def get_llm_client() -> DeepSeekClient:
    """获取 LLM 客户端（对话用）"""
    return DeepSeekClient()


def get_embedding_client() -> EmbeddingClient:
    """获取 Embedding 客户端"""
    from config import EMBEDDING_PROVIDER
    return EmbeddingClient(provider=EMBEDDING_PROVIDER)
