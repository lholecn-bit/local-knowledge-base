# 本地知识库系统 - 部署和使用文档

## 目录

1. [系统要求](#系统要求)
2. [安装步骤](#安装步骤)
3. [配置说明](#配置说明)
4. [部署方式](#部署方式)
5. [使用指南](#使用指南)
6. [API 文档](#api-文档)
7. [故障排查](#故障排查)
8. [性能优化](#性能优化)

---

## 系统要求

### 硬件要求

| 项目 | 最低配置       | 推荐配置 |
| ---- | -------------- | -------- |
| CPU  | 2核            | 4核+     |
| 内存 | 4GB            | 8GB+     |
| 存储 | 10GB           | 50GB+    |
| 网络 | 稳定互联网连接 | 20Mbps+  |

### 软件要求

```
- Python 3.8+
- pip 或 conda
- Git
```

### 云端服务（选择一个或多个）

#### Embedding 服务

- **OpenAI**: text-embedding-3-small / text-embedding-3-large
- **阿里云通义**: text-embedding-v1 / text-embedding-v2
- **智谱 AI**: embedding-2
- **Ollama**: 自部署（支持离线）

#### LLM 服务

- **OpenAI**: gpt-3.5-turbo / gpt-4
- **Anthropic Claude**: claude-3-opus / claude-3-sonnet
- **阿里云通义**: qwen-plus / qwen-max
- **智谱 AI**: glm-3-turbo / glm-4

---

## 安装步骤

### 1. 克隆项目

```bash
git clone https://github.com/your-repo/local-knowledge-base.git
cd local-knowledge-base
```

### 2. 创建虚拟环境

#### 使用 venv（推荐）

```bash
# 创建虚拟环境
python -m venv venv

# 激活虚拟环境
# Windows
venv\Scripts\activate
# macOS/Linux
source venv/bin/activate
```

#### 或使用 conda

```bash
conda create -n kb-env python=3.10
conda activate kb-env
```

### 3. 安装依赖

```bash
# 基础依赖
pip install -r requirements.txt

# 或者手动安装
pip install langchain langchain-core langchain-community
pip install openai anthropic
pip install flask flask-cors
pip install python-dotenv
pip install pypdf python-docx markdown2
pip install chromadb
pip install requests
pip install zhipuai dashscope
```

### 4. 项目结构

```
local-knowledge-base/
├── config.py              # 配置文件
├── embeddings.py          # Embedding 适配层
├── llm.py                 # LLM 适配层
├── knowledge_base.py      # 核心知识库
├── app.py                 # Flask API
├── requirements.txt       # 依赖列表
├── .env.example           # 环境变量示例
├── .env                   # 环境变量配置（本地）
├── knowledge_db/          # 向量数据库（自动创建）
├── docs/                  # 文档目录
├── examples/              # 示例脚本
└── README.md
```

---

## 配置说明

### 1. 环境变量配置

创建 `.env` 文件（复制 `.env.example`）：

```bash
cp .env.example .env
```

编辑 `.env` 文件：

```env
# ============ OpenAI 配置 ============
OPENAI_API_KEY=sk-xxxxxxxxxxxxx
OPENAI_API_BASE=https://api.openai.com/v1

# ============ 阿里云通义 配置 ============
DASHSCOPE_API_KEY=sk-xxxxxxxxxxxxx

# ============ 智谱 AI 配置 ============
ZHIPU_API_KEY=xxxxxxxxxxxxx

# ============ Anthropic Claude 配置 ============
CLAUDE_API_KEY=sk-ant-xxxxxxxxxxxxx

# ============ Ollama 配置（本地部署） ============
OLLAMA_API_BASE=http://localhost:11434

# ============ LLM 配置 ============
LLM_PROVIDER=openai              # openai / claude / zhipu / qwen
LLM_MODEL=gpt-3.5-turbo
LLM_API_KEY=${OPENAI_API_KEY}
LLM_API_BASE=${OPENAI_API_BASE}

# ============ Embedding 配置 ============
EMBEDDING_PROVIDER=openai        # openai / zhipu / qwen / ollama
EMBEDDING_MODEL=text-embedding-3-small
EMBEDDING_API_KEY=${OPENAI_API_KEY}
EMBEDDING_API_BASE=${OPENAI_API_BASE}

# ============ 数据库配置 ============
VECTOR_DB_PATH=./knowledge_db
VECTOR_DB_TYPE=chroma            # chroma / milvus / weaviate

# ============ 应用配置 ============
FLASK_ENV=development            # development / production
FLASK_DEBUG=False
LOG_LEVEL=INFO
```

### 2. 详细配置示例

#### 2.1 使用 OpenAI

```env
OPENAI_API_KEY=sk-proj-xxxxxxxxxxxxx
LLM_PROVIDER=openai
LLM_MODEL=gpt-3.5-turbo
EMBEDDING_PROVIDER=openai
EMBEDDING_MODEL=text-embedding-3-small
```

#### 2.2 使用阿里云通义

```env
DASHSCOPE_API_KEY=sk-xxxxxxxxxxxxx
LLM_PROVIDER=qwen
LLM_MODEL=qwen-max
EMBEDDING_PROVIDER=qwen
EMBEDDING_MODEL=text-embedding-v2
```

#### 2.3 使用智谱 AI

```env
ZHIPU_API_KEY=xxxxxxxxxxxxx
LLM_PROVIDER=zhipu
LLM_MODEL=glm-4
EMBEDDING_PROVIDER=zhipu
EMBEDDING_MODEL=embedding-2
```

#### 2.4 使用 Claude

```env
CLAUDE_API_KEY=sk-ant-xxxxxxxxxxxxx
LLM_PROVIDER=claude
LLM_MODEL=claude-3-sonnet-20240229
EMBEDDING_PROVIDER=openai
EMBEDDING_MODEL=text-embedding-3-small
```

#### 2.5 混合配置（本地 Embedding + 云端 LLM）

```env
# 使用本地 Ollama 进行向量化
OLLAMA_API_BASE=http://localhost:11434
EMBEDDING_PROVIDER=ollama
EMBEDDING_MODEL=nomic-embed-text

# 使用 OpenAI 进行回答
OPENAI_API_KEY=sk-xxxxxxxxxxxxx
LLM_PROVIDER=openai
LLM_MODEL=gpt-3.5-turbo
```

### 3. config.py 配置

编辑 `config.py` 中的配置类（可选，如果不想使用 .env）：

```python
# config.py
import os
from dotenv import load_dotenv

load_dotenv()

# 根据环境变量设置
@dataclass
class EmbeddingConfig:
    provider: str = os.getenv("EMBEDDING_PROVIDER", "openai")
    model: str = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")
    api_key: str = os.getenv("OPENAI_API_KEY", "")
    api_base: str = os.getenv("OPENAI_API_BASE", "https://api.openai.com/v1")
    batch_size: int = 100

@dataclass
class LLMConfig:
    provider: str = os.getenv("LLM_PROVIDER", "openai")
    model: str = os.getenv("LLM_MODEL", "gpt-3.5-turbo")
    api_key: str = os.getenv("LLM_API_KEY", "")
    api_base: str = os.getenv("LLM_API_BASE", "")
    temperature: float = 0.7
    max_tokens: int = 2048
```

---

## 部署方式

### 方式 1: 本地开发部署

#### 1.1 单机部署（推荐用于开发测试）

```bash
# 1. 激活虚拟环境
source venv/bin/activate

# 2. 设置环境变量
export FLASK_APP=app.py
export FLASK_ENV=development

# 3. 运行应用
python app.py
```

访问地址：`http://localhost:5000`

#### 1.2 使用 Gunicorn 部署（推荐用于生产）

```bash
# 安装 Gunicorn
pip install gunicorn

# 运行应用
gunicorn -w 4 -b 0.0.0.0:5000 app:app
```

参数说明：

- `-w 4`: 4个工作进程
- `-b 0.0.0.0:5000`: 绑定地址和端口
- `--timeout 300`: 请求超时时间（秒）
- `--access-logfile -`: 输出访问日志
- `--error-logfile -`: 输出错误日志

```bash
gunicorn -w 4 -b 0.0.0.0:5000 --timeout 300 --access-logfile - app:app
```

---

### 方式 2: Docker 部署

#### 2.1 创建 Dockerfile

```dockerfile
# Dockerfile
FROM python:3.10-slim

# 设置工作目录
WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 复制依赖文件
COPY requirements.txt .

# 安装 Python 依赖
RUN pip install --no-cache-dir -r requirements.txt

# 复制应用代码
COPY . .

# 创建数据卷挂载点
VOLUME ["/app/knowledge_db"]

# 暴露端口
EXPOSE 5000

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:5000/api/health || exit 1

# 启动应用
CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:5000", "--timeout", "300", "app:app"]
```

#### 2.2 创建 docker-compose.yml

```yaml
# docker-compose.yml
version: '3.8'

services:
  knowledge-base:
    build: .
    container_name: local-kb
    ports:
      - "5000:5000"
    volumes:
      - ./knowledge_db:/app/knowledge_db
      - ./docs:/app/docs
    environment:
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - LLM_PROVIDER=openai
      - LLM_MODEL=gpt-3.5-turbo
      - EMBEDDING_PROVIDER=openai
      - EMBEDDING_MODEL=text-embedding-3-small
      - FLASK_ENV=production
    restart: always
  
  # 可选：Ollama 本地部署
  ollama:
    image: ollama/ollama
    container_name: ollama
    ports:
      - "11434:11434"
    volumes:
      - ollama_data:/root/.ollama
    environment:
      - OLLAMA_HOST=0.0.0.0:11434
    restart: always

volumes:
  ollama_data:
```

#### 2.3 使用 Docker Compose 部署

```bash
# 1. 创建 .env 文件
cp .env.example .env
# 编辑 .env，填入 API Key

# 2. 启动服务
docker-compose up -d

# 3. 查看日志
docker-compose logs -f knowledge-base

# 4. 停止服务
docker-compose down
```

---

### 方式 3: Kubernetes 部署

#### 3.1 创建 Kubernetes 配置

```yaml
# k8s-deployment.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: kb-config
data:
  FLASK_ENV: "production"
  LLM_PROVIDER: "openai"
  EMBEDDING_PROVIDER: "openai"

---
apiVersion: v1
kind: Secret
metadata:
  name: kb-secrets
type: Opaque
stringData:
  OPENAI_API_KEY: "sk-xxxxxxxxxxxxx"

---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: knowledge-base
spec:
  replicas: 3
  selector:
    matchLabels:
      app: knowledge-base
  template:
    metadata:
      labels:
        app: knowledge-base
    spec:
      containers:
      - name: knowledge-base
        image: your-registry/knowledge-base:latest
        ports:
        - containerPort: 5000
        envFrom:
        - configMapRef:
            name: kb-config
        - secretRef:
            name: kb-secrets
        resources:
          requests:
            cpu: "500m"
            memory: "1Gi"
          limits:
            cpu: "1000m"
            memory: "2Gi"
        livenessProbe:
          httpGet:
            path: /api/health
            port: 5000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /api/health
            port: 5000
          initialDelaySeconds: 10
          periodSeconds: 5
        volumeMounts:
        - name: kb-data
          mountPath: /app/knowledge_db
      volumes:
      - name: kb-data
        persistentVolumeClaim:
          claimName: kb-pvc

---
apiVersion: v1
kind: Service
metadata:
  name: knowledge-base-service
spec:
  type: LoadBalancer
  ports:
  - port: 80
    targetPort: 5000
  selector:
    app: knowledge-base

---
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: kb-pvc
spec:
  accessModes:
    - ReadWriteOnce
  resources:
    requests:
      storage: 50Gi
```

#### 3.2 部署到 Kubernetes

```bash
# 1. 构建镜像并推送到仓库
docker build -t your-registry/knowledge-base:latest .
docker push your-registry/knowledge-base:latest

# 2. 部署到 K8s
kubectl apply -f k8s-deployment.yaml

# 3. 查看部署状态
kubectl get pods
kubectl get svc

# 4. 查看日志
kubectl logs -f deployment/knowledge-base

# 5. 访问服务
kubectl port-forward svc/knowledge-base-service 5000:80
```

---

### 方式 4: 云平台部署

#### 4.1 部署到阿里云 ECS

```bash
# 1. 连接到 ECS 实例
ssh -i your-key.pem root@your-instance-ip

# 2. 安装依赖
apt-get update
apt-get install -y python3.10 python3-pip python3-venv git

# 3. 克隆项目
git clone https://github.com/your-repo/local-knowledge-base.git
cd local-knowledge-base

# 4. 创建虚拟环境
python3 -m venv venv
source venv/bin/activate

# 5. 安装依赖
pip install -r requirements.txt

# 6. 配置环境变量
nano .env
# 填入 API Key 和配置

# 7. 使用 systemd 管理服务
sudo nano /etc/systemd/system/knowledge-base.service
```

编辑 `/etc/systemd/system/knowledge-base.service`：

```ini
[Unit]
Description=Local Knowledge Base Service
After=network.target

[Service]
Type=notify
User=root
WorkingDirectory=/root/local-knowledge-base
Environment="PATH=/root/local-knowledge-base/venv/bin"
EnvironmentFile=/root/local-knowledge-base/.env
ExecStart=/root/local-knowledge-base/venv/bin/gunicorn \
    -w 4 \
    -b 0.0.0.0:5000 \
    --timeout 300 \
    --access-logfile /var/log/kb/access.log \
    --error-logfile /var/log/kb/error.log \
    app:app
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

启动服务：

```bash
# 创建日志目录
mkdir -p /var/log/kb
chmod 755 /var/log/kb

# 启动服务
sudo systemctl start knowledge-base
sudo systemctl enable knowledge-base

# 查看状态
sudo systemctl status knowledge-base

# 查看日志
tail -f /var/log/kb/error.log
```

#### 4.2 部署到 AWS Lambda（无服务器）

```python
# lambda_handler.py
from knowledge_base import LocalKnowledgeBase
from config import EmbeddingConfig, LLMConfig
import json
import os

# 全局初始化（Lambda 会复用）
kb = None

def init_kb():
    global kb
    if kb is None:
        embedding_config = EmbeddingConfig(
            provider=os.getenv("EMBEDDING_PROVIDER", "openai"),
            model=os.getenv("EMBEDDING_MODEL"),
            api_key=os.getenv("OPENAI_API_KEY"),
        )
        llm_config = LLMConfig(
            provider=os.getenv("LLM_PROVIDER", "openai"),
            model=os.getenv("LLM_MODEL"),
            api_key=os.getenv("OPENAI_API_KEY"),
        )
        kb = LocalKnowledgeBase(
            embedding_config=embedding_config,
            llm_config=llm_config,
        )

def lambda_handler(event, context):
    """Lambda 处理函数"""
    try:
        init_kb()
      
        body = json.loads(event.get("body", "{}"))
        action = body.get("action")
      
        if action == "query":
            result = kb.query(
                question=body.get("question"),
                top_k=body.get("top_k", 3),
            )
            return {
                "statusCode": 200,
                "body": json.dumps(result, ensure_ascii=False),
            }
      
        elif action == "search":
            results = kb.similarity_search(
                query=body.get("query"),
                top_k=body.get("top_k", 5),
            )
            return {
                "statusCode": 200,
                "body": json.dumps({"results": results}, ensure_ascii=False),
            }
      
        else:
            return {
                "statusCode": 400,
                "body": json.dumps({"error": "未知的 action"}),
            }
  
    except Exception as e:
        return {
            "statusCode": 500,
            "body": json.dumps({"error": str(e)}),
        }
```

---

## 使用指南

### 1. 快速开始脚本

创建 `quick_start.py`：

```python
# quick_start.py
"""快速开始示例"""

from knowledge_base import LocalKnowledgeBase
from config import EmbeddingConfig, LLMConfig, VECTOR_STORE_CONFIG

def main():
    print("=" * 60)
    print("本地知识库系统 - 快速开始")
    print("=" * 60)
  
    # 1. 初始化知识库
    print("\n[1/4] 初始化知识库...")
  
    embedding_config = EmbeddingConfig(
        provider="openai",
        model="text-embedding-3-small",
    )
  
    llm_config = LLMConfig(
        provider="openai",
        model="gpt-3.5-turbo",
    )
  
    kb = LocalKnowledgeBase(
        embedding_config=embedding_config,
        llm_config=llm_config,
        vector_store_config=VECTOR_STORE_CONFIG,
    )
  
    # 2. 添加文档
    print("\n[2/4] 添加文档...")
    print("请放置文档到 ./docs 目录，支持 PDF、TXT、Markdown 格式")
  
    doc_paths = ["./docs"]  # 修改为实际路径
    count = kb.add_documents(doc_paths)
    print(f"✓ 成功添加 {count} 个文本块")
  
    # 3. 执行查询
    print("\n[3/4] 执行查询...")
    question = input("请输入问题（或按 Enter 使用默认问题）: ").strip()
    if not question:
        question = "请总结一下文档的主要内容"
  
    result = kb.query(question, top_k=3)
  
    print(f"\n📌 问题: {result['question']}")
    print(f"\n💬 回答:\n{result['answer']}")
  
    print(f"\n📚 相关文档 ({len(result['source_documents'])} 个):")
    for i, doc in enumerate(result['source_documents'], 1):
        print(f"\n  [{i}] {doc['content'][:150]}...")
        print(f"      来源: {doc['metadata']}")
  
    # 4. 相似度搜索
    print("\n[4/4] 相似度搜索...")
    query = input("请输入搜索关键词: ").strip()
    if query:
        similar_docs = kb.similarity_search(query, top_k=3)
        print(f"\n搜索结果 ({len(similar_docs)} 个):")
        for i, doc in enumerate(similar_docs, 1):
            print(f"\n  [{i}] 相似度: {doc['score']:.3f}")
            print(f"      内容: {doc['content'][:150]}...")


if __name__ == "__main__":
    main()
```

运行：

```bash
python quick_start.py
```

---

### 2. Python 集成示例

#### 2.1 基础使用

```python
# example_basic.py
from knowledge_base import LocalKnowledgeBase

# 初始化
kb = LocalKnowledgeBase()

# 添加文档
kb.add_documents([
    "./docs/document1.pdf",
    "./docs/document2.txt",
    "./docs/folder",
])

# 查询
result = kb.query("什么是机器学习？")
print(f"问题: {result['question']}")
print(f"回答: {result['answer']}")

# 搜索
docs = kb.similarity_search("神经网络", top_k=5)
for doc in docs:
    print(f"相似度: {doc['score']:.3f}, 内容: {doc['content'][:100]}")
```

#### 2.2 流式响应

```python
# example_stream.py
from knowledge_base import LocalKnowledgeBase

kb = LocalKnowledgeBase()

# 流式查询
print("回答: ", end="", flush=True)
for chunk in kb.stream_query("解释一下深度学习的原理"):
    print(chunk, end="", flush=True)
print()
```

#### 2.3 批量处理

```python
# example_batch.py
from knowledge_base import LocalKnowledgeBase

kb = LocalKnowledgeBase()

# 添加大量文档
import glob
pdf_files = glob.glob("./docs/**/*.pdf", recursive=True)
kb.add_documents(pdf_files)

# 批量查询
questions = [
    "什么是人工智能？",
    "机器学习的应用有哪些？",
    "深度学习和神经网络有什么区别？",
]

for question in questions:
    result = kb.query(question, top_k=3)
    print(f"\nQ: {question}")
    print(f"A: {result['answer'][:200]}...")
```

---

### 3. API 使用示例

#### 3.1 使用 curl

```bash
# 启动服务
python app.py

# 健康检查
curl http://localhost:5000/api/health

# 查询
curl -X POST http://localhost:5000/api/query \
  -H "Content-Type: application/json" \
  -d '{
    "question": "什么是机器学习？",
    "top_k": 3
  }'

# 添加文档
curl -X POST http://localhost:5000/api/add-documents \
  -H "Content-Type: application/json" \
  -d '{
    "doc_paths": ["./docs/example.pdf"]
  }'

# 相似度搜索
curl -X POST http://localhost:5000/api/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "神经网络",
    "top_k": 5
  }'

# 清空知识库
curl -X POST http://localhost:5000/api/clear-db
```

#### 3.2 使用 Python requests

```python
# example_api.py
import requests
import json

BASE_URL = "http://localhost:5000"

def query(question, top_k=3):
    """查询知识库"""
    response = requests.post(
        f"{BASE_URL}/api/query",
        json={"question": question, "top_k": top_k}
    )
    return response.json()

def add_documents(doc_paths):
    """添加文档"""
    response = requests.post(
        f"{BASE_URL}/api/add-documents",
        json={"doc_paths": doc_paths}
    )
    return response.json()

def search(query_text, top_k=5):
    """搜索"""
    response = requests.post(
        f"{BASE_URL}/api/search",
        json={"query": query_text, "top_k": top_k}
    )
    return response.json()

# 使用示例
if __name__ == "__main__":
    # 添加文档
    print("添加文档...")
    result = add_documents(["./docs"])
    print(f"✓ 添加了 {result['added_chunks']} 个文本块")
  
    # 查询
    print("\n查询...")
    result = query("什么是机器学习？", top_k=3)
    print(f"问题: {result['question']}")
    print(f"回答: {result['answer']}")
  
    # 搜索
    print("\n搜索...")
    result = search("神经网络", top_k=3)
    print(f"找到 {len(result['results'])} 个结果")
    for doc in result['results']:
        print(f"  - {doc['content'][:100]}...")
```

#### 3.3 使用 JavaScript/Node.js

```javascript
// example_api.js
const fetch = require('node-fetch');

const BASE_URL = 'http://localhost:5000';

async function query(question, topK = 3) {
    const response = await fetch(`${BASE_URL}/api/query`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question, top_k: topK })
    });
    return response.json();
}

async function search(queryText, topK = 5) {
    const response = await fetch(`${BASE_URL}/api/search`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query: queryText, top_k: topK })
    });
    return response.json();
}

// 使用示例
(async () => {
    const result = await query('什么是机器学习？', 3);
    console.log('问题:', result.question);
    console.log('回答:', result.answer);
})();
```

#### 3.4 流式 API 调用

```python
# example_stream_api.py
import requests
import json

BASE_URL = "http://localhost:5000"

def stream_query(question, top_k=3):
    """流式查询"""
    response = requests.post(
        f"{BASE_URL}/api/stream-query",
        json={"question": question, "top_k": top_k},
        stream=True
    )
  
    for line in response.iter_lines():
        if line:
            data = json.loads(line)
            if "chunk" in data:
                yield data["chunk"]

# 使用示例
print("回答: ", end="", flush=True)
for chunk in stream_query("解释一下深度学习"):
    print(chunk, end="", flush=True)
print()
```

---

## API 文档

### 1. 查询接口

**请求**

```
POST /api/query
Content-Type: application/json

{
  "question": "什么是机器学习？",
  "top_k": 3
}
```

**响应**

```json
{
  "question": "什么是机器学习？",
  "answer": "机器学习是人工智能的一个重要分支...",
  "source_documents": [
    {
      "content": "机器学习是使计算机系统能够从数据中学习和改进，而无需被明确编程的科学...",
      "metadata": {
        "source": "/path/to/document.pdf",
        "page": 1
      }
    }
  ]
}
```

**参数说明**

| 参数     | 类型    | 必需 | 说明                       |
| -------- | ------- | ---- | -------------------------- |
| question | string  | ✓   | 问题                       |
| top_k    | integer |      | 返回的相关文档数（默认 3） |

**返回值**

| 字段     | 类型   | 说明     |
| -------- | ------ | -------- |
| question | string | 原始问题 |
| answer   |        |          |
