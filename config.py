import os
import logging
from datetime import datetime

# 基础配置
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LOGS_DIR = os.path.join(BASE_DIR, 'logs')
os.makedirs(LOGS_DIR, exist_ok=True)

# 自定义日志轮转Handler（不再生成日期log，只保留最新1000行）
class RotatingLineFileHandler(logging.FileHandler):
    def __init__(self, filename, max_lines=1000, encoding=None):
        super().__init__(filename, encoding=encoding)
        self.filename = filename
        self.max_lines = max_lines

    def emit(self, record):
        super().emit(record)
        self.rotate_if_needed()

    def rotate_if_needed(self):
        try:
            with open(self.filename, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            if len(lines) > self.max_lines:
                # 只保留最新max_lines行，丢弃旧的
                with open(self.filename, 'w', encoding='utf-8') as f:
                    f.writelines(lines[-self.max_lines:])
        except Exception as e:
            print(f'Log rotation error: {e}')

# API配置
API_CONFIG = {
    "HOST": "127.0.0.1",
    "PORT": 8000,
    "DEBUG": True
}

# 路径配置
PATHS = {
    "BASE_DIR": BASE_DIR,
    "APPS_DIR": os.path.join(BASE_DIR, "apps"),
    "ROUTES_FILE": os.path.join(BASE_DIR, "routes.txt"),
    "STATIC_DIR": os.path.join(BASE_DIR, "admin", "static"),
    "TEMPLATES_DIR": os.path.join(BASE_DIR, "admin", "templates"),
    "LOGS_DIR": LOGS_DIR
}

# 日志配置
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "default": {
            "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        }
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "default",
        },
        "file": {
            "()": RotatingLineFileHandler,
            "filename": os.path.join(LOGS_DIR, "app.log"),
            "max_lines": 1000,
            "formatter": "default",
            "encoding": "utf-8"
        }
    },
    "loggers": {
        "watchfiles": {
            "handlers": [],
            "propagate": False,
            "level": "WARNING"
        },
        "uvicorn.error": {
            "handlers": [],
            "propagate": False,
            "level": "WARNING"
        }
    },
    "root": {
        "handlers": ["console", "file"],
        "level": "INFO",
    }
} 