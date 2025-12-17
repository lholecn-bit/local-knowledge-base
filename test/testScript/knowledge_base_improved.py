# 改进版本：支持 Re-Ranking 的 LocalKnowledgeBase

"""
这个文件展示如何改进 knowledge_base.py，集成 Re-Ranking 功能。
直接替换原来的 search 方法即可。
"""

from typing import Dict, Optional, List
from sentence_transformers import CrossEncoder

class LocalKnowledgeBaseImproved:
    """带 Re-Ranking 支持的改进版知识库"""
    
    def __init__(self, use_reranking: bool = True, reranker_model: str = None):
        """
        初始化
        
        Args:
            use_reranking: 是否使用重排序（默认启用）
            reranker_model: 重排序模型名称
                - None: 使用默认轻量级模型
                - 'light': cross-encoder/ms-marco-MiniLM-L-6-v2 (小，快)
                - 'medium': BAAI/bge-reranker-base (中等)
                - 'large': BAAI/bge-reranker-large (大，精准但慢)
        """
        self.use_reranking = use_reranking
        self.reranker = None
        self.reranker_model = reranker_model or 'light'
        
        if use_reranking:
            self._init_reranker()
    
    def _init_reranker(self):
        """初始化重排序器"""
        model_map = {
            'light': 'cross-encoder/ms-marco-MiniLM-L-6-v2',
            'medium': 'BAAI/bge-reranker-base',
            'large': 'BAAI/bge-reranker-large'
        }
        
        model_name = model_map.get(self.reranker_model, model_map['light'])
        
        try:
            print(f"📦 加载重排序模型: {model_name}...")
            self.reranker = CrossEncoder(model_name)
            print(f"✅ 重排序器已加载")
        except Exception as e:
            print(f"⚠️ 重排序器加载失败: {e}")
            print(f"   使用原始向量搜索")
            self.reranker = None
    
    def search(self, query: str, top_k: int = 3) -> Dict:
        """
        改进的搜索方法（无需硬阈值）
        
        Args:
            query: 查询文本
            top_k: 返回的结果数
        
        Returns:
            包含搜索结果的字典
        """
        if not self.vector_store:
            return {
                'question': query,
                'results': [],
                'has_results': False,
                'method': 'none'  # 新增：记录使用的检索方法
            }
        
        try:
            # ✅ 关键改动：向量检索时召回更多候选（供重排序使用）
            recall_k = top_k * 3 if self.reranker else top_k
            candidates = self.vector_store.similarity_search_with_score(
                query, 
                k=recall_k
            )
            
            # ✅ 重排序阶段
            if self.reranker and candidates:
                docs = [doc for doc, _ in candidates]
                
                # 用重排序器评分
                print(f"🔄 用重排序器重新评估 {len(docs)} 个候选...")
                rerank_scores = self.reranker.predict([
                    (query, doc.page_content)
                    for doc in docs
                ])
                
                # 按重排序分数排序
                candidates = sorted(
                    zip(docs, rerank_scores),
                    key=lambda x: x[1],
                    reverse=True
                )
                
                method = 'rerank'  # 使用了重排序
            else:
                # 降级到纯向量搜索
                method = 'vector'  # 使用向量搜索
            
            # ✅ 格式化结果
            results = []
            for i, (doc, score) in enumerate(candidates[:top_k]):
                result = {
                    'content': doc.page_content,
                    'source': doc.metadata.get('source', 'Unknown'),
                    'score': float(score),
                    'rank': i + 1
                }
                results.append(result)
            
            has_results = len(results) > 0
            
            # ✅ 改进的日志输出
            print(f"\n{'='*60}")
            print(f"🔍 搜索完成 (方法: {method.upper()})")
            print(f"   查询: {query}")
            print(f"   候选数: {len(candidates)} → 返回: {len(results)}")
            print(f"   {'='*56}")
            
            if results:
                for result in results:
                    print(f"   {result['rank']}. [{result['source']}] "
                          f"(分数: {result['score']:.3f})")
            else:
                print(f"   ⚠️ 未找到相关文档")
            
            print(f"{'='*60}\n")
            
            return {
                'question': query,
                'results': results,
                'has_results': has_results,
                'method': method  # 新增：返回使用的方法
            }
        
        except Exception as e:
            print(f"❌ 搜索错误: {e}")
            import traceback
            traceback.print_exc()
            return {
                'question': query,
                'results': [],
                'has_results': False,
                'method': 'error'
            }
    
    def toggle_reranking(self, enabled: bool):
        """动态启用/禁用重排序"""
        if enabled and not self.reranker:
            self._init_reranker()
        
        self.use_reranking = enabled
        status = "启用" if enabled else "禁用"
        print(f"✅ 重排序已{status}")


# 使用示例
if __name__ == "__main__":
    
    # 创建改进版知识库
    kb = LocalKnowledgeBaseImproved(
        use_reranking=True,
        reranker_model='light'  # 轻量级，推荐
    )
    
    # 搜索（无需担心硬阈值！）
    results = kb.search("Python 导入错误", top_k=3)
    
    # 检查返回的结果
    print(f"返回方法: {results['method']}")
    print(f"结果数: {len(results['results'])}")
    
    # 如果需要临时禁用重排序
    kb.toggle_reranking(False)
    results = kb.search("另一个查询", top_k=3)
