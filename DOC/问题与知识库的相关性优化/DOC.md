# 1. 要解决什么问题

**问题**：RAG 系统相关性判断困难，硬阈值难以调参

## 1.1 问题诊断

你的项目当前面临的核心问题：

```
硬阈值问题（当前方案）
    ↓
0.2 太宽松？还是 0.3 太严格？
    ↓
需要频繁调参和测试
    ↓
调参之间没有理论依据（全靠试）
    ↓
不同查询类型可能需要不同阈值
    ↓
永远无法找到"完美"的阈值
```

## **1.2 根本原因**：

试图用单一数字（0.2/0.3/0.4）来解决复杂的语义相似度判断问题。

# 2. 解决方案：Re-Ranking

### 2.1 核心思想

不依赖单一阈值，而是用一个**专业的 AI 模型**来评估文档相关性。

```
┌──────────────────────────────────────┐
│ 用户问题：Python 导入错误如何解决？   │
└──────────────────────────────────────┘
             ↓
┌──────────────────────────────────────┐
│ 步骤 1：向量快速检索                  │
│ • 返回相似度最高的 9 个候选           │
│ • 速度快（~10ms）                    │
│ • 可能包含噪声                       │
└──────────────────────────────────────┘
             ↓
    [文档 1] [文档 2] [文档 3]
    [文档 4] [文档 5] [文档 6]
    [文档 7] [文档 8] [文档 9]
             ↓
┌──────────────────────────────────────┐
│ 步骤 2：Re-Ranking（重排序）         │
│ • 用 CrossEncoder 模型重新评分       │
│ • 理解上下文（不只看表面相似度）     │
│ • 消除噪声，找到真正相关的文档       │
└──────────────────────────────────────┘
             ↓
    [文档 1] [文档 4] [文档 7]
    (0.95)  (0.88)  (0.72)
             ↓
┌──────────────────────────────────────┐
│ 步骤 3：返回最相关的 3 个              │
│ • 无需硬阈值！                       │
│ • 自动选择最好的 3 个                │
│ • 效果显著提升                       │
└──────────────────────────────────────┘
```

---

## 2.2 为什么 Re-Ranking 效果更好

### 问题 1：表面相似度不等于真实相关性

**例子**：

```
问题：Python 如何导入模块？

向量相似度分析：
┌─────────────────────────────────┐
│ 文档 A："Python 导入 numpy"      │
│ 相似度：0.95 ← 最高分             │
│ 实际相关性：⭐⭐⭐⭐⭐ 非常相关    │
└─────────────────────────────────┘

┌─────────────────────────────────┐
│ 文档 B："JavaScript import 语法"  │
│ 相似度：0.78 ← 次高分            │
│ 实际相关性：❌ 完全无关（噪声）   │
│ 原因：关键词相似，但语言不同      │
└─────────────────────────────────┘

┌─────────────────────────────────┐
│ 文档 C："Python 包管理最佳实践"    │
│ 相似度：0.62 ← 较低分             │
│ 实际相关性：⭐⭐⭐⭐ 非常有用      │
│ 原因：语义相关，但表述不同        │
└─────────────────────────────────┘

❌ 硬阈值 0.7：选 A, B → 包含噪声！
✅ Re-Ranking：选 A, C → 完美！
```

## 2.3 具体操作步骤

### 第 1 步：安装依赖（5 分钟）

```bash
pip install sentence-transformers
```

这会自动下载 CrossEncoder 模型（~200MB）。

### 第 2 步：修改代码（2 小时）

#### 文件 1：`backend/knowledge_base.py`

在 `search()` 方法中添加 Re-Ranking 支持：

```python
# 在导入部分添加
from sentence_transformers import CrossEncoder

# 在初始化时加载重排序器
def __init__(self, ...):
    # ... 现有代码
    self.reranker = CrossEncoder('cross-encoder/ms-marco-MiniLM-L-6-v2')

# 修改 search 方法
def search(self, query: str, top_k: int = 3) -> Dict:
    if not self.vector_store:
        return {'question': query, 'results': [], 'has_results': False}
  
    # 步骤 1：向量检索（宽松）
    candidates = self.vector_store.similarity_search_with_score(query, k=top_k*3)
  
    # 步骤 2：重排序（精确）
    docs = [doc for doc, _ in candidates]
    scores = self.reranker.predict([
        (query, doc.page_content) for doc in docs
    ])
  
    candidates = sorted(
        zip(docs, scores),
        key=lambda x: x[1],
        reverse=True
    )
  
    # 步骤 3：格式化结果（无需阈值！）
    results = []
    for doc, score in candidates[:top_k]:
        results.append({
            'content': doc.page_content,
            'source': doc.metadata.get('source', 'Unknown'),
            'score': float(score),
        })
  
    return {
        'question': query,
        'results': results,
        'has_results': len(results) > 0
    }
```

#### 文件 2：`backend/app.py`

移除硬阈值逻辑（约第 195-210 行）：

```python
# ❌ 删除这段代码
if mode == 'kb':
    relevance_threshold = 0.2
elif mode == 'llm':
    relevance_threshold = 0.4
else:
    relevance_threshold = 0.3

search_results = kb.search(question, top_k, relevance_threshold=relevance_threshold)

# ✅ 替换为
search_results = kb.search(question, top_k)  # 简单！
```

### 第 3 步：测试验证（1 小时）

创建测试脚本 `test_reranking.py`：

```python
from backend.knowledge_base import LocalKnowledgeBase

kb = LocalKnowledgeBase()

# 测试 3 个查询
queries = [
    "Python 导入错误",
    "如何安装依赖",
    "Git 提交",
]

for query in queries:
    results = kb.search(query, top_k=3)
    print(f"\n查询：{query}")
    for r in results['results']:
        print(f"  - {r['source']} (分数: {r['score']:.3f})")
```

### 第 4 步：部署（0.5 小时）

```bash
# 确保后端能启动
python backend/app.py

# 在前端测试几个查询
# 观察是否效果更好
```

# **3. 预期收益**：

相关性精度 +30-50%，调参工作量 -100%

# 4. 下一步的优化方向：

### 优化 1：动态模型选择

如果查询结果少，用更精准的模型：

```python
def search(self, query, top_k):
    candidates = vector_search(...)
  
    if len(candidates) < 5:
        model = 'BAAI/bge-reranker-large'  # 精准但慢
    else:
        model = 'cross-encoder/ms-marco-MiniLM-L-6-v2'  # 快速
```

### 优化 2：LLM 二次确认

对低置信度的结果用 LLM 再检查：

```python
def search(self, query, top_k):
    results = rerank_search(...)
  
    # 对分数 < 0.7 的结果用 LLM 确认
    for result in results:
        if result['score'] < 0.7:
            if llm_judge(query, result['content']):
                keep(result)
```

### 优化 3：结果缓存

缓存常见查询的重排序结果：

```python
self.cache = {}

def search(self, query, top_k):
    if query in self.cache:
        return self.cache[query]
  
    results = expensive_rerank(query, top_k)
    self.cache[query] = results
    return results
```

# 5. 其他方案及原理：

## LLM-Judge

详情请见*RAG_QUICK_COMPARISON.md*与*RAG_THRESHOLD_SOLUTIONS.md*

## Hybrid

详情请见*RAG_QUICK_COMPARISON.md*与*RAG_THRESHOLD_SOLUTIONS.md*

## 6. 问题

1. sentence-transformers中为什么包含了crossEncoder？
