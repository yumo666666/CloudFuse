import sys
import os
from datetime import datetime
import re # Import re module for regex
# ANSI escape code regex
ANSI_ESCAPE = re.compile(r'\x1B(?:[@-Z\\-_]|\\[0-?][ -/][@-~])')

# Tee class to duplicate stdout/stderr
class Tee(object):
    def __init__(self, *files):
        self.files = files
        # Store original stdout/stderr to forward isatty() calls
        self.original_stdout = sys.__stdout__ # Use sys.__stdout__ for the actual original stream
        self.original_stderr = sys.__stderr__ # Use sys.__stderr__ for the actual original stream

    def filter_ansi(self, text):
        # More robust ANSI escape code removal
        # Source: https://stackoverflow.com/questions/14693701/how-can-i-remove-the-ansi-escape-sequences-from-a-string-in-python
        ansi_escape = re.compile(r'(\x1b[^m]*m)')
        return ansi_escape.sub('', text)

    def write(self, obj):
        for f in self.files:
            # If writing to the log file, filter ANSI codes
            if f is log_file: # Directly check if it's the log file object
                content_to_write = self.filter_ansi(obj)
                # Ensure newlines for file logging consistency
                if not content_to_write.endswith('\n'):
                    content_to_write += '\n'
            else:
                content_to_write = obj
            f.write(content_to_write)
            f.flush()
    def flush(self):
        for f in self.files:
            f.flush()
    def isatty(self):
        # Forward the isatty() call to the original stdout/stderr
        # Check if original_stdout is a file-like object before calling isatty
        if hasattr(self.original_stdout, 'isatty'):
            return self.original_stdout.isatty()
        return False # Default to False if not a proper terminal
# 日志目录和文件
log_dir = os.path.join(os.path.dirname(__file__), "logs")
os.makedirs(log_dir, exist_ok=True)
log_path = os.path.join(log_dir, "app.log")
# 日志归档函数
import threading, time

def rotate_log_daily():
    while True:
        now = datetime.now()
        next_day = datetime(now.year, now.month, now.day)  # 今天0点
        next_day = next_day.replace(day=now.day+1) if now.hour >= 0 else next_day
        seconds = (next_day - now).total_seconds()
        time.sleep(seconds)
        # 归档
        archive_name = os.path.join(log_dir, now.strftime("%Y-%m-%d.log"))
        if os.path.exists(log_path):
            with open(log_path, "rb") as src, open(archive_name, "ab") as dst:
                dst.write(src.read())
            open(log_path, "w").close()  # 清空
threading.Thread(target=rotate_log_daily, daemon=True).start()
# Redirect stdout and stderr to both the log file and original stdout
log_file = open(log_path, "a", encoding="utf-8", buffering=1)
original_stdout = sys.stdout
sys.stdout = Tee(original_stdout, log_file)
sys.stderr = Tee(sys.stderr, log_file)

from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
import time
from utils.logger import logger
from config import API_CONFIG, PATHS
from admin.admin import router as admin_router, FunctionManager
import importlib
from typing import List, Dict
import json
import asyncio
from datetime import datetime

# 定义生命周期管理器
@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动时执行
    try:
        logger.info("Checking dependencies on startup...")
        new_deps = await FunctionManager.check_and_install_dependencies()
        if new_deps:
            logger.info(f"Installed new dependencies on startup: {new_deps}")
        else:
            logger.info("No new dependencies needed")
    except Exception as e:
        logger.error(f"Error checking dependencies on startup: {e}")
        raise e
    
    yield  # 这里是应用运行的地方
    
    # 关闭时执行（如果需要）
    # 清理代码可以放在这里

# 使用生命周期管理器创建应用
app = FastAPI(title="API Service", version="1.0.0", lifespan=lifespan)

# CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 添加可信主机中间件
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=["*"]  # 在生产环境中应该限制允许的主机
)

# 请求计时中间件
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    return response

# 全局错误处理
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Global error: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error", "message": str(exc)}
    )

# 静态文件
app.mount("/static", StaticFiles(directory=PATHS["STATIC_DIR"]), name="static")

# 路由
app.include_router(admin_router, prefix="/admin")

# 获取函数列表的路由
@app.get("/functions")
async def get_functions():
    try:
        module = importlib.import_module("apps.functions.function")
        return module.functions()
    except Exception as e:
        logger.error(f"Error getting functions list: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# 动态函数调用
@app.get("/function/{function_name}")
async def call_function(function_name: str, request: Request):
    try:
        module = importlib.import_module(f"apps.{function_name}.function")
        func = getattr(module, function_name)
        logger.info(f"Calling function: {function_name}")
        
        # 获取所有查询参数
        query_params = dict(request.query_params)
        
        # 获取函数参数信息
        import inspect
        sig = inspect.signature(func)
        
        # 准备函数参数
        kwargs = {}
        for param_name, param in sig.parameters.items():
            if param_name in query_params:
                # 根据参数类型转换值
                param_type = param.annotation if param.annotation != inspect.Parameter.empty else str
                try:
                    if param_type == float:
                        kwargs[param_name] = float(query_params[param_name])
                    elif param_type == int:
                        kwargs[param_name] = int(query_params[param_name])
                    else:
                        kwargs[param_name] = query_params[param_name]
                except ValueError as e:
                    raise HTTPException(status_code=400, 
                                     detail=f"Invalid value for parameter {param_name}: {str(e)}")
            elif param.default == inspect.Parameter.empty:
                # 如果参数没有默认值且未提供，则报错
                raise HTTPException(status_code=400, 
                                 detail=f"Missing required parameter: {param_name}")
        
        # 调用函数
        result = func(**kwargs)
        
        # 统计调用次数（支持天/小时）
        try:
            now = datetime.now()
            day_str = now.strftime('%Y-%m-%d')
            hour_str = now.strftime('%Y-%m-%d-%H')
            stats_file = os.path.join(PATHS["BASE_DIR"], "call_stats.json")
            # 兼容旧数据结构
            if os.path.exists(stats_file):
                with open(stats_file, "r", encoding="utf-8") as f:
                    stats = json.load(f)
                if "history_day" not in stats or not isinstance(stats["history_day"], dict):
                    stats["history_day"] = {}
                if "history_hour" not in stats or not isinstance(stats["history_hour"], dict):
                    stats["history_hour"] = {}
            else:
                stats = {"total": 0, "functions": {}, "history_day": {}, "history_hour": {}}
            # 总数
            stats["total"] = stats.get("total", 0) + 1
            stats["functions"][function_name] = stats["functions"].get(function_name, 0) + 1
            # 按天
            if day_str not in stats["history_day"] or not isinstance(stats["history_day"][day_str], dict):
                stats["history_day"][day_str] = {"total": 0}
            stats["history_day"][day_str]["total"] = stats["history_day"][day_str].get("total", 0) + 1
            stats["history_day"][day_str][function_name] = stats["history_day"][day_str].get(function_name, 0) + 1
            # 按小时
            if hour_str not in stats["history_hour"] or not isinstance(stats["history_hour"][hour_str], dict):
                stats["history_hour"][hour_str] = {"total": 0}
            stats["history_hour"][hour_str]["total"] = stats["history_hour"][hour_str].get("total", 0) + 1
            stats["history_hour"][hour_str][function_name] = stats["history_hour"][hour_str].get(function_name, 0) + 1
            with open(stats_file, "w", encoding="utf-8") as f:
                json.dump(stats, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Error updating call stats: {e}")
        
        return result
            
    except Exception as e:
        logger.error(f"Error calling function {function_name}: {e}")
        raise HTTPException(status_code=404, detail=f"Function error: {str(e)}")

# 添加错误处理中间件
@app.middleware("http")
async def error_handling_middleware(request: Request, call_next):
    try:
        response = await call_next(request)
        return response
    except Exception as e:
        logger.error(f"Unhandled error: {e}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal server error", "message": str(e)}
        )

if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",  # 修改为监听所有网络接口
        port=API_CONFIG["PORT"],
        reload=API_CONFIG["DEBUG"]
    )
