from fastapi import APIRouter, UploadFile, HTTPException, BackgroundTasks, File, Form, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, FileResponse, Response, JSONResponse, StreamingResponse
import os
import importlib.util
import sys
import shutil
from utils.logger import logger
from config import PATHS
import pkg_resources
import subprocess
from typing import List, Union
import mimetypes
from pydantic import BaseModel
from datetime import datetime, timedelta
import asyncio
import zipfile, io
from starlette.responses import HTMLResponse
from starlette.requests import Request
from pathlib import Path
import aiofiles
from fastapi.templating import Jinja2Templates

router = APIRouter()

# 模板目录配置
TEMPLATES_DIR = os.path.join(PATHS["TEMPLATES_DIR"])
templates = Jinja2Templates(directory=TEMPLATES_DIR)

class FunctionManager:
    @staticmethod
    async def load_function_info():
        functions_info = {}
        apps_dir = PATHS["APPS_DIR"]
        
        for item in os.listdir(apps_dir):
            if os.path.isdir(os.path.join(apps_dir, item)) and not item.startswith('__'):
                try:
                    intro_path = os.path.join(apps_dir, item, 'intro.md')
                    if os.path.exists(intro_path):
                        with open(intro_path, "r", encoding='utf-8') as f:
                            functions_info[item] = {
                                "name": f.read(),
                                "path": f"/function/{item}"
                            }
                except Exception as e:
                    logger.error(f"Error loading function info for {item}: {e}")
        
        return functions_info

    @staticmethod
    async def add_new_route(function_name: str):
        """添加新路由，如果路由已存在则不添加"""
        route_path = f"/function/{function_name}"
        
        try:
            # 读取现有路由
            existing_routes = set()
            if os.path.exists(PATHS["ROUTES_FILE"]):
                with open(PATHS["ROUTES_FILE"], "r", encoding='utf-8') as f:
                    existing_routes = {line.strip() for line in f if line.strip()}
            
            # 如果路由已存在，返回False
            if route_path in existing_routes:
                return False
            
            # 如果是新路由，添加到文件
            with open(PATHS["ROUTES_FILE"], "a", encoding='utf-8') as f:
                f.write(f"{route_path}\n")
            
            return True
            
        except Exception as e:
            logger.error(f"Error adding new route: {e}")
            return False

    @staticmethod
    async def clean_routes():
        """清理不存在函数的路由"""
        try:
            # 获取当前所有函数目录
            apps_dir = PATHS["APPS_DIR"]
            existing_functions = {
                f"function/{item}" for item in os.listdir(apps_dir) 
                if os.path.isdir(os.path.join(apps_dir, item)) and not item.startswith('__')
            }
            
            # 读取现有路由
            if os.path.exists(PATHS["ROUTES_FILE"]):
                with open(PATHS["ROUTES_FILE"], "r", encoding='utf-8') as f:
                    routes = {line.strip() for line in f if line.strip()}
                
                # 只保留存在的函数路由
                valid_routes = {route for route in routes if route.split('/')[-1] in existing_functions}
                
                # 写回文件
                with open(PATHS["ROUTES_FILE"], "w", encoding='utf-8') as f:
                    for route in sorted(valid_routes):
                        f.write(f"{route}\n")
        
        except Exception as e:
            logger.error(f"Error cleaning routes: {e}")

    @staticmethod
    async def check_and_install_dependencies():
        """检查并安装所有函数的依赖"""
        try:
            # 读取主requirements.txt
            main_req_path = os.path.join(PATHS["BASE_DIR"], "requirements.txt")
            main_requirements = set()
            if os.path.exists(main_req_path):
                with open(main_req_path, "r", encoding='utf-8') as f:
                    for line in f:
                        if line.strip() and not line.startswith('#'):
                            # 提取包名和版本要求
                            parts = line.strip().split('>=')
                            if len(parts) > 1:
                                main_requirements.add((parts[0], parts[1]))
                            else:
                                main_requirements.add((parts[0], None))
            
            # 检查每个函数的依赖
            new_requirements = set()
            conflict_requirements = set()
            
            apps_dir = PATHS["APPS_DIR"]
            for item in os.listdir(apps_dir):
                if os.path.isdir(os.path.join(apps_dir, item)) and not item.startswith('__'):
                    req_path = os.path.join(apps_dir, item, "requirements.txt")
                    if os.path.exists(req_path):
                        with open(req_path, "r", encoding='utf-8') as f:
                            for line in f:
                                if line.strip() and not line.startswith('#'):
                                    # 检查是否有版本要求
                                    parts = line.strip().split('>=')
                                    pkg_name = parts[0]
                                    pkg_version = parts[1] if len(parts) > 1 else None
                                    
                                    # 检查是否在主依赖中
                                    main_pkg = next((p for p in main_requirements if p[0] == pkg_name), None)
                                    
                                    if not main_pkg:
                                        new_requirements.add((pkg_name, pkg_version))
                                    elif pkg_version and main_pkg[1] and pkg_version > main_pkg[1]:
                                        conflict_requirements.add((pkg_name, pkg_version, main_pkg[1]))
            
            result = {
                "status": "success",
                "message": "依赖环境检查完成",
                "new_deps": [],
                "conflicts": []
            }
            
            # 处理冲突的依赖
            if conflict_requirements:
                conflict_msgs = []
                for pkg, new_ver, old_ver in conflict_requirements:
                    msg = f"{pkg}: 需要 >={new_ver}，但当前为 >={old_ver}"
                    conflict_msgs.append(msg)
                result["conflicts"] = conflict_msgs
                result["status"] = "conflict"
                result["message"] = "存在依赖冲突"
            
            # 安装新依赖
            if new_requirements:
                result["message"] = "正在安装新依赖..."
                for pkg, version in new_requirements:
                    req = f"{pkg}>={version}" if version else pkg
                    try:
                        subprocess.check_call(["pip", "install", req])
                        result["new_deps"].append(req)
                    except subprocess.CalledProcessError as e:
                        result["status"] = "error"
                        result["message"] = f"安装依赖 {req} 失败: {str(e)}"
                        return result
                
                # 更新主requirements.txt
                with open(main_req_path, "a", encoding='utf-8') as f:
                    for pkg, version in new_requirements:
                        f.write(f"\n{pkg}>={version}" if version else f"\n{pkg}")
                
                result["message"] = "新依赖安装完成"
            
            return result
            
        except Exception as e:
            return {
                "status": "error",
                "message": f"依赖检查过程出错: {str(e)}",
                "new_deps": [],
                "conflicts": []
            }

@router.get("/")
async def admin_page(request: Request):
    return templates.TemplateResponse("sysinfo.html", {"request": request, "page": "sysinfo"})

@router.get("/sysinfo")
async def sysinfo_page(request: Request):
    return templates.TemplateResponse("sysinfo.html", {"request": request, "page": "sysinfo"})

@router.get("/apidebug")
async def apidebug_page(request: Request):
    return templates.TemplateResponse("apidebug.html", {"request": request, "page": "apidebug"})

@router.get("/log")
async def log_page(request: Request):
    return templates.TemplateResponse("log.html", {"request": request, "page": "log"})

@router.get("/file")
async def file_page(request: Request):
    return templates.TemplateResponse("file.html", {"request": request, "page": "file"})

@router.post("/upload_function")
async def upload_function(files: List[UploadFile] = File(...)):
    try:
        if not files or len(files) == 0:
            raise HTTPException(status_code=400, detail="No files uploaded")

        # 获取函数名（从第一个文件的路径中提取）
        first_file_path = files[0].filename
        if '/' not in first_file_path:
            raise HTTPException(status_code=400, detail="Invalid file structure")
            
        function_name = first_file_path.split('/')[0]
        function_path = os.path.join(PATHS["APPS_DIR"], function_name)

        # 如果目录已存在，先删除
        if os.path.exists(function_path):
            shutil.rmtree(function_path)

        # 创建必要的目录
        os.makedirs(function_path, exist_ok=True)

        # 保存文件
        for file in files:
            try:
                # 获取相对路径
                relative_path = file.filename
                if not relative_path:
                    continue

                # 构建完整路径
                full_path = os.path.join(PATHS["APPS_DIR"], relative_path)
                os.makedirs(os.path.dirname(full_path), exist_ok=True)

                # 读取并保存文件内容
                content = await file.read()
                with open(full_path, 'wb') as f:
                    f.write(content)
                
                # 重置文件指针
                await file.seek(0)
                
            except Exception as e:
                logger.error(f"Error saving file {file.filename}: {e}")
                # 如果保存失败，清理已创建的目录
                if os.path.exists(function_path):
                    shutil.rmtree(function_path)
                raise HTTPException(
                    status_code=500, 
                    detail=f"Error saving file {file.filename}: {str(e)}"
                )

        # 添加路由
        route_path = f"/function/{function_name}"
        with open(PATHS["ROUTES_FILE"], "a", encoding='utf-8') as f:
            f.write(f"{route_path}\n")
        
        return {
            "status": "success", 
            "message": "Function uploaded successfully",
            "function_name": function_name
        }
        
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Error uploading function: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/refresh_functions")
async def refresh_functions():
    try:
        # 检查并安装新依赖
        new_deps = await FunctionManager.check_and_install_dependencies()
        if new_deps:
            logger.info(f"Installed new dependencies: {new_deps}")

        # 获取当前所有函数
        apps_dir = PATHS["APPS_DIR"]
        new_routes = []
        current_functions = set()

        # 读取已存在的路由
        existing_routes = set()
        if os.path.exists(PATHS["ROUTES_FILE"]):
            with open(PATHS["ROUTES_FILE"], "r") as f:
                existing_routes = set(line.strip() for line in f)

        # 扫描apps目录
        for item in os.listdir(apps_dir):
            if os.path.isdir(os.path.join(apps_dir, item)) and not item.startswith('__'):
                current_functions.add(item)
                route_path = f"/function/{item}"
                
                # 如果是新路由，添加到main.py
                if route_path not in existing_routes:
                    new_routes.append(route_path)
                    
                    # 检查函数是否需要filename参数
                    module_path = os.path.join(apps_dir, item, "function.py")
                    if os.path.exists(module_path):
                        spec = importlib.util.spec_from_file_location(item, module_path)
                        module = importlib.util.module_from_spec(spec)
                        spec.loader.exec_module(module)
                        func = getattr(module, item)
                        
                        import inspect
                        params = inspect.signature(func).parameters
                        
                        # 根据是否需要filename参数生成不同的路由代码
                        if 'filename' in params:
                            route_code = f'''
@app.get("{route_path}")
async def call_{item}(filename: str):
    module = importlib.import_module("apps.{item}.function")
    return module.{item}(filename)
'''
                        else:
                            route_code = f'''
@app.get("{route_path}")
async def call_{item}():
    module = importlib.import_module("apps.{item}.function")
    return module.{item}()
'''
                        
                        # 添加新路由到main.py
                        with open("main.py", "a", encoding='utf-8') as f:
                            f.write(route_code)

        # 更新routes.txt
        if new_routes:
            with open(PATHS["ROUTES_FILE"], "w") as f:
                for route in sorted(existing_routes.union(new_routes)):
                    f.write(f"{route}\n")

        # 重新加载所有函数信息
        functions_info = await FunctionManager.load_function_info()
        
        return {
            "status": "success",
            "new_routes": new_routes,
            "new_dependencies": new_deps,
            "functions": functions_info
        }
    except Exception as e:
        logger.error(f"Error refreshing functions: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/get_function_files/{function_name}")
async def get_function_files(function_name: str):
    try:
        function_path = os.path.join(PATHS["APPS_DIR"], function_name)
        if not os.path.exists(function_path):
            raise HTTPException(status_code=404, detail="Function not found")
        
        # 读取必需的文件
        files = {}
        for file_name in ["function.py", "config.json", "intro.md"]:
            file_path = os.path.join(function_path, file_name)
            if os.path.exists(file_path):
                with open(file_path, "r", encoding='utf-8') as f:
                    files[file_name.split('.')[0]] = f.read()
            else:
                files[file_name.split('.')[0]] = ""
        
        # 获取其他文件和目录列表
        other_files = []
        other_dirs = []
        for root, dirs, filenames in os.walk(function_path):
            # 跳过 __pycache__ 目录
            if '__pycache__' in dirs:
                dirs.remove('__pycache__')
            
            # 添加目录
            for dir_name in dirs:
                full_path = os.path.join(root, dir_name)
                rel_path = os.path.relpath(full_path, function_path)
                other_dirs.append(rel_path)
            
            # 添加文件（只加真正的文件）
            for filename in filenames:
                if filename not in ['function.py', 'config.json', 'intro.md']:
                    full_path = os.path.join(root, filename)
                    if os.path.isfile(full_path):
                        rel_path = os.path.relpath(full_path, function_path)
                        other_files.append(rel_path)
        
        files['other_files'] = other_files
        files['other_dirs'] = other_dirs
        
        return files
        
    except Exception as e:
        logger.error(f"Error getting function files: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/save_function/{function_name}")
async def save_function(function_name: str, files: dict):
    try:
        function_path = os.path.join(PATHS["APPS_DIR"], function_name)
        if not os.path.exists(function_path):
            raise HTTPException(status_code=404, detail="Function not found")
        
        # 保存文件
        for file_name, content in files.items():
            file_path = os.path.join(function_path, f"{file_name}.{'py' if file_name == 'function' else 'json' if file_name == 'config' else 'md'}")
            with open(file_path, "w", encoding='utf-8') as f:
                f.write(content)
        
        # 检查并安装依赖
        deps_result = await FunctionManager.check_and_install_dependencies()
        if deps_result["status"] == "error":
            return {
                "status": "error",
                "message": f"保存成功，但依赖安装失败：{deps_result['message']}"
            }
        
        return {
            "status": "success",
            "message": "函数保存成功" + ("，并安装了新依赖" if deps_result.get("new_deps") else "")
        }
        
    except Exception as e:
        logger.error(f"Error saving function: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/create_function")
async def create_function(data: dict):
    try:
        function_name = data.get("function_name")
        files = data.get("files", {})
        
        if not function_name or not files:
            raise HTTPException(status_code=400, detail="Missing required data")
        
        function_path = os.path.join(PATHS["APPS_DIR"], function_name)
        
        # 检查函数是否已存在
        if os.path.exists(function_path):
            raise HTTPException(status_code=400, detail="Function already exists")
        
        # 创建函数目录
        os.makedirs(function_path, exist_ok=True)

        # 保存文件
        file_mapping = {
            'function': 'function.py',
            'config': 'config.json',
            'intro': 'intro.md'
        }
        
        for file_type, content in files.items():
            if file_type in file_mapping:
                file_path = os.path.join(function_path, file_mapping[file_type])
                with open(file_path, "w", encoding='utf-8') as f:
                    f.write(content)
        # 自动生成 requirements.txt
        req_path = os.path.join(function_path, 'requirements.txt')
        with open(req_path, 'w', encoding='utf-8') as f:
            f.write('# 在此填写本函数所需的依赖包\n')
        # 自动生成 readme.md
        readme_path = os.path.join(function_path, 'readme.md')
        with open(readme_path, 'w', encoding='utf-8') as f:
            f.write('# 详细说明\n在这里补充函数的详细介绍、参数说明、返回值说明、使用示例等。\n')
        
        # 添加路由
        route_path = f"/function/{function_name}"
        with open(PATHS["ROUTES_FILE"], "a", encoding='utf-8') as f:
            f.write(f"{route_path}\n")
        
        # 检查并安装依赖
        deps_result = await FunctionManager.check_and_install_dependencies()
        if deps_result["status"] == "error":
            return {
                "status": "error",
                "message": f"函数创建成功，但依赖安装失败：{deps_result['message']}"
            }
        
        return {
            "status": "success",
            "message": "函数创建成功" + ("，并安装了新依赖" if deps_result.get("new_deps") else "")
        }
        
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Error creating function: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/delete_function/{function_name}")
async def delete_function(function_name: str):
    try:
        function_path = os.path.join(PATHS["APPS_DIR"], function_name)
        if not os.path.exists(function_path):
            raise HTTPException(status_code=404, detail="Function not found")
        
        # 删除函数目录
        shutil.rmtree(function_path)
        
        # 从routes.txt中删除路由
        if os.path.exists(PATHS["ROUTES_FILE"]):
            with open(PATHS["ROUTES_FILE"], "r", encoding='utf-8') as f:
                routes = [line.strip() for line in f if line.strip()]
            
            # 过滤掉要删除的路由
            routes = [route for route in routes if not route.endswith(f"/{function_name}")]
            
            # 写回文件
            with open(PATHS["ROUTES_FILE"], "w", encoding='utf-8') as f:
                for route in routes:
                    f.write(f"{route}\n")
        
        return {
            "status": "success",
            "message": f"函数 {function_name} 已删除"
        }
        
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Error deleting function: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/upload_function_file/{function_name}")
async def upload_function_file(
    function_name: str,
    file: UploadFile = File(...),
    relative_path: str = Form(...)
):
    try:
        function_path = os.path.join(PATHS["APPS_DIR"], function_name)
        if not os.path.exists(function_path):
            raise HTTPException(status_code=404, detail="Function not found")
        
        # 检查文件名是否合法
        if file.filename in ['function.py', 'config.json', 'intro.md']:
            raise HTTPException(status_code=400, detail="Cannot overwrite core function files")
        
        # 构建目标路径
        target_path = os.path.join(function_path, relative_path)
        os.makedirs(os.path.dirname(target_path), exist_ok=True)
        
        # 保存文件
        content = await file.read()
        with open(target_path, 'wb') as f:
            f.write(content)
        
        return {
            "status": "success",
            "message": f"文件 {file.filename} 上传成功"
        }
        
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Error uploading function file: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/delete_function_file/{function_name}")
async def delete_function_file(
    function_name: str,
    file_path: str
):
    try:
        function_path = os.path.join(PATHS["APPS_DIR"], function_name)
        if not os.path.exists(function_path):
            raise HTTPException(status_code=404, detail="Function not found")
        
        # 构建完整路径
        full_path = os.path.join(function_path, file_path)
        
        # 检查是否是核心文件
        if os.path.basename(file_path) in ['function.py', 'config.json', 'intro.md']:
            raise HTTPException(status_code=400, detail="Cannot delete core function files")
        
        # 检查文件是否存在
        if not os.path.exists(full_path):
            raise HTTPException(status_code=404, detail="File not found")
        
        # 删除文件或文件夹
        if os.path.isfile(full_path):
            os.remove(full_path)
        elif os.path.isdir(full_path):
            shutil.rmtree(full_path)
        else:
            raise HTTPException(status_code=404, detail="File or directory not found")
        
        # 如果目录为空，删除目录
        dir_path = os.path.dirname(full_path)
        if os.path.exists(dir_path) and not os.listdir(dir_path):
            os.rmdir(dir_path)
        
        return {
            "status": "success",
            "message": f"文件 {file_path} 已删除"
        }
        
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Error deleting function file: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/get_function_file_content/{function_name}")
async def get_function_file_content(function_name: str, file_path: str):
    try:
        function_path = os.path.join(PATHS["APPS_DIR"], function_name)
        if not os.path.exists(function_path):
            raise HTTPException(status_code=404, detail="Function not found")
        full_path = os.path.join(function_path, file_path)
        if not os.path.exists(full_path):
            raise HTTPException(status_code=404, detail="File not found")
        ext = os.path.splitext(full_path)[1].lower()
        if ext in [".png", ".jpg", ".jpeg", ".svg"]:
            mime, _ = mimetypes.guess_type(full_path)
            if not mime:
                mime = "application/octet-stream"
            return FileResponse(full_path, media_type=mime)
        else:
            with open(full_path, "r", encoding="utf-8") as f:
                content = f.read()
            return {"type": "text", "content": content}
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Error getting file content: {e}")
        raise HTTPException(status_code=500, detail=str(e))

class SaveFileRequest(BaseModel):
    file_path: str
    content: str

@router.post("/save_function_file/{function_name}")
async def save_function_file(function_name: str, req: SaveFileRequest):
    try:
        function_path = os.path.join(PATHS["APPS_DIR"], function_name)
        if not os.path.exists(function_path):
            raise HTTPException(status_code=404, detail="Function not found")
        full_path = os.path.join(function_path, req.file_path)
        # 只允许保存文本文件
        ext = os.path.splitext(full_path)[1].lower()
        if ext not in [".py", ".json", ".yaml", ".yml", ".txt", ".md", ".csv", ".log"]:
            raise HTTPException(status_code=400, detail="只允许保存文本文件")
        with open(full_path, "w", encoding="utf-8") as f:
            f.write(req.content)
        return {"status": "success", "message": f"文件 {req.file_path} 已保存"}
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Error saving file: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/create_function_item/{function_name}")
async def create_function_item(function_name: str, data: dict):
    try:
        item_type = data.get("type") # 'folder' or 'file'
        item_path = data.get("path") # Relative path from function directory
        if not item_type or not item_path:
            raise HTTPException(status_code=400, detail="Missing type or path")
        function_path = os.path.join(PATHS["APPS_DIR"], function_name)
        if not os.path.exists(function_path):
            raise HTTPException(status_code=404, detail="Function not found")
        full_path = os.path.join(function_path, item_path)
        if os.path.exists(full_path):
            raise HTTPException(status_code=400, detail=f"{item_type.capitalize()} already exists")
        if item_type == 'folder':
            os.makedirs(full_path)
            message = "文件夹创建成功"
        elif item_type == 'file':
            os.makedirs(os.path.dirname(full_path), exist_ok=True)  # 确保父目录存在
            with open(full_path, 'w') as f:
                pass
            message = "文件创建成功"
        else:
            raise HTTPException(status_code=400, detail="Invalid item type")
        return {"status": "success", "message": message, "path": item_path}
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Error creating function item: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/call_stats")
async def call_stats_page():
    try:
        with open(os.path.join(PATHS["TEMPLATES_DIR"], "call_stats", "call_stats.html"), "r", encoding='utf-8') as f:
            return HTMLResponse(f.read())
    except Exception as e:
        logger.error(f"Error loading call stats page: {e}")
        raise HTTPException(status_code=500, detail="Error loading call stats page")

@router.get("/call_stats_data")
async def call_stats_data():
    import json
    stats_file = os.path.join(PATHS["BASE_DIR"], "call_stats.json")
    if os.path.exists(stats_file):
        with open(stats_file, "r", encoding="utf-8") as f:
            stats = json.load(f)
    else:
        stats = {"total": 0, "functions": {}, "history_day": {}, "history_hour": {}}
    # 取最近7天的天数据
    today = datetime.now().date()
    days = [(today - timedelta(days=i)).strftime('%Y-%m-%d') for i in range(6, -1, -1)]
    history_day = {d: stats.get("history_day", {}).get(d, {}) for d in days}
    # 取当天24小时数据
    now = datetime.now()
    day_str = now.strftime('%Y-%m-%d')
    hours = [f"{day_str}-{str(h).zfill(2)}" for h in range(24)]
    history_hour = {h: stats.get("history_hour", {}).get(h, {}) for h in hours}
    return JSONResponse({
        "total": stats.get("total", 0),
        "functions": stats.get("functions", {}),
        "history_day": history_day,
        "history_hour": history_hour
    })

@router.get("/logs")
async def get_logs(tail: int = 200, level: str = '', download: int = 0):
    log_path = os.path.join(PATHS["LOGS_DIR"], "app.log")
    if not os.path.exists(log_path):
        return {"logs": ""}
    # 兼容二进制日志
    try:
        with open(log_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
    except UnicodeDecodeError:
        with open(log_path, "rb") as f:
            raw = f.read()
        try:
            lines = raw.decode("gbk").splitlines(keepends=True)
        except Exception:
            lines = raw.decode(errors="ignore").splitlines(keepends=True)
    # 日志级别过滤
    levels = [l.strip().lower() for l in level.split(",") if l.strip()]
    if levels:
        def match_level(line):
            for lv in levels:
                if f"[{lv.upper()}]" in line or f"[{lv.capitalize()}]" in line:
                    return True
            return False
        lines = [l for l in lines if match_level(l)]
    logs = "".join(lines[-tail:])
    if download:
        from io import BytesIO
        buf = BytesIO(logs.encode("utf-8", errors="ignore"))
        return StreamingResponse(buf, media_type="text/plain", headers={"Content-Disposition": "attachment; filename=app.log"})
    return {"logs": logs}

@router.websocket("/logs/stream")
async def logs_stream(ws: WebSocket):
    await ws.accept()
    log_path = os.path.join(PATHS["LOGS_DIR"], "app.log")
    try:
        last_size = 0
        buffer = []
        while True:
            if not os.path.exists(log_path):
                await asyncio.sleep(1)
                continue
            try:
                with open(log_path, "rb") as f:
                    f.seek(0, 2)
                    size = f.tell()
                    if size < last_size:
                        last_size = 0
                        buffer = []
                    if size > last_size:
                        f.seek(last_size)
                        data = f.read().decode("utf-8", errors="ignore")
                        lines = data.splitlines(keepends=True)
                        buffer.extend(lines)
                        # Send lines individually or in chunks if needed
                        await ws.send_text(''.join(lines)) # Sending as a single chunk
                        last_size = size
            except Exception:
                # Handle exceptions during file reading or sending
                pass # Continue loop on error
            await asyncio.sleep(1)
    except (WebSocketDisconnect, asyncio.CancelledError):
        # This block is executed when the WebSocket connection is closed
        logger.info("Log stream WebSocket disconnected or cancelled.") # Log on disconnection or cancellation
        return
    except Exception as e:
        # Log any other unexpected exceptions
        logger.error(f"Log stream WebSocket error: {e}")

@router.get("/logs/list")
async def list_logs():
    log_dir = PATHS["LOGS_DIR"]
    if not os.path.exists(log_dir):
        return {"logs": []}
    files = [f for f in os.listdir(log_dir) if f.endswith('.log')]
    files.sort(reverse=True)
    return {"logs": files}

@router.get("/logs/file")
async def get_log_file(name: str):
    log_dir = PATHS["LOGS_DIR"]
    file_path = os.path.join(log_dir, name)
    if not os.path.exists(file_path):
        return {"logs": ""}
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
    except UnicodeDecodeError:
        with open(file_path, "rb") as f:
            raw = f.read()
        try:
            content = raw.decode("gbk")
        except Exception:
            content = raw.decode(errors="ignore")
    return {"logs": content}

@router.get("/files_tree")
async def files_tree():
    def walk_dir(path):
        items = []
        for name in os.listdir(path):
            full_path = os.path.join(path, name)
            if os.path.isdir(full_path):
                items.append({
                    "name": name,
                    "type": "folder",
                    "children": walk_dir(full_path)
                })
            else:
                items.append({
                    "name": name,
                    "type": "file"
                })
        return items
    apps_dir = PATHS["APPS_DIR"]
    return walk_dir(apps_dir)

@router.get("/list_dir")
async def list_dir(path: str = ""):
    """
    列出 apps 目录下指定子目录内容，返回文件名、类型、大小、修改时间。
    path: 相对 apps 的路径，如 "" 表示 apps 根目录，"foo/bar" 表示 apps/foo/bar
    """
    base_dir = PATHS["APPS_DIR"]
    target_dir = os.path.normpath(os.path.join(base_dir, path))
    # 防止越界
    if not target_dir.startswith(base_dir):
        raise HTTPException(status_code=400, detail="路径越界")
    if not os.path.exists(target_dir) or not os.path.isdir(target_dir):
        raise HTTPException(status_code=404, detail="目录不存在")
    items = []
    for name in os.listdir(target_dir):
        full_path = os.path.join(target_dir, name)
        stat = os.stat(full_path)
        item = {
            "name": name,
            "type": "folder" if os.path.isdir(full_path) else "file",
            "size": None if os.path.isdir(full_path) else stat.st_size,
            "mtime": datetime.fromtimestamp(stat.st_mtime).strftime("%Y/%m/%d %H:%M:%S")
        }
        items.append(item)
    # 文件夹优先
    items.sort(key=lambda x: (x["type"] != "folder", x["name"]))
    return items

@router.get('/download_file')
async def download_file(path: str):
    base_dir = PATHS['APPS_DIR']
    target = os.path.normpath(os.path.join(base_dir, path))
    if not target.startswith(base_dir):
        raise HTTPException(status_code=400, detail='路径越界')
    if not os.path.exists(target):
        raise HTTPException(status_code=404, detail='文件不存在')
    if os.path.isdir(target):
        # 文件夹打包zip
        mem = io.BytesIO()
        with zipfile.ZipFile(mem, 'w', zipfile.ZIP_DEFLATED) as zf:
            for root, dirs, files in os.walk(target):
                for file in files:
                    abs_path = os.path.join(root, file)
                    rel_path = os.path.relpath(abs_path, base_dir)
                    zf.write(abs_path, rel_path)
        mem.seek(0)
        headers = {
            'Content-Disposition': f'attachment; filename="{os.path.basename(target)}.zip"'
        }
        return StreamingResponse(mem, media_type='application/zip', headers=headers)
    else:
        return FileResponse(target, filename=os.path.basename(target))

@router.delete('/delete_file')
async def delete_file(path: str):
    base_dir = PATHS['APPS_DIR']
    target = os.path.normpath(os.path.join(base_dir, path))
    if not target.startswith(base_dir):
        raise HTTPException(status_code=400, detail='路径越界')
    if not os.path.exists(target):
        raise HTTPException(status_code=404, detail='文件不存在')
    if os.path.isdir(target):
        shutil.rmtree(target)
    else:
        os.remove(target)
    return {'status': 'success'}

@router.post('/rename_file')
async def rename_file(path: str = Form(...), new_name: str = Form(...)):
    base_dir = PATHS['APPS_DIR']
    target = os.path.normpath(os.path.join(base_dir, path))
    if not target.startswith(base_dir):
        raise HTTPException(status_code=400, detail='路径越界')
    if not os.path.exists(target):
        raise HTTPException(status_code=404, detail='文件不存在')
    new_path = os.path.join(os.path.dirname(target), new_name)
    if os.path.exists(new_path):
        raise HTTPException(status_code=400, detail='新名称已存在')
    os.rename(target, new_path)
    return {'status': 'success'}

class CreateItemRequest(BaseModel):
    path: str
    name: str
    type: str

@router.post('/create_file_or_folder')
async def create_file_or_folder(req: CreateItemRequest):
    base_dir = PATHS['APPS_DIR']
    parent = os.path.normpath(os.path.join(base_dir, req.path))
    if not parent.startswith(base_dir):
        raise HTTPException(status_code=400, detail='路径越界')
    if not os.path.exists(parent):
        raise HTTPException(status_code=404, detail='父目录不存在')
    target = os.path.join(parent, req.name)
    if os.path.exists(target):
        raise HTTPException(status_code=400, detail='已存在同名文件或文件夹')
    if req.type == 'folder':
        os.makedirs(target)
    elif req.type == 'file':
        with open(target, 'w', encoding='utf-8') as f:
            pass
    elif req.type == 'project':
        os.makedirs(target) # Create the project directory
        # Create default files for a new project
        default_files_content = {
            'function.py': '# Add your function code here\n\ndef function_name():\n    pass\n',
            'config.json': '{\n    "name": "",\n    "description": "",\n    "url": "",\n    "method": "GET",\n    "parameters": []\n}\n',
            'intro.md': '# Function Introduction\n\nDescribe your function here.\n',
            'requirements.txt': '# Add any dependencies here\n'
        }
        for filename, content in default_files_content.items():
            file_path = os.path.join(target, filename)
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
        # Optionally add the new function to routes.txt
        route_path = f"/function/{req.name}"
        routes_file = PATHS['ROUTES_FILE']
        if os.path.exists(routes_file):
            with open(routes_file, 'a', encoding='utf-8') as f:
                f.write(f"\n{route_path}")
        else:
            # If routes.txt doesn't exist, create it
            with open(routes_file, 'w', encoding='utf-8') as f:
                f.write(route_path)
    else:
        raise HTTPException(status_code=400, detail='type参数错误')
    return {'status': 'success'}

@router.post('/upload_file')
async def upload_file(
    path: str = Form(...),
    files: Union[List[UploadFile], UploadFile] = File(...)
):
    logger.info(f"收到上传请求 path={path}, files={getattr(files, 'filename', None) or [f.filename for f in files]}")
    base_dir = PATHS['APPS_DIR']
    if path in ("", ".", "/"):
        target_dir = base_dir
    else:
        target_dir = os.path.normpath(os.path.join(base_dir, path))
    if not target_dir.startswith(base_dir):
        logger.error(f"路径越界: {target_dir}")
        raise HTTPException(status_code=400, detail='路径越界')
    # 兼容单文件
    if isinstance(files, UploadFile):
        files = [files]
    try:
        if not files or not files[0].filename:
            raise HTTPException(status_code=400, detail="没有选择文件夹")
        folder_name = files[0].filename.split('/')[0]
        folder_path = os.path.join(target_dir, folder_name)
        if os.path.exists(folder_path):
            shutil.rmtree(folder_path)
        os.makedirs(folder_path, exist_ok=True)
        for file in files:
            relative_path = file.filename
            if not relative_path:
                continue
            full_path = os.path.join(target_dir, relative_path)
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            content = await file.read()
            with open(full_path, 'wb') as f:
                f.write(content)
            logger.info(f"文件保存成功: {full_path}")
        return {
            'status': 'success',
            'message': f'文件夹 {folder_name} 上传成功',
            'path': os.path.relpath(folder_path, base_dir)
        }
    except Exception as e:
        logger.error(f"文件夹上传失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f'文件夹上传失败: {str(e)}')

# New endpoint to get file content
@router.get("/get_file_content")
async def get_file_content(path: str):
    logger.info(f"Received get_file_content request for path: {path}")
    
    # Ensure the path is within the 'apps' directory
    base_dir = Path("./apps")
    file_path = base_dir / path
    
    # Basic security check: prevent directory traversal
    if not str(file_path.resolve()).startswith(str(base_dir.resolve())):
        logger.error(f"Path traversal attempt detected for get_file_content: {file_path}")
        raise HTTPException(status_code=400, detail="Invalid path.")

    if not file_path.is_file():
        logger.error(f"Target file not found or is not a file for get_file_content: {file_path}")
        raise HTTPException(status_code=404, detail="File not found or is not a file.")

    try:
        logger.info(f"Attempting to open file for reading: {file_path}")
        async with aiofiles.open(file_path, mode='r', encoding='utf-8') as f:
            logger.info("File opened successfully for reading, attempting to read content.")
            content = await f.read()
        logger.info("File content read successfully.")
        return JSONResponse(content={"content": content})
    except Exception as e:
        logger.error(f"Error reading file {file_path} for get_file_content: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error reading file: {e}")

@router.post("/save_file")
async def save_file(path: str = Form(...), content: str = Form(...)):
    logger.info(f"Received save_file request for path: {path}")
    # Log content snippet for debugging (avoiding logging very large content)
    logger.info(f"Content snippet: {content[:100]}{'...' if len(content) > 100 else ''}")
    
    # Ensure the path is within the 'apps' directory
    base_dir = Path("./apps")
    file_path = base_dir / path

    # Correct comparison for WindowsPath objects
    if not str(file_path.resolve()).startswith(str(base_dir.resolve())):
        logger.error(f"Path traversal attempt detected: {file_path}")
        raise HTTPException(status_code=400, detail="Invalid path.")

    if not file_path.is_file():
        logger.error(f"Target file not found or is not a file: {file_path}")
        raise HTTPException(status_code=404, detail="File not found or is not a file.")

    try:
        logger.info(f"Attempting to open file for writing: {file_path}")
        async with aiofiles.open(file_path, mode='w', encoding='utf-8', newline='') as f:
            logger.info("File opened successfully, attempting to write.")
            await f.write(content)
        logger.info(f"File saved successfully: {file_path}")
        return JSONResponse(content={"status": "success"})
    except Exception as e:
        logger.error(f"Error saving file {file_path}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error saving file: {e}")