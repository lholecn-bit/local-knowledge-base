# RAG 系统相关性阈值问题 - 行业解决方案

## 问题背景

向量相似度阈值（Relevance Threshold）很难调整的原因：
1. **向量空间非线性** - 相似度分数与实际相关性的映射关系不是线性的
2. **域差异** - 不同领域的内容相似度分布完全不同
3. **向量模型限制** - text-embedding-3-small 对某些细微差异反应不敏感
4. **动态性** - 知识库更新后阈值效果会变化

---

## 行业主流解决方案

### 🏆 方案1：多层次混合检索（Hybrid Retrieval）- ⭐ 推荐

**核心思想**：不依赖单一的相似度分数，而是结合多个信号。

```python
# 伪代码
results = []

# 第一层：向量相似度检索
vector_results = vector_search(query, top_k=10)

# 第二层：BM25 关键词检索（稀疏）
keyword_results = bm25_search(query, top_k=10)

# 第三层：融合排序（RRF - Reciprocal Rank Fusion）
fused_results = rrf_fusion(vector_results, keyword_results)

# 只取融合后的 top_k
return fused_results[:top_k]
```

**优点**：
- ✅ 避免单一阈值问题
- ✅ 关键词匹配补充语义理解的不足
- ✅ 鲁棒性强

**缺点**：
- ❌ 实现复杂度高
- ❌ 需要额外的搜索引擎（如 Elasticsearch）

---

### 📊 方案2：Re-Ranking（重排序） - ⭐⭐ 推荐

**核心思想**：先用向量检索快速召回大量候选，再用专门的重排序模型精细化排序。

```python
# 伪代码
# 第一步：向量检索（宽松阈值，召回多个结果）
candidates = vector_search(query, top_k=50, threshold=0.2)

# 第二步：用重排序模型重新评分
reranked = rerank_model.rank(query, candidates)

# 第三步：取前 top_k
return reranked[:top_k]
```

**使用的重排序模型**：
- **Cohere Rerank** - 商用（效果最好）
- **jina-reranker** - 开源（3B 参数，效果次好）
- **bge-reranker** - 开源（轻量级）
- **LLM-based Ranking** - 用 LLM 重新评估（慢但准）

**推荐用法**：
```python
from sentence_transformers import CrossEncoder

reranker = CrossEncoder('cross-encoder/ms-marco-MiniLM-L-6-v2')

# 快速召回
candidates = vector_store.similarity_search(query, k=50)

# 重排序
scores = reranker.predict([
    (query, doc.page_content) for doc in candidates
])

# 按分数排序
ranked_docs = sorted(
    zip(candidates, scores),
    key=lambda x: x[1],
    reverse=True
)[:top_k]
```

**优点**：
- ✅ 精准度高
- ✅ 可以用开源模型
- ✅ 相对易实现

**缺点**：
- ❌ 多一层推理，延迟增加
- ❌ 需要额外计算资源

---

### 🤖 方案3：LLM 审查（LLM-as-Judge） - ⭐⭐⭐ 最可靠

**核心思想**：让 LLM 自己判断检索结果是否足够相关，而不是依赖硬阈值。

```python
# 伪代码
# 第一步：宽松检索
candidates = vector_search(query, top_k=10, threshold=0.1)

# 第二步：LLM 评估相关性
relevant_docs = []
for doc in candidates:
    prompt = f"""
    问题：{query}
    文档内容：{doc.content}
    
    请判断这个文档是否能帮助回答问题。
    回答：是/否
    """
    decision = llm(prompt)
    if "是" in decision:
        relevant_docs.append(doc)

# 第三步：用最相关的文档回答
return relevant_docs
```

**优点**：
- ✅ 最符合人类判断
- ✅ 完全避免阈值问题
- ✅ 效果最好

**缺点**：
- ❌ 额外的 LLM 调用，成本高
- ❌ 延迟最高

**改进版本**（成本优化）：
```python
# 只用 LLM 审查前 3 个候选
candidates = vector_search(query, top_k=3)
for doc in candidates:
    if llm_judge(query, doc) == "相关":
        return doc
# 如果都不相关，用向量结果的第一个
return candidates[0]
```

---

### 📈 方案4：学习式阈值（Learning-based）

**核心思想**：根据历史数据自动学习最优阈值。

```python
# 伪代码
# 收集用户反馈数据
training_data = [
    (query, doc, user_relevance_rating),  # 1-5 分
    ...
]

# 训练模型找到最优的得分 → 相关性映射
optimal_threshold = learn_optimal_threshold(training_data)
```

**优点**：
- ✅ 自适应
- ✅ 精准度高

**缺点**：
- ❌ 需要大量标注数据
- ❌ 实现复杂

---

## 🎯 针对你的场景推荐

根据你的项目特点（本地知识库 RAG），我建议的分阶段方案：

### **第一阶段（现在）** ✅
```
使用：Re-Ranking 方案
理由：
- 开源模型 bge-reranker 轻量级，延迟低
- 效果显著提升
- 实现相对简单
```

### **第二阶段（如果效果不理想）**
```
使用：LLM-as-Judge 的成本优化版本
理由：
- 充分利用已有的 LLM
- 成本较低（只审查前 3 个候选）
- 效果最佳
```

### **第三阶段（规模化）**
```
使用：Hybrid Retrieval
理由：
- 生产级系统的标准做法
- 需要集成 Elasticsearch
- 最可靠
```

---

## 快速对比表

| 方案 | 效果 | 复杂度 | 成本 | 推荐指数 |
|------|------|--------|------|---------|
| **多阈值调整** | ⭐ | ⭐ | ⭐ | ❌ |
| **Re-Ranking** | ⭐⭐⭐⭐ | ⭐⭐ | ⭐⭐ | ✅✅ |
| **LLM-as-Judge** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐ | ✅✅✅ |
| **Hybrid Retrieval** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⚠️ 复杂 |
| **学习式阈值** | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⚠️ 需数据 |

---

## 开源工具推荐

### Re-Ranking 库
```bash
pip install sentence-transformers
# 模型选择：
# - cross-encoder/ms-marco-MiniLM-L-6-v2（小，快）
# - BAAI/bge-reranker-large（大，精准）
```

### Hybrid Retrieval
```bash
pip install elasticsearch langchain-elasticsearch
```

### LLM Ranking
```bash
# 直接用现有的 OpenAI API
# 无需额外安装
```

---

## 参考资源

- [Langchain Re-ranking](https://python.langchain.com/docs/modules/data_connection/retrievers/long_context_reorder)
- [BGE Reranker GitHub](https://github.com/FlagOpen/FlagEmbedding)
- [Hybrid Search Best Practices](https://docs.pinecone.io/guides/hybrid-search)
- [RAG Evaluation Framework](https://github.com/langchain-ai/langsmith-cookbook)
