import os
from pathlib import Path

from dotenv import load_dotenv

ENV_PATH = Path(__file__).resolve().parents[2] / ".env"
load_dotenv(dotenv_path=ENV_PATH)


def get_redis_config() -> dict[str, object]:
    return {
        "host": os.getenv("REDIS_HOST", "localhost"),
        "port": int(os.getenv("REDIS_PORT", "6379")),
        "db": int(os.getenv("REDIS_DB", "0")),
        "password": os.getenv("REDIS_PASSWORD") or None,
        "decode_responses": True,
        "socket_connect_timeout": 3,
        "socket_timeout": 3,
    }


def get_mysql_config() -> dict[str, object]:
    return {
        "host": os.getenv("MYSQL_HOST", "localhost"),
        "port": int(os.getenv("MYSQL_PORT", "3306")),
        "user": os.getenv("MYSQL_USER", "root"),
        "password": os.getenv("MYSQL_PASSWORD", ""),
        "database": os.getenv("MYSQL_DATABASE", "jijin_db"),
        "charset": "utf8",
    }


def get_redis_cache_config() -> dict[str, object]:
    config = get_redis_config()
    return {
        "host": config["host"],
        "port": config["port"],
        "db": config["db"],
        "password": config["password"],
        "default_ttl": int(os.getenv("REDIS_TTL", "30")),
    }
