from fastapi import APIRouter, UploadFile, HTTPException, BackgroundTasks, File, Form
from fastapi.responses import HTMLResponse
import os
import importlib.util
import sys
import shutil
from utils.logger import logger
from config import PATHS
import pkg_resources
import subprocess
from typing import List

router = APIRouter()

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
                                "description": f.read(),
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
async def admin_page():
    try:
        with open(os.path.join(PATHS["TEMPLATES_DIR"], "index.html"), "r", encoding='utf-8') as f:
            return HTMLResponse(f.read())
    except Exception as e:
        logger.error(f"Error loading admin page: {e}")
        raise HTTPException(status_code=500, detail="Error loading admin page")

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

        # 检查是否包含必要文件
        file_paths = [file.filename for file in files]
        required_files = [
            f"{function_name}/config.json",
            f"{function_name}/function.py",
            f"{function_name}/intro.md"
        ]
        
        missing_files = [f for f in required_files if not any(f in path for path in file_paths)]
        
        if missing_files:
            raise HTTPException(
                status_code=400, 
                detail=f"Missing required files: {', '.join(missing_files)}"
            )

        # 如果目录已存在，先删除
        if os.path.exists(function_path):
            shutil.rmtree(function_path)

        # 创建必要的目录
        os.makedirs(function_path, exist_ok=True)
        os.makedirs(os.path.join(function_path, 'xlsx_files'), exist_ok=True)

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