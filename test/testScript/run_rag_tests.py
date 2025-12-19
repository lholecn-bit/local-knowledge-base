#!/usr/bin/env python3
"""
RAG 系统自动化测试脚本
"""

import os
import sys
import json
from pathlib import Path
from datetime import datetime

# 设置环境变量
os.environ['HF_HUB_OFFLINE'] = '1'
os.environ['HF_HOME'] = str(Path(__file__).parent / 'models_cache')
os.environ['TRANSFORMERS_CACHE'] = str(Path(__file__).parent / 'models_cache')

sys.path.insert(0, str(Path(__file__).parent / 'backend'))

def run_rag_tests():
    """运行 RAG 系统测试"""
    print("\n" + "="*70)
    print("🧪 RAG 系统自动化测试")
    print("="*70)
    
    try:
        from knowledge_base import LocalKnowledgeBase
    except ImportError as e:
        print(f"❌ 导入失败: {e}")
        return False
    
    # 初始化知识库
    print("\n📦 初始化知识库...")
    try:
        kb = LocalKnowledgeBase()
        print("✅ 知识库初始化成功")
    except Exception as e:
        print(f"❌ 初始化失败: {e}")
        return False
    
    # 获取统计信息
    print("\n📊 知识库统计信息:")
    stats = kb.get_stats()
    print(f"  - 文档块数: {stats['total_chunks']}")
    print(f"  - 文件数: {stats['total_files']}")
    for file_info in stats['files']:
        print(f"    • {file_info['name']}")
    
    if stats['total_chunks'] == 0:
        print("\n⚠️  知识库中没有文档!")
        print("请先上传或添加文档。")
        return False
    
    # 定义测试问题
    test_questions = [
        {
            "id": 1,
            "difficulty": "⭐",
            "question": "RAG 是什么意思？",
            "category": "RAG 系统"
        },
        {
            "id": 2,
            "difficulty": "⭐",
            "question": "RAG 系统有哪几个核心组件？",
            "category": "RAG 系统"
        },
        {
            "id": 3,
            "difficulty": "⭐",
            "question": "什么是 Cross-Encoder？",
            "category": "RAG 系统"
        },
        {
            "id": 4,
            "difficulty": "⭐",
            "question": "什么是向量数据库？",
            "category": "向量数据库"
        },
        {
            "id": 5,
            "difficulty": "⭐",
            "question": "FAISS 是什么？",
            "category": "向量数据库"
        },
        {
            "id": 6,
            "difficulty": "⭐⭐",
            "question": "RAG 系统的工作流程是什么？",
            "category": "RAG 系统"
        },
        {
            "id": 7,
            "difficulty": "⭐⭐",
            "question": "为什么需要对文本进行分割？",
            "category": "RAG 系统"
        },
        {
            "id": 8,
            "difficulty": "⭐⭐",
            "question": "Flat、IVF 和 HNSW 索引的区别是什么？",
            "category": "向量数据库"
        },
        {
            "id": 9,
            "difficulty": "⭐",
            "question": "什么是神经网络？",
            "category": "机器学习"
        },
        {
            "id": 10,
            "difficulty": "⭐",
            "question": "什么是反向传播？",
            "category": "机器学习"
        },
    ]
    
    # 运行测试
    print("\n" + "="*70)
    print("🔍 执行测试问题")
    print("="*70)
    
    results = []
    
    for q in test_questions:
        print(f"\n【{q['id']}/{len(test_questions)}】 {q['difficulty']} {q['question']}")
        print(f"    类别: {q['category']}")
        
        try:
            # 执行搜索
            search_result = kb.search(
                q['question'],
                top_k=3,
                use_reranking=True
            )
            
            # 获取答案
            query_result = kb.query(
                q['question'],
                top_k=3
            )
            
            # 记录结果
            result = {
                "id": q['id'],
                "question": q['question'],
                "difficulty": q['difficulty'],
                "category": q['category'],
                "answer": query_result['answer'][:200],  # 前 200 个字符
                "has_sources": query_result['has_sources'],
                "sources": query_result['sources'],
                "num_results": len(search_result['results']),
                "status": "✅ 成功" if search_result['has_results'] else "⚠️ 无结果"
            }
            
            results.append(result)
            
            # 显示结果
            print(f"    {result['status']}")
            if search_result['has_results']:
                print(f"    找到 {result['num_results']} 个相关文档")
                for i, r in enumerate(search_result['results'][:2], 1):
                    print(f"      {i}. {r['source']} (相似度: {r['score']:.3f})")
                print(f"    回答: {result['answer']}...")
            
        except Exception as e:
            print(f"    ❌ 错误: {e}")
            results.append({
                "id": q['id'],
                "question": q['question'],
                "error": str(e),
                "status": "❌ 失败"
            })
    
    # 生成测试报告
    print("\n" + "="*70)
    print("📈 测试报告")
    print("="*70)
    
    # 统计结果
    total = len(results)
    success = sum(1 for r in results if r.get('status', '').startswith('✅'))
    has_results = sum(1 for r in results if r.get('has_sources', False))
    
    print(f"\n总体统计:")
    print(f"  - 总问题数: {total}")
    print(f"  - 成功查询: {success} ({success*100//total}%)")
    print(f"  - 有相关文档: {has_results} ({has_results*100//total}%)")
    
    # 按难度统计
    print(f"\n按难度统计:")
    for difficulty in ["⭐", "⭐⭐", "⭐⭐⭐"]:
        difficulty_results = [r for r in results if r.get('difficulty') == difficulty]
        if difficulty_results:
            difficulty_success = sum(1 for r in difficulty_results if r.get('has_sources', False))
            print(f"  {difficulty}: {difficulty_success}/{len(difficulty_results)} ({difficulty_success*100//len(difficulty_results) if difficulty_results else 0}%)")
    
    # 按类别统计
    print(f"\n按类别统计:")
    categories = set(r.get('category') for r in results if r.get('category'))
    for category in sorted(categories):
        category_results = [r for r in results if r.get('category') == category]
        category_success = sum(1 for r in category_results if r.get('has_sources', False))
        print(f"  {category}: {category_success}/{len(category_results)}")
    
    # 保存详细结果
    report_file = Path(__file__).parent / f"test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump({
            "timestamp": datetime.now().isoformat(),
            "statistics": {
                "total": total,
                "success": success,
                "has_results": has_results
            },
            "results": results
        }, f, ensure_ascii=False, indent=2)
    
    print(f"\n💾 详细报告已保存到: {report_file}")
    
    # 建议
    print("\n" + "="*70)
    print("💡 建议")
    print("="*70)
    
    if success < total * 0.8:
        print("⚠️  成功率低于 80%，建议:")
        print("  1. 检查知识库文档的质量和相关性")
        print("  2. 调整相似度阈值 (relevance_threshold)")
        print("  3. 尝试不同的 Embedding 模型")
        print("  4. 启用或调整 Cross-Encoder 重排序参数")
    else:
        print("✅ 系统表现良好！")
        if has_results < success * 0.7:
            print("💡 建议：虽然查询成功，但部分问题的相关文档较少。")
            print("   可以考虑优化文本分割策略或改进知识库内容。")
    
    return success >= total * 0.6

if __name__ == '__main__':
    try:
        success = run_rag_tests()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
