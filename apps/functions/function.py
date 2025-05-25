import os
import json
from config import PATHS
from fastapi import HTTPException

def functions():
    """
    获取所有可用函数列表
    """
    try:
        functions = []
        apps_dir = PATHS["APPS_DIR"]
        
        for item in os.listdir(apps_dir):
            if os.path.isdir(os.path.join(apps_dir, item)) and not item.startswith('__'):
                config_path = os.path.join(apps_dir, item, 'config.json')
                if os.path.exists(config_path):
                    with open(config_path, 'r', encoding='utf-8') as f:
                        config = json.load(f)
                        functions.append({
                            "name": item,
                            "url": config["url"],
                            "method": config["method"],
                            "display_name": config.get("name", item),
                            "parameters": config["parameters"]
                        })
        
        return {"functions": functions}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) 