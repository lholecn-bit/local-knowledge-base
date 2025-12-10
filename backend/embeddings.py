# embeddings.py
from typing import List
from abc import ABC, abstractmethod
from backend.config import EmbeddingConfig


class BaseEmbedding(ABC):
    """Embedding基类"""

    def __init__(self, config: EmbeddingConfig):
        self.config = config

    @abstractmethod
    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """嵌入文档列表"""
        pass

    @abstractmethod
    def embed_query(self, text: str) -> List[float]:
        """嵌入查询"""
        pass


class OpenAIEmbedding(BaseEmbedding):
    """OpenAI Embedding"""

    def __init__(self, config: EmbeddingConfig):
        super().__init__(config)
        from openai import OpenAI

        self.client = OpenAI(
            api_key=config.api_key,
            base_url=config.api_base,
        )

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """批量嵌入文档"""
        embeddings = []
        for i in range(0, len(texts), self.config.batch_size):
            batch = texts[i : i + self.config.batch_size]
            response = self.client.embeddings.create(
                model=self.config.model,
                input=batch,
            )
            embeddings.extend([item.embedding for item in response.data])
        return embeddings

    def embed_query(self, text: str) -> List[float]:
        """嵌入单个查询"""
        response = self.client.embeddings.create(
            model=self.config.model,
            input=text,
        )
        return response.data[0].embedding


class ZhipuEmbedding(BaseEmbedding):
    """智谱 Embedding"""

    def __init__(self, config: EmbeddingConfig):
        super().__init__(config)
        import zhipuai

        zhipuai.api_key = config.api_key

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """批量嵌入文档"""
        import zhipuai

        embeddings = []
        for i in range(0, len(texts), self.config.batch_size):
            batch = texts[i : i + self.config.batch_size]
            response = zhipuai.model_api.embedding(
                model=self.config.model,
                texts=batch,
            )
            if response["code"] == 200:
                embeddings.extend([item["embedding"] for item in response["data"]])
        return embeddings

    def embed_query(self, text: str) -> List[float]:
        """嵌入单个查询"""
        import zhipuai

        response = zhipuai.model_api.embedding(
            model=self.config.model,
            texts=[text],
        )
        if response["code"] == 200:
            return response["data"][0]["embedding"]
        return []


class QwenEmbedding(BaseEmbedding):
    """阿里云通义 Embedding"""

    def __init__(self, config: EmbeddingConfig):
        super().__init__(config)
        from dashscope import TextEmbedding

        self.client = TextEmbedding

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """批量嵌入文档"""
        embeddings = []
        for i in range(0, len(texts), self.config.batch_size):
            batch = texts[i : i + self.config.batch_size]
            response = self.client.call(
                model=self.config.model,
                input=batch,
                api_key=self.config.api_key,
            )
            if response.status_code == 200:
                embeddings.extend(
                    [item["embedding"] for item in response.output["embeddings"]]
                )
        return embeddings

    def embed_query(self, text: str) -> List[float]:
        """嵌入单个查询"""
        response = self.client.call(
            model=self.config.model,
            input=[text],
            api_key=self.config.api_key,
        )
        if response.status_code == 200:
            return response.output["embeddings"][0]["embedding"]
        return []


class OllamaEmbedding(BaseEmbedding):
    """Ollama Embedding (可部署在云端)"""

    def __init__(self, config: EmbeddingConfig):
        super().__init__(config)
        import requests

        self.base_url = config.api_base or "http://localhost:11434"
        self.requests = requests

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """批量嵌入文档"""
        embeddings = []
        for text in texts:
            embedding = self.embed_query(text)
            embeddings.append(embedding)
        return embeddings

    def embed_query(self, text: str) -> List[float]:
        """嵌入单个查询"""
        response = self.requests.post(
            f"{self.base_url}/api/embeddings",
            json={
                "model": self.config.model,
                "prompt": text,
            },
        )
        if response.status_code == 200:
            return response.json()["embedding"]
        return []


def create_embedding(config: EmbeddingConfig) -> BaseEmbedding:
    """工厂函数创建Embedding实例"""
    embeddings = {
        "openai": OpenAIEmbedding,
        "zhipu": ZhipuEmbedding,
        "qwen": QwenEmbedding,
        "ollama": OllamaEmbedding,
    }

    embedding_class = embeddings.get(config.provider)
    if not embedding_class:
        raise ValueError(f"不支持的provider: {config.provider}")

    return embedding_class(config)
