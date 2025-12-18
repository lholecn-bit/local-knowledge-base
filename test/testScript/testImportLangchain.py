import os
import json
from typing import List, Dict, Optional
from pathlib import Path
import hashlib
from datetime import datetime

from dotenv import load_dotenv
load_dotenv()

# ✅ 第一步：预检查和清理环境
project_root = Path(__file__).parent.parent
models_cache_path = project_root / 'models_cache'
models_cache_path.mkdir(parents=True, exist_ok=True)  # 提前创建目录

# ✅ 第二步：设置环境变量（在导入任何大型库之前）
os.environ['HF_HUB_OFFLINE'] = '1'
os.environ['HF_HOME'] = str(models_cache_path.absolute())

# ✅ 第三步：谨慎设置代理（可能导致问题）
# 注意：不是所有库都支持代理，需要选择性设置
try:
    os.environ["HTTP_PROXY"] = "http://127.0.0.1:10808"
    os.environ["HTTPS_PROXY"] = "http://127.0.0.1:10808"
except Exception as e:
    print(f"⚠️ 代理设置失败: {e}")

# ✅ 第四步：现在才导入依赖库
try:
    from langchain_community.document_loaders import PDFPlumberLoader, TextLoader
    from langchain.text_splitter import RecursiveCharacterTextSplitter
    from langchain_openai import OpenAIEmbeddings
    from langchain_community.vectorstores import FAISS
    LANGCHAIN_AVAILABLE = True
    print("✅ LangChain 组件导入成功")
except ImportError as e:
    print(f"⚠️ Warning: langchain components not fully installed: {e}")
    LANGCHAIN_AVAILABLE = False
except Exception as e:
    print(f"❌ 导入 LangChain 失败: {e}")
    LANGCHAIN_AVAILABLE = False

# ✅ 注意：CrossEncoder 的导入延迟到 search() 方法中
# 不要在这里导入它！