# RAG 系统测试指南

## 📋 概述

本指南说明如何使用准备好的知识库和测试问题来验证 RAG 系统的效果。

## 🎯 测试目标

1. **验证系统基础功能** - 检索和重排序是否正常工作
2. **评估答案质量** - 回答是否准确、相关、完整
3. **找出改进方向** - 识别系统的薄弱环节
4. **建立性能基线** - 为未来改进提供参考

---

## 📦 准备工作

### 1. 将知识库文档导入系统

知识库包含以下3个文档：

```
knowledge_db/documents/
├── RAG_SYSTEM_GUIDE.md           (RAG 系统完整指南)
├── VECTOR_DATABASE_GUIDE.md      (向量数据库详解)
└── MACHINE_LEARNING_BASICS.md    (机器学习和神经网络)
```

**导入方式选项A：使用 Web 界面**
```bash
1. 启动 Flask 应用: python backend/app.py
2. 打开浏览器访问: http://localhost:5000
3. 上传 documents 文件夹中的 3 个 MD 文件
```

**导入方式选项B：使用 Python 脚本**
```python
from backend.knowledge_base import LocalKnowledgeBase

kb = LocalKnowledgeBase()
result = kb.add_documents([
    "knowledge_db/documents/RAG_SYSTEM_GUIDE.md",
    "knowledge_db/documents/VECTOR_DATABASE_GUIDE.md",
    "knowledge_db/documents/MACHINE_LEARNING_BASICS.md"
])
print(result)
```

### 2. 验证知识库加载

```bash
cd /home/zhouanchao/Project/local-knowledge-base

# 运行验证脚本
python -c "
from backend.knowledge_base import LocalKnowledgeBase
import os
os.environ['HF_HUB_OFFLINE'] = '1'
kb = LocalKnowledgeBase()
stats = kb.get_stats()
print(f'知识库状态: {stats[\"total_chunks\"]} 个块，{stats[\"total_files\"]} 个文件')
"
```

---

## 🧪 执行测试

### 方式1：自动化测试（推荐）

运行测试脚本，自动执行所有 10 个测试问题：

```bash
cd /home/zhouanchao/Project/local-knowledge-base
python run_rag_tests.py
```

**预期输出**：
```
🧪 RAG 系统自动化测试
...
📈 测试报告
总体统计:
  - 总问题数: 10
  - 成功查询: 8 (80%)
  - 有相关文档: 7 (70%)
...
💾 详细报告已保存到: test_report_20231218_120000.json
```

### 方式2：手动测试

使用 Python 交互式环节运行单个问题：

```python
import os
os.environ['HF_HUB_OFFLINE'] = '1'

from backend.knowledge_base import LocalKnowledgeBase

kb = LocalKnowledgeBase()

# 执行搜索
question = "RAG 是什么意思？"
result = kb.query(question, top_k=3)

# 查看结果
print("问题:", result['question'])
print("答案:", result['answer'])
print("相关文档:", result['sources'])
print("有相关文档:", result['has_sources'])
```

### 方式3：Web 界面测试

1. 启动应用
```bash
cd /home/zhouanchao/Project/local-knowledge-base/backend
python app.py
```

2. 打开浏览器：http://localhost:5000

3. 在搜索框输入问题，查看结果

---

## 📊 理解测试结果

### 测试问题分类

**按难度**：
- ⭐ 简单 - 直接在文档中出现的概念
- ⭐⭐ 中等 - 需要组合多个知识点
- ⭐⭐⭐ 困难 - 需要推理和理解

**按领域**：
- RAG 系统相关
- 向量数据库相关
- 机器学习相关

### 性能评分标准

| 指标 | 优秀 | 良好 | 一般 | 需改进 |
|------|------|------|------|--------|
| 找到相关文档 | >90% | 70-90% | 50-70% | <50% |
| 答案完整性 | 包含关键点 | 部分完整 | 片段式 | 不相关 |
| 答案准确性 | 完全正确 | 基本正确 | 部分正确 | 错误 |

### 常见问题及解释

**Q: 为什么某些问题没有找到相关文档？**

A: 可能的原因：
1. 问题的措辞与文档差异大
2. 相似度阈值设置过高（relevance_threshold）
3. Embedding 模型不够强
4. 知识库缺少相关内容

**Q: 为什么找到了文档但答案不准确？**

A: 可能的原因：
1. 检索的文档不是最相关的（Cross-Encoder 重排序效果不好）
2. LLM 理解有偏差
3. 文档本身有错误或歧义

**Q: 为什么结果时好时坏（非确定性）？**

A: 可能原因：
1. Cross-Encoder 模型的随机初始化
2. 相似度很接近的多个候选
3. LLM 的生成具有随机性

---

## 🔧 优化和调试

### 1. 调整系统参数

```python
# relevance_threshold - 相似度阈值，影响检索的文档数量
# 降低阈值 → 更多文档 → 可能噪音增加
# 提高阈值 → 更少文档 → 可能漏掉相关内容

kb.relevance_threshold = 0.3  # 默认值

# top_k - 返回的相关文档数
result = kb.search(question, top_k=5, use_reranking=True)

# use_reranking - 是否使用 Cross-Encoder 重排序
result_with_reranking = kb.search(question, use_reranking=True)
result_without_reranking = kb.search(question, use_reranking=False)
```

### 2. 检查 Embedding 模型质量

```python
# 测试 Embedding 相似性
emb1 = kb.embeddings.embed_query("RAG 是什么？")
emb2 = kb.embeddings.embed_query("RAG 系统的定义")

# 计算余弦相似度
import numpy as np
sim = np.dot(emb1, emb2) / (np.linalg.norm(emb1) * np.linalg.norm(emb2))
print(f"相似度: {sim:.3f}")  # 应该接近 1（高度相似）
```

### 3. 启用详细日志

```python
# 查看检索过程
import logging
logging.basicConfig(level=logging.DEBUG)

result = kb.search("RAG 系统", use_reranking=True)
# 日志会显示：
# - 检索到的候选数
# - 各候选的相似度分数
# - 重排序后的顺序
# - 最终返回的结果
```

### 4. 手动评估结果

```python
# 获取详细的搜索结果
search_result = kb.search(question, top_k=5, use_reranking=True)

for i, result in enumerate(search_result['results'], 1):
    print(f"\n【{i}】{result['source']}")
    print(f"相似度: {result['score']:.3f}")
    print(f"内容: {result['content'][:200]}...")
```

---

## 📈 生成测试报告

自动化测试会生成 JSON 格式的详细报告：

```json
{
  "timestamp": "2023-12-18T12:00:00",
  "statistics": {
    "total": 10,
    "success": 8,
    "has_results": 7
  },
  "results": [
    {
      "id": 1,
      "question": "RAG 是什么意思？",
      "difficulty": "⭐",
      "has_sources": true,
      "sources": ["RAG_SYSTEM_GUIDE.md"],
      "status": "✅ 成功"
    },
    ...
  ]
}
```

**如何分析报告**：
1. 检查 `statistics` 了解总体成功率
2. 查看各个 `results` 了解具体问题的表现
3. 按 `difficulty` 分组分析难度影响
4. 按 `category` 分组分析领域影响

---

## 🎯 改进指标

### 如果成功率 < 60%

**立即行动**：
1. ✅ 确保知识库文档已正确上传
2. ✅ 检查 Embedding 模型是否加载
3. ✅ 查看是否有错误日志

**可能原因**：
- 知识库文档数量不足
- Embedding 模型质量问题
- 系统配置错误

### 如果成功率 60-80%

**正常改进方向**：
1. 🔧 调整 `relevance_threshold` 参数
2. 🔧 启用 Cross-Encoder 重排序
3. 🔧 增加 `top_k` 值
4. 📚 补充或优化知识库文档

### 如果成功率 > 80%

**优化建议**：
1. 对更复杂的问题（⭐⭐⭐）进行测试
2. 测试特定领域的问题
3. 测试边界情况和负面案例
4. 考虑性能优化（响应时间、内存占用）

---

## 📝 手动测试问题示例

如果想手动测试，可以使用以下问题：

**快速测试（5分钟）**
```
1. RAG 是什么？
2. 什么是向量数据库？
3. 神经网络如何工作？
```

**标准测试（15分钟）**
```
1. RAG 系统的工作流程？
2. FAISS 有哪些索引方法？
3. 如何防止神经网络过拟合？
4. 文本分割为什么重要？
5. Cross-Encoder 和 Bi-Encoder 的区别？
```

**完整测试（30分钟+）**
- 使用 `TEST_QUESTIONS.md` 中的所有 42 个问题
- 根据回答质量手动打分
- 记录改进方向

---

## 🚀 下一步

### 如果系统表现良好

1. **部署到生产环境**
   ```bash
   # 配置生产参数
   # 启用监控和日志
   # 定期更新知识库
   ```

2. **收集用户反馈**
   - 记录用户提问
   - 评估回答质量
   - 持续改进

3. **扩展功能**
   - 多语言支持
   - 更复杂的查询处理
   - 与其他系统集成

### 如果系统需要改进

1. **分析失败原因**
   - 哪些类型的问题失败率高？
   - 问题措辞的影响？
   - 文档内容的问题？

2. **有针对性地优化**
   - 改进知识库内容
   - 调整系统参数
   - 考虑使用更强大的模型

3. **迭代测试**
   - 修改后重新运行测试
   - 对比改进效果
   - 持续优化

---

## 📞 故障排查

### 常见错误

| 错误 | 原因 | 解决方案 |
|------|------|---------|
| ImportError | 依赖未安装 | `pip install -r requirements.txt` |
| CUDA Error | GPU 内存不足 | 减小 batch_size，或使用 CPU |
| Timeout | 网络问题 | 检查代理设置，使用离线模式 |
| 内存溢出 | 数据太大 | 减小知识库，分批处理 |

### 调试工具

```python
# 1. 检查系统配置
import os
print(f"HF_HOME: {os.getenv('HF_HUB_OFFLINE')}")
print(f"CUDA: {os.getenv('CUDA_VISIBLE_DEVICES')}")

# 2. 检查模型加载
from backend.knowledge_base import LocalKnowledgeBase
kb = LocalKnowledgeBase()
print(f"Embeddings: {kb.embeddings}")
print(f"Vector Store: {kb.vector_store}")

# 3. 检查 Embedding 质量
query_vec = kb.embeddings.embed_query("test")
print(f"Embedding 维度: {len(query_vec)}")
print(f"Embedding 范围: [{min(query_vec):.3f}, {max(query_vec):.3f}]")
```

---

## 📞 获取帮助

查看以下文档获取更多信息：
- `RAG_SYSTEM_GUIDE.md` - RAG 系统详细说明
- `VECTOR_DATABASE_GUIDE.md` - 向量数据库深入讲解
- `MACHINE_LEARNING_BASICS.md` - 机器学习基础知识
- `TEST_QUESTIONS.md` - 所有 42 个测试问题的详细说明

---

## ✅ 检查清单

开始测试前请确认：

- [ ] 知识库文档已上传（3个 MD 文件）
- [ ] 系统初始化无错误
- [ ] `total_chunks > 0`（知识库有内容）
- [ ] Embedding 模型已加载
- [ ] 向量数据库已加载
- [ ] 环境变量已正确设置

准备就绪后，运行：
```bash
python run_rag_tests.py
```

祝测试顺利！ 🎉
