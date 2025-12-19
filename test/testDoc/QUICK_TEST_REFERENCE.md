# 🚀 RAG 测试快速参考

## ⚡ 30 秒快速启动

```bash
# 1. 进入项目目录
cd /home/zhouanchao/Project/local-knowledge-base

# 2. 导入知识库（如果还未导入）
python -c "
from backend.knowledge_base import LocalKnowledgeBase
import os
os.environ['HF_HUB_OFFLINE'] = '1'
kb = LocalKnowledgeBase()
result = kb.add_documents([
    'knowledge_db/documents/RAG_SYSTEM_GUIDE.md',
    'knowledge_db/documents/VECTOR_DATABASE_GUIDE.md',
    'knowledge_db/documents/MACHINE_LEARNING_BASICS.md'
])
print(f'✅ 导入成功: {result[\"added_chunks\"]} 个块')
"

# 3. 运行测试
python run_rag_tests.py
```

---

## 📊 预期结果参考

### 理想情况（系统工作正常）
```
总体统计:
  - 总问题数: 10
  - 成功查询: 8-10 (80-100%)
  - 有相关文档: 7-10 (70-100%)
```

### 正常情况（系统基本可用）
```
总体统计:
  - 总问题数: 10
  - 成功查询: 6-8 (60-80%)
  - 有相关文档: 5-7 (50-70%)
```

### 需要改进（系统有问题）
```
总体统计:
  - 总问题数: 10
  - 成功查询: <6 (<60%)
  - 有相关文档: <5 (<50%)
  
→ 查看 RAG_TEST_GUIDE.md 的 🔧 优化部分
```

---

## 🎯 测试问题示例

### ⭐ 简单问题（应 100% 成功）
1. RAG 是什么意思？
2. 什么是向量数据库？
3. 什么是神经网络？

### ⭐⭐ 中等问题（应 70%+ 成功）
1. RAG 系统的工作流程是什么？
2. 为什么需要对文本进行分割？
3. Flat、IVF 和 HNSW 索引的区别？

### ⭐⭐⭐ 困难问题（应 40%+ 成功）
1. 设计一个完整的 RAG 系统架构
2. 如何处理多语言文档？
3. RAG 和微调各有什么优缺点？

---

## 🔧 快速优化清单

如果成功率低于 70%，按顺序尝试：

1. **检查知识库** - 确保文档已导入
   ```bash
   python -c "
   from backend.knowledge_base import LocalKnowledgeBase
   import os
   os.environ['HF_HUB_OFFLINE'] = '1'
   kb = LocalKnowledgeBase()
   print(kb.get_stats())
   "
   ```

2. **降低相似度阈值**
   ```python
   kb.relevance_threshold = 0.2  # 从 0.3 降低到 0.2
   ```

3. **增加返回文档数**
   ```python
   result = kb.search(question, top_k=5, use_reranking=True)
   ```

4. **启用重排序**
   ```python
   result = kb.search(question, use_reranking=True)
   ```

5. **检查日志**
   ```python
   import logging
   logging.basicConfig(level=logging.DEBUG)
   ```

---

## 📈 完整测试流程

```
1. 准备阶段 (5分钟)
   ├─ 导入知识库文档
   └─ 验证系统初始化
   
2. 快速测试 (5分钟)
   ├─ 运行 run_rag_tests.py
   └─ 查看简要结果
   
3. 详细分析 (10分钟)
   ├─ 阅读 JSON 测试报告
   ├─ 按难度分析结果
   └─ 按类别分析结果
   
4. 改进调整 (30分钟)
   ├─ 识别失败原因
   ├─ 调整系统参数
   ├─ 手动测试关键问题
   └─ 对比改进效果
   
5. 最终评估 (10分钟)
   ├─ 再次运行完整测试
   ├─ 对比改进前后结果
   └─ 记录最终性能指标

总耗时: 60 分钟
```

---

## 📁 关键文件位置

```
知识库文档:
  📄 knowledge_db/documents/RAG_SYSTEM_GUIDE.md
  📄 knowledge_db/documents/VECTOR_DATABASE_GUIDE.md
  📄 knowledge_db/documents/MACHINE_LEARNING_BASICS.md

测试资源:
  📄 TEST_QUESTIONS.md          (42 个测试问题)
  📄 RAG_TEST_GUIDE.md          (完整测试指南)
  📄 run_rag_tests.py           (自动化测试脚本)

测试报告:
  📄 test_report_YYYYMMDD_HHMMSS.json  (自动生成)
```

---

## 🎯 关键指标说明

| 指标 | 含义 | 目标 |
|------|------|------|
| 总问题数 | 执行的测试问题总数 | 10+ |
| 成功查询 | 成功检索到相关文档的问题数 | >80% |
| 有相关文档 | 返回的答案有相关来源的问题数 | >70% |
| 平均分数 | 检索结果的平均相似度分数 | >0.5 |

---

## 💡 常见错误及解决

| 错误 | 原因 | 解决 |
|------|------|------|
| ImportError | 缺少依赖 | `pip install -r requirements.txt` |
| 0 个块 | 知识库未导入 | 运行导入脚本 |
| 超时 | 网络问题 | 启用离线模式 |
| 内存溢出 | 数据过大 | 减小 top_k 值 |

---

## 📞 快速参考链接

- 📚 完整指南：`RAG_TEST_GUIDE.md`
- 🧪 测试问题：`TEST_QUESTIONS.md`
- 📊 准备总结：`TEST_PREPARATION_SUMMARY.md`
- 📖 RAG 知识库：`knowledge_db/documents/RAG_SYSTEM_GUIDE.md`

---

## ⚡ 一键测试命令

```bash
# 完整测试流程
cd /home/zhouanchao/Project/local-knowledge-base && \
python -c "
from backend.knowledge_base import LocalKnowledgeBase
import os
os.environ['HF_HUB_OFFLINE'] = '1'
kb = LocalKnowledgeBase()
# 如果是首次使用，取消下面这行的注释
# kb.add_documents(['knowledge_db/documents/RAG_SYSTEM_GUIDE.md', 'knowledge_db/documents/VECTOR_DATABASE_GUIDE.md', 'knowledge_db/documents/MACHINE_LEARNING_BASICS.md'])
print(f'知识库状态: {kb.get_stats()}')
" && \
python run_rag_tests.py
```

---

## 🎓 学习路径

```
初级使用
  ↓
快速测试 (5分钟)
  ├─ 运行 run_rag_tests.py
  └─ 查看成功率
  
中级优化
  ↓
详细分析 (15分钟)
  ├─ 理解测试报告
  ├─ 识别失败原因
  └─ 调整参数
  
高级应用
  ↓
完整测试 (60分钟+)
  ├─ 所有 42 个问题
  ├─ 手动评估答案
  └─ 系统架构优化
```

---

## ✅ 成功标志

✅ 系统工作正常 - 当你看到：
```
📈 测试报告
总体统计:
  - 总问题数: 10
  - 成功查询: 8 (80%)
  - 有相关文档: 7 (70%)

🎉 所有检查通过！修复有效。
```

---

**版本**: 1.0  
**最后更新**: 2025-12-18  
**维护者**: RAG 系统开发团队

祝测试顺利！ 🚀
