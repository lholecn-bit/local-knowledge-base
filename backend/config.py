# backend/config.py
import os
from pathlib import Path
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 基础配置
BASE_DIR = Path(__file__).parent
UPLOAD_FOLDER = BASE_DIR / "uploads"
KNOWLEDGE_DB_PATH = BASE_DIR / "knowledge_db"
ALLOWED_EXTENSIONS = {'pdf', 'txt', 'md', 'docx'}

# 创建必要的目录
UPLOAD_FOLDER.mkdir(exist_ok=True)
KNOWLEDGE_DB_PATH.mkdir(exist_ok=True)

# OpenAI 配置
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")

if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY 未设置，请在 .env 文件中配置")

# 知识库配置
EMBEDDING_MODEL = "text-embedding-3-small"
LLM_MODEL = "gpt-3.5-turbo"
CHUNK_SIZE = 500
CHUNK_OVERLAP = 50
TOP_K = 3

# Flask 配置
class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-change-in-production")
    JSON_AS_ASCII = False
    JSON_SORT_KEYS = False
    JSONIFY_PRETTYPRINT_REGULAR = True

# 日志配置
import logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)
