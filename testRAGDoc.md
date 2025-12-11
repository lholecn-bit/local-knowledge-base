# 本地知识库系统 - 完整指南

## 1. 系统概述

本地知识库系统是一个基于检索增强生成（RAG）技术的智能问答系统。它允许用户上传本地文档，系统会自动处理这些文档并创建向量索引，用户可以基于这些文档提出问题，系统会检索相关内容并使用大语言模型生成答案。

### 核心特性

- 支持多种文档格式（PDF、Word、TXT、Markdown）
- 自动文档处理和分块
- 向量化索引和相似度搜索
- 多种查询模式（知识库模式、LLM模式、自动模式）
- 流式响应和实时反馈
- 完整的文档管理功能

## 2. 快速开始

### 2.1 系统要求

- Python 3.8 或更高版本
- Node.js 14.0 或更高版本
- 4GB 内存或以上
- 稳定的网络连接

### 2.2 安装步骤

#### 后端安装

```bash
# 克隆项目
git clone https://github.com/your-repo/local-knowledge-base.git
cd local-knowledge-base/backend

# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt

# 配置环境变量
cp .env.example .env
# 编辑 .env 文件，设置 OPENAI_API_KEY 等参数
```
