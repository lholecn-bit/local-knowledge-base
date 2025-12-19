# AI编程助手工作指南 - 本地知识库系统

## 架构概览

**本地知识库系统** 是一个 RAG（检索增强生成）应用，结合了向量搜索、文档重排序和LLM集成。

### 核心组件

| 组件 | 功能 | 关键文件 |
|------|------|--------|
| **后端(Flask)** | 知识库操作的REST API服务器 | `backend/app.py`、`backend/knowledge_base.py` |
| **向量数据库(FAISS)** | 存储文档嵌入用于语义搜索 | `knowledge_db/faiss_index/`，使用LangChain的FAISS包装器 |
| **嵌入模型** | 通过OpenAI API将文档和查询转换为向量 | `backend/embeddings.py`，模型：`text-embedding-3-small` |
| **重排序器** | 使用`sentence-transformers` CrossEncoder重排搜索结果 | `backend/knowledge_base.py`（延迟加载） |
| **LLM客户端** | 调用OpenAI API进行聊天和生成，支持流式输出 | `backend/llm_client.py` |
| **前端** | 原生JS + HTML/CSS UI，支持3种查询模式 | `frontend/`（index.html、js/app.js、js/api.js） |

### 查询流程（流式查询模式）
```
用户问题
  → KB.search(question, top_k=3)
  → FAISS相似度搜索 → 相关性阈值过滤(0.3)
  → CrossEncoder重排序（可选，"light"模型）
  → 构建RAG提示词
  → LLMClient.chat() → 流式响应到前端
  → 去重显示相关文档
```

## 关键配置和模式

### 环境设置（`backend/app.py`、`backend/knowledge_base.py`）
- **OPENAI_API_KEY**: 必需；如果未传递给构造函数，则回退到环境变量
- **OPENAI_BASE_URL**: 可选自定义API端点（`knowledge_base.py`第121行）
- **离线模式**: `HF_HOME`和`HF_HUB_OFFLINE=1`强制使用本地模型缓存存在`models_cache/`目录（第19-23行）
- **CORS配置**: 详见第36-44行；`/api/*`路由允许来自`http://localhost:3000`的跨域请求
- **代理处理**: `knowledge_base.py`（第123-129行）和`llm_client.py`（第48-54行）都显式清除代理环境变量，防止OpenAI/HuggingFace故障

### 延迟模型加载（启动时的关键）
- 嵌入模型和重排序器在`search()`方法中**延迟加载**，不在`__init__`中加载（第100行，knowledge_base.py）
- 原因：确保在导入模型之前环境变量（`HF_HOME`、离线模式）已设置
- 模式：检查`if self.embeddings is None`，然后初始化（见`search()`方法，第280行+）

### 重排序模式（`knowledge_base.py:350-395`）
- 重排序器在**首次搜索时加载**（延迟）：`sentence-transformers` CrossEncoder模型`ms-marco-MiniLM-L-6-v2`
- 由`search()`中的`use_reranking=True`参数和`/api/stream-query`控制（app.py第129行）
- 返回元组：`(search_results, reranked_results)` - 前端显示重排序结果，但包含原始来源

### 元数据和文档跟踪
- `knowledge_db/metadata.json`：存储文件哈希(MD5)和上传时间戳，防止重复
- 添加文档时：检查`_should_skip_file()`（第204-217行）后再处理
- 文件删除时：同时更新元数据和向量存储

## API端点和请求模式

### 主要端点

| 端点 | 方法 | 功能 | 响应 |
|------|------|------|------|
| `/api/stream-query` | POST | **主查询**：带流式响应的RAG | `type: 'start' \| 'chunk' \| 'end'`，JSON行格式 |
| `/api/kb/search` | POST | 仅向量搜索（不调用LLM） | `{'results': [...], 'query': '...'}` |
| `/api/documents/upload` | POST | 上传PDF/MD/TXT文件 | `{'added_chunks': int, 'files': [], 'errors': []}` |
| `/api/documents/list` | GET | 列出知识库中的所有文档 | `{'documents': [{'filename': str, ...}]}` |
| `/api/documents/<filename>` | DELETE | 删除文档 | `{'message': 'deleted', ...}` |
| `/api/health` | GET | 系统状态 | `{'status': 'ok', 'kb_ready': bool, ...}` |

### 流式查询模式参数（`app.py:196-210`）
- **mode**: `'auto'`（先搜索后调用LLM）、`'kb'`（总是搜索）、`'llm'`（跳过KB）→ 影响结果评分
- **top_k**: 要检索的向量数（默认3）- 控制深度vs速度的权衡

## 前端架构

### API包装模式（`js/api.js`）
- `API`类提供方法：`search()`、`query()`、`streamQuery()`、`upload()`、`deleteDoc()`
- 所有方法使用集中的`request()`方法 → 标准化的错误处理
- `streamQuery()`将响应作为**文本流**读取（第~100行），逐行解析JSON

### 流式响应处理（`js/app.js`）
- 前端逐行读取流式响应，解析JSON块
- 类型：`'start'`（元数据）、`'chunk'`（LLM令牌）、`'end'`（来源数组）
- **去重逻辑**：移除来源中重复的文档（见`js/ui.js`中的`deduplicateSources()`）

### Markdown渲染
- 使用`marked.js`库（index.html第8行）
- 代码高亮通过`highlight.js`（第7行）
- 模式：`marked.parse(markdown)` → 添加到DOM并进行适当转义

## 重要约定和陷阱

### 1. **Python模块既是脚本又是模块**
- `app.py`使用模式：`if __name__ == '__main__':`（第463行+）
- 全局初始化（`load_dotenv()`、`kb = LocalKnowledgeBase()`）发生在检查**之前**
- 这允许导入`app`模块而不自动启动Flask服务器

### 2. **错误处理策略**
- 后端返回带描述性消息的JSON错误：`{'error': 'specific reason'}`
- 前端将API调用包装在`try-catch`中，向用户显示错误
- **控制台日志**：`app.py`和`knowledge_base.py`中有大量调试日志（带emoji标记的print语句）用于故障排除

### 3. **知识库初始化**
- `kb = LocalKnowledgeBase()`在app.py第59行，需要在`.env`中设置OPENAI_API_KEY
- 如果初始化失败：`/api/health`返回`kb_ready: false`，端点返回500
- 测试命令：`curl http://localhost:5000/api/health`

### 4. **文档处理**
- 支持：`.pdf`、`.md`、`.txt`文件
- 使用`langchain_community`加载器（`PDFPlumberLoader`、`TextLoader`）
- 通过`RecursiveCharacterTextSplitter`分块（chunk_size=1000，overlap=200）
- 文件上传返回`added_chunks`计数和`errors`数组用于处理部分失败

### 5. **相关性阈值**
- 设置在`self.relevance_threshold = 0.3`（knowledge_base.py第80行）
- 过滤基于嵌入的搜索结果低于此分数
- 如果搜索返回0个结果（过滤后），模式之间的处理不同：
  - `auto`/`kb`：返回"未找到相关文档"
  - `llm`：完全跳过KB，仅使用纯LLM

## 开发工作流

### 本地运行
```bash
# 后端(Flask)
cd backend
pip install -r requirements.txt
export OPENAI_API_KEY="sk-..."
python app.py  # 运行在 http://localhost:5000

# 前端（需要后端运行）
# 在浏览器中打开 frontend/index.html（或使用Python的 `python -m http.server 3000`）
```

### 测试
- 测试脚本模板：`test/testScript/run_rag_tests.py`
- 文档测试用例：`test/testDoc/TEST_QUESTIONS.md`

### 模型缓存
- 首次`search()`或`add_documents()`下载嵌入和重排序模型 → 存储在`models_cache/`
- 后续运行使用缓存版本（检查`HF_HOME`环境变量）
- 重置：删除`models_cache/`目录

## 按目的划分的关键文件

| 目标 | 主要文件 | 辅助文件 |
|------|--------|--------|
| 为KB操作添加功能 | `backend/knowledge_base.py` | `backend/app.py`（路由） |
| 添加REST API端点 | `backend/app.py` | `frontend/js/api.js`（客户端） |
| 改进搜索质量 | `backend/knowledge_base.py:search()`，重排序逻辑 | `backend/llm_client.py`（提示词） |
| 修复流式响应 | `backend/app.py:stream_query()`生成器，`frontend/js/app.js` | `frontend/index.html`（UI） |
| 文档管理 | `backend/knowledge_base.py:add_documents()`，元数据处理 | 向量存储持久化 |

## 待解决的设计问题（来自TODOLIST.txt）
- **问题#16**：KB模式和自动模式对用户看起来相同 → 未来可能需要模式差异化
- **问题#14**：即使LLM说未使用，仍显示无关文档 → 来源选择逻辑需要审查
- **重排序效果** (#11)：CrossEncoder改进排名但收益递减
- **去重处理**：前端去重相关文档，但后端可能需更早优化

---

*最后更新：2025-12-19 | 带有LangChain + FAISS + 流式LLM的RAG系统*
