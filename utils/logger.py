import logging.config
from config import LOGGING

# 配置日志
logging.config.dictConfig(LOGGING)
logger = logging.getLogger(__name__) 