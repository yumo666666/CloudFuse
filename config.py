import os

# 基础配置
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

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
    "TEMPLATES_DIR": os.path.join(BASE_DIR, "admin", "templates")
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
            "class": "logging.FileHandler",
            "filename": os.path.join(BASE_DIR, "app.log"),
            "formatter": "default",
        }
    },
    "root": {
        "handlers": ["console", "file"],
        "level": "INFO",
    }
} 