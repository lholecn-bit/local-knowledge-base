# 本地知识库系统 (Local Knowledge Base System)

一个基于 **RAG（检索增强生成）** 的智能知识库系统，支持文档管理、向量检索、智能重排序和流式LLM回复。

![Python](https://img.shields.io/badge/Python-3.8+-blue) 
![Flask](https://img.shields.io/badge/Flask-2.3+-green) 
![LangChain](https://img.shields.io/badge/LangChain-0.1+-purple)
![License](https://img.shields.io/badge/License-MIT-brightgreen)

---

## ✨ 核心特性

- 📄 **多格式文档支持**: PDF、Markdown、纯文本文件
- 🔍 **向量语义搜索**: 基于 OpenAI Embeddings + FAISS 向量数据库
- 🎯 **智能重排序**: 使用 CrossEncoder 重新排列搜索结果
- 🤖 **三种查询模式**:
  - **Auto** 自动模式：优先使用知识库，无相关内容则直接调用LLM
  - **KB** 知识库模式：强制搜索知识库
  - **LLM** 大模型模式：直接调用LLM，跳过知识库
- 🌊 **流式响应**: 实时输出LLM生成内容，提升用户体验
- 📊 **系统统计**: 实时查看知识库内容和系统状态
- 🏠 **完全本地化**: 支持离线模式，模型缓存在本地
- 🔐 **隐私保护**: 所有数据存储在本地，无云端依赖

---

## 🚀 快速开始

### 1. 环境要求

- Python 3.8+
- pip 或 conda
- OpenAI API Key（用于向量化和LLM回复）

### 2. 安装依赖

```bash
# 克隆仓库
git clone https://github.com/lholecn-bit/local-knowledge-base.git
cd local-knowledge-base

# 创建虚拟环境（推荐）
python -m venv venv
source venv/bin/activate  # macOS/Linux
# 或
venv\Scripts\activate  # Windows

# 安装依赖
pip install -r backend/requirements.txt
```

### 3. 配置环境变量

在项目根目录创建 `.env` 文件：

```bash
# 必需
OPENAI_API_KEY=sk-your-api-key-here

# 可选
OPENAI_BASE_URL=https://api.openai.com/v1  # 支持国内代理API
LLM_MODEL=gpt-3.5-turbo                     # 默认模型
FLASK_ENV=development
```

### 4. 启动后端

```bash
cd backend
python app.py
```

系统将在 `http://localhost:5000` 启动，日志输出如下：

```
✅ Flask 应用已启动
📚 知识库已初始化
🌐 服务运行在 http://localhost:5000
```

### 5. 启动前端

新开一个终端：

```bash
# 方法1: 使用 Python 简单服务器
cd frontend
python -m http.server 3000

# 方法2: 直接在浏览器打开
open frontend/index.html
```

然后在浏览器访问 `http://localhost:3000`

---

## 📋 使用指南

### 上传文档

1. 点击前端 "📤 上传文件" 按钮
2. 选择 PDF、MD 或 TXT 文件（支持多选）
3. 系统自动：
   - 加载和分块（chunk_size=1000, overlap=200）
   - 向量化（使用 text-embedding-3-small）
   - 存储到 FAISS 向量库
   - 记录元数据防止重复

### 查询知识库

#### 自动模式 (推荐)
```javascript
POST /api/stream-query
{
  "question": "什么是向量数据库？",
  "mode": "auto",
  "top_k": 3
}
```
- 优先搜索知识库
- 若有相关文档，使用RAG生成回复
- 若无相关文档，直接调用LLM

#### 知识库模式
```javascript
{
  "question": "...",
  "mode": "kb",
  "top_k": 5
}
```
- 必须从知识库中搜索
- 无论是否有相关文档都返回搜索结果
- 适合专注于知识库内容的场景

#### LLM模式
```javascript
{
  "question": "...",
  "mode": "llm"
}
```
- 跳过知识库，直接调用LLM
- 适合通用问题和实时信息需求

---

## 🏗️ 系统架构

```
┌─────────────────────────────────────────────────────────────┐
│                        Frontend (Vue/JS)                    │
│                 index.html + js/{app,api,ui}.js             │
└────────────┬────────────────────────────────────────────────┘
             │ HTTP REST (JSON)
             ▼
┌─────────────────────────────────────────────────────────────┐
│                    Backend (Flask)                          │
│                      app.py                                 │
├─────────────────────────────────────────────────────────────┤
│  /api/stream-query      (流式RAG查询)                       │
│  /api/kb/search         (向量搜索)                          │
│  /api/documents/upload  (文档上传)                          │
│  /api/documents/list    (文档列表)                          │
│  /api/health            (系统检查)                          │
└────────┬────────────────────────┬─────────────────────────┘
         │                        │
         ▼                        ▼
   ┌──────────────┐      ┌──────────────────────┐
   │ LangChain    │      │ OpenAI API           │
   │ + FAISS      │      │ - Embeddings         │
   │ 向量检索     │      │ - LLM Chat/Streaming │
   └──────────────┘      └──────────────────────┘
         │
         ▼
   ┌──────────────────────┐
   │ models_cache/        │
   │ - embeddings         │
   │ - CrossEncoder       │
   └──────────────────────┘
```

### 数据流

```
User Question
    ▼
Frontend (js/app.js)
    ▼
POST /api/stream-query
    ▼
Backend (app.py:stream_query)
    ▼
┌─────────────────────────────────────────┐
│ 1. Knowledge Base Search                │
│    kb.search(question, top_k=3)         │
│    ├─ FAISS 相似度搜索                  │
│    ├─ 阈值过滤 (similarity >= 0.3)      │
│    └─ CrossEncoder 重排序               │
└─────────────────────────────────────────┘
    ▼
┌─────────────────────────────────────────┐
│ 2. Build RAG Prompt                     │
│    "Based on the documents: {...}"      │
└─────────────────────────────────────────┘
    ▼
┌─────────────────────────────────────────┐
│ 3. Stream LLM Response                  │
│    llm_client.stream_chat()             │
│    └─ 逐token流式返回                   │
└─────────────────────────────────────────┘
    ▼
Frontend (parseStreamResponse)
    ▼
Real-time Display
```

---

## 📡 API 文档

### 1. 流式查询 (主要接口)

**请求:**
```http
POST /api/stream-query
Content-Type: application/json

{
  "question": "什么是向量数据库？",
  "mode": "auto",
  "top_k": 3
}
```

**响应流 (JSON Lines 格式):**
```json
{"type":"start","mode":"auto","sources":[]}
{"type":"chunk","content":"向量数据库是"}
{"type":"chunk","content":"一种存储"}
...
{"type":"end","sources":["file1.pdf","file2.md"]}
```

### 2. 向量搜索

**请求:**
```http
POST /api/kb/search
Content-Type: application/json

{
  "query": "向量数据库",
  "top_k": 5
}
```

**响应:**
```json
{
  "query": "向量数据库",
  "results": [
    {
      "content": "向量数据库是...",
      "source": "file1.pdf",
      "score": 0.87
    }
  ],
  "has_results": true
}
```

### 3. 上传文档

**请求:**
```http
POST /api/documents/upload
Content-Type: multipart/form-data

files: [file1.pdf, file2.md, ...]
```

**响应:**
```json
{
  "added_chunks": 42,
  "files": ["file1.pdf", "file2.md"],
  "errors": []
}
```

### 4. 列表文档

**请求:**
```http
GET /api/documents/list
```

**响应:**
```json
{
  "documents": [
    {
      "filename": "VECTOR_DATABASE_GUIDE.md",
      "chunks": 12,
      "added_time": "2025-01-15T10:00:00",
      "size_kb": 45
    }
  ]
}
```

### 5. 删除文档

**请求:**
```http
DELETE /api/documents/<filename>
```

**响应:**
```json
{
  "message": "deleted",
  "filename": "old_file.pdf"
}
```

### 6. 系统状态

**请求:**
```http
GET /api/health
```

**响应:**
```json
{
  "status": "ok",
  "kb_ready": true,
  "embeddings_loaded": true,
  "vector_count": 156,
  "document_count": 3
}
```

---

## ⚙️ 配置详解

### 环境变量

| 变量 | 必需 | 说明 | 示例 |
|------|------|------|------|
| `OPENAI_API_KEY` | ✅ | OpenAI API密钥 | `sk-...` |
| `OPENAI_BASE_URL` | ❌ | API代理地址 | `https://api.openai.com/v1` |
| `LLM_MODEL` | ❌ | LLM模型名称 | `gpt-3.5-turbo` |
| `FLASK_ENV` | ❌ | Flask环境 | `development` |
| `HF_HUB_OFFLINE` | ❌ | 离线模式 | `1` |

### 知识库配置 (backend/knowledge_base.py)

```python
LocalKnowledgeBase(
    db_path="./knowledge_db",      # 数据库路径
    chunk_size=1000,               # 分块大小
    chunk_overlap=200,             # 分块重叠
    openai_api_key=os.getenv(...)  # API密钥
)
```

### 搜索参数

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `top_k` | 3 | 返回的文档数 |
| `relevance_threshold` | 0.3 | 相似度阈值（0-1） |
| `use_reranking` | True | 是否使用重排序 |

---

## 🔧 开发指南

### 项目结构

```
local-knowledge-base/
├── backend/
│   ├── app.py                      # Flask 应用主文件
│   ├── knowledge_base.py           # 知识库核心逻辑
│   ├── embeddings.py               # 嵌入模型抽象
│   ├── llm_client.py               # LLM 客户端
│   ├── requirements.txt            # Python 依赖
│   ├── knowledge_db/
│   │   ├── faiss_index/           # FAISS 向量索引
│   │   ├── metadata.json          # 文件元数据
│   │   └── documents/             # 文档备份
│   └── __pycache__/
│
├── frontend/
│   ├── index.html                  # 主页面
│   ├── css/style.css              # 样式表
│   └── js/
│       ├── app.js                 # 应用逻辑
│       ├── api.js                 # API 客户端
│       └── ui.js                  # UI 交互
│
├── models_cache/                   # 模型缓存（自动生成）
│   └── models--cross-encoder-.../
│
├── test/                          # 测试文件
│   ├── testScript/
│   └── testDoc/
│
├── .github/
│   └── copilot-instructions.md   # AI 代码助手指南
│
├── .env                           # 环境变量配置
├── .gitignore
└── README.md
```

### 修改知识库逻辑

**主要文件**: `backend/knowledge_base.py`

关键方法：
- `search(question, top_k, use_reranking)` - 搜索逻辑
- `add_documents(file_paths)` - 添加文档
- `add_documents_from_upload(files)` - 从上传添加

### 添加新API端点

**示例**: 在 `backend/app.py` 中添加新端点

```python
@app.route('/api/custom', methods=['POST'])
def custom_endpoint():
    try:
        data = request.get_json()
        result = kb.custom_method(data['param'])
        return jsonify({'result': result}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500
```

### 修改前端UI

**主要文件**: `frontend/js/app.js` 和 `frontend/js/ui.js`

- `app.js` - 处理API调用和模式切换
- `ui.js` - DOM 操作和事件绑定
- `index.html` - HTML 结构和样式

### 测试

```bash
# 运行测试脚本
python test/testScript/run_rag_tests.py

# 手动测试 API
curl -X POST http://localhost:5000/api/health

curl -X POST http://localhost:5000/api/kb/search \
  -H "Content-Type: application/json" \
  -d '{"query":"向量数据库","top_k":3}'
```

---

## 🐛 常见问题

### Q1: 启动时提示 "OPENAI_API_KEY 未设置"

**解决方案**:
```bash
# 检查 .env 文件
cat .env

# 或者直接设置环境变量
export OPENAI_API_KEY="sk-your-key-here"
python backend/app.py
```

### Q2: 前端无法连接后端

**解决方案**:
1. 确保后端运行在 `http://localhost:5000`
2. 检查 CORS 配置 (backend/app.py:36-44)
3. 浏览器控制台查看详细错误信息
4. 尝试 `curl http://localhost:5000/api/health`

### Q3: 搜索速度慢

**原因和优化**:
- **首次搜索**: 模型需要下载和加载（5-30秒）→ 第二次搜索会快很多
- **关闭重排序**: 设置 `use_reranking=False` 加快速度
- **减少 top_k**: 从 5 改为 3 减少计算量

### Q4: 上传大文件失败

**解决方案**:
1. 检查文件格式（仅支持 PDF、MD、TXT）
2. 增加 Flask 请求超时时间
3. 分割大文件后重新上传
4. 查看后端日志找出具体错误

### Q5: 向量库占用空间过大

**解决方案**:
```bash
# 删除所有向量索引，重新建立
rm -rf knowledge_db/faiss_index/
# 删除模型缓存（重新下载）
rm -rf models_cache/
```

### Q6: 如何使用国内 API 代理？

在 `.env` 中配置：
```bash
OPENAI_API_KEY=sk-your-key-here
OPENAI_BASE_URL=https://api.gpt-4o.cn/v1  # 示例：ChatGPT API China
```

---

## 📊 性能指标

| 操作 | 时间 | 说明 |
|------|------|------|
| 首次搜索 | 5-30s | 包括模型下载和加载 |
| 后续搜索 | 0.5-2s | FAISS搜索 + CrossEncoder重排 |
| 上传PDF(10页) | 2-5s | 包括向量化 |
| 流式回复 | 实时 | 首token ~1s，后续 ~50-100ms/token |
| 向量库大小 | ~1MB/100docs | 取决于文档长度 |

---

## 🔐 隐私和安全

- ✅ 所有数据存储在本地（`knowledge_db/`）
- ✅ 向量索引（FAISS）未上传至云端
- ✅ 模型缓存在本地（`models_cache/`）
- ⚠️ OpenAI API 调用涉及网络请求（需要API密钥）
- ⚠️ 建议在自己的服务器上部署，避免在不安全的网络使用

---

## 🚀 生产部署

### Docker 部署

```dockerfile
# Dockerfile
FROM python:3.10-slim

WORKDIR /app
COPY . .
RUN pip install -r backend/requirements.txt

ENV OPENAI_API_KEY=""
ENV FLASK_ENV="production"

CMD ["python", "backend/app.py"]
```

```bash
docker build -t knowledge-base .
docker run -p 5000:5000 \
  -e OPENAI_API_KEY="sk-..." \
  -v $(pwd)/knowledge_db:/app/knowledge_db \
  knowledge-base
```

### Gunicorn 部署

```bash
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:5000 backend.app:app
```

---

## 📈 未来计划

- [ ] 支持联网搜索功能
- [ ] 多轮对话记忆
- [ ] Agent 自主分析
- [ ] 用户管理和权限控制
- [ ] 知识图谱展示
- [ ] 批量文档上传优化
- [ ] 更多LLM模型支持

---

## 📄 许可证

MIT License - 详见 [LICENSE](LICENSE) 文件

---

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

```bash
# 开发流程
1. Fork 项目
2. 创建特性分支 (git checkout -b feature/amazing-feature)
3. 提交更改 (git commit -m 'Add amazing feature')
4. 推送分支 (git push origin feature/amazing-feature)
5. 开启 Pull Request
```

---

## 📞 联系和支持

- 📧 Email: lholecn@gmail.com
- 🐛 Bug Report: [GitHub Issues](https://github.com/lholecn-bit/local-knowledge-base/issues)
- 💬 讨论: [GitHub Discussions](https://github.com/lholecn-bit/local-knowledge-base/discussions)

---

## 致谢

感谢以下开源项目的支持：

- [LangChain](https://github.com/langchain-ai/langchain) - 向量数据库和文档处理
- [FAISS](https://github.com/facebookresearch/faiss) - 向量搜索
- [sentence-transformers](https://github.com/UKPLab/sentence-transformers) - 重排序模型
- [Flask](https://github.com/pallets/flask) - Web 框架
- [marked.js](https://github.com/markedjs/marked) - Markdown 渲染

---

<div align="center">

**⭐ 如果这个项目有帮助，请给个 Star！**

Made with ❤️ by Local Knowledge Base Community

</div>
