import json
import os
from dotenv import load_dotenv

from common.path_utils import get_file_path

# 加载 .env 文件，指定 encoding='utf-8' 避免编码问题
_env_path = get_file_path(f".env")
if os.path.exists(_env_path):
    # 尝试用 utf-8 加载，失败则用 gbk
    try:
        with open(_env_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except UnicodeDecodeError:
        with open(_env_path, 'r', encoding='gbk') as f:
            content = f.read()
        # 将 GBK 编码的内容重新写入为 UTF-8
        with open(_env_path, 'w', encoding='utf-8') as f:
            f.write(content)
    load_dotenv(_env_path, encoding='utf-8')


def _int(key: str, default: int = 0) -> int:
    val = os.getenv(key)
    return int(val) if val is not None else default


def _bool(key: str, default: bool = True) -> bool:
    val = os.getenv(key)
    if val is None:
        return default
    return val.lower() in ("1", "true", "yes", "on")


def _str(key: str, default: str = "") -> str:
    return os.getenv(key) or default


class Config:
    def __init__(self):
        # 大模型相关
        self.MODEL_API_KEY = _str("MODEL_API_KEY")
        self.MODEL_BASE_URL = _str("MODEL_BASE_URL")
        self.MODEL_NAME = _str("MODEL_NAME")

        # MySQL
        self.MYSQL_HOST = _str("MYSQL_HOST", "localhost")
        self.MYSQL_USER = _str("MYSQL_USER")
        self.MYSQL_PASSWORD = _str("MYSQL_PASSWORD")
        self.MYSQL_DATABASE = _str("MYSQL_DATABASE")

        # Redis
        self.REDIS_HOST = _str("REDIS_HOST", "localhost")
        self.REDIS_PORT = _int("REDIS_PORT", 6379)
        self.REDIS_PASSWORD = _str("REDIS_PASSWORD")
        self.REDIS_DB = _int("REDIS_DB", 0)
        self.REDIS_EXPIRE = _int("REDIS_EXPIRE", 86400)

        # Milvus
        self.MILVUS_HOST = _str("MILVUS_HOST", "localhost")
        self.MILVUS_PORT = _int("MILVUS_PORT", 19530)
        self.MILVUS_DATABASE_NAME = _str("MILVUS_DATABASE_NAME")
        self.MILVUS_COLLECTION_NAME = _str("MILVUS_COLLECTION_NAME")

        # 检索参数
        self.PARENT_CHUNK_SIZE = _int("PARENT_CHUNK_SIZE", 1200)
        self.CHILD_CHUNK_SIZE = _int("CHILD_CHUNK_SIZE", 300)
        self.CHUNK_OVERLAP = _int("CHUNK_OVERLAP", 50)
        self.RETRIEVAL_K = _int("RETRIEVAL_K", 5)
        self.CANDIDATE_M = _int("CANDIDATE_M", 2)

        # 本地模型路径
        self.BGE_M3_PATH = _str("BGE_M3_PATH")
        self.BGE_RERANKER_PATH = _str("BGE_RERANKER_PATH")
        self.BERT_BASE_PATH = _str("BERT_BASE_PATH")
        self.DOCUMENT_SEGMENTATION_PATH = _str("DOCUMENT_SEGMENTATION_PATH")
        self.BERT_CLASSIFIER_PATH = get_file_path("models/bert_classifier")

        # 日志
        self.LOG_FILE = get_file_path("logs/app.log")

        # 应用配置
        _sources = _str("VALID_SOURCES")
        self.VALID_SOURCES = json.loads(_sources) if _sources else ["ai", "java", "test", "ops", "bigdata"]
        self.CUSTOMER_SERVICE_PHONE = _str("CUSTOMER_SERVICE_PHONE")

        # RepoAgent - GitHub
        self.GITHUB_TOKEN = _str("GITHUB_TOKEN")
        self.GITHUB_API_BASE = _str("GITHUB_API_BASE", "https://api.github.com")
        # Windows/企业代理环境下 SSL 校验；开发可设 HTTP_SSL_VERIFY=false
        self.HTTP_SSL_VERIFY = _bool("HTTP_SSL_VERIFY", True)

        # RepoAgent - 任务控制
        self.TASK_TIMEOUT = _int("TASK_TIMEOUT", 300)
        self.AGENT_TIMEOUT = _int("AGENT_TIMEOUT", 120)
        self.MAX_CONCURRENT_TASKS = _int("MAX_CONCURRENT_TASKS", 3)
        self.RATE_LIMIT_PER_MINUTE = _int("RATE_LIMIT_PER_MINUTE", 5)

        # RepoAgent - 应用
        self.APP_ENV = _str("APP_ENV", "development")
        _cors = _str("CORS_ORIGINS", "http://localhost:5173")
        self.CORS_ORIGINS = [o.strip() for o in _cors.split(",") if o.strip()]
        self.APP_VERSION = _str("APP_VERSION", "0.1.0")

if __name__ == "__main__":
    conf = Config()
    #print(conf.BERT_BASE_PATH)
    print(conf.MODEL_API_KEY)
    print(conf.MODEL_BASE_URL)
    print(conf.MODEL_NAME)
