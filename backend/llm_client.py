# backend/llm_client.py
import httpx
import asyncio
from typing import AsyncGenerator, Optional
import json
import os


class LLMClient:
    """LLM 客户端 - 调用大模型 API"""
    
    def __init__(self, 
                 api_url: str = "https://api.openai.com/v1",
                 api_key: str = None,
                 model: str = "gpt-3.5-turbo",
                 temperature: float = 0.7,
                 max_tokens: int = 2000):
        """
        初始化 LLM 客户端
        
        Args:
            api_url: API 地址
            api_key: API 密钥
            model: 使用的模型
            temperature: 温度参数
            max_tokens: 最大令牌数
        """
        self.api_url = api_url
        self.api_key = api_key or self._get_api_key()
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        
        # 清除系统代理设置
        self._clear_proxy_env()
        
        if not self.api_key:
            print("Warning: No API key found. LLM features may not work.")
    
    def _get_api_key(self) -> Optional[str]:
        """从环境变量获取 API 密钥"""
        return os.getenv('OPENAI_API_KEY') or os.getenv('LLM_API_KEY')
    
    def _clear_proxy_env(self):
        """清除代理相关的环境变量 - 这很重要！"""
        proxy_vars = [
            'http_proxy', 'https_proxy', 'HTTP_PROXY', 'HTTPS_PROXY',
            'ALL_PROXY', 'SOCKS_PROXY', 'socks_proxy',
            'no_proxy', 'NO_PROXY'
        ]
        for var in proxy_vars:
            if var in os.environ:
                print(f"DEBUG: Removing proxy env var: {var}={os.environ[var]}")
                os.environ.pop(var, None)
    
    def chat(self, message: str, system: str = None) -> str:
        """
        同步调用 LLM
        
        Args:
            message: 用户消息
            system: 系统提示词
            
        Returns:
            模型响应文本
        """
        try:
            headers = {
                'Authorization': f'Bearer {self.api_key}',
                'Content-Type': 'application/json'
            }
            
            messages = []
            if system:
                messages.append({'role': 'system', 'content': system})
            messages.append({'role': 'user', 'content': message})
            
            payload = {
                'model': self.model,
                'messages': messages,
                'temperature': self.temperature,
                'max_tokens': self.max_tokens
            }
            
            # 创建客户端时显式禁用代理
            with httpx.Client(
                timeout=60.0,
                trust_env=False  # 这很关键！
            ) as client:
                response = client.post(
                    f'{self.api_url}/chat/completions',
                    headers=headers,
                    json=payload
                )
            
            response.raise_for_status()
            result = response.json()
            
            return result['choices'][0]['message']['content']
        
        except Exception as e:
            print(f"LLM Error: {e}")
            return f"Error calling LLM: {str(e)}"
    
    async def stream_chat(self, message: str, system: str = None) -> AsyncGenerator[str, None]:
        """
        异步流式调用 LLM
        
        Args:
            message: 用户消息
            system: 系统提示词
            
        Yields:
            模型响应片段
        """
        try:
            headers = {
                'Authorization': f'Bearer {self.api_key}',
                'Content-Type': 'application/json'
            }
            
            messages = []
            if system:
                messages.append({'role': 'system', 'content': system})
            messages.append({'role': 'user', 'content': message})
            
            payload = {
                'model': self.model,
                'messages': messages,
                'temperature': self.temperature,
                'max_tokens': self.max_tokens,
                'stream': True
            }
            
            # 创建客户端时显式禁用代理
            async with httpx.AsyncClient(
                timeout=60.0,
                trust_env=False  # 这很关键！
            ) as client:
                async with client.stream(
                    'POST',
                    f'{self.api_url}/chat/completions',
                    headers=headers,
                    json=payload
                ) as response:
                    response.raise_for_status()
                    
                    async for line in response.aiter_lines():
                        if line.startswith('data: '):
                            data_str = line[6:]
                            
                            if data_str == '[DONE]':
                                break
                            
                            try:
                                data = json.loads(data_str)
                                chunk = data['choices'][0].get('delta', {}).get('content', '')
                                if chunk:
                                    yield chunk
                            except json.JSONDecodeError:
                                continue
        
        except Exception as e:
            print(f"LLM Stream Error: {e}")
            yield f"\n\nError: {str(e)}"


# 如果要支持其他 API（如阿里云、百度等），可以添加相应的实现
class ALiLLMClient(LLMClient):
    """阿里云 LLM 客户端"""
    
    def __init__(self, api_key: str = None, model: str = "qwen-plus"):
        super().__init__(
            api_url="https://dashscope.aliyuncs.com/api/v1",
            api_key=api_key,
            model=model
        )


class LocalLLMClient(LLMClient):
    """本地 LLM 客户端（例如 Ollama）"""
    
    def __init__(self, api_url: str = "http://localhost:11434/api", model: str = "llama2"):
        super().__init__(
            api_url=api_url,
            model=model
        )
