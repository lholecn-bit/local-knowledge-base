# 使用 Re-Ranking 改进 RAG 检索

这个文件展示如何集成 Re-Ranking 模型来改进相关性判断，避免硬阈值问题。

## 安装依赖

```bash
pip install sentence-transformers
```

## 核心实现

```python
from sentence_transformers import CrossEncoder

class RankingSearch:
    def __init__(self, use_reranker=True):
        """
        初始化搜索引擎
        
        Args:
            use_reranker: 是否使用重排序器
        """
        self.use_reranker = use_reranker
        
        if use_reranker:
            # 轻量级重排序模型（推荐）
            self.reranker = CrossEncoder(
                'cross-encoder/ms-marco-MiniLM-L-6-v2'
            )
            # 如果追求更高精度，可用：
            # self.reranker = CrossEncoder('BAAI/bge-reranker-base')
    
    def search(self, vector_store, query, top_k=3):
        """
        混合搜索：先向量检索 + 后重排序
        
        Args:
            vector_store: FAISS 向量库
            query: 查询文本
            top_k: 最终返回的结果数
        
        Returns:
            重排序后的前 top_k 个结果
        """
        
        # 第一步：向量检索（宽松阈值，召回更多候选）
        candidates = vector_store.similarity_search_with_score(query, k=top_k * 3)
        
        if not candidates:
            return []
        
        # 第二步：重排序
        if self.use_reranker:
            docs = [doc for doc, _ in candidates]
            
            # 用重排序器重新评分
            scores = self.reranker.predict([
                (query, doc.page_content) 
                for doc in docs
            ])
            
            # 按重排序分数排序
            ranked = sorted(
                zip(docs, scores),
                key=lambda x: x[1],
                reverse=True
            )
            
            return [doc for doc, _ in ranked[:top_k]]
        
        else:
            # 不用重排序，直接返回向量检索结果
            return [doc for doc, _ in candidates[:top_k]]
```

## 优势对比

### 之前（纯向量相似度 + 硬阈值）
```
Query: "如何修复 Python 导入错误？"

向量搜索结果：
1. "Python import error solutions" (0.85)  ← 显然相关
2. "JavaScript require vs import" (0.78)   ← 虽然高分但无关
3. "Python async/await guide" (0.72)       ← 低分但可能有用
4. "How to install packages" (0.68)        ← 低分，不相关

阈值 0.7 时：1, 2 被选中 ← ❌ 第 2 个是噪声！
阈值 0.8 时：只有 1 被选中   ← ❌ 遗漏了第 4 个可能有用的信息
```

### 之后（向量 + Re-Ranking）
```
同样的查询和向量搜索结果：

重排序器评分（0-1）：
1. "Python import error solutions" (0.92)  ← 保持第 1
2. "JavaScript require vs import" (0.15)   ← 降低到接近 0（识别出无关）
3. "How to install packages" (0.85)        ← 升高（识别出有用）
4. "Python async/await guide" (0.42)       ← 适中评分

最终排序：1 → 3 → 4（移除了 2）
结果：[1, 3]  ← ✅ 精准相关！
```

## 集成到你的 knowledge_base.py

在 `search` 方法中添加重排序：

```python
def search(self, query: str, top_k: int = 3, use_reranking: bool = True) -> Dict:
    """
    搜索知识库（支持重排序）
    
    Args:
        query: 查询文本
        top_k: 返回的结果数
        use_reranking: 是否使用重排序器
    """
    if not self.vector_store:
        return {'question': query, 'results': [], 'has_results': False}
    
    try:
        # 第一步：向量检索（召回更多候选）
        candidates = self.vector_store.similarity_search_with_score(
            query, 
            k=top_k * 3  # 召回 3 倍的候选
        )
        
        # 第二步：重排序
        if use_reranking:
            from sentence_transformers import CrossEncoder
            
            if not hasattr(self, 'reranker'):
                self.reranker = CrossEncoder(
                    'cross-encoder/ms-marco-MiniLM-L-6-v2'
                )
            
            docs = [doc for doc, _ in candidates]
            
            # 重排序
            scores = self.reranker.predict([
                (query, doc.page_content)
                for doc in docs
            ])
            
            # 按分数重新排序
            candidates = sorted(
                zip(docs, scores),
                key=lambda x: x[1],
                reverse=True
            )
            # 转换格式
            candidates = [(doc, score) for doc, score in candidates]
        
        # 第三步：格式化结果（不再需要硬阈值！）
        results = []
        for doc, score in candidates[:top_k]:
            results.append({
                'content': doc.page_content,
                'source': doc.metadata.get('source', 'Unknown'),
                'score': float(score),  # 现在是重排序分数而不是向量距离
            })
        
        has_results = len(results) > 0
        
        print(f"✅ 重排序完成: {len(results)} 个结果")
        for i, result in enumerate(results, 1):
            print(f"   {i}. {result['source']} (分数: {result['score']:.3f})")
        
        return {
            'question': query,
            'results': results,
            'has_results': has_results
        }
    
    except Exception as e:
        print(f"❌ 搜索错误: {e}")
        return {
            'question': query,
            'results': [],
            'has_results': False
        }
```

## 后续优化方向

### 选项 1：动态权重
```python
# 组合向量分数和重排序分数
final_score = 0.3 * vector_score + 0.7 * rerank_score
```

### 选项 2：LLM 二次确认（高成本但最准）
```python
if rerank_score < 0.5:
    # 用 LLM 再次确认
    if llm_judge(query, document):
        include_document()
```

### 选项 3：多模型投票
```python
# 用多个重排序模型投票
scores = [
    bge_reranker.predict(...),
    cohere_rerank.predict(...),
    custom_reranker.predict(...)
]
final_score = mean(scores)
```

## 性能注意事项

- **首次运行**：重排序模型会自动下载 (~200MB)
- **速度**：相比纯向量搜索，增加 50-200ms（可接受）
- **显存**：增加 ~300MB（可选 GPU 加速）
- **成本**：完全开源，无 API 调用费用

## 何时使用

| 场景 | 建议 |
|------|------|
| 快速原型 | 🔴 不用重排序 |
| 小规模知识库 | 🟡 开启重排序 |
| 生产环境 | 🟢 必须用重排序 |
| 追求最高精度 | 🟢 + LLM 二次确认 |
