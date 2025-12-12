#!/usr/bin/env python3
"""
RAG 系统迁移脚本：从硬阈值迁移到 Re-Ranking

使用方法：
  python migrate_to_reranking.py
"""

import os
import sys
from pathlib import Path

def print_header(msg):
    """打印头部信息"""
    print("\n" + "=" * 60)
    print(f"🔄 {msg}")
    print("=" * 60 + "\n")

def print_success(msg):
    """打印成功信息"""
    print(f"✅ {msg}")

def print_warning(msg):
    """打印警告信息"""
    print(f"⚠️  {msg}")

def print_error(msg):
    """打印错误信息"""
    print(f"❌ {msg}")

def check_dependencies():
    """检查依赖"""
    print_header("检查环境依赖")
    
    required_packages = {
        'sentence_transformers': 'Re-Ranking 支持库',
        'flask': 'Web 框架',
        'langchain': 'LLM 框架',
    }
    
    missing = []
    for package, description in required_packages.items():
        try:
            __import__(package)
            print_success(f"{package} 已安装 ({description})")
        except ImportError:
            print_warning(f"{package} 未安装 ({description})")
            missing.append(package)
    
    if missing:
        print(f"\n安装缺失的包：")
        print(f"  pip install {' '.join(missing)}")
        return False
    
    return True

def backup_file(filepath):
    """备份文件"""
    backup_path = str(filepath) + '.backup'
    if Path(filepath).exists():
        import shutil
        shutil.copy2(filepath, backup_path)
        print_success(f"已备份: {filepath} → {backup_path}")
        return backup_path
    return None

def show_migration_plan():
    """显示迁移计划"""
    print_header("Re-Ranking 迁移计划")
    
    plan = """
📋 迁移步骤：

1️⃣  安装依赖
    命令：pip install sentence-transformers
    耗时：5-10 分钟（取决于网络）
    
2️⃣  备份原始文件
    ✓ knowledge_base.py 备份
    ✓ app.py 备份
    
3️⃣  修改 knowledge_base.py
    ✓ 添加 Re-Ranking 支持
    ✓ 修改 search() 方法
    ✓ 移除硬阈值代码
    
4️⃣  修改 app.py
    ✓ 移除动态阈值逻辑（0.2/0.3/0.4）
    ✓ 简化搜索调用
    
5️⃣  本地测试
    ✓ 运行 3-5 个测试查询
    ✓ 检查延迟
    ✓ 验证结果质量
    
6️⃣  部署上线
    ✓ 验证生产环境
    ✓ 监控日志

⏱️  预计总耗时：5-6 小时

💰 成本：$0（完全开源）

✨ 预期收益：
   • 相关性精度提升 30-50%
   • 完全消除硬阈值调参问题
   • 代码更清晰易维护
"""
    print(plan)

def show_code_examples():
    """显示代码示例"""
    print_header("代码改动示例")
    
    print("""
【改动 1】knowledge_base.py - 添加 Re-Ranking

❌ 之前（用硬阈值）：
───────────────────────────────────────────
def search(self, query: str, top_k: int = 3, 
       relevance_threshold: Optional[float] = None) -> Dict:
    
    threshold = relevance_threshold or self.relevance_threshold
    candidates = self.vector_store.similarity_search_with_score(query, k=top_k*2)
    
    filtered = []
    for doc, distance in candidates:
        similarity = 1 / (1 + distance)
        if similarity >= threshold:  # ← 硬阈值判断！困难！
            filtered.append(doc)
    
    return filtered[:top_k]


✅ 之后（用 Re-Ranking）：
───────────────────────────────────────────
def search(self, query: str, top_k: int = 3, use_reranking: bool = True) -> Dict:
    
    # 第一步：向量检索（宽松）
    candidates = self.vector_store.similarity_search_with_score(
        query, 
        k=top_k * 3  # 召回更多候选
    )
    
    # 第二步：Re-Ranking（精确）
    if use_reranking:
        if not hasattr(self, 'reranker'):
            from sentence_transformers import CrossEncoder
            self.reranker = CrossEncoder('cross-encoder/ms-marco-MiniLM-L-6-v2')
        
        docs = [doc for doc, _ in candidates]
        scores = self.reranker.predict([
            (query, doc.page_content) for doc in docs
        ])
        
        candidates = sorted(
            zip(docs, scores),
            key=lambda x: x[1],
            reverse=True
        )
    
    # 第三步：返回结果（无需阈值！）
    return candidates[:top_k]


【改动 2】app.py - 移除硬阈值

❌ 之前：
───────────────────────────────────────────
if mode == 'kb':
    relevance_threshold = 0.2
elif mode == 'llm':
    relevance_threshold = 0.4
else:
    relevance_threshold = 0.3

search_results = kb.search(question, top_k, relevance_threshold=relevance_threshold)


✅ 之后：
───────────────────────────────────────────
# 简化到一行！
search_results = kb.search(question, top_k, use_reranking=True)

""")

def install_sentence_transformers():
    """安装 sentence-transformers"""
    print_header("安装 sentence-transformers")
    
    try:
        import subprocess
        print("正在安装 sentence-transformers...")
        print("这会自动下载 CrossEncoder 模型（~200MB）")
        print("首次运行可能需要 5-10 分钟...\n")
        
        subprocess.check_call([
            sys.executable, '-m', 'pip', 'install', 
            'sentence-transformers', '-q'
        ])
        
        print_success("sentence-transformers 安装完成！")
        
        # 验证安装
        from sentence_transformers import CrossEncoder
        print_success("CrossEncoder 可以导入，验证成功！")
        
        return True
    
    except Exception as e:
        print_error(f"安装失败: {e}")
        print("\n手动安装：pip install sentence-transformers")
        return False

def create_test_script():
    """创建测试脚本"""
    print_header("创建测试脚本")
    
    test_script = '''#!/usr/bin/env python3
"""
Re-Ranking 测试脚本
"""

import sys
from pathlib import Path

# 添加后端目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent / 'backend'))

from knowledge_base import LocalKnowledgeBase

def test_reranking():
    """测试 Re-Ranking 功能"""
    
    print("\\n" + "="*60)
    print("🧪 Re-Ranking 功能测试")
    print("="*60 + "\\n")
    
    try:
        # 初始化知识库
        kb = LocalKnowledgeBase()
        
        # 测试查询
        test_queries = [
            "Python 导入错误",
            "如何安装依赖包",
            "Git 提交信息",
        ]
        
        for query in test_queries:
            print(f"\\n🔍 查询：{query}")
            print("-" * 60)
            
            results = kb.search(query, top_k=3, use_reranking=True)
            
            if results['has_results']:
                for i, result in enumerate(results['results'], 1):
                    print(f"{i}. [{result['source']}]")
                    print(f"   分数: {result['score']:.3f}")
                    print(f"   摘要: {result['content'][:100]}...")
            else:
                print("⚠️ 未找到相关文档")
        
        print("\\n" + "="*60)
        print("✅ 测试完成！")
        print("="*60 + "\\n")
        
    except Exception as e:
        print(f"\\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_reranking()
'''
    
    test_file = Path(__file__).parent / 'test_reranking.py'
    
    with open(test_file, 'w', encoding='utf-8') as f:
        f.write(test_script)
    
    test_file.chmod(0o755)
    print_success(f"测试脚本已创建: test_reranking.py")

def show_next_steps():
    """显示后续步骤"""
    print_header("后续步骤")
    
    print("""
✨ 迁移完成！接下来：

1️⃣  运行测试
    python test_reranking.py
    
2️⃣  启动应用
    python backend/app.py
    
3️⃣  测试几个查询
    在前端尝试 3-5 个查询，观察结果质量
    
4️⃣  收集反馈
    • 结果是否更相关？
    • 延迟是否可接受（+100-200ms）？
    • 是否需要进一步优化？
    
5️⃣  可选优化
    如果效果不理想，考虑：
    • 用更大的重排序模型：BAAI/bge-reranker-large
    • 添加 LLM 二次确认
    • 调整召回的候选数（top_k*3 → top_k*5）

📚 参考文档
    • RAG_MIGRATION_GUIDE.md - 详细迁移指南
    • RAG_QUICK_COMPARISON.md - 方案对比
    • RERANKING_GUIDE.md - Re-Ranking 详解

💬 如有问题
    查看日志输出和 README.md 中的故障排查部分

🎉 祝迁移顺利！
""")

def main():
    """主函数"""
    
    print("""
╔══════════════════════════════════════════════════════════╗
║                                                          ║
║  RAG 系统迁移工具：硬阈值 → Re-Ranking                    ║
║                                                          ║
║  本工具帮助你快速迁移到更好的相关性评估方式               ║
║                                                          ║
╚══════════════════════════════════════════════════════════╝
""")
    
    # 1. 显示迁移计划
    show_migration_plan()
    
    # 2. 显示代码示例
    show_code_examples()
    
    # 3. 检查依赖
    if not check_dependencies():
        print("\n" + "="*60)
        print("需要安装依赖，继续? (y/n): ", end='')
        if input().lower() != 'y':
            print_error("取消迁移")
            return
        
        if not install_sentence_transformers():
            print_error("依赖安装失败，请手动安装")
            return
    
    # 4. 备份文件
    print_header("备份原始文件")
    backend_dir = Path(__file__).parent / 'backend'
    
    if backend_dir.exists():
        backup_file(backend_dir / 'knowledge_base.py')
        backup_file(backend_dir / 'app.py')
    else:
        print_warning("backend 目录不存在")
    
    # 5. 创建测试脚本
    create_test_script()
    
    # 6. 显示后续步骤
    show_next_steps()
    
    print("\n" + "="*60)
    print("✅ 迁移准备完成！")
    print("="*60)
    print("""
现在手动执行以下步骤：

1. 修改 backend/knowledge_base.py search() 方法
   （参考上面的代码示例 ✅ 之后 部分）

2. 修改 backend/app.py stream_query() 方法
   （移除 0.2/0.3/0.4 硬阈值部分）

3. 运行测试：python test_reranking.py

有详细指南吗？查看 RAG_MIGRATION_GUIDE.md
""")

if __name__ == "__main__":
    main()
